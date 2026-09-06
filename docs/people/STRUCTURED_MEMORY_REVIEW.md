# Structured People memory review

**Phase:** People Phase 4  
**Purpose:** extract important dates and resolved person-to-person relationships from the live Obsidian vault without turning narrative or ambiguous names into durable Neon memory automatically.

## Inputs

The reviewer reuses the private identity work already completed by `people_obsidian_candidates.py`:

- `.private/people/obsidian_candidate_review.json`
- `.private/people/obsidian_person_links.json`
- `OBSIDIAN_VAULT_PATH`

Default source roots are:

- `20 Areas/People`
- `00 Inbox/iCloud Calendar Import 2026-06-25`
- `10 Daily/Diary`

These include active profiles, archived People, imported calendar summaries, recurring People notes, and diary material. The scan is read-only.

## Candidate policy

The reviewer deliberately favors precision over recall.

### Important dates

It surfaces explicit date anchors such as:

- birthdays;
- friendship anniversaries;
- relationship anniversaries;
- generic anniversaries;
- memorial/remembrance anchors.

A recurring calendar occurrence such as `2021-10-10 — Person birthday` establishes month/day, not a birth year. The reviewer therefore stores the year as unknown unless the source explicitly establishes the origin year.

Memorial/death-related date candidates are classified as sensitive and are held by the routine importer.

### Person-to-person relationships

Durable graph edges require two already-resolved Neon People IDs. Supported explicit relation vocabulary includes parent, sibling, child, spouse/partner, grandparent, aunt/uncle, friend and coworker.

The reviewer can retain a private held candidate when a source explicitly names a relationship but the other person's identity is unresolved. Held names never enter `person_relationship_edges`.

The existing `llm4life.relationships` table remains the user-to-person relationship state and is not replaced by this graph.

## One-command safe workflow

After pulling the latest repo and ensuring the Phase 4 Python requirements are installed, the preferred local flow is:

```bash
bash scripts/run_people_structured_memory_review.sh
```

This performs, in order:

1. interactive candidate review;
2. validation into an apply-disabled private plan;
3. a production Neon dry-run.

The wrapper never passes `--apply`, so it cannot write date or relationship rows to Neon.

## Manual workflow

First refresh the comprehensive identity review if necessary:

```bash
python3 scripts/people_obsidian_candidates.py --interactive
```

Then build and interactively review structured memory candidates:

```bash
python3 scripts/people_structured_memory_review.py build --interactive
```

Private outputs:

- `.private/people/structured_memory_review.json`
- `.private/people/structured_memory_review_receipt.json`

The review file contains private source evidence so the user can make an informed decision. The aggregate receipt contains no names, People IDs, note paths or raw evidence.

## Validate

After the review:

```bash
python3 scripts/people_structured_memory_review.py validate
```

Outputs:

- `.private/people/structured_memory_plan.json`
- `.private/people/structured_memory_plan_receipt.json`

The plan explicitly remains `apply_allowed: false`; validation does not write Neon.

## Neon dry-run

Install Phase 4 requirements if needed:

```bash
python3 -m pip install -r requirements-people-phase4.txt
```

Then run the importer without `--apply`:

```bash
python3 scripts/import_people_structured_memory.py
```

The importer verifies:

- all referenced People are active;
- the People memory graph schema is live;
- birthday/anniversary singleton conflicts are held;
- conflicting relationship edges are held;
- deterministic IDs make exact reruns idempotent;
- sensitive proposals are refused by the routine path.

Private receipt:

- `.private/people/structured_memory_neon_import_receipt.json`

## Apply gate

A write requires a separate explicit authorization after the user has reviewed the plan and production dry-run:

```bash
python3 scripts/import_people_structured_memory.py --apply --user-authorized
```

Do not infer authorization merely because a review file exists.

## Privacy boundary

The Neon records contain structured date/edge data and provenance system identifiers only. They do not contain:

- Obsidian note paths;
- raw source lines;
- diary prose;
- unresolved names;
- subjective relationship analysis.

Rich narrative remains in Obsidian.
