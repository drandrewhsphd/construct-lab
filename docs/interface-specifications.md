# Construct Lab developer specifications

Proposed production behavior accompanying the 60-slide PowerPoint. All API routes below are application design proposals. The HTML is an interactive prototype using synthetic evidence and simulated services.

## S01 implementation: research framing

POST /projects/{id}/briefs

| Control | Behavior and data | Validation and state |
|---|---|---|
| Inputs | Phenomenon, purpose, level, temporal form, initial scope. Candidate label optional. | Require nonempty phenomenon/scope. “Unresolved” temporal form creates an open issue. |
| Save brief | Create BriefVersion with actor, timestamp, parent ID and field values. | Save is a draft event. It does not approve scope or start a provider job. |
| Probe assumptions | Queue an LLM run with this brief and approved project context. | Return questions + targeted fields. No changes to user fields without acceptance. |
| States / errors | Empty, dirty draft, saving, saved, AI queued/running/failed. | Preserve edits on failure. Show inline validation. Retry AI independently of saving. |
| Acceptance | Blank phenomenon blocks save. Valid save returns a new brief ID. | An AI suggestion cannot become an approved search boundary. |

Request {expected_version, phenomenon, purpose, level, temporal_form, scope, label?}. Return 201 {brief_id, version, open_issues}. A separate approved ScopeVersion is required by search-job creation. On stale version return 409 with current version and preserve the unsaved draft. UI route #1. Prototype simulates persistence locally. Production must store all events server-side. Keyboard labels and focus order follow the visible form.

## S02 implementation: literature discovery

POST /projects/{id}/search-jobs

| Control | Behavior and data | Validation and state |
|---|---|---|
| Inputs | Query family, related search family, cutoff, selected adapters. | Require an approved scope, a query, and ≥1 capable/connected source. |
| Run search | Human approves plan. Queue paginated provider jobs with an idempotency key. | Disable duplicate submit while queued. Return job ID and per-source status. |
| Merged results | Canonical works retain every provider ID, query, access tier and raw-response hash. | Merge matching IDs carefully. Keep distinct versions and duplicate-review evidence. |
| Connections / log | Provider capabilities and server secret references. Search log opens exact retrievals. | Partial source failure stays visible. Retry failed pages, not completed contributions. |
| Acceptance | A timed-out provider yields a partial job plus a coverage issue. | A partial/empty job never counts as a zero-novelty batch. |

Request {scope_version, plan_version, queries[], provider_ids[], cutoff, idempotency_key}. 202 {job_id,status:"queued"}. GET /search-jobs/{id} exposes pagination cursors, progress, errors and result IDs. Proposed job states: queued, running, partial, complete, failed, canceled. Re-run creates a new manifest or an idempotent resume. Provider credentials never enter the browser, logs or exports. Search results in the screenshot are synthetic fixtures. The results list scrolls as it grows.

## S03 implementation: scope and coverage

POST /projects/{id}/scope-versions

| Control | Behavior and data | Validation and state |
|---|---|---|
| Inputs | Inclusion/exclusion choices, boundary rationale, coverage matrix and access issues. | Persist each exclusion with a reason and affected work IDs. |
| Approve boundary | Save a human-approved ScopeVersion and material-change flag. | Scope approval and coverage adequacy are distinct records. Gaps can remain open. |
| Search coverage gap | Create a SearchTask linked to gap ID, target stratum and scope version. | Carry the target into S02. Keep the gap open until a reviewer resolves it. |
| Changed scope | Re-screen affected works and invalidate affected coverage/metric approvals. | Material scope change resets stability. Preserve earlier decisions in history. |
| Acceptance | Approve rules while a critical access gap remains unresolved. | Rules save successfully, but candidate-stop eligibility remains blocked. |

Request {parent_scope_id, inclusion_rules, exclusion_rules, rationale, coverage_items[], expected_version}. Save ScopeVersion and human decision transactionally. A separate coverage review records adequacy, exceptions, required evidence and reviewer. No percent-complete claim implies all knowledge is covered. Use 409 for stale rules and 422 for missing rationale. A changed level or theoretical purpose must explicitly state which prior batches remain comparable.

