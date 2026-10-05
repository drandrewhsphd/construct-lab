# Construct Lab

Private research software project for developing the construct **curiosity**.
The construct's domain, level, temporal form and definition remain research decisions.
No definition or evidence has been preapproved.

## Current status

Working local project setup application with persistent settings, version history,
and reusable templates. Curiosity is created on the first launch with its research
choices left open. This is not yet a deployed or study-ready application.

The underlying research record library also includes source passages, proposed
claims, explicit review, versioned definition approval, and an exportable event
history. Its evidence and definition operations are not yet exposed in the new UI.
Tests use synthetic fixtures only.

## Open the application

From this repository folder, with Python 3.9 or later:

```sh
PYTHONPATH=src python3 -m construct_lab.server
```

Open **http://127.0.0.1:8765** in your browser. No runtime packages, API keys or cloud
accounts are needed for this local milestone. Stop the server with Ctrl+C; restart
using the same command and directory to reopen the same saved research records.
The server accepts connections only from this computer.

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

Python 3.9 or later is required. No runtime packages are needed for these checks.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Implementation sequence

1. Complete: connect project setup, reusable templates and version history to
   persistent records. Next: source ingestion and evidence review UI.
2. Add document upload, parsing, passage anchors and verified AI extraction.
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
