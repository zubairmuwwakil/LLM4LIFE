# Security & Privacy

_Last verified: 2026-08-27_

LLM4LIFE coordinates tools that can contain private life, work, financial, communication, and account context. Security is therefore part of the architecture, not an afterthought.

## Repository visibility

`LLM4LIFE` is currently a **public repository**.

Treat every committed line as potentially visible to anyone.

The repo should document **structure and policy**, not private content.

## Never commit

Do not commit any of the following to LLM4LIFE:

- passwords;
- API keys or OAuth tokens;
- cookies/session material;
- private SSH keys;
- recovery codes;
- account or routing numbers;
- government/high-risk identifiers;
- authentication URLs containing secrets;
- private email/message bodies unless intentionally public;
- confidential employer/client information;
- medical/health records;
- private diary or intimate relationship content;
- raw AI Activity Log exports containing sensitive context.

Use placeholders and conceptual identifiers instead.

## Public architecture vs private state

Good content for this repo:

- `Things 3 owns the personal backlog.`
- `Movable work defaults to 1 PM–9 PM.`
- `The planner should search before creating duplicates.`
- `Slack is the work communication surface.`

Bad content for this repo:

- actual credentials;
- private message transcripts;
- bank/account identifiers;
- private people profiles;
- full Calendar event details that expose sensitive life information;
- detailed personal records copied from Notion/Obsidian.

The AI may use private connected context to operate the system without reproducing that private context in this public design repository.

## Least-privilege rule

A new integration should receive only the access necessary to perform its job.

Examples:

- a Things bridge should use supported Things automation surfaces, not raw database manipulation;
- a Discord bridge should not gain access to unrelated servers/channels by default;
- an inventory reader does not need permission to send external messages;
- a calendar planner does not need financial transaction authority.

Standing approval for safe recommendations **does not authorize new credentials or permissions**.

## Consequence boundary

The system may autonomously perform low-risk reversible organization.

Stronger safeguards remain required for:

- purchases/subscriptions;
- cancelling services/financial products;
- moving money;
- security or credential changes;
- destructive deletion;
- production changes with material impact;
- externally consequential messages or commitments;
- legal commitments;
- granting the AI broader access.

The AI may never reinterpret its own optimization policy to remove these safeguards.

## Audit logging

The Notion **AI Activity Log** should record enough to answer:

- what changed;
- where it changed;
- whether it succeeded;
- whether it was reversible;
- where the source/destination can be found.

It should **not** record:

- private chain-of-thought;
- secrets/tokens;
- unnecessary full private message bodies;
- sensitive information when a short non-sensitive description is sufficient.

## Knowledge capture privacy

Autonomous conversation-to-Obsidian capture should preserve durable value without becoming surveillance or transcript archiving.

Do not implicitly persist:

- credentials/secrets;
- high-risk identifiers;
- unusually sensitive personal material where explicit storage intent would be more appropriate.

See `docs/KNOWLEDGE_CAPTURE.md`.

## Connector verification

Never treat a tool as connected because it is mentioned in policy.

Before live operations:

1. verify the connector/bridge exists;
2. perform a harmless read when necessary;
3. verify exact write capability before promising a write;
4. do not expose account identifiers in public documentation;
5. if access disappears, degrade gracefully and report the limitation.

## Local bridge security

Future local bridges for Things/Obsidian should:

- use supported app interfaces;
- validate incoming payloads;
- restrict commands/actions to an allowlist;
- bind only to necessary local interfaces;
- avoid exposing unauthenticated network endpoints;
- keep credentials out of source control;
- log actions without logging secret payloads;
- make destructive operations harder than reversible ones.

## Security findings

Do not place detailed vulnerability findings or credential-exposure specifics in this public repository when doing so would increase risk.

Track sensitive remediation privately and keep only the generalized rule/status here.

If a repository is ever suspected to have contained a secret, treat the secret as compromised and rotate/revoke it; deleting the current file is not sufficient because Git history may retain it.

## Public-repo review checklist

Before committing an AI-generated documentation update, check:

- [ ] No secrets or credentials
- [ ] No private emails/account IDs
- [ ] No sensitive personal profiles
- [ ] No confidential work content
- [ ] No unnecessary raw event/message data
- [ ] Links are safe to expose publicly
- [ ] Runtime status does not reveal authentication details
- [ ] Examples use fabricated IDs/data