## S04 implementation: evidence review

POST /extractions/{id}/reviews

| Control | Behavior and data | Validation and state |
|---|---|---|
| Source pane | Immutable passage text, document/version, locator, access tier and source identifier. | Open the original source at the cited location. Missing support remains unresolved. |
| AI extraction | Typed fields, evidence IDs, “not stated” values, synthesis proposal and run link. | Validate output schema and exact spans before showing a reviewable proposal. |
| Verify / correct | Human selects verified or corrected and supplies correction rationale. | Store the original AI output, new interpretation, reviewer and evidence links. |
| Leave unresolved | Create an issue with affected fields and required follow-up. | AI failure offers retry. Saved evidence and human draft remain available. |
| Acceptance | A provider invents a quote or cites an unknown passage ID. | Reject the extraction as invalid. No claim or eligible batch enters approval. |

Request {decision:"verified|corrected|rejected|unresolved", corrected_fields?, rationale, evidence_ids[], expected_version}. Corrected output creates a new interpretation rather than editing source evidence. Run record requires provider/model ID, prompt/schema version, supplied passage IDs, input/output hashes, timestamp and validation outcomes. A second model is a discrepancy signal, not independent proof. Prototype quote E-02 is explicitly synthetic. Human review checks entailment, negation, level and causal status.

## S05 implementation: construct proposal

POST /constructs/{id}/proposals

| Control | Behavior and data | Validation and state |
|---|---|---|
| Representation tabs | Definition, attributes, boundaries, network and competitors share one draft version. | Each field carries evidence IDs and supported/inferred/disputed/not-stated status. |
| Save draft | Persist partial field edits and unresolved alternatives. | Switching tabs preserves unsaved text. Draft saves never change approved R_b. |
| Submit for adjudication | Freeze the proposal payload and its approved base version for S06. | Require a definition and valid evidence references. Open issues remain visible. |
| AI operation | Synthesize verified evidence and list rival interpretations and missing fields. | No silent merge of conflicting definitions. No unsupported dimension or causal edge. |
| Acceptance | Submit R-01 while temporal form remains unresolved. | Proposal enters review, but approved state and stop eligibility remain unchanged. |

Request {base_version, definition, attributes[], dimensions[], boundaries[], entity, level, temporal_form, edges[], competitors[], evidence_links[], open_issues[]}. 201 {proposal_id,status:"submitted"}. AI may create proposals using a restricted service identity. It has no permission to create approved revisions. The definition tab, attributes and boundary fields are parts of one structured object, not separate independently approved definitions. Real implementation must provide row editors for graph and competitor data, provenance inspection, and draft persistence.

## S06 implementation: human adjudication

POST /constructs/{id}/revisions

| Control | Behavior and data | Validation and state |
|---|---|---|
| Review inputs | Approved base, proposed field diff, linked source, materiality, decision and rationale. | Materiality is material, nonmaterial or unresolved, with descriptive category labels. |
| Accept revision | Atomically write the approved snapshot and a human Decision event. | Material acceptance resets streak to 0. Record all changed conceptual fields. |
| Reject / unresolved | Reject preserves approved version. Unresolved opens/retains the issue. | An unresolved consequential issue blocks candidate eligibility. Preserve dissent. |
| Concurrency / roles | Require human reviewer identity, expected version and idempotency key. | 409 preserves draft for re-review. AI service identity receives 403 on approval. |
| Acceptance | Two reviewers submit decisions against the same base version. | One commits. The stale decision cannot overwrite it or count as another stable batch. |

Request {proposal_id, expected_version, decision, materiality, categories[], rationale, evidence_ids[], idempotency_key}. Server validates role, project access, source links and current base version inside one transaction. Acceptance creates a new immutable RepresentationVersion plus event. Rejection and unresolved choices use the same audit contract but do not create an approved representation. A semantic score never overrides a human materiality decision. In S06 the current approved base is v0 and the proposed next approved state is v1.

