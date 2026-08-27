# Claude Instructions

Read [`AGENTS.md`](AGENTS.md) first and follow its mandatory read order.

This file intentionally does not duplicate architecture rules. In particular, Claude must distinguish:

- canonical tool ownership;
- current runtime connectivity;
- authorization/autonomy policy;
- actual technical ability to perform a write.

Use the repo as the shared operating model rather than creating a separate Claude-specific productivity architecture.

Keep private/sensitive state out of this public repository. When changing architecture, runtime status, integrations, or automations, update the canonical files identified by `AGENTS.md` and add a dated decision record when the change is material.
