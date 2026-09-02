# Identity, Passwords & Security Inventory

**Status:** Provisional / subject to change  
**Inventory date:** 2026-09-02

This document records the current identity/security tooling and the likely long-term direction. It intentionally excludes private identifiers, passwords, recovery codes, 2FA seeds, and other secrets because the LLM4LIFE repository is public.

## Current usage

| Area | Current tool / pattern | Current role | Provisional direction |
|---|---|---|---|
| Passwords | Apple Passwords + Chrome Password Manager | Password storage/autofill across Apple and browser contexts | Consolidate to one canonical password manager; avoid maintaining two equal stores |
| 2FA | Authy | Time-based one-time-password authentication | Keep temporarily; reassess during implementation for portability, backup/recovery, and integration fit |
| Primary identity | Primary personal Gmail account | Main personal account/email identity | Keep as primary identity |
| Secondary identity | Secondary personal Gmail account | Secondary/recovery/alternate personal identity | Keep as secondary identity with a clearly documented purpose |
| AI-agent identity | Dedicated Gmail account for AI agents | Separate identity for agent-operated services/workflows | Keep the role separation, but apply least privilege and do not give agents broader account access than required |
| VPN | NordVPN | General-purpose VPN, currently perceived as low value | Reassess ROI; do not preserve solely because it is already paid for |
| Other security/privacy tooling | None currently identified | — | Add only when a clear threat model or operational need justifies it |

## Important security boundary

The public LLM4LIFE repository may document **roles and architecture**, but must never contain:

- actual email addresses when not necessary;
- passwords or password hints;
- API keys/tokens;
- 2FA seeds;
- backup/recovery codes;
- VPN credentials;
- database connection strings containing credentials;
- session cookies or authentication exports;
- private security questions/answers.

Use labels such as `primary_personal_email`, `secondary_personal_email`, and `agent_email` in architecture/config examples.

## Password-manager decision

The current Apple Passwords + Chrome Password Manager setup has duplicated responsibility.

Production-grade target:

```text
one canonical password manager
          |
          +--> Apple devices
          +--> Chrome/browser autofill
          +--> recovery / emergency access
          +--> passkeys / TOTP where appropriate
```

The exact product is intentionally **not decided yet**. During implementation, compare the current Apple-first approach against cross-platform dedicated managers such as 1Password/Bitwarden and choose based on:

1. security model;
2. cross-platform/browser support;
3. passkey support;
4. import/export and recovery;
5. family/emergency access requirements;
6. automation/API fit without exposing secrets to LLMs;
7. long-term vendor portability;
8. cost/ROI.

AI agents should generally receive **scoped credentials or delegated OAuth access**, not direct access to the user's primary password vault.

## AI-agent identity

Keeping a dedicated agent email identity is a useful separation-of-duties pattern.

Long-term rules:

- use the agent identity only for services where automation genuinely needs its own account;
- prefer OAuth/delegation/service accounts over sharing the user's personal credentials;
- grant least-privilege scopes;
- separate production and experimental agent credentials where risk warrants it;
- make actions attributable to a specific agent/service identity;
- preserve an audit trail for consequential writes.

## NordVPN

Current value is unclear. During the post-inventory implementation/cleanup phase, evaluate whether there is a real need such as:

- travel/untrusted Wi-Fi;
- location-specific testing;
- privacy requirements;
- development/network testing.

If there is no recurring use case with measurable value, treat it as a cancel/downgrade candidate rather than architectural infrastructure.

## Post-inventory implementation actions

After the full stack inventory is complete:

1. select one canonical password-manager strategy;
2. migrate/deduplicate Apple Passwords and Chrome entries safely;
3. review Authy recovery/backup and whether it remains the best long-term 2FA tool;
4. document the purpose of each account identity without storing the address publicly;
5. define a least-privilege credential model for AI agents;
6. audit existing agent/service access and revoke unnecessary permissions;
7. evaluate NordVPN ROI and keep/cancel accordingly.
