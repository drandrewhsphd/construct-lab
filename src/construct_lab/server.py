"""Local-only setup application: python -m construct_lab.server."""
import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .setup import SetupStore
from .store import Conflict


def make_server(database, port=8765):
    database = Path(database).resolve()
    database.parent.mkdir(parents=True, exist_ok=True)
    store = SetupStore(database)
    try:
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
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if attachment:
                self.send_header("Content-Disposition", 'attachment; filename="construct-lab-project.json"')
            self.end_headers()
            self.wfile.write(data)

        def handle_request(self, write=False):
            port = self.server.server_port
            allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            host = self.headers.get("Host", "")
            if host not in allowed_hosts:
                self.respond(403, {"error": "This application is available only on this computer"})
                return
            if write and (self.headers.get("Origin") != f"http://{host}" or
                          self.headers.get("X-Construct-Lab") != "local" or
                          self.headers.get("Content-Type", "").split(";")[0] != "application/json"):
                self.respond(403, {"error": "Open the local application to save settings"})
                return
            store = None
            try:
                body = {}
                if write:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 150000:
                        raise ValueError("Request is empty or too large")
                    body = json.loads(self.rfile.read(length))
                    if not isinstance(body, dict):
                        raise ValueError("Expected a settings object")
                path = urlsplit(self.path).path
                if path == "/" and not write:
                    self.respond(200, Path(__file__).with_name("app.html").read_bytes(), "text/html; charset=utf-8")
                    return
                store = SetupStore(database)
                parts = path.strip("/").split("/")
                if path == "/api/state" and not write:
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

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description="Run the local Construct Lab setup app")
    parser.add_argument("--database", default="data/construct-lab.sqlite")
    parser.add_argument("--port", type=int, default=8765)
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
