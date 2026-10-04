# Construct Lab

Private research software project for developing the construct **curiosity**.
The construct's domain, level, temporal form and definition remain research decisions.
No definition or evidence has been preapproved.

## Current status

Initial local persistence foundation, not a deployed or study-ready application.
Includes source passages, proposed claims, explicit review, versioned definition
approval, and an exportable event history. Tests use synthetic fixtures only.

The interface in `docs/interface-prototype.html` is the earlier interactive design
prototype. Its services are simulated. It is not connected to the persistence layer.
The proposed production behavior is in `docs/interface-specifications.md`.

## Run the checks

Python 3.9 or later is required. No runtime packages are needed for these checks.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Implementation sequence

1. Connect the research brief and source review interface to persistent records.
2. Add document upload, parsing, passage anchors and verified AI extraction.
3. Implement full construct proposals, materiality review, and version comparison.
4. Implement evaluable evidence batches, configurable gates and challenge records.
5. Add collaborator authentication, roles, access control and deployment.
6. Pilot with real curiosity literature, then calibrate and validate stopping rules.

## Deployment and repository boundaries

Private repository: https://github.com/drandrewhsphd/construct-lab.
GitHub hosts the source and automated tests. The running service will need a backend
host and persistent storage. A production hosting provider has not been selected.
Do not deploy this library as a public service: reviewer names currently come from
local function inputs and are not authenticated identities. SQLite is for local
development; the shared deployment needs a database migration and service layer.

Keep paper files, research exports, databases and API secrets out of Git. The
`data/` directory is ignored for this purpose. The event log is transactional but
not cryptographically tamper-proof. Local exports contain stored source passages;
review source permissions before sharing them.

No AI provider, API key, live literature service, or saturation calculation is
connected yet. The software does not assert that a construct is saturated.
