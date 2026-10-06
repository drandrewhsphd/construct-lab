# Construct Lab

Private research software project for developing the construct **curiosity**.
The construct's domain, level, temporal form and definition remain research decisions.
No definition or evidence has been preapproved.

## Current status

Working local project setup and PDF library application with persistent settings, version history,
and reusable templates. Curiosity is created on the first launch with its research
choices left open. This is not yet a deployed or study-ready application.

The underlying research record library also includes source passages, proposed
claims, explicit review, versioned definition approval, and an exportable event
history. Its evidence and definition operations are not yet exposed in the new UI.
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
text extraction failures are visible. **OCR is not implemented yet.** Tables,
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

## Run the checks

Python 3.9 or later and the project dependencies above are required.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Implementation sequence

1. Complete: project setup, reusable templates, version history, PDF batch import,
   original-page previews, citation review and page-level text extraction.
2. Add OCR for scanned papers, passage selection and reviewed AI extraction.
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

No AI provider, API key, live literature service, or saturation calculation is
connected yet. The software does not assert that a construct is saturated.