## S07 implementation: change assessment

POST /batches/{id}/evaluate

| Control | Behavior and data | Validation and state |
|---|---|---|
| Computation input | Approved before/after versions, complete batch, signed decisions and policy version. | Require complete eligibility, source access and adjudication. Never score drafts. |
| Metric report | VCN, AC, NC and diagnostic DD with denominators, IDs and missingness reasons. | Code calculates values. AI explains the stored report and cannot invent metrics. |
| Outcome | Material change resets streak. Low-change evaluable batch adds one credit. | Count each unique batch once. Empty, failed or partial batches receive no credit. |
| Targeted search | Human approves an evidence target and creates a linked SearchTask. | Retain objective, competing interpretation, priority features and exploration allocation. |
| Acceptance | A replay runs twice on the same approved inputs. | Metric hash and decision agree. Stability credit is not awarded twice. |

POST input {before_version, after_version, batch_id, policy_version, embedding_version}. Return metric_run_id, measures with numerator/denominator/undefined reasons, gate results, outcome and reset_reason. A deterministic worker owns evaluation. LLM receives only the computed report plus approved evidence to propose next search. Provider changes invalidate incompatible vector comparisons. The screenshot intentionally gives material count/streak and a qualitative diff rather than fabricated calibrated distances.

## S08 implementation: freeze a candidate

POST /projects/{id}/stop-candidates

| Control | Behavior and data | Validation and state |
|---|---|---|
| Eligibility packet | Coverage review, k evaluable batches, issue register and approved representation. | Every gate links to supporting records. A review checkbox cannot satisfy a missing gate. |
| Freeze action | Require rationale, human acknowledgement and a final confirmation dialog. | Recheck gates server-side. Freeze representation, scope, policy and evidence manifest. |
| Result | Create immutable candidate C-01 and its independent challenge plan. | Status = challenge pending. This event never authorizes a stop. |
| Blocked / stale | Show failing gate and a link to the required review or search. | Changed version, open issue or failed metric returns a blocked/stale response. |
| Acceptance | A new material issue opens after the screen loads. | Confirmation fails the server recheck. The UI refreshes the blocker without losing rationale. |

Request {representation_version, scope_version, policy_version, metric_run_ids[], coverage_review_id, rationale, expected_version, idempotency_key}. 201 {candidate_id,status:"challenge_pending",frozen_manifest_hash}. On conflict return 409 and current gate packet. Demo k=3 is an illustrative fixture, not a validated default. Human can continue searching even when eligible. Production cannot allow a discretionary bypass of required gates. The frozen candidate is retired, not overwritten, when its representation changes.

## S09 implementation: independent challenges

POST /stop-candidates/{id}/challenge-runs

| Control | Behavior and data | Validation and state |
|---|---|---|
| Plan inputs | Frozen candidate, required test types, reserved evidence partitions and independent reviewers. | Version the plan and effort budget before execution. Lock required tests. |
| Run plan | Queue holdout, adversarial retrieval, sensitivity and expert-review tasks. | Track queued/running/partial/complete/failed per test, with resumable job IDs. |
| Evidence finding | Link each potential contradiction to source, candidate field and run ID. | AI flags a possible consequence. Independent humans determine materiality in S10. |
| Freshness controls | Separate development evidence from unused challenge material. | Used evidence is never relabeled fresh. Model pretraining remains a disclosed limitation. |
| Acceptance | Three tests finish while a required expert review is pending. | Candidate remains challenge pending. Partial success cannot enable authorization. |

Request {plan_version, candidate_snapshot_hash, required_tests[], partition_ids[], reviewer_ids[], idempotency_key}. 202 {challenge_run_id}. Store every test result, error, cost, source set and model configuration. Independent reviewer assignment is a project governance rule. Order permutations are robustness checks, not independent samples. Finding F-09 about familiar technology is synthetic and illustrates a material boundary challenge. Prototype includes preloaded finding data for inspection, not live challenge execution.

