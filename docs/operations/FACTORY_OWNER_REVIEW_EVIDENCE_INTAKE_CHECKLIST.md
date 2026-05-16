# Factory Owner Review Evidence Intake Checklist

## Purpose

This checklist defines the minimum evidence required before a future D6 stage can record factory owner/reviewer feedback.

It is an intake gate. It does not mean owner review has completed, and it does not approve production deployment or live/shared DB migration.

## Evidence intake checklist

- [ ] Evidence package identifies the selected branch.
- [ ] Evidence package identifies the selected commit SHA.
- [ ] Evidence package identifies runtime mode.
- [ ] Evidence package identifies review date.
- [ ] Evidence package identifies operational owner or explicitly defers that role.
- [ ] Evidence package identifies technical reviewer or explicitly defers that role.
- [ ] Evidence package identifies DB owner or explicitly defers that role.
- [ ] Evidence package identifies rollback owner or explicitly defers that role.
- [ ] Every required route has an observation, skip reason, or block reason.
- [ ] No-click confirmation is present.
- [ ] No-upload confirmation is present.
- [ ] No ETL/backfill/materialization confirmation is present.
- [ ] No carry-forward reconciliation confirmation is present.
- [ ] No live/shared DB migration confirmation is present.
- [ ] No model retraining/promotion confirmation is present.
- [ ] DB/artifact safety confirmation is present.
- [ ] Accepted pilot risks are marked.
- [ ] Rejected production risks are marked.
- [ ] Decision category is present.
- [ ] Final owner/reviewer notes are present or explicitly deferred.

## Required identity fields

| Field | Required? | Intake status |
| --- | --- | --- |
| operational owner name or explicit deferral | yes | TBD |
| technical reviewer name or explicit deferral | yes | TBD |
| DB owner name or explicit deferral | yes | TBD |
| rollback owner name or explicit deferral | yes | TBD |
| initials or decision marker for each non-deferred role | yes | TBD |
| review date | yes | TBD |

## Required route evidence fields

| Route | Required intake field | Intake status |
| --- | --- | --- |
| ETL Pipeline | observation, skip reason, or block reason | TBD |
| Canonical Operations Overview | observation, skip reason, or block reason | TBD |
| Energy Analysis | observation, skip reason, or block reason | TBD |
| Operational Decision Support | observation, skip reason, or block reason | TBD |
| Efficiency Prediction & Governance | observation, skip reason, or block reason | TBD |
| Maintenance | observation, skip reason, or block reason | TBD |
| Experimental Intelligence Lab | hidden-in-`demo_readonly` confirmation or approved `pilot_review` observation | TBD |

Each route entry must include runtime mode, expected observation, forbidden-action confirmation, evidence note or screenshot reference, observed status, and reviewer marker.

## Required DB safety evidence

| Safety evidence | Required? | Intake status |
| --- | --- | --- |
| GitHub-safe tree DB scan result | yes | TBD |
| review/smoke workspace DB scan result, if app was launched | yes if applicable | TBD |
| `manufacturing_data.db` untracked confirmation | yes | TBD |
| no DB files staged confirmation | yes | TBD |
| no raw Excel files staged confirmation | yes | TBD |
| no generated `etl_outputs` artifacts staged confirmation | yes | TBD |
| no model artifacts staged confirmation | yes | TBD |
| no temp DB promoted confirmation | yes | TBD |
| no live/shared DB migration confirmation | yes | TBD |

## Required risk acceptance fields

| Pilot risk | Required decision |
| --- | --- |
| Route walkthrough is controlled owner-review evidence, not production launch | accept / reject / defer |
| Local runtime DB remains a review/rehearsal boundary | accept / reject / defer |
| Experimental Intelligence Lab remains non-defended for production claims | accept / reject / defer |
| Live/shared DB migration is still future gated work | accept / reject / defer |
| Monitoring, access control, support ownership, and incident response remain future work | accept / reject / defer |

## Required rejected-risk fields

| Production risk | Required decision |
| --- | --- |
| Live/shared DB migration without migration gate | reject / defer |
| Promoted DB writes without backup/checksum/rollback evidence | reject / defer |
| Runtime carry-forward adoption without adoption gate | reject / defer |
| Model artifact promotion without model-promotion gate | reject / defer |
| Production launch completion without owner approval | reject / defer |
| Production launch completion without monitoring/support/access readiness | reject / defer |

## Required owner / reviewer fields

| Field | Required intake rule |
| --- | --- |
| operational owner decision | Required for acceptance; otherwise mark deferred. |
| technical reviewer decision | Required for acceptance; otherwise mark deferred. |
| DB owner decision | Required before any migration-related claim; otherwise mark deferred. |
| rollback owner decision | Required before any promoted DB write; otherwise mark deferred. |
| final decision category | Required for D6 decision record. |
| final decision notes | Required or explicitly deferred. |

## Required timestamp / branch / commit fields

| Field | Required intake rule |
| --- | --- |
| selected branch | Must match reviewed branch. |
| selected commit SHA | Must be immutable and recorded before review. |
| review timestamp/date | Must be present. |
| evidence package timestamp/date | Must be present or explicitly same as review date. |
| runtime mode | Must be `demo_readonly` unless `pilot_review` is explicitly justified. |

## Completeness criteria

Evidence is complete only if:

- required identity fields are present or explicitly deferred;
- branch and commit SHA are present;
- route evidence exists for every required route;
- forbidden-action confirmations are present;
- DB/artifact safety evidence is present;
- accepted pilot risks are marked;
- rejected production risks are marked;
- decision category is present;
- no evidence contradicts the no-ETL/no-migration/no-write boundaries.

## Reasons to reject incomplete evidence

Reject the evidence package if:

- owner/reviewer identity is missing and not explicitly deferred;
- branch or commit SHA is missing;
- any required route lacks observation, skip reason, or block reason;
- no-click or no-upload confirmation is missing;
- no DB/artifact safety confirmation is missing;
- any DB file appears inside the GitHub-safe tree;
- any DB file is staged;
- raw Excel files, generated `etl_outputs`, or model artifacts are staged unexpectedly;
- live/shared DB migration is claimed as executed;
- carry-forward is claimed as active runtime behavior;
- production deployment is claimed complete;
- owner acceptance is implied without a real owner/reviewer decision.

## How D6 should process returned evidence

D6 should:

- verify branch and commit SHA;
- verify the returned evidence against this checklist;
- keep owner acceptance pending if evidence is incomplete;
- record acceptance only if actual owner/reviewer evidence is complete;
- preserve NO-GO for production deployment unless a separate production gate is explicitly approved;
- preserve NO-GO for live/shared DB migration unless a separate migration gate is explicitly approved;
- preserve disabled-by-default runtime carry-forward unless a separate adoption gate is explicitly approved;
- keep runtime behavior unchanged unless a future prompt explicitly opens implementation scope.

