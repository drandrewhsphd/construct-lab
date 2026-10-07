# Construct Lab

Private research software project for developing the construct **curiosity**.
The construct's domain, level, temporal form and definition remain research decisions.
No definition or evidence has been preapproved.

## Current status

Working local project setup, PDF library, OCR and passage-review application with persistent settings, version history,
and reusable templates. Curiosity is created on the first launch with its research
choices left open. This is not yet a deployed or study-ready application.

The underlying research record library also includes source passages, proposed
claims, explicit review, versioned definition approval, and an exportable event
history. Passage evidence review is available in the UI; definition approval remains a library operation.
Tests use synthetic fixtures only.

## Open the application

From this repository folder, with Python 3.9 or later:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
PYTHONPATH=src python3 -m construct_lab.server
```

Open **http://127.0.0.1:8765** in your browser. PDF extraction uses the installed pypdf
package; original page previews use PDFium and Pillow. No API keys or cloud accounts are needed. Stop the server with Ctrl+C; restart
using the same command and directory to reopen the same saved research records.
The server accepts connections only from this computer.

If the port is already in use, add `--port 8767` and open that port instead.

## Literature Library

Choose **Open Literature Library** from project setup, or open `/library`.
Select your project and upload up to 20 PDFs per batch (20 MB and 500 pages per PDF).
Each file is processed independently: a damaged or encrypted file fails visibly
without discarding successful imports. Identical files are deduplicated within each
project. Files are not sent to any AI provider or external service. URL retrieval
is not part of this release; save a PDF locally, then select it for upload.

Select a paper to edit its citation and inspect the original beside extracted text.
PDF metadata supplies initial title/author suggestions; other fields stay blank.
Confirm bibliographic details only after checking them against the original. This
does not verify scientific claims. Citation changes are versioned and recorded in
the event history; stale edits are rejected. Matching DOIs flag possible alternate
versions, which can coexist without being silently merged.

Page locators are **PDF file page numbers**, not printed journal page numbers.
Pages with fewer than 80 alphabetic characters are flagged for visual inspection;
this is a heuristic, not an OCR or quality assessment. Empty/image/scanned pages and
text extraction failures are visible. Local OCR is available through **OCR & passage review**. Tables,
columns, symbols and reading order require checking even when text is available.
Extraction runs in a separate process with a one-minute timeout, page/text limits,
and a worker memory cap on Linux. This is a local trusted-user application, not a
production document sandbox.

Original PDF bytes, hashes, citations and page text are stored transactionally in
the same local SQLite database. Back up that database while the server is stopped.
JSON exports include library records and text but not PDF bytes; download original
PDFs from each paper's detail view. PDFs and local data remain outside GitHub.

1. Open Curiosity and fill in the research brief, evidence plan and stopping plan.
   Unresolved fields may stay blank. Proposed batch counts are optional.
2. Enter your name and a change reason, then choose **Save new version**.
3. Use **Version history** to inspect previous settings. Saving settings does not
   approve a scope, definition, evidence claim or saturation decision.
4. Choose **Save settings as a template** to preserve a reusable snapshot.
5. Choose **New research project**, enter a name, and select a blank setup or your
   template. Review copied settings for the new domain. Evidence, definition
   approvals and decision histories are never copied.

Settings save into `data/construct-lab.sqlite`, not browser storage or GitHub.
An alternate location can be selected with `--database /path/to/research.sqlite`.
Use the same database path when restarting. Back up this file while the server is
stopped. **Download saved project record** exports that project's saved settings,
history and research records, not unsaved edits. Export import/restore is not yet
implemented; the database backup is the restore mechanism for this release.

Stale saves are rejected instead of overwriting another edit. On a conflict, your
text remains on screen; copy any changes you want to retain before reloading the
latest settings. Saved templates are immutable snapshots, with new names required
for later variants. Template settings are drafts, not validated research protocols.

The interface in `docs/interface-prototype.html` is the earlier interactive design
prototype. Its services are simulated. It is not connected to the persistence layer.
The proposed production behavior is in `docs/interface-specifications.md`.

## OCR and passage review

Open **OCR & passage review** from the library. For local English OCR, install
Node.js and run `npm install` once in this repository. The worker uses Tesseract.js;
its first run downloads the English language model into `data/ocr-tools/`. PDF
content stays on this computer. A native `tesseract` executable with English data
can also be used when Node is unavailable. `CONSTRUCT_LAB_NODE` optionally specifies
the Node executable. Ordinary import and passage review do not require OCR tools.

1. Select a paper and enter your name in **Recorded by**.
2. Run OCR on one page or the remaining flagged pages. Stop takes effect after the
   current page. Each result is an unreviewed version; original text and PDFs remain intact.
3. Highlight a passage in the page text and choose **Use selected passage**.
4. Classify it as a definition, dimension, boundary, antecedent, consequence,
   measurement or other evidence. Add your interpretation and save the proposal.
5. Choose **Review passage**, compare it with the displayed original, and record
   an accepted, rejected or unresolved decision with your name and rationale.
   Acceptance requires confirming that you checked the original. An optional
   corrected transcription preserves the initially selected text in the history.

Accepted passages create verified evidence claims; saving a proposal alone does
not. Accepted and rejected decisions are final in this interface; unresolved
proposals can be revisited. Passage records preserve the PDF hash, citation snapshot,
PDF page, text version and character offsets. Later OCR does not rewrite a saved
passage. Project exports include passages and OCR history, but not original PDF bytes.
OCR errors, columns, symbols and reading order still require human checking.
AI-assisted extraction is available through the passage-review screen; configure a provider before a live run.

## AI-assisted extraction

From passage review, choose **AI-assisted extraction**. Select OpenAI, an
OpenAI-compatible API, or a local model. Enter the model identifier available to
you and, for an external provider, its API key in the local password field.
Compatible providers must support Chat Completions, JSON object mode and
`max_completion_tokens`. Local models use a loopback HTTP endpoint; external
providers require HTTPS. Redirects are refused so credentials cannot follow them.
The adapter follows the [OpenAI Chat Completions reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

Connection settings and keys stay in server memory, shared across this local
application's tabs, and are cleared on disconnect or restart. They are not written
to GitHub, browser storage, database or exports. Connecting does not test credentials.
A live extraction sends the chosen page text and research focus to the configured
provider, after the researcher authorizes that request in the interface. Provider
usage may be billable. OpenAI requests set `store: false`; this does not promise
zero retention under every provider/account policy. Provider credentials are
separate from signing into ChatGPT or GitHub.

Each request examines one PDF page (80–30,000 characters), with at most eight
suggestions and 4,000 output tokens. The focus is editable for every project.
The model selects numbered source-line ranges; the application copies exact
quotations from those ranges, preserving OCR artifacts and offsets. OpenAI uses
a strict output schema for line IDs and the allowed categories. Invalid ranges,
invalid categories and duplicates are skipped with reasons.
Exact repeated requests reuse completed results. Failed requests can be retried
manually; timeouts may still be charged. Runs interrupted by server restart are
marked interrupted. Page changes during a request prevent saving stale proposals.

Runs retain source text, citation and PDF hash, prompt/version, provider/model,
usage when supplied, output, requester, and resulting passage IDs. This is a
reproducibility record, not a guarantee of deterministic output. All suggestions
remain proposed evidence and use the same original-PDF human-review gate. An exact
quotation can still be misinterpreted. Empty results do not establish saturation.
Project JSON exports include extraction history (schema 5); API keys are excluded.
The automated provider tests use synthetic responses. A real provider requires
credentials and an explicitly authorized live run; no live accuracy claim is made.
Choose **Whole paper / page range** to process eligible pages sequentially. The
scope notice lists the paper, eligible count, destination and excluded pages before
you authorize transmission. Stop takes effect after the current page. The batch
stops on its first error, preserving earlier results. Keep the tab open; closing
it stops scheduling further pages, although an in-flight request may finish.
To resume, select the same range, focus and model: the server reuses completed
page runs without another provider request. Text shorter than 80 or longer than
30,000 characters is excluded visibly. The page selector previews individual
pages even when the batch covers the whole range.

The passage-review screen includes an approved-evidence matrix by paper and
category. Click a count to filter to those accepted source passages. Counts are
passage records, not independent findings or saturation measures. This comparison
view makes no automated agreement, contradiction or construct-definition claims.
Cross-paper AI synthesis and automatic full-corpus runs remain future work.

## Run the checks

Python 3.9 or later and the project dependencies above are required.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Implementation sequence

1. Complete: project setup, reusable templates, version history, PDF batch import,
   original-page previews, citation review and page-level text extraction.
2. Complete: local English OCR, source-linked passage selection and human review.
   Complete: bounded AI-assisted page extraction with exact-quotation checks and explicit human review.
3. Implement full construct proposals, materiality review, and version comparison.
4. Implement evaluable evidence batches, configurable gates and challenge records.
5. Add collaborator authentication, roles, access control and deployment.
6. Pilot with real curiosity literature, then calibrate and validate stopping rules.

## Deployment and repository boundaries

Private repository: https://github.com/drandrewhsphd/construct-lab.
GitHub hosts the source and automated tests. The running service will need a backend
host and persistent storage. A production hosting provider has not been selected.
Do not deploy this local service publicly: names are research attributions, not
authenticated identities. The service binds to loopback and rejects cross-origin
writes. Shared deployment still needs authenticated accounts, roles, production
hosting, backups and a database/deployment review.

Keep paper files, research exports, databases and API secrets out of Git. The
`data/` directory is ignored for this purpose. The event log is transactional but
not cryptographically tamper-proof. Local exports contain stored source passages;
review source permissions before sharing them.

An AI provider can be connected for the current server session. No live literature
search service or saturation calculation is connected yet. The software does not assert that a construct is saturated.
