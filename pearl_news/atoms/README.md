# Pearl News — Article atoms

Reusable building blocks for article assembly. **Not** the same as book atoms (`atoms/<persona>/<topic>/`).

## Atom types

| Directory | Purpose |
|-----------|---------|
| **news_summaries/** | Optional pre-summarized news items; usually filled from feed ingest output. |
| **youth_impact/** | Snippets by theme (e.g. `climate_anxiety.md`, `education_stress.yaml`) — how topic affects Gen Z/Gen Alpha. |
| **teacher_quotes_practices/** | By teacher_id (forum); civic-language quotes or practices per topic. |
| **sdg_un_refs/** | Boilerplate and UN department references per SDG (no endorsement claim). |

One atom can be reused across many articles. Add content here as you build the pipeline.
