# Prescription Quality Contract

CyberHuaTuo accepts a real solved problem quickly, but it does not treat every submission as a trusted cure. Intake speed and retrieval trust are separate states.

## Quality states

| State | Meaning | Default `cure` result | Soul Ring credit |
|---|---|---:|---:|
| `draft` | Saved or submitted, not independently reproduced | No | No |
| `reviewed` | Root cause, exact fix, stable signatures, safety boundary, and reviewable source accepted | One labeled fallback when no Gold matches | Yes |
| `gold` | Reviewed plus dated reproducible verification and evidence URLs | Yes | Yes |

Missing `quality_status` on a legacy case is treated as `draft` by trusted retrieval. Legacy contributor counts are grandfathered only for statusless cases dated on or before `2026-07-14`; newer statusless or explicit `draft` files do not increase cultivation or Soul Ring counts.

## Historical maintainer incidents

A problem that the maintainer previously encountered and resolved may be accepted as `reviewed` without repeating a costly external or production experiment. It must record `case_origin: maintainer-incident`, the reusable `origin_skill`, a review date, the complete diagnosis and fix, a safe verification procedure, and primary documentation for the relevant technical semantics. The prescription must state that the original experiment was not rerun during the current review.

Historical experience is not sufficient for Gold by itself. Gold still requires the dated reproducible verification and evidence contract below.

Every new prescription also carries a stable `disease_category`. Categories are independent of framework and quality status; they support retrieval and navigation but never raise trust. Legacy cases without a category are displayed as `other` / 综合科. The complete taxonomy is in `docs/prescription-classification.md`.

## Reviewed and Gold requirements

Every Reviewed or Gold prescription must contain a substantive root cause, exact prescription, safety/rollback section, non-placeholder `source_url`, `reviewed_at`, `reviewed_by`, and one or more stable `match_signatures`. These signatures drive trusted retrieval; generic overlap with an entire case is not enough.

Gold additionally requires all of the following:

A Gold prescription must contain all of the following:

1. A substantive root-cause section.
2. A substantive exact prescription section.
3. A substantive verification section with commands and expected results.
4. A reviewable, non-placeholder `source_url`.
5. `reviewed_at` and `verified_at` in `YYYY-MM-DD` format, neither in the future.
6. A named reviewer and `verification_method`.
7. At least one reviewable, non-placeholder HTTP(S) URL in `evidence_urls`.

The runtime never infers Gold from polished prose. An invalid Gold declaration is downgraded for retrieval and appears in `cyberhuatuo quality-audit`.

## User path

```bash
cyberhuatuo cure "<real traceback or error>"
cyberhuatuo cure "<real traceback or error>" --gold-only
cyberhuatuo cure-feedback <case-id> yes --verification "<result>" --verification-method "<method>"
cyberhuatuo departments
cyberhuatuo quality-audit
```

`cure` is offline-first: it scans bundled local cases, loads no LLM, starts no vector database, and executes no fix. It returns Gold first; if no Gold signature matches, it may return exactly one high-confidence Reviewed candidate with an explicit verify-first label. `--gold-only` suppresses that fallback, while `--include-drafts` remains an explicit human-review mode. `--category` filters by a stable department key without changing trust labels.

`cure-feedback` accepts `yes`, `partial`, or `no`, validates that the case exists, and appends a local case-bound evidence event. It does not retain the original query or traceback and does not promote a case automatically.

New contributions are always generated as `draft`, even when the submitter includes verification. Maintainers promote them only after reproduction and review. Real-time sharing therefore means immediate intake and visible review status, not immediate distribution as a trusted default cure.
