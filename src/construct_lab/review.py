"""Versioned OCR and human passage review; originals and quotations stay traceable."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .library import LibraryStore, MAX_PDF
from .setup import short_text
from .store import Conflict, required

CATEGORIES = ('definition', 'dimension', 'boundary', 'antecedent', 'consequence', 'measurement', 'other')


def text_hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def recognize(data, number, cache):
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    node = os.environ.get('CONSTRUCT_LAB_NODE') or shutil.which('node')
    native = shutil.which('tesseract')
    if not node and not native:
        raise ValueError('Local OCR requires Node.js with Tesseract.js, or Tesseract with English language data')
    with tempfile.TemporaryDirectory(prefix='ocr-', dir=cache) as folder:
        image = Path(folder) / 'page.png'
        try:
            subprocess.run([sys.executable, '-m', 'construct_lab.review', '--image', str(number), str(image)],
                           input=data, check=True, capture_output=True, timeout=45)
            if node:
                result = subprocess.run([node, str(Path(__file__).with_name('ocr.cjs')), str(image), str(cache)],
                                        check=True, capture_output=True, timeout=120)
                return json.loads(result.stdout)
            result = subprocess.run([native, str(image), 'stdout', '-l', 'eng'], check=True, capture_output=True, timeout=90)
            version = subprocess.run([native, '--version'], capture_output=True, timeout=10).stdout.decode().splitlines()[0]
            return {'text': result.stdout.decode('utf-8'), 'blocks': [], 'engine': version + ' (English)'}
        except (OSError, subprocess.SubprocessError, ValueError):
            raise ValueError('Local OCR failed or timed out; the original and previous text are unchanged. Retry this page') from None


class ReviewStore(LibraryStore):
    def __init__(self, path):
        super().__init__(path)
        self.ocr_cache = Path(path).resolve().parent / 'ocr-tools'
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS page_ocr(
          document TEXT NOT NULL REFERENCES documents(id), page INTEGER NOT NULL,
          revision INTEGER NOT NULL, text TEXT NOT NULL, engine TEXT NOT NULL,
          blocks TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(document,page,revision));
        CREATE TABLE IF NOT EXISTS passages(
          id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id),
          document TEXT NOT NULL REFERENCES documents(id), page INTEGER NOT NULL,
          source_revision INTEGER NOT NULL, source_text TEXT NOT NULL, source_hash TEXT NOT NULL,
          start INTEGER NOT NULL, end INTEGER NOT NULL, quote TEXT NOT NULL,
          citation TEXT NOT NULL, pdf_hash TEXT NOT NULL, category TEXT NOT NULL,
          interpretation TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'proposed', version INTEGER NOT NULL DEFAULT 1,
          reviewed_quote TEXT NOT NULL DEFAULT '', claim_id TEXT REFERENCES claims(id));
        ''')

    def paper(self, project, document):
        item = super().paper(project, document)
        for page in item['pages']:
            page['native_status'] = page['status']
            row = self.db.execute('SELECT * FROM page_ocr WHERE document=? AND page=? ORDER BY revision DESC LIMIT 1', (document, page['number'])).fetchone()
            page['text_revision'] = row['revision'] if row else 0
            page['engine'] = row['engine'] if row else 'PDF text extraction'
            if row:
                page['text'] = row['text']
                page['status'] = 'ocr_unreviewed' if sum(c.isalpha() for c in row['text']) >= 80 else 'ocr_check_original'
            page['text_hash'] = text_hash(page['text'])
        return item

    def ocr_page(self, project, document, page, expected_revision, actor):
        actor = short_text(actor)
        if type(page) is not int or type(expected_revision) is not int:
            raise ValueError('A page number and current text version are required')
        paper = self.paper(project, document)
        if not 1 <= page <= len(paper['pages']):
            raise KeyError('PDF page not found')
        if paper['pages'][page-1]['text_revision'] != expected_revision:
            raise Conflict('The page text changed; reload before running OCR')
        result = recognize(self.original(project, document), page, self.ocr_cache)
        if not isinstance(result.get('text'), str) or len(result['text']) > 500000:
            raise ValueError('OCR returned invalid or excessive text')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if self.paper(project, document)['pages'][page-1]['text_revision'] != expected_revision:
                raise Conflict('Another OCR run saved this page first; reload the page')
            self.db.execute('INSERT INTO page_ocr VALUES(?,?,?,?,?,?,?,?)',
                            (document, page, expected_revision+1, result['text'], result['engine'],
                             json.dumps(result.get('blocks', [])), actor, datetime.now(timezone.utc).isoformat()))
            self.event(project, 'page_ocr_saved', {'document': document, 'page': page,
                       'revision': expected_revision+1, 'actor': actor, 'engine': result['engine'], 'status': 'unreviewed'})
        return self.paper(project, document)

    def passages(self, project):
        self.project(project)
        result = []
        for row in self.db.execute('SELECT * FROM passages WHERE project=? ORDER BY created_at,id', (project,)):
            item = dict(row)
            item['citation'] = json.loads(item['citation'])
            latest = self.db.execute('SELECT max(revision) FROM page_ocr WHERE document=? AND page=?', (item['document'], item['page'])).fetchone()[0] or 0
            item['newer_page_text'] = latest != item['source_revision']
            result.append(item)
        return result

    def propose_passage(self, project, document, page, revision, digest, start, end, quote, category, interpretation, actor):
        actor, interpretation = short_text(actor), required(interpretation)
        if category not in CATEGORIES or len(interpretation) > 8000:
            raise ValueError('Choose an evidence category and an interpretation of at most 8,000 characters')
        if any(type(n) is not int for n in (page, revision, start, end)):
            raise ValueError('Select an exact passage from a saved page')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            paper = self.paper(project, document)
            if not 1 <= page <= len(paper['pages']):
                raise KeyError('PDF page not found')
            source = paper['pages'][page-1]
            if source['text_revision'] != revision or source['text_hash'] != digest:
                raise Conflict('The page text changed. Reload and select the passage again')
            if not isinstance(quote, str) or not quote.strip() or not 0 <= start < end <= len(source['text']) or source['text'][start:end] != quote or len(quote) > 20000:
                raise ValueError('The quotation must match the selected page text exactly (maximum 20,000 characters)')
            pid = str(uuid4())
            self.db.execute('''INSERT INTO passages(id,project,document,page,source_revision,source_text,source_hash,start,end,quote,citation,pdf_hash,category,interpretation,actor,created_at)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (pid, project, document, page, revision, source['text'], digest, start, end, quote,
                             json.dumps(paper['metadata']), paper['sha256'], category, interpretation, actor, datetime.now(timezone.utc).isoformat()))
            self.event(project, 'passage_proposed', {'passage': pid, 'document': document, 'page': page, 'source_revision': revision, 'actor': actor})
        return pid

    def review_passage(self, project, passage, version, decision, category, interpretation, reviewer, rationale, original_checked, corrected_quote=''):
        reviewer, rationale, interpretation = short_text(reviewer), required(rationale), required(interpretation)
        if type(version) is not int or decision not in ('verified', 'rejected', 'unresolved') or category not in CATEGORIES or type(original_checked) is not bool:
            raise ValueError('Choose a review decision, category and current version')
        if len(rationale) > 8000 or len(interpretation) > 8000 or not isinstance(corrected_quote, str) or len(corrected_quote) > 20000:
            raise ValueError('Review text exceeds the supported limit')
        if decision == 'verified' and not original_checked:
            raise ValueError('Check the quotation and interpretation against the original PDF before accepting')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT * FROM passages WHERE project=? AND id=?', (project, passage)).fetchone()
            if row is None:
                raise KeyError('Passage not found in this project')
            if row['version'] != version or row['status'] not in ('proposed', 'unresolved'):
                raise Conflict('This passage was already reviewed or changed; reload before continuing')
            quote = corrected_quote.strip() or row['quote']
            claim_id = None
            if decision == 'verified':
                sid, claim_id = str(uuid4()), str(uuid4())
                citation = json.loads(row['citation'])
                locator = f"PDF page {row['page']}; document {row['document']}; source text revision {row['source_revision']}; passage {passage}"
                self.db.execute('INSERT INTO sources VALUES(?,?,?,?,?)', (sid, project, json.dumps(citation), locator, quote))
                self.db.execute('INSERT INTO claims VALUES(?,?,?,?,?)', (claim_id, sid, quote, interpretation, 'verified'))
            self.db.execute('UPDATE passages SET status=?,version=version+1,category=?,interpretation=?,reviewed_quote=?,claim_id=? WHERE id=?',
                            (decision, category, interpretation, quote, claim_id, passage))
            self.event(project, 'passage_reviewed', {'passage': passage, 'version': version+1, 'decision': decision,
                       'category': category, 'interpretation': interpretation, 'reviewer': reviewer, 'rationale': rationale,
                       'original_checked': original_checked, 'original_quote': row['quote'], 'reviewed_quote': quote,
                       'claim_id': claim_id, 'previous_category': row['category'], 'previous_interpretation': row['interpretation']})

    def export(self, project):
        result = super().export(project)
        result['schema_version'] = 4
        result['passages'] = self.passages(project)
        result['ocr_history'] = [dict(r) for r in self.db.execute('SELECT o.* FROM page_ocr o JOIN documents d ON o.document=d.id WHERE d.project=? ORDER BY o.document,o.page,o.revision', (project,))]
        return result


if __name__ == '__main__' and '--image' in sys.argv:
    import pypdfium2 as pdfium
    with pdfium.PdfDocument(sys.stdin.buffer.read(MAX_PDF+1)) as pdf:
        page = pdf[int(sys.argv[2])-1]
        scale = min(3, 3500/max(page.get_size()))
        bitmap = page.render(scale=scale)
        bitmap.to_pil().save(sys.argv[3])
        bitmap.close()
        page.close()
