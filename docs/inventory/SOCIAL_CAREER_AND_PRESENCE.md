# Social, Career & Professional Presence Inventory

**Status:** Provisional / subject to change  
**Purpose:** Define how social networks, job platforms, GitHub, and owned websites fit into the long-term LLM4LIFE architecture.

## Operating preference

The user does not use social media heavily for its own sake. Social platforms are primarily **purpose-driven channels** for professional visibility, research, community participation, product/project distribution, or specific communication goals.

LLM4LIFE should therefore optimize for useful outcomes rather than engagement for engagement's sake.

## Current systems

| System | Current role | Provisional long-term direction |
|---|---|---|
| **LinkedIn** | Primary professional network, recruiter presence, project/software posts, career distribution | Keep as the primary professional social channel. Use intentionally for career/project distribution rather than making it a source of truth |
| **GitHub profile** | Public engineering proof, code portfolio, repositories, contributions and technical credibility | Keep as canonical public implementation evidence. Project facts should come from repositories rather than being manually duplicated across social profiles |
| **Indeed** | Job discovery/application platform | Keep as an external job-market channel; evaluate other free channels only where they materially improve search coverage |
| **X / Twitter** | Available social/distribution/research channel; not heavily used by default | Keep optional. Use when it serves a concrete networking, technical-community, product-distribution, or research goal |
| **Instagram** | Available social channel; low general usage | Keep optional/personal. Do not build core architecture around it unless a concrete content/distribution use case appears |
| **TikTok** | Available social/content channel; low general usage | Keep optional. Use only where short-form distribution or research provides meaningful value |
| **Reddit** | Research/community/discussion surface | Keep as a useful research and community-intelligence source; do not treat community claims as canonical facts without validation |
| **zubairmuwwakil.com** | Personal engineering portfolio: experience, education, skills, projects, case studies/technical writing and recruiter-facing identity | Keep as the user's canonical owned professional web presence. Prefer automating facts from authoritative sources where practical rather than maintaining inconsistent duplicates |
| **zemiechelon.com** | Parent technology/venture umbrella representing products, engineering systems and platforms founded/architected by the user | Keep as the canonical owned umbrella/venture presence distinct from the personal recruiter-facing portfolio |

## Owned-property hierarchy

```text
                 Professional identity
                         |
             zubairmuwwakil.com
        personal engineer / recruiter site
                         |
            projects + technical work
                         |
                 GitHub repositories

                 Venture ecosystem
                         |
                 zemiechelon.com
            parent technology umbrella
                         |
       InUnity / PickMe / MarketLens / ORC / etc.
```

The two websites should remain distinct unless a future branding decision intentionally merges them:

- **zubairmuwwakil.com** answers: "Who is Zubair as an engineer and candidate?"
- **zemiechelon.com** answers: "What technology products/systems exist under the venture umbrella?"

## Production-grade content model

Avoid manually maintaining the same factual project metadata in many places.

Preferred direction:

```text
GitHub / project repositories
       canonical technical facts
                |
                v
       structured projection
        /       |        \
       v        v         v
personal site  umbrella   LinkedIn/social
               site       distribution
```

Examples of facts that should ideally be generated or synchronized from authoritative project metadata where practical:

- project name
- repository URL
- current status
- technology stack
- live deployment URL
- release/version information
- concise project description

Human-authored positioning, storytelling, case studies, recruiter messaging and social posts can remain purpose-specific rather than mechanically synchronized.

## Social-media rule

LLM4LIFE should treat social networks as **distribution and research endpoints**, not canonical databases.

A future content workflow may look like:

```text
project/repository event or intentional idea
                |
                v
          content candidate
                |
       LLM4LIFE planning layer
         /        |         \
        v         v          v
   LinkedIn       X       other channel
 professional   technical   only when useful
```

Do not introduce paid social-media management software by default. The architecture has a **free / already-paid-for first** constraint. Prefer native scheduling, APIs where free/appropriate, existing AI subscriptions, or small self-hosted automation before adding another subscription.

## Career-system direction

- **Owned portfolio + GitHub** should form the durable professional foundation.
- **LinkedIn** should amplify that foundation and connect it to recruiters/industry.
- **Indeed** and similar services are discovery/application channels, not the canonical record of the user's career.
- If a job-application tracker is needed, prefer an existing free system or LLM4LIFE-owned structured state rather than buying another SaaS product.
- Resume/profile facts should eventually have one authoritative structured representation to reduce drift between resume, portfolio, LinkedIn and applications.

## Cost constraint

Recommendations in this domain must be **free by default**. A paid product should only be proposed when its advantage is material, no good free/already-paid-for solution exists, and the incremental value justifies another recurring cost.

## Implementation follow-up after inventory

- Define a canonical professional-profile data model for experience, education, projects and skills.
- Determine which portions can safely project into zubairmuwwakil.com, LinkedIn-supporting workflows and other career surfaces.
- Keep zemiechelon.com as a separate venture/product hierarchy.
- Consider generating project metadata for both websites from repository-owned manifests/contracts rather than hand-maintained duplicate facts.
- Build social publishing automation only for channels with actual demonstrated value; do not optimize for posting volume.
