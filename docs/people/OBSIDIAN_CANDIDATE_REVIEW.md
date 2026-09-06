# People ↔ Obsidian Candidate Review

**Phase:** People Phase 4  
**Purpose:** create a private, reviewable identity map before any Obsidian frontmatter or Neon mutation

## Why this exists

The live vault contains canonical person profiles under `20 Areas/People/**/00 *.md`. The candidate-review helper compares those canonical notes with the private post-cutover Google Contacts snapshot and, when `DATABASE_URL` is available, resolves Google provider IDs to active Neon `person_id`s.

Candidate generation is read-only. It never writes note frontmatter and never inserts Neon refs.

## Matching classes

Candidates are ranked with these review-only classes:

1. `strong_identifier` — exact structured email and/or phone from person-note frontmatter.
2. `exact_name` — exact normalized name/alias match.
3. `token_name` — same first and last name with only middle-name token differences.
4. `fuzzy_name` — high name similarity (`>= 0.88`), shown only as a suggestion.

No class is automatically accepted. Name-based matching is never an auto-link path.

Only structured frontmatter contact fields are considered strong identifiers. Narrative prose is not mined for phone numbers or emails.

## Private inputs

Default inputs:

```text
OBSIDIAN_VAULT_PATH
DATABASE_URL (optional for candidate generation; required to accept a mapping)
.private/people/google_people_live_after_apple.json
```

The Google snapshot stays private and is already gitignored under `.private/`.

## Generate review candidates

```bash
python3 scripts/people_obsidian_candidates.py
```

This writes:

```text
.private/people/obsidian_candidate_review.json
.private/people/obsidian_candidate_receipt.json
```

The review file contains names, provider IDs, candidate person IDs when resolvable, and note paths. It is private and must never be committed.

The aggregate receipt contains no names, emails, phones, provider IDs, person IDs, or note paths.

## Interactive approval

After candidate generation succeeds:

```bash
python3 scripts/people_obsidian_candidates.py --interactive
```

For each canonical person note, the command shows up to three candidates and asks the user to choose or skip. A second confirmation is required before a choice enters the private manifest.

If a candidate does not have a resolved Neon `person_id`, the command refuses to accept it and asks for `DATABASE_URL` to be configured.

Accepted choices are written only to:

```text
.private/people/obsidian_person_links.json
```

No note or database mutation occurs during interactive approval.

## Apply after review

Once the private mapping manifest is reviewed:

```bash
python3 scripts/people_obsidian_link.py \
  --manifest .private/people/obsidian_person_links.json \
  --apply-frontmatter
```

This adds the managed `llm4life_person_id` and `llm4life_note_id` fields atomically.

Then dry-run the Neon external-ref import:

```bash
python3 scripts/import_people_obsidian_refs.py
```

Only after that succeeds should the validated refs be applied:

```bash
python3 scripts/import_people_obsidian_refs.py --apply
```

## Safety boundaries

- No same-name-only automatic linking.
- No fuzzy automatic linking.
- No candidate-generation writes.
- Archived profiles are excluded by default; opt in with `--include-archived`.
- Only canonical `00 *.md` notes with `type: person` are scanned.
- Narrative remains in Obsidian.
- Note paths never enter Neon.
- Held Google identity conflicts, weak matches, and note candidates from earlier People phases remain separate.
