"""Local-only setup application: python -m construct_lab.server."""
import argparse
import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs

from .library import LibraryStore, MAX_PDF, render_page
from .extraction import ExtractionStore, Connection
from .store import Conflict
from .definitions import DefinitionStore
from .learning import LearningStore
from .research_loop import ResearchLoopStore
from .run_report import render_run_report
from .walkthrough import render_walkthrough, PILOT
from .backup import create_backup, list_backups, acquire_lock


def make_server(database, port=8765):
    database = Path(database).resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    server_lock = acquire_lock(database)
    store = ResearchLoopStore(database)
    connection = Connection()
    try:
        with store.db:
            store.db.execute("UPDATE extraction_runs SET status='interrupted' WHERE status='running'")
        with store.db:
            store.db.execute("UPDATE loop_runs SET status='interrupted' WHERE status='running'")
        store.seed_curiosity()
    finally:
        store.close()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log research titles or settings.

        def respond(self, status, body, content_type="application/json; charset=utf-8", attachment=False):
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'")
            if attachment:
                self.send_header("Content-Disposition", 'attachment; filename="construct-lab-project.json"')
            self.end_headers()
            self.wfile.write(data)

        def handle_request(self, write=False):
            self.connection.settimeout(90)
            path = urlsplit(self.path).path
            parts = path.strip("/").split("/")
            pdf_upload = write and len(parts) == 4 and parts[:2] == ["api", "projects"] and parts[3] == "papers"
            port = self.server.server_port
            allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            host = self.headers.get("Host", "")
            if host not in allowed_hosts:
                self.respond(403, {"error": "This application is available only on this computer"})
                return
            if write and (self.headers.get("Origin") != f"http://{host}" or
                          self.headers.get("X-Construct-Lab") != "local" or
                          self.headers.get("Content-Type", "").split(";")[0] != ("application/pdf" if pdf_upload else "application/json")):
                self.respond(403, {"error": "Open the local application to save settings"})
                return
            store = None
            try:
                body = {}
                if write:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= (MAX_PDF if pdf_upload else 150000):
                        raise ValueError("Request is empty or too large")
                    raw = self.rfile.read(length)
                    body = raw if pdf_upload else json.loads(raw)
                    if not pdf_upload and not isinstance(body, dict):
                        raise ValueError("Expected a settings object")
                if path == "/shell.js" and not write:
                    self.respond(200, Path(__file__).with_name("shell.js").read_bytes(), "text/javascript; charset=utf-8")
                    return
                if path in ("/", "/setup", "/library", "/review", "/extract", "/definitions", "/learning", "/coding", "/coding-guide", "/dashboard", "/rounds", "/novelty", "/saturation", "/demonstration", "/maintenance", "/etymology", "/research-loop") and not write:
                    page_file = {"/": "home.html", "/setup": "app.html", "/library": "library.html", "/review": "review.html", "/extract": "extract.html", "/definitions": "definitions.html", "/learning": "learning.html", "/coding": "coding.html", "/coding-guide": "coding-guide.html", "/dashboard": "dashboard.html", "/rounds": "rounds.html", "/novelty": "novelty.html", "/saturation": "saturation.html", "/demonstration": "demonstration.html", "/maintenance": "maintenance.html", "/etymology": "etymology.html", "/research-loop": "research-loop.html"}[path]
                    self.respond(200, Path(__file__).with_name(page_file).read_bytes() + b'<script src="/shell.js"></script>', "text/html; charset=utf-8")
                    return
                if path.startswith('/submission/') and not write:
                    name = path.rsplit('/', 1)[-1]
                    if name not in ('organization-science-proposal.docx', 'construct-lab-technical-supplement.docx') or path != '/submission/' + name:
                        raise KeyError('Document not found')
                    document = Path(__file__).with_name('submission') / name
                    if not document.is_file(): raise KeyError('Research drafts are distributed separately from this software release')
                    self.respond(200, document.read_bytes(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                    return
                store = ResearchLoopStore(database)
                if path == '/walkthrough' and not write:
                    project = parse_qs(urlsplit(self.path).query).get('project', [PILOT])[0]
                    self.respond(200, render_walkthrough(store, project).encode(), 'text/html; charset=utf-8')
                    return
                if len(parts) == 6 and parts[:2] == ['api','projects'] and parts[3] == 'runs' and parts[5] == 'report' and not write:
                    self.respond(200, render_run_report(store,parts[2],parts[4]).encode(), 'text/html; charset=utf-8')
                    return
                if len(parts) >= 4 and parts[:2] == ['api','projects'] and parts[3] == 'research-loop':
                    project = parts[2]
                    if len(parts) == 4 and not write:
                        result = store.research_loop(project)
                    elif len(parts) == 5 and write:
                        action = parts[4]
                        if action == 'preview': result = store.preview_loop(project, body)
                        elif action == 'execute': result = store.execute_loop(project, body, connection.snapshot() if body.get('mode') == 'live' else None)
                        elif action == 'evidence': result = store.add_loop_evidence(project, body)
                        elif action == 'search': result = store.search_evidence(project, body)
                        else: raise KeyError('Research action not found')
                    elif len(parts) == 6 and parts[5] == 'review' and write:
                        result = store.review_loop(project, parts[4], body)
                    else: raise KeyError('Research action not found')
                elif len(parts) == 4 and parts[:2] == ['api','projects'] and parts[3] == 'etymology':
                    result = store.save_etymology(parts[2], body) if write else store.etymology(parts[2])
                elif path == '/api/backups':
                    result = create_backup(database) if write else list_backups(database)
                elif path == '/api/shutdown' and write:
                    self.respond(200, {'stopped':True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                elif path == '/api/health' and not write:
                    result = {'app':'construct-lab', 'build':'research-loop-1'}
                elif path == '/api/navigation' and not write:
                    result = store.navigation()
                elif len(parts) == 4 and parts[:2] == ['api','projects'] and parts[3] == 'demonstration' and not write:
                    result = store.demonstration(parts[2])
                elif len(parts) == 4 and parts[:2] == ['api','projects'] and parts[3] == 'saturation':
                    result = store.save_saturation(parts[2], body) if write else store.saturation(parts[2])
                elif len(parts) == 4 and parts[:2] == ['api','projects'] and parts[3] == 'novelty':
                    result = store.save_novelty(parts[2], body) if write else store.novelty(parts[2])
                elif len(parts) == 4 and parts[:2] == ['api','projects'] and parts[3] == 'rounds':
                    result = store.save_round(parts[2], body) if write else store.rounds(parts[2])
                elif len(parts) == 4 and parts[:2] == ['api','projects'] and parts[3] == 'dashboard' and not write:
                    result = store.dashboard(parts[2])
                elif len(parts) == 4 and parts[:2] == ['api','projects'] and parts[3] == 'coding':
                    result = store.save_coding(parts[2], body) if write else store.coding(parts[2])
                elif len(parts) == 4 and parts[:2] == ['api','projects'] and parts[3] == 'learning':
                    result = store.save_question(parts[2], body) if write else store.learning(parts[2])
                elif len(parts) == 4 and parts[:2] == ['api','projects'] and parts[3] == 'definitions':
                    result = store.save_definition(parts[2], body, body.get('approve') is True) if write else store.workspace(parts[2])
                elif path == '/api/ai/connection':
                    result = (connection.clear() if body.get('disconnect') is True else connection.configure(body)) if write else connection.public()
                elif len(parts) == 4 and parts[:2] == ['api','projects'] and parts[3] == 'extractions' and not write:
                    result = store.runs(parts[2])
                elif len(parts) == 6 and parts[:2] == ['api','projects'] and parts[3] == 'papers' and parts[5] == 'extract' and write:
                    result = store.extract(parts[2], parts[4], body, connection.snapshot())
                elif len(parts) in (4,5) and parts[:2] == ["api", "projects"] and parts[3] == "passages":
                    pid = parts[2]
                    if len(parts) == 4 and not write:
                        result = store.passages(pid)
                    elif len(parts) == 4 and write:
                        result = {"id": store.propose_passage(pid, body.get('document'), body.get('page'), body.get('revision'), body.get('digest'), body.get('start'), body.get('end'), body.get('quote'), body.get('category'), body.get('interpretation'), body.get('actor'))}
                    elif len(parts) == 5 and write:
                        store.review_passage(pid, parts[4], body.get('version'), body.get('decision'), body.get('category'), body.get('interpretation'), body.get('reviewer'), body.get('rationale'), body.get('original_checked'), body.get('corrected_quote',''))
                        result = {"saved": True}
                    else:
                        raise KeyError('Page not found')
                elif len(parts) >= 4 and parts[:2] == ["api", "projects"] and parts[3] == "papers":
                    pid = parts[2]
                    if len(parts) == 4:
                        result = store.import_pdf(pid, body, unquote(self.headers.get("X-Filename", "paper.pdf"))) if write else store.papers(pid)
                    elif len(parts) == 5:
                        result = store.update_citation(pid, parts[4], body.get("expected_version"), body.get("metadata"), body.get("actor"), body.get("confirmed")) if write else store.paper(pid, parts[4])
                    elif len(parts) == 6 and parts[5] == "pdf" and not write:
                        self.respond(200, store.original(pid, parts[4]), "application/pdf")
                        return
                    elif len(parts) == 6 and parts[5] == "ocr" and write:
                        result = store.ocr_page(pid, parts[4], body.get('page'), body.get('expected_revision'), body.get('actor'))
                    elif len(parts) == 7 and parts[5] == "pages" and not write:
                        paper = store.paper(pid, parts[4])
                        number = int(parts[6])
                        if not 1 <= number <= len(paper["pages"]):
                            raise KeyError("PDF page not found")
                        self.respond(200, render_page(store.original(pid, parts[4]), number), "image/png")
                        return
                    else:
                        raise KeyError("Page not found")
                elif path == "/api/state" and not write:
                    result = store.state()
                elif path == "/api/projects" and write:
                    result = store.create_setup(body.get("name"), body.get("actor"), body.get("template_id"))
                elif len(parts) in (3, 4) and parts[:2] == ["api", "projects"]:
                    pid = parts[2]
                    if len(parts) == 3 and not write:
                        result = store.project(pid)
                    elif len(parts) == 4 and parts[3] == "settings" and write:
                        result = store.save_configuration(pid, body.get("expected_version"), body.get("settings"), body.get("actor"), body.get("rationale"))
                    elif len(parts) == 4 and parts[3] == "templates" and write:
                        result = {"id": store.save_template(pid, body.get("expected_version"), body.get("name"))}
                    elif len(parts) == 4 and parts[3] == "export" and not write:
                        store.project(pid)
                        self.respond(200, store.export(pid), attachment=True)
                        return
                    else:
                        raise KeyError("Page not found")
                else:
                    raise KeyError("Page not found")
                self.respond(200, result)
            except Conflict as exc:
                self.respond(409, {"error": str(exc)})
            except KeyError as exc:
                self.respond(404, {"error": str(exc.args[0])})
            except (ValueError, TypeError, UnicodeError) as exc:
                self.respond(400, {"error": str(exc)})
            except sqlite3.Error:
                self.respond(503, {"error": "The local database is unavailable. Your on-screen edits have been kept; try again."})
            finally:
                if store is not None:
                    store.close()

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request(write=True)

    class LockedServer(ThreadingHTTPServer):
        daemon_threads = False
        def server_close(self):
            try: super().server_close()
            finally: server_lock.close()
    try:
        return LockedServer(("127.0.0.1", port), Handler)
    except Exception:
        server_lock.close()
        raise


def main():
    parser = argparse.ArgumentParser(description="Run the local Construct Lab setup app")
    parser.add_argument("--database", default="data/construct-lab.sqlite")
    parser.add_argument("--port", type=int, default=8780)
    args = parser.parse_args()
    server = make_server(args.database, args.port)
    print(f"Construct Lab is running at http://127.0.0.1:{server.server_port}", flush=True)
    print(f"Local research records: {Path(args.database).resolve()}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