## S10 implementation: adjudicate a challenge

POST /challenge-findings/{id}/decisions

| Control | Behavior and data | Validation and state |
|---|---|---|
| Review inputs | Candidate definition, exact finding evidence, materiality classification and rationale. | Human adjudicator sees the frozen representation, not a silently updated draft. |
| Material finding | Retire candidate, reset streak and create a linked revision task for S06. | Move used challenge evidence to development. Later candidate needs fresh challenges. |
| Coverage / unresolved | Coverage gap creates search task. Unresolved creates a blocking issue. | Both block authorization until coverage and convergence are reassessed. |
| Nonmaterial finding | Save reasons and evidence as an adjudicated result. | Do not auto-authorize. All other required challenge outcomes must also pass. |
| Acceptance | Classify E-09 as a material familiarity-boundary change. | C-01 remains in history as failed. No retry can restore its authorization eligibility. |

Request {candidate_id, finding_id, classification, rationale, evidence_ids[], expected_version, idempotency_key}. Transaction appends Decision and associated retirement/reset/partition events. The UI action label should reflect selected classification: Record and reopen, Record coverage gap, Record nonmaterial decision, or Leave unresolved. The visible snapshot shows the material branch. Used challenge material becomes development evidence once revealed and used; preserve exposure history even where a finding is nonmaterial.

## S11 implementation: authorize a scoped stop

POST /stop-candidates/{id}/authorize

| Control | Behavior and data | Validation and state |
|---|---|---|
| Decision packet | Current frozen candidate, coverage, metrics, fresh challenges and issue register. | Required gates must pass for the same representation and scope versions. |
| Human action | Review scope/cutoff, rationale, reopening conditions and acknowledgement. | Confirm a dialog showing signer and candidate. Recheck all gates in the transaction. |
| Saved result | Immutable StopDecision with signer, timestamp, policy and manifest hashes. | Output is provisional saturation within a scope/date. It does not validate a measure. |
| Resource limit | Separate action asks for limitation and records incomplete search. | Never convert budget exhaustion, access failure or an override into saturation. |
| Acceptance | Authorization arrives after evidence invalidates the candidate. | Return 409/blocked. Save draft rationale. Do not create a stop event. |

Request {candidate_id, expected_version, scope_version, evidence_cutoff, rationale, reopening_conditions, acknowledged:true, idempotency_key}. Authorized human role required. Scope and cutoff shown on screen must match the frozen candidate; changing either routes back to scope/candidate review rather than authorizing a mismatched packet. 201 {stop_decision_id,status:"provisional_stop"}. A separate incomplete-search endpoint records resource limits. Reopening creates a new event and work sequence without deleting the historical stop.

## S12 implementation: audit and export

POST /projects/{id}/audit-exports

| Control | Behavior and data | Validation and state |
|---|---|---|
| Package inputs | Brief, scope, evidence, versions, decisions, metrics, challenges and stop record. | Include failed candidates, rejected proposals, open issues and access limitations. |
| Formats / permissions | JSON bundle and methods outline. Source policy excludes restricted documents. | Check rights server-side. A checked review box does not grant redistribution rights. |
| Download | Queue export, validate references and produce a checksummed manifest. | Export completion returns an authenticated download. Never include credentials. |
| AI contribution | Draft a methods narrative from approved records with explicit source IDs. | Label generated prose as draft. Human decisions remain distinguishable. |
| Acceptance | Independent reviewer opens the exported bundle. | Every stop claim resolves to signed decisions and evidence; missing links fail package validation. |

Request {representation_version, stop_decision_id?, format, source_policy, idempotency_key}. 202 {export_job_id}. Preserve schema version, checksums and referenced IDs. A pre-stop export is permitted but must say ongoing/incomplete and contain no saturation assertion. Prototype export is only a synthetic demonstration manifest; it is not the full production audit package. Provide stable IDs, a machine-readable event log, human-readable decision register, pinned model/prompt/policy manifests and permission-filtered evidence links.
