# Profile relationship review

**Phase:** People Phase 4  
**Purpose:** extract explicit person-to-person relationships from resolved Obsidian People profiles while keeping unresolved names private and out of Neon.

## Why this pass exists

The general structured-memory reviewer handles explicit relationship forms such as `mother: Name` and sentence-style relationships. Real People profiles also use section-oriented notes such as:

```text
Family & Friends

Person A (closer friend)
Person B (cousin)
Person C (mom)
[[Other Person]] (brother)
```

This profile pass recognizes that structure without broad free-form NLP.

## Resolution order

A durable relationship edge still requires two stable People IDs. Target resolution is deliberately conservative:

1. exact Obsidian wikilink path already mapped to a Person;
2. exact same-folder wikilink already mapped to a Person;
3. unique already-approved alias from the private People identity review;
4. otherwise hold the target name privately for identity review.

A plain or fuzzy name never creates a Neon graph edge automatically.

## Supported relationship vocabulary

The profile pass currently recognizes:

- parent (`mom`, `mother`, `dad`, `father`);
- sibling (`sister`, `brother`);
- child (`daughter`, `son`);
- spouse / partner;
- grandparent;
- aunt / uncle;
- niece / nephew;
- cousin;
- friend;
- coworker / colleague.

Modifiers such as `closer friend` or `close cousin` are allowed because the relationship word itself remains explicit.

## Directionality

`person_relationship_edges` is directional. If a resolved profile contains `Kandice (mom)`, the graph edge means Kandice is a parent of the profile owner. Symmetric relationships such as friend, sibling, and cousin use the profile owner as the source by default.

## Local relationship-only run

```bash
bash scripts/run_people_relationship_review.sh
```

The runner:

1. rebuilds the private structured-memory review without asking about dates;
2. scans resolved People profiles for Family & Friends sections;
3. enriches the private review with resolved and held relationship candidates;
4. prompts only for resolved standard relationship edges;
5. validates the private plan;
6. runs the Neon importer in dry-run mode only.

No Neon or Obsidian writes occur.

## Private outputs

- `.private/people/structured_memory_review.json`
- `.private/people/profile_relationship_review_receipt.json`
- `.private/people/structured_memory_plan.json`
- `.private/people/structured_memory_neon_import_receipt.json`

Only aggregate receipts are appropriate for the public repository. Raw names, People IDs, note paths, and source evidence remain private.
