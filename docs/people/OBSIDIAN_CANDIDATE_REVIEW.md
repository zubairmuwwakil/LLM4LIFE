# People ↔ Obsidian Candidate Review

**Phase:** People Phase 4  
**Purpose:** create a private, reviewable identity map and diary-evidence inventory before any Obsidian frontmatter or Neon mutation

## Source model

The Obsidian People area is not limited to canonical `00 *.md` profiles. The review helper now treats the vault as three distinct source classes:

1. **Active canonical profiles** — `20 Areas/People/**/00 *.md` notes with `type: person`.
2. **Archived people** — both canonical archived profiles and legacy person folders under `20 Areas/People/ZZ_Archived`, including folders that contain person notes such as `Interests.md`, `Likes.md`, or `Personality.md` but no `00` profile.
3. **Diary / journal evidence** — notes under `Journal Entries` or with `source: imported_diary_text`.

Diary notes are evidence sources, **not person entities**. They can contain person references, relationship history, and facts that should eventually be attached to the relevant person with provenance. Raw diary prose remains in Obsidian.

Candidate generation is read-only. It never writes note frontmatter and never inserts Neon refs.

## Matching classes

Person sources are ranked with these review-only classes:

1. `strong_identifier` — exact structured email and/or phone from person-note frontmatter.
2. `exact_name` — exact normalized name/alias match.
3. `token_name` — same first and last name with only middle-name token differences.
4. `fuzzy_name` — high name similarity (`>= 0.88`), shown only as a suggestion.

No class is automatically accepted. Name-based matching is never an auto-link path.

Only structured frontmatter contact fields are considered strong identifiers. Narrative prose is not mined for phone numbers or emails.

## Legacy archived folders

Archived people are included by default.

A legacy folder may represent one person even when it has no canonical `00` profile. The scanner identifies person-like folders from their direct narrative notes and archive MOC links. MOC-only/category folders are excluded.

When a legacy folder is approved, all person-specific Markdown notes directly in that folder are mapped to the same Neon `person_id`. MOCs, hidden notes, and category index notes are not included.

Use `--exclude-archived` only when a deliberately active-only review is needed. `--include-archived` remains accepted as a compatibility flag but is no longer required.

## Diary / imported journal evidence

Diary evidence scanning is enabled by default for:

- paths containing `Journal Entries`; or
- notes whose frontmatter contains `source: imported_diary_text`.

The private review records:

- the source note and source date;
- explicit person/profile wikilinks;
- unique alias/name mentions as `review_required`;
- ambiguous-reference counts;
- whether a referenced person source already has a known `person_id`.

The scanner does **not** copy diary prose into the review object, public receipt, or Neon. It does not infer or persist facts automatically. Plain name mentions are review-only and ambiguous same-name references are not resolved automatically.

Use `--exclude-diary-sources` when diary evidence intentionally should not be scanned.

## Existing mappings are preserved

The default private manifest is:

```text
.private/people/obsidian_person_links.json
```

If it already exists, candidate generation reuses those mappings. Interactive review merges newly approved mappings into the existing manifest instead of replacing prior approvals.

Mappings already present in managed Obsidian frontmatter (`llm4life_person_id`) are also recognized as existing mappings.

## Private inputs

Default inputs:

```text
OBSIDIAN_VAULT_PATH
DATABASE_URL (optional for candidate generation; required to accept a new mapping)
.private/people/google_people_live_after_apple.json
.private/people/obsidian_person_links.json (optional existing mappings)
```

Private artifacts stay under `.private/` and must never be committed.

## Generate review candidates

```bash
python3 scripts/people_obsidian_candidates.py
```

This writes:

```text
.private/people/obsidian_candidate_review.json
.private/people/obsidian_candidate_receipt.json
```

The private review may contain names, provider IDs, candidate person IDs, note paths, and aggregate diary-reference metadata.

The aggregate receipt contains no names, emails, phones, provider IDs, person IDs, note paths, or diary prose. It reports only source counts and matching/evidence totals.

## Interactive approval

```bash
python3 scripts/people_obsidian_candidates.py --interactive
```

The command skips already-mapped sources. For each unresolved person source, it shows up to three candidates and asks the user to choose or skip. A second confirmation is required before a choice enters the private manifest.

If a candidate does not have a resolved Neon `person_id`, the command refuses to accept it and asks for `DATABASE_URL` to be configured.

No note or database mutation occurs during interactive approval.

## Apply after review

Once the private mapping manifest is reviewed:

```bash
python3 scripts/people_obsidian_link.py \
  --manifest .private/people/obsidian_person_links.json \
  --apply-frontmatter
```

This adds the managed `llm4life_person_id` and `llm4life_note_id` fields atomically to approved note paths.

Then dry-run the Neon external-ref import:

```bash
python3 scripts/import_people_obsidian_refs.py
```

Only after that succeeds should the validated refs be applied:

```bash
python3 scripts/import_people_obsidian_refs.py --apply
```

Diary-derived structured facts/interactions are a later reviewed step. This candidate scanner does not write them.

## Safety boundaries

- Archived person sources are included by default; `--exclude-archived` is explicit opt-out.
- Legacy archived person folders do not need a canonical `00` note to be discoverable.
- Diary entries are evidence sources, never person entities.
- No same-name-only automatic linking.
- No fuzzy automatic linking.
- No diary fact auto-write.
- Existing approved mappings are preserved.
- No candidate-generation writes.
- Raw narrative remains in Obsidian.
- Note paths never enter Neon.
- Public receipts are aggregate-only and contain no diary prose.
- Held Google identity conflicts, weak matches, and note candidates from earlier People phases remain separate.
