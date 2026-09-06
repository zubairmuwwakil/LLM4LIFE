# Diary-derived People facts and interactions

**Phase:** People Phase 4  
**Purpose:** turn diary/journal evidence into reviewable structured People facts and interactions without silently persisting model inference or copying narrative into Neon.

## Boundary

Diary entries remain narrative authority in Obsidian. They are evidence sources, not person entities and not an automatic database feed.

The pipeline has two private stages:

1. **Build a review batch** from diary entries that already have at least one resolved person identity.
2. **Validate human-approved proposals** into a private apply-disabled plan.

There is intentionally no Neon write path in this helper.

## Preconditions

First run the comprehensive People ↔ Obsidian candidate review:

```bash
python3 scripts/people_obsidian_candidates.py
```

That creates:

```text
.private/people/obsidian_candidate_review.json
```

Only diary evidence with an already-resolved `person_id` is eligible for fact review. Plain-name mentions remain excluded until their person identity is separately approved.

## Build a private batch

```bash
python3 scripts/people_diary_fact_review.py batch --batch-size 25
```

Default output:

```text
.private/people/diary_fact_review_batch.json
.private/people/diary_fact_review_batch_receipt.json
```

The batch is private and may contain raw diary narrative so a human or trusted local/interactive agent can review the actual evidence. The public-safe receipt contains aggregate counts only.

Use `--offset` and `--batch-size` to process the corpus incrementally.

## Proposal contract

Each batch item has an empty `proposals` array. Reviewers may add only source-grounded proposals.

### Fact proposal

Required fields:

```json
{
  "proposal_type": "fact",
  "person_id": "<resolved UUID from this batch item>",
  "fact_key": "likes.example",
  "value": true,
  "sensitivity_class": "standard",
  "evidence_basis": "explicit_user_statement",
  "approved": true
}
```

### Interaction proposal

```json
{
  "proposal_type": "interaction",
  "person_ids": ["<resolved UUID from this batch item>"],
  "interaction_type": "met_in_person",
  "occurred_on": "2025-01-02",
  "summary": "Optional reviewed summary, maximum 280 characters",
  "sensitivity_class": "standard",
  "evidence_basis": "explicit_user_statement",
  "approved": true
}
```

## Extraction rules

Only explicit diary statements are eligible. Do not infer or persist a person's:

- motives or intentions;
- personality traits;
- diagnoses or health state;
- sexuality or sex-life attributes;
- religion;
- political beliefs;
- relationship status;
- other sensitive characteristics;

unless the diary itself explicitly states the fact and the proposal is then deliberately reviewed. Sensitive explicit facts may be represented in the private review, but they are never silently persisted.

A proposal about a person reached only through a plain-name candidate is not eligible until the identity link has separately been approved.

## Validate reviewed proposals

Save the reviewed private artifact as:

```text
.private/people/diary_fact_reviewed.json
```

Then run:

```bash
python3 scripts/people_diary_fact_review.py validate
```

Default output:

```text
.private/people/diary_fact_plan.json
.private/people/diary_fact_plan_receipt.json
```

Validation checks:

- referenced person IDs are resolved for that source entry;
- only `fact` and `interaction` proposal types are accepted;
- facts use stable lowercase machine keys;
- interactions carry an explicit date;
- evidence basis is exactly `explicit_user_statement`;
- sensitivity is classified as `standard` or `sensitive`;
- unapproved proposals are omitted;
- raw diary narrative is stripped from the plan;
- final source kinds are `user_edited_import` for facts and `interaction_import` for interactions;
- `model_suggestion` is never accepted as a persisted source kind.

The resulting plan contains:

```text
apply_allowed: false
```

A separate importer and separate user authorization are required before any diary-derived fact or interaction may be written to Neon.

## Privacy

The following must stay private and gitignored:

```text
.private/people/diary_fact_review_batch.json
.private/people/diary_fact_reviewed.json
.private/people/diary_fact_plan.json
```

Public documentation and receipts must not contain diary prose, names, person IDs, note paths, emails, phones, or other narrative payloads.

## Why this separation matters

Diary text often mixes observations, interpretations, feelings, and sensitive context. Identity resolution, fact extraction, human approval, and database persistence therefore remain separate gates. This keeps Obsidian as narrative truth while allowing carefully reviewed structured facts and interaction dates to become operational People data later.
