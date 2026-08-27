# Autonomous Knowledge Capture

_Last updated: 2026-08-27_

## Purpose

The AI may extract **durable knowledge and context** from conversations and write it to Obsidian even when the user does not explicitly say `save this`.

The goal is not to archive conversations. The goal is to convert useful conversational output into a maintained personal knowledge graph.

## Capture threshold

Capture something when it is likely to remain useful beyond the current conversation, such as:

- a durable insight or mental model;
- a decision with rationale;
- a lesson learned or mistake worth remembering;
- a reusable framework, checklist, heuristic, or process;
- research conclusions that will likely be referenced again;
- meaningful project context or reasoning not better owned by GitHub/Jira;
- a stable preference or workflow rule that materially changes future behavior;
- a useful relationship, life, career, or personal-context note when it clearly belongs in the existing vault structure;
- a source/reference worth preserving and linking.

Do **not** capture merely because something was mentioned.

## Noise filter

Normally skip:

- casual chatter;
- transient questions whose answer has no durable value;
- one-off logistics already owned by Things or Calendar;
- duplicate facts already represented in a canonical note;
- raw assistant prose when a shorter synthesized insight is enough;
- temporary status information that will quickly become stale;
- notifications or receipts;
- information whose canonical live state belongs in Notion, Jira, GitHub, Calendar, Things, or a dedicated app.

## Sensitive-content rule

Implicit capture is **not permission to indiscriminately persist sensitive data**.

Do not autonomously create durable notes containing secrets, passwords, API keys, authentication material, full financial account identifiers, government identifiers, or similarly high-risk credentials/identifiers.

For unusually sensitive personal material, prefer leaving it in the originating context unless the user explicitly asks for durable storage and the destination is appropriate.

## Routing into Obsidian

Before creating a new note:

1. search for an existing canonical note;
2. update/merge that note when appropriate;
3. otherwise choose the correct PARA location;
4. add useful frontmatter and links without over-tagging;
5. link to canonical external records rather than duplicating their live state.

Typical destinations:

- `10 Daily` for dated narrative/context that is inherently chronological;
- `20 Areas` for ongoing responsibilities and durable life context;
- `30 Projects` for reasoning/context around a finite active project when that reasoning is not already canonical in the project repo;
- `50 Resources` for reusable knowledge, references, frameworks, research, and prompts;
- `90 Archive` for superseded material that remains worth retaining.

## Conversation-to-note transformation

Do not dump full transcripts into Obsidian by default.

Prefer this transformation:

```text
conversation
  -> identify durable signal
  -> check canonical home
  -> synthesize only what matters
  -> preserve source/provenance when useful
  -> update/link/merge
  -> log meaningful autonomous write
```

A captured note should be understandable later without needing the full conversation.

## Updating existing knowledge

When a conversation changes an existing belief or decision:

- update the canonical note rather than creating `v2`, `new`, or duplicate notes;
- preserve important prior reasoning when it explains why the decision changed;
- distinguish `superseded` from `wrong`;
- keep unresolved conflicts explicit;
- repair links/MOCs when necessary.

## Learning exception

For software-engineering learning, the Obsidian vault's `AGENTS.md` and canonical AI Operating Manual remain higher-priority constraints.

Conversation capture must not turn study sessions into passive AI-authored notes. The AI may capture mistakes, user-generated reasoning, retrieval prompts, transfer questions, and already-understood material, but it must preserve the retrieval-first learning model.

## Receipts

Do not interrupt every conversation with a verbose capture report.

When a meaningful note was autonomously created or materially rewritten, include a compact receipt when useful, for example:

```text
Obsidian: updated `Tool Selection Heuristics` with today's conclusion.
```

Multiple captures from one interaction should be consolidated.

## Audit

Meaningful autonomous captures, merges, or material rewrites should be recorded in the central AI Activity Log when practical. Routine link or frontmatter maintenance does not need individual log spam.

## Guiding rule

> Capture durable signal, not conversational exhaust.
