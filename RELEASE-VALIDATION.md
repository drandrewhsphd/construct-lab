# v0.2.0 validation — 12 October 2026

- 89 automated tests passed on macOS / Python 3.12, including the four-stage research loop, review gates, reference validation, source-change blocking, project isolation, caching, failure records, reviewer edits, and HTTP provider request/response serialization.
- A fresh virtual environment installed the built package and dependencies; the same 89 tests passed against that installed package.
- Browser checks exercised input preview, authorization, synthetic generation, review acceptance and a dependent challenge stage.
- The bundled immersiveness demonstration loaded and exposed five source/history/finding records to the research loop.
- A live Crossref bibliographic search returned eight records. Metadata was not automatically admitted as evidence.

## Limits

The provider HTTP test uses a local synthetic server. The four-stage end-to-end test uses clearly labeled fixtures. **No live OpenAI model response has yet been verified for this release.** An API connection and live test remain necessary to verify a particular account/model. No claim of model quality, scientific validity, saturation, or superiority to prompting is supported by these software tests.

Native Windows and other Python versions were not tested. Optional OCR was not revalidated end-to-end with a newly downloaded OCR engine in this release.

Release notes record the final GitHub download/installation verification after publication.
