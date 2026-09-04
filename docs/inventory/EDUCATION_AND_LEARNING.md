# Education & Learning Inventory

**Status:** Provisional / subject to change  
**Purpose:** Define the role of education, courses, practice platforms, and durable learning knowledge inside the LLM4LIFE architecture.

## Current picture

The user's learning system is broader than any one course platform. Formal education and credentials are already represented on the personal portfolio, while durable technical learning is captured in Obsidian and reinforced through projects.

Current/known learning surfaces include:

- University coursework and formal study
- Codio and similar course/LMS environments when required
- YouTube for tutorials/explanations
- Textbooks, PDFs, and online reading material
- Coding practice platforms when useful
- Project-based learning through the user's own repositories/products
- Obsidian as the durable knowledge/learning system
- Certifications and professional training as career credentials

## Formal education and credential role

Formal degrees, certifications, and completed professional programs are career/profile facts. They should be represented in the professional-profile source and projected to the portfolio/resume/LinkedIn as needed.

Do not turn LMS/course platforms into long-term sources of truth merely because they hosted the original material.

## Durable learning architecture

```text
Courses / LMS / YouTube / books / PDFs / tutorials
                    |
                    v
               learning intake
                    |
         practice / projects / quizzes
                    |
                    v
                 Obsidian
        durable knowledge and memory
                    |
                    +--> GitHub projects when knowledge becomes implementation
                    +--> professional profile when it becomes a credential
```

### Ownership rules

- **Obsidian** owns durable conceptual knowledge, explanations, learning notes, review material, and personal understanding.
- **GitHub repositories** own project-specific implementation truth and shipped technical artifacts.
- **Course/LMS platforms** are temporary delivery systems, not canonical knowledge stores.
- **YouTube/web tutorials** are references/sources, not durable truth.
- **Professional-profile data** owns completed degrees/certifications that should appear consistently across the portfolio/resume/LinkedIn.

## Production-grade direction

1. Prefer **free learning resources first**. Paid courses should only be added when they materially improve learning outcomes over free alternatives.
2. Do not maintain a separate permanent database for every course provider.
3. Capture only learning that is worth retaining; avoid turning Obsidian into a dump of copied course content.
4. Track active learning goals and next actions separately from knowledge itself.
5. Learning progress may produce tasks in Google Tasks or structured progress/state in the LLM4LIFE backend, but learning notes remain in Obsidian.
6. Where possible, convert passive study into project work, quizzes, recall, or shipped code.
7. Credentials should have one authoritative structured representation and be projected to public professional surfaces to avoid drift.

## Potential future structured learning state

If LLM4LIFE needs machine-readable learning state, keep it lightweight:

- topic / skill
- status (planned / learning / practicing / competent / revisiting)
- current resource
- next action
- last reviewed date
- optional target/certification
- link to Obsidian knowledge area
- link to relevant GitHub project

Do not store full learning notes in PostgreSQL merely because structured state is available.

## Immediate implementation follow-up after inventory

- Keep Obsidian as canonical durable learning memory.
- Add a lightweight learning-goal/progress domain only if it materially improves planning and resurfacing.
- Connect learning tasks to Google Tasks rather than embedding todos inside learning notes.
- Ensure certifications/degrees can be projected consistently into the portfolio/resume/LinkedIn professional profile model.
- Preserve the user's existing Obsidian software-engineering learning system rather than replacing it with another paid platform.
