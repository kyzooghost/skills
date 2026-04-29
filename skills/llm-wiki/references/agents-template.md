# {SUBJECT_AREA} Wiki

This directory is an LLM-maintained wiki for **{SUBJECT_AREA}**. Bootstrapped on {BOOTSTRAP_DATE}.

Any LLM agent working in this directory must read this file first and follow the conventions below. Co-evolve this file as you and the user discover what works for this subject area.

## Three layers

- `raw/` - immutable user-curated sources. Read but never modify.
- `wiki/` - LLM-owned markdown pages. Create, update, cross-reference.
- `AGENTS.md` (this file) - conventions and workflows for this wiki.

The wiki is a compounding artifact. Every ingest enriches it. Every filed-back query enriches it. Cross-references and synthesis live in `wiki/`, not in chat history.

## Source types expected

{SOURCE_TYPES}

(Update this section as the actual mix of sources becomes clear.)

## Output formats supported

{OUTPUT_FORMATS}

(Add or remove formats as the user's needs settle.)

## Frontmatter

{FRONTMATTER_CHOICE}

If frontmatter is in use, document the schema here:

```yaml
# Example - replace with the schema actually in use
# tags: [character, maiar]
# source_count: 3
# updated: 2026-04-15
```

## Page conventions

Most pages fall into one of four types. Use the type that fits; do not force a page into a type.

### Entity pages

A person, place, organization, character, product, etc.

```markdown
# {Entity Name}

One-line summary.

## Overview
Prose covering the essentials.

## Relationships
- Linked to [Other Entity](other-entity.md) because ...
- Member of [Organization](organization.md).

## Sources
- [Source Summary 1](source-summary-1.md)
- [Source Summary 2](source-summary-2.md)
```

### Concept pages

An idea, theme, mechanism, framework.

```markdown
# {Concept Name}

One-line definition.

## Definition
Precise statement.

## Examples
- ...

## Related concepts
- [Sibling concept](sibling-concept.md)

## Sources
- [Source Summary](source-summary.md)
```

### Source summary pages

The wiki's record of a single raw source. One per source.

```markdown
# {Source Title}

> Source: [raw/{source-file}](../raw/{source-file})
> Type: {article | paper | transcript | journal | book | ...}
> Ingested: {YYYY-MM-DD}

## Key takeaways
1. ...
2. ...
3. ...

## Entities mentioned
- [Entity A](entity-a.md), [Entity B](entity-b.md)

## Concepts introduced
- [Concept X](concept-x.md)

## Notable quotes
> "..."
```

### Analysis pages

A synthesis or comparison filed back from a query.

```markdown
# {Analysis Title}

> Question: {original question}
> Filed: {YYYY-MM-DD}

## Answer
Synthesis with inline links to wiki pages used.

## Sources used
- [Page 1](page-1.md)
- [Page 2](page-2.md)
```

## Linking

- Standard markdown links only: `[Title](kebab-case-name.md)`. Never `[[wikilinks]]`.
- Wiki-to-wiki links are relative within `wiki/`.
- Citations to raw sources use relative paths: `[Source](../raw/some-source.md)`.
- Filenames are kebab-case, no spaces, no caps.

## `index.md` rules

`index.md` is the content-oriented catalog. It must be updated on every ingest and every filed-back query. Format:

```markdown
# Index

## Entities
- [Title](path.md) - one-line summary.

## Concepts
- [Title](path.md) - one-line summary.

## Sources
- [Title](path.md) - YYYY-MM-DD.

## Analyses
- [Title](path.md) - YYYY-MM-DD.
```

## `log.md` rules

`log.md` is chronological and append-only. Every entry starts with a parseable prefix:

```markdown
## [YYYY-MM-DD] {ingest|query|lint|bootstrap} | {short title}
- New: [page](page.md), ...
- Updated: [page](page.md), ...
- Notes: optional one-liner
```

This format lets the user run `grep '^## \[' log.md | tail -10` to skim recent activity.

## Workflows

### When the user ingests a source

1. Read the source from `raw/`. If the source is not yet in `raw/`, copy it there first.
2. Surface 3-7 key takeaways. Discuss with the user.
3. Read `index.md` to see what already exists.
4. Write a source summary page in `wiki/`.
5. Update or create the entity/concept pages this source touches. A single source typically touches 10-15 wiki pages.
6. When new information contradicts an existing claim, surface a `> NOTE:` blockquote on the affected page rather than silently overwriting.
7. Update `index.md`.
8. Append to `log.md`.
9. Show the user the list of new and updated pages.

### When the user queries the wiki

1. Read `index.md` to find candidate pages.
2. Read those pages (and follow links transitively as needed).
3. Read the underlying raw source if the wiki summary lacks the detail required.
4. Synthesize with inline citations to wiki pages.
5. Offer to file the answer back as an analysis page. Default to asking, not auto-filing.
6. If filed: update `index.md` under Analyses, append to `log.md`.

### When the user requests a lint pass

Read-only check across `wiki/`. Report:
- HIGH: broken markdown links, contradictions
- MEDIUM: stale claims, missing pages (concepts mentioned >=3 times without their own page)
- LOW: orphan pages, missing cross-references, data gaps the user could fill

Do not auto-fix. Append a one-line log entry summarizing the lint result.

## Subject-specific notes

Use this section to capture conventions that emerge as you work in this domain. Examples of things to document here over time:

- Specific page-type variants this subject area needs (e.g. `event` pages for historical research, `experiment` pages for scientific notes)
- Naming patterns for recurring entities (e.g. how to disambiguate two characters with the same first name)
- Sources of truth when sources contradict (e.g. "primary text wins over secondary commentary")
- Domains where web search is welcome to fill gaps vs. domains where only user-curated sources are allowed
- Emphasis preferences (e.g. "always extract dates" or "always note contradictions explicitly")

This section is intentionally empty at bootstrap. Both user and LLM should add to it as the wiki matures.
