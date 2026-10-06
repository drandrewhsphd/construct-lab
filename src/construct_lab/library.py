"""Local PDF library. Original bytes and extracted pages share one transaction."""
import hashlib
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

from .setup import SetupStore, short_text
from .store import Conflict, required

MAX_PDF = 20 * 1024 * 1024
FIELDS = ("title", "authors", "year", "journal", "doi", "publication_version", "source_url")


def extract_pdf(data):
    from pypdf import PdfReader
    if not data.startswith(b"%PDF-") or len(data) > MAX_PDF:
        raise ValueError("Choose a PDF file of 20 MB or less")
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("Password-protected PDFs are not supported; upload an unlocked copy")
    if not 0 < len(reader.pages) <= 500:
        raise ValueError("PDFs must contain between 1 and 500 pages")
    metadata = reader.metadata or {}
    pages = []
    total = 0
    for number, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
            total += len(text)
            if len(text) > 500000 or total > 5000000:
                raise ValueError("Extracted text is too large for this local importer")
            status = "text_available" if sum(c.isalpha() for c in text) >= 80 else "check_original"
        except ValueError:
            raise
        except Exception:
            text, status = "", "extraction_failed"
        pages.append({"number": number, "text": text, "status": status})
    return {"title": str(metadata.get("/Title", ""))[:2000],
            "authors": str(metadata.get("/Author", ""))[:2000], "pages": pages}


