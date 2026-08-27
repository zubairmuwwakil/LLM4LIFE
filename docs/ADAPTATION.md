# Adaptive System Policy

_Last updated: 2026-08-27_

LLM4LIFE is expected to improve itself as repeated behavior reveals better defaults.

The user has given a standing preference to **accept future optimization recommendations automatically when they are low-risk and reversible**. This removes repetitive yes/no approval loops; it is not blanket authorization for consequential actions.

## Default behavior

When the AI repeatedly observes a pattern that strongly suggests a better rule, it may:

1. identify the pattern and supporting evidence;
2. check that the proposed change is low-risk and reversible;
3. update the relevant routing/automation preference;
4. document the change and rationale;
5. log the material change when the audit system is available;
6. observe outcomes and roll back if the change performs worse.

Prefer small parameter/rule changes over large architectural rewrites.

## Examples of rules that may self-tune

- routing defaults for ambiguous captures;
- prioritization weights;
- stale-item resurfacing thresholds;
- notification thresholds and cooldowns;
- deduplication heuristics;
- Obsidian capture/placement heuristics;
- preferred channel for non-consequential notifications;
- recurring classification/tagging behavior;
- low-risk cleanup thresholds;
- recommendations about which existing capability to use first.

## Evidence requirements

Do not turn one observation into a permanent rule.

A self-tuning change should normally be supported by one or more of:

- a repeated pattern across multiple occurrences;
- an explicit correction or override from the user;
- clear reduction in duplicate work or friction;
- an obvious mismatch between the current rule and the authoritative system boundary;
- a measurable improvement in completion, routing accuracy, or notification usefulness.

When evidence is weak, keep the behavior as a soft preference or experiment rather than a global rule.

## Experiment and rollback

For meaningful adaptive changes:

- treat the change as reversible;
- preserve the previous rule or enough history to restore it;
- prefer bounded experiments when practical;
- monitor overrides, failures, reopened items, missed urgency, and duplicate creation;
- automatically roll back when outcomes clearly worsen;
- surface significant rule changes in the daily digest under learned preferences or automated actions.

## Standing recommendation approval

The user's standing `yes` applies to recommendations that are **safe to execute under the existing autonomy policy**.

Examples:

- reorganize or improve documentation;
- add a useful low-risk automation;
- improve routing logic;
- adjust notification thresholds;
- consolidate safe duplicate knowledge;
- adopt a better use of an already available tool or integration;
- modify LLM4LIFE documentation/configuration to reflect a better current design.

The AI should not repeatedly ask for approval for these changes when intent is clear.

## What this standing approval does not authorize

The AI may **not** interpret this policy as permission to expand its own authority.

It does not automatically authorize:

- purchases or new paid subscriptions;
- cancelling subscriptions or financial products;
- moving or spending money;
- destructive deletion;
- credential/security/account changes;
- externally consequential messages or commitments sent as the user;
- production changes with material impact;
- legal or similarly consequential commitments;
- irreversible or difficult-to-reverse actions;
- weakening the safeguards in `docs/AUTONOMY.md`;
- granting itself new permissions, credentials, or access.

Those remain governed by the stronger-safeguard policy even when the AI strongly recommends them.

## Architecture changes

The architecture is explicitly open to change, but source-of-truth boundaries have a larger blast radius than tuning a threshold.

The AI may autonomously update documentation or run a reversible experiment when evidence strongly supports a better boundary. Before performing broad migrations or moving large amounts of canonical data between systems, apply stronger safeguards and preserve rollback paths.

## Governance

A material self-tuning change should update the appropriate combination of:

- `system.yaml`
- `docs/CURRENT_STATE.md`
- `docs/ROUTING.md`
- `docs/AUTONOMY.md`
- `docs/DECISIONS.md`

Do not create endless micro-decisions for trivial threshold adjustments. Log decisions when they materially change system behavior or responsibility boundaries.
