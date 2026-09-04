# Development Tools & Infrastructure Inventory

**Status:** Provisional / subject to change  
**Purpose:** Record the current development stack and evaluate each tool for long-term, scalable, production-grade use. Current usage does not imply permanent recommendation.

## Current tools

| Tool | Current use | Provisional direction |
|---|---|---|
| **VS Code** | Primary code editor | Keep as the default editor unless a materially better workflow emerges |
| **Cursor** | Intentionally not used because ORC is being built as the coding-agent orchestration layer | Do not adopt merely for convenience if it would duplicate ORC's purpose |
| **Xcode** | iOS application development | Keep; required/first-class for Apple platform development |
| **IntelliJ IDEA** | Installed but not meaningfully used yet | Optional; evaluate for Java/Spring productivity before standardizing |
| **Eclipse** | Historically used | Legacy familiarity; no need to standardize on it unless a project specifically benefits |
| **Docker Desktop** | Used before; familiarity still developing | Keep as an available container workflow for now; evaluate alternatives based on reliability, resource use, licensing, and automation needs |
| **Colima** | Tried/used lightly; familiarity still developing | Candidate Docker-runtime alternative on macOS; compare during implementation rather than running both without a reason |
| **Postman** | API testing | Keep for now; evaluate whether automated API tests plus lighter tooling can reduce dependency over time |
| **Insomnia** | No meaningful current use / uncertain familiarity | No architectural role unless a specific need appears |
| **pgAdmin** | Local PostgreSQL administration | Keep as a GUI/admin convenience, not as the canonical database management layer |
| **Git CLI** | Primary Git workflow through terminal | Keep as canonical local Git interaction |
| **GitHub Desktop** | Little/no meaningful use | No need to add to the standard workflow |
| **Homebrew** | macOS package management | Keep; useful for reproducible developer setup when paired with documented dependencies/Brewfile where appropriate |
| **iTerm** | Primary terminal application; user referred to it as iTerm3, exact product/version should be verified | Keep terminal workflow; terminal brand itself is replaceable |
| **Vercel** | Application hosting/deployment | Keep where it is a strong fit, especially frontend/Next.js-style workloads; do not force all services onto it |
| **Cloudflare** | DNS/edge/CDN/security and related infrastructure | Keep as an important edge/infrastructure platform; exact responsibilities should be made explicit per project |
| **Render** | Application/service hosting | Keep where useful; review overlap with Vercel and other compute platforms project-by-project |
| **Neon PostgreSQL** | Hosted PostgreSQL / emerging LLM4LIFE durable structured state | Strong candidate to keep; evaluate architecture, backups, branching, connection model, and limits before making it central production state |
| **Local PostgreSQL** | Local development databases | Keep for development/testing where useful; production data should not depend on a laptop-local database |
| **AWS** | Not currently used; user wants to learn it | Learn, but do not migrate workloads merely to claim 'production grade' |
| **Azure** | Not currently used; user wants to learn it | Same: learn and use only when requirements justify it |

## Current development architecture direction

```text
Developer
   |
   +--> VS Code / Xcode / optional IntelliJ
   |
   +--> iTerm + Git CLI + Homebrew
   |
   +--> ORC
          |
          +--> coding agents / model providers
          +--> verification
          +--> cross-vendor review
          |
          v
        GitHub
          |
          +--> CI/CD
          +--> deployment targets
                 |
                 +--> Vercel
                 +--> Render
                 +--> Cloudflare edge/DNS
                 +--> other compute only when justified

Data:
local Postgres --> development/testing
Neon Postgres --> hosted structured state where appropriate
```

## Production-grade principles

1. **Do not confuse hyperscaler complexity with maturity.** AWS/Azure are valuable skills and may become appropriate infrastructure, but moving a small/medium system to them without a requirement can increase operational burden without improving reliability.
2. **Prefer managed services while they fit.** Neon, Vercel, Render, and Cloudflare can be highly scalable components when boundaries are clear and portability is preserved.
3. **Infrastructure should be project-specific, policy should be shared.** LLM4LIFE should document common standards for secrets, deployment, observability, backups, environments, and recovery, while each repo owns its actual deployment architecture.
4. **Reduce overlapping local tooling.** Docker Desktop vs Colima should eventually have a preferred default instead of two parallel container stacks without reason.
5. **GUIs are interfaces, not sources of truth.** pgAdmin/Postman may remain useful, but schemas, migrations, API contracts, tests, and deployment configuration belong in version-controlled project artifacts.
6. **ORC remains the development AI control plane.** Avoid adopting editor-specific AI workflows that recreate competing routing/state unless they provide a clearly isolated capability ORC does not intend to own.
7. **Automate verification.** The long-term goal is not manual Postman/pgAdmin clicking as the only validation path; production systems should rely on automated tests, migrations, CI, and reproducible commands.

## AWS / Azure learning direction

The user wants to learn AWS and Azure. Treat this as a **skills-development goal**, separate from an infrastructure migration decision.

Recommended approach after the core LLM4LIFE architecture is implemented:

- learn fundamental cloud concepts: IAM, networking/VPC/VNet, compute, object storage, managed databases, queues/events, observability, secrets/KMS, and infrastructure as code;
- deploy one deliberately small project or sandbox workload to each cloud;
- compare operational cost/complexity against the current managed stack;
- migrate a real production workload only if requirements such as enterprise integration, compliance, geographic architecture, specialized services, scale, or economics justify it.

## Implementation follow-up after inventory

- Decide a preferred macOS container runtime: Docker Desktop vs Colima (or another option if research supports it).
- Document standard local developer bootstrap using Homebrew and repo-native dependency managers.
- Define a deployment decision matrix for Vercel vs Render vs other compute.
- Define Cloudflare's standard responsibilities (DNS, CDN, WAF, storage, workers, tunnels, etc.) rather than allowing ad hoc use.
- Formalize Neon operational requirements before centralizing LLM4LIFE state: migrations, backups/restore, connection pooling, environments/branches, least-privilege credentials, observability, and disaster recovery.
- Add cloud-learning tasks for AWS/Azure without coupling them to an unnecessary migration.
- Verify the exact iTerm product/version reference.