def extract_isolated(data):
    # Keep malformed or expensive PDFs away from the HTTP request process.
    try:
        result = subprocess.run([sys.executable, "-m", "construct_lab.library", "--extract"],
                                input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    except subprocess.TimeoutExpired:
        raise ValueError("Extraction exceeded one minute. Try a smaller or repaired PDF") from None
    if result.returncode:
        raise ValueError("PDF could not be read. It may be damaged, encrypted or exceed the extraction limits")
    return json.loads(result.stdout)


def render_page(data, number):
    if type(number) is not int or not 1 <= number <= 500:
        raise ValueError("Invalid PDF page number")
    try:
        result = subprocess.run([sys.executable, "-m", "construct_lab.library", "--render", str(number)],
                                input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    except subprocess.TimeoutExpired:
        raise ValueError("Page preview timed out. Open the original PDF instead") from None
    if result.returncode:
        raise ValueError("Page preview unavailable. Open the original PDF instead")
    return result.stdout


def validate_metadata(value):
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        raise ValueError("Use the supported citation fields")
    result = {}
    for field in FIELDS:
        item = value[field]
        if not isinstance(item, str) or len(item) > 4000:
            raise ValueError("Citation fields must be text of 4,000 characters or fewer")
        result[field] = item.strip()
    result["title"] = required(result["title"])
    if result["year"] and (not result["year"].isdigit() or len(result["year"]) != 4):
        raise ValueError("Use a four-digit publication year or leave it blank")
    if result["source_url"] and not result["source_url"].startswith(("https://", "http://")):
        raise ValueError("Source link must be an HTTP or HTTPS URL")
    return result


class LibraryStore(SetupStore):
    def __init__(self, path):
        super().__init__(path)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS documents(
          id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id),
          sha256 TEXT NOT NULL, filename TEXT NOT NULL, original BLOB NOT NULL,
          metadata TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
          citation_status TEXT NOT NULL DEFAULT 'needs_review', created_at TEXT NOT NULL,
          UNIQUE(project,sha256));
        CREATE TABLE IF NOT EXISTS document_pages(
          document TEXT NOT NULL REFERENCES documents(id), number INTEGER NOT NULL,
          text TEXT NOT NULL, status TEXT NOT NULL, PRIMARY KEY(document,number));
        """)

    def papers(self, project):
        self.project(project)
        result = []
        for row in self.db.execute("SELECT id,filename,metadata,version,citation_status,created_at FROM documents WHERE project=? ORDER BY created_at,id", (project,)):
            item = dict(row)
            item["metadata"] = json.loads(item["metadata"])
            item["page_count"], item["flagged_pages"] = self.db.execute(
                "SELECT count(*), coalesce(sum(status != 'text_available'),0) FROM document_pages WHERE document=?", (item["id"],)).fetchone()
            result.append(item)
        return result

    def paper(self, project, document):
        row = self.db.execute("SELECT id,filename,sha256,metadata,version,citation_status,created_at FROM documents WHERE project=? AND id=?", (project, document)).fetchone()
        if row is None:
            raise KeyError("Paper not found in this project")
        item = dict(row)
        item["metadata"] = json.loads(item["metadata"])
        item["pages"] = [dict(r) for r in self.db.execute("SELECT number,text,status FROM document_pages WHERE document=? ORDER BY number", (document,))]
        doi = item["metadata"]["doi"].lower().removeprefix("https://doi.org/").removeprefix("doi:").strip()
        item["possible_duplicates"] = [p["id"] for p in self.papers(project) if p["id"] != document and doi and p["metadata"]["doi"].lower().removeprefix("https://doi.org/").removeprefix("doi:").strip() == doi]
        return item

    def original(self, project, document):
        row = self.db.execute("SELECT original FROM documents WHERE project=? AND id=?", (project, document)).fetchone()
        if row is None:
            raise KeyError("Paper not found in this project")
        return bytes(row[0])

    def import_pdf(self, project, data, filename):
        self.project(project)
        if not isinstance(data, bytes) or not data.startswith(b"%PDF-") or len(data) > MAX_PDF:
            raise ValueError("Choose a PDF file of 20 MB or less")
        filename = short_text(filename.replace("\\", "/").split("/")[-1])
        digest = hashlib.sha256(data).hexdigest()
        old = self.db.execute("SELECT id FROM documents WHERE project=? AND sha256=?", (project, digest)).fetchone()
        if old:
            return {"id": old[0], "duplicate": True}
        extracted = extract_isolated(data)
        metadata = dict.fromkeys(FIELDS, "")
        metadata.update(title=extracted["title"].strip() or filename, authors=extracted["authors"])
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            old = self.db.execute("SELECT id FROM documents WHERE project=? AND sha256=?", (project, digest)).fetchone()
            if old:
                return {"id": old[0], "duplicate": True}
            did = str(uuid4())
            self.db.execute("INSERT INTO documents(id,project,sha256,filename,original,metadata,created_at) VALUES(?,?,?,?,?,?,?)",
                            (did, project, digest, filename, data, json.dumps(metadata), datetime.now(timezone.utc).isoformat()))
            self.db.executemany("INSERT INTO document_pages VALUES(?,?,?,?)", [(did, p["number"], p["text"], p["status"]) for p in extracted["pages"]])
            self.event(project, "document_imported", {"document": did, "sha256": digest,
                       "filename": filename, "pages": len(extracted["pages"]), "extractor": "pypdf", "evidence_status": "unreviewed"})
        return {"id": did, "duplicate": False}

    def update_citation(self, project, document, expected_version, metadata, actor, confirmed):
        metadata, actor = validate_metadata(metadata), short_text(actor)
        if type(confirmed) is not bool or type(expected_version) is not int:
            raise ValueError("A citation review choice and current version are required")
        if confirmed and not all(metadata[k] for k in ("title", "authors", "year", "journal", "publication_version")):
            raise ValueError("Complete title, authors, year, journal and publication version before confirming")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            old = self.paper(project, document)
            if old["version"] != expected_version:
                raise Conflict("This citation changed. Copy your edits, then reload the paper before saving")
            status = "confirmed" if confirmed else "needs_review"
            self.db.execute("UPDATE documents SET metadata=?,version=version+1,citation_status=? WHERE id=?", (json.dumps(metadata), status, document))
            self.event(project, "citation_updated", {"document": document, "version": expected_version+1,
                       "actor": actor, "before": old["metadata"], "after": metadata, "citation_status": status})
        return self.paper(project, document)

    def export(self, project):
        result = super().export(project)
        result["schema_version"] = 3
        result["literature"] = [self.paper(project, p["id"]) for p in self.papers(project)]
        result["pdf_export_note"] = "Original PDFs are stored in the database; JSON contains metadata and extracted text only."
        return result


if __name__ == "__main__":
    try:
        # Limit extraction worker memory on platforms supporting RLIMIT_AS.
        import resource
        if sys.platform != "darwin":
            resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (45, 45))
        data = sys.stdin.buffer.read(MAX_PDF + 1)
        if "--render" in sys.argv:
            import pypdfium2 as pdfium
            with pdfium.PdfDocument(data) as document:
                page = document[int(sys.argv[-1]) - 1]
                width, height = page.get_size()
                scale = min(1.6, 1800 / max(width, height))
                bitmap = page.render(scale=scale)
                bitmap.to_pil().save(sys.stdout.buffer, format="PNG")
                bitmap.close()
                page.close()
        else:
            print(json.dumps(extract_pdf(data)))
    except Exception:
        sys.exit(1)
