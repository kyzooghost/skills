---
name: llm-wiki
description: Build and maintain a personal knowledge wiki using LLMs. Bootstraps a portable markdown wiki for a subject area, ingests sources into it, answers queries against it, and health-checks it. Triggers on "/wiki-init", "/wiki-ingest", "/wiki-query", "/wiki-lint", or natural-language phrases like "set up a wiki for X", "ingest this source into my wiki", "query my wiki", "health-check my wiki", "lint my wiki". Use when the user wants a persistent, compounding knowledge base that the LLM maintains over time, rather than one-shot RAG against raw sources.
---

# LLM Wiki

A pattern for building a personal knowledge wiki that the LLM maintains incrementally, instead of re-deriving knowledge from raw sources on every query.

## Core idea

Three layers:

- **Raw sources** (`raw/`) - immutable, user-curated. Articles, papers, transcripts, journal entries. The LLM reads but never modifies.
- **Wiki** (`wiki/`) - LLM-owned markdown pages. Summaries, entity pages, concept pages, analyses, an index, a log.
- **Schema** (`AGENTS.md` at the wiki root) - per-wiki conventions and workflows. Co-evolved with the user. Tells any LLM working in the wiki how to behave.

The wiki is a **compounding artifact**. Every ingest enriches it. Every query can be filed back into it. Cross-references, contradictions, and synthesis already live there - the LLM doesn't rebuild them on each turn.

The user curates sources, asks questions, and directs analysis. The LLM does the bookkeeping: summarizing, cross-referencing, filing, updating. Humans abandon wikis because maintenance grows faster than value. LLMs don't.

## Routing

Match the user's invocation to one of four operations:

| Trigger phrases | Operation | Section |
| --- | --- | --- |
| `/wiki-init`, "set up a wiki for X", "form a wiki", "bootstrap a wiki" | Bootstrap | [Operation: Bootstrap](#operation-bootstrap) |
| `/wiki-ingest`, "ingest this source", "add this to my wiki", "process this article into the wiki" | Ingest | [Operation: Ingest](#operation-ingest) |
| `/wiki-query`, "query my wiki", "ask my wiki", "what does my wiki say about X" | Query | [Operation: Query](#operation-query) |
| `/wiki-lint`, "lint my wiki", "health-check my wiki", "audit my wiki" | Lint | [Operation: Lint](#operation-lint) |

For Ingest/Query/Lint: if the current directory has no wiki (no `AGENTS.md` + `wiki/` + `raw/`), ask the user for the wiki path or offer to bootstrap one.

---

## Conventions (shared core)

Every operation follows these rules. They are intentionally portable: plain markdown, no editor- or plugin-specific syntax.

### Directory layout

```
<wiki-root>/
  AGENTS.md          # schema/conventions for THIS wiki, co-evolved with user
  raw/               # immutable user-curated sources
    assets/          # downloaded images and binary assets (optional)
  wiki/              # LLM-owned markdown pages
    index.md         # content-oriented catalog
    log.md           # chronological append-only record
    <pages>.md
```

### Linking

- **Standard markdown only.** `[Gandalf](gandalf.md)`. Never `[[Gandalf]]`.
- Links between wiki pages are **relative paths** within `wiki/`.
- Citations to raw sources use relative paths to `raw/` from the wiki page (e.g. `[Article](../raw/some-article.md)`).
- This is the single biggest portability rule: it works in VS Code, Cursor, Obsidian, GitHub web, and plain text editors.

### Filenames

- Kebab-case: `gandalf.md`, `the-shire.md`, `meeting-2026-04-15.md`.
- No spaces, no capital letters, no `[[brackets]]`.

### Frontmatter

Optional. If a wiki uses YAML frontmatter (e.g. `tags`, `source_count`, `updated`), the wiki's `AGENTS.md` defines the schema. The skill never requires it.

### `index.md` format

Content-oriented catalog. Flat lists grouped by category. Categories typical for most wikis:

```markdown
# Index

## Entities
- [Gandalf](gandalf.md) - Maiar wizard, member of the Istari.
- [The Shire](the-shire.md) - Hobbit homeland in Eriador.

## Concepts
- [The One Ring](one-ring.md) - Sauron's master ring of power.

## Sources
- [The Fellowship of the Ring](fellowship-summary.md) - 2026-04-15.

## Analyses
- [Comparative power of the Maiar](analysis-maiar-power.md) - 2026-04-20.
```

Each entry: `- [Title](path.md) - one-line summary`. Update on every ingest and every filed-back query.

### `log.md` format

Append-only, chronological. Every entry starts with a parseable prefix:

```markdown
## [2026-04-15] ingest | The Fellowship of the Ring (chapters 1-3)
- New: [fellowship-summary.md](fellowship-summary.md), [bilbo.md](bilbo.md)
- Updated: [gandalf.md](gandalf.md), [the-shire.md](the-shire.md), [index.md](index.md)

## [2026-04-20] query | How does the Ring corrupt its bearers?
- Filed: [analysis-ring-corruption.md](analysis-ring-corruption.md)
- Read: [one-ring.md](one-ring.md), [bilbo.md](bilbo.md), [frodo.md](frodo.md), [gollum.md](gollum.md)

## [2026-04-25] lint | health check
- 2 orphan pages, 1 broken link, 3 missing cross-references suggested
```

The `## [YYYY-MM-DD] {op} | {title}` prefix lets the user run `grep '^## \[' wiki/log.md | tail -10` to skim recent activity.

### Page types

Most wikis settle on four page types. The `AGENTS.md` template encodes them but they are not strict.

- **Entity** - a person, place, organization, character, etc. Has properties, relationships, references.
- **Concept** - an idea, theme, mechanism, framework. Has definition, examples, contrasts.
- **Source summary** - the LLM's summary of a single raw source, with citations back into `raw/`.
- **Analysis** - a synthesis or comparison generated from a query, filed back into the wiki.

---

## Operation: Bootstrap

Trigger: `/wiki-init`, or natural-language equivalents.

### Phase 1 - Discovery (single consolidated prompt)

Ask the user, in **one** message:

1. **Subject area** - one short phrase that names what this wiki is about.
   _Examples: "Tolkien legendarium", "personal psychology and goals", "competitor X due diligence", "GraphQL deep-dive"._
2. **Target path** - absolute or relative path where the wiki should live. Default: current working directory. If non-empty and not already a wiki, ask for confirmation.
3. **Source types** - what kinds of inputs they expect to feed in.
   _Examples: articles, papers, podcast transcripts, journal entries, meeting notes, books, mixed._
4. **Output formats** - markdown only, or also slide decks (Marp), charts, comparison tables, canvases.
5. **Frontmatter preference** - none (default), or YAML frontmatter with a small schema (e.g. `tags`, `source_count`, `updated`).

Do not proceed until all five are answered.

### Phase 2 - Scaffold

Create the directory structure exactly as documented under [Conventions: Directory layout](#directory-layout):

- `<wiki-root>/raw/`
- `<wiki-root>/raw/assets/`
- `<wiki-root>/wiki/`
- `<wiki-root>/wiki/index.md` - empty catalog stub with the four category headers (Entities, Concepts, Sources, Analyses)
- `<wiki-root>/wiki/log.md` - one bootstrap entry: `## [{today}] bootstrap | {subject_area}`
- `<wiki-root>/AGENTS.md` - read [references/agents-template.md](references/agents-template.md), substitute the placeholders below, write the result.

Placeholders to substitute in the template:

| Placeholder | Source |
| --- | --- |
| `{SUBJECT_AREA}` | Phase 1 answer 1 |
| `{SOURCE_TYPES}` | Phase 1 answer 3 |
| `{OUTPUT_FORMATS}` | Phase 1 answer 4 |
| `{FRONTMATTER_CHOICE}` | Phase 1 answer 5 (literal text describing the choice) |
| `{BOOTSTRAP_DATE}` | Today's date in `YYYY-MM-DD` format |

If a Phase 1 answer is vague, leave the placeholder filled with the user's literal phrasing - the user can refine `AGENTS.md` later.

### Phase 3 - Confirm

Print the resulting tree (depth 2, leaves only) and tell the user:

- The wiki path
- The next concrete step: `/wiki-ingest <source-path>` to file the first source
- That `AGENTS.md` is meant to be edited as conventions emerge

Do not ingest anything during bootstrap. Bootstrap is structural only.

---

## Operation: Ingest

Trigger: `/wiki-ingest <source>`, or natural-language equivalents.

### Phase 1 - Locate the source

Source can be:
- A path (file in `raw/` or anywhere on disk - copy into `raw/` if it isn't already there)
- A URL (fetch and convert to markdown, save to `raw/`)
- Pasted content (write to a new file in `raw/` with a kebab-case name from a 2-4 word summary)

If the source already exists in `raw/`, do not overwrite. Ask for confirmation if the user re-ingests.

### Phase 2 - Read and discuss

Read the source. Surface **3-7 key takeaways** to the user. Ask:
- Which takeaways to emphasize in the wiki
- Whether any contradict claims already in the wiki (read `wiki/index.md` first to know what's there)
- Whether to create new entity/concept pages, or fold the source into existing ones

Do not write to the wiki yet. Ingest is a discussion, not a dump. The source prompt this skill is based on emphasizes: _"I prefer to ingest sources one at a time and stay involved."_

### Phase 3 - Write the summary page

Create `wiki/<source-slug>.md` with:
- Title (from source title)
- Citation block linking back to `raw/<source-file>`
- Sections for the takeaways the user emphasized
- Inline links to entity/concept pages mentioned, even if those pages do not exist yet (so they show up as broken links and surface in lint)

### Phase 4 - Update affected pages

A single source typically touches 10-15 wiki pages. This phase is non-optional.

For each entity, concept, or claim mentioned in the source:
1. Check `wiki/index.md` - does a page already exist?
2. If yes: read it, surgically integrate the new information. Note when the source contradicts existing claims (do not silently overwrite - flag the contradiction in the page itself with a `> NOTE: ...` blockquote).
3. If no, and the user emphasized this entity/concept in Phase 2: create the page.

Cross-reference: every page that mentions another page must link to it.

### Phase 5 - Update `index.md`

Add new pages under their categories. Refresh the one-line summaries of any pages whose scope changed.

### Phase 6 - Append to `log.md`

```markdown
## [{today}] ingest | {Source Title}
- New: [page-1](page-1.md), [page-2](page-2.md)
- Updated: [page-3](page-3.md), [page-4](page-4.md), [index.md](index.md)
- Contradictions: 0 (or list)
```

### Phase 7 - Confirm

Show the user the list of files created and modified, and a short summary of contradictions/uncertainties surfaced.

---

## Operation: Query

Trigger: `/wiki-query <question>`, or natural-language phrasings.

### Phase 1 - Read `index.md`

Read `wiki/index.md` first. It is a content-oriented catalog and is the cheapest way to find candidate pages at small/medium scale. No embedding RAG is required.

If the wiki has grown beyond what `index.md` can serve well (typically hundreds of pages), the wiki's `AGENTS.md` may declare a search tool to use instead. Defer to it.

### Phase 2 - Read candidate pages

Identify 3-10 pages relevant to the question and read them with the Read tool. Read linked pages transitively when needed.

If the answer requires raw-source detail not captured in the wiki summary, follow the citation back into `raw/` and read there too.

### Phase 3 - Synthesize with citations

Produce the answer in the format that fits the question:

- Default: a markdown response with inline links back to the wiki pages used
- Comparison: a markdown table
- Slide deck: a Marp markdown document
- Chart: a matplotlib script
- Canvas: when the answer is data-heavy or warrants rich layout

Citations are **wiki page links** (`[Gandalf](wiki/gandalf.md)`), with raw-source links secondary.

### Phase 4 - Offer to file the answer back

Good answers are valuable artifacts. Ask the user: _"File this back into the wiki as an analysis page?"_

If yes:
1. Write to `wiki/analysis-<short-slug>.md`
2. Add an entry under `## Analyses` in `wiki/index.md`
3. Append a log entry: `## [{today}] query | {Question}` with new/read pages listed

If no, leave the wiki unchanged. The answer lives in the chat only.

---

## Operation: Lint

Trigger: `/wiki-lint`, or natural-language equivalents.

Read-only. Do not auto-fix. Report findings, ranked by severity.

### Checks

1. **HIGH - Broken links** - markdown links in `wiki/*.md` that point to a missing file or missing heading. Use the same approach as [commands/audit-docs.md](../../commands/audit-docs.md) Check 7.
2. **HIGH - Contradictions** - claims on different pages that conflict. Cross-reference pages that mention the same entity/concept and look for `> NOTE:` blockquotes left during ingest, or for direct contradictions in prose.
3. **MEDIUM - Stale claims** - pages whose claims are superseded by newer source summaries. Cross-reference the log to see ingest order.
4. **MEDIUM - Missing pages** - concepts mentioned >=3 times across the wiki but lacking their own page.
5. **LOW - Orphan pages** - pages with zero inbound links from any other wiki page (excluding `index.md` and `log.md`).
6. **LOW - Missing cross-references** - page A mentions entity B (which has its own page), but A does not link to B.
7. **LOW - Data gaps** - topics where the wiki is thin and the user could profitably search the web or seek another source.

### Report format

Mirror [commands/audit-docs.md](../../commands/audit-docs.md):

```
## Wiki Lint: {N} issues found across {M} pages

### [HIGH] Broken link: {brief title}
- **Location:** wiki/gandalf.md:42 - links to `mithrandir.md`
- **Problem:** target file does not exist
- **Suggested fix:** {actionable recommendation}

### [MEDIUM] Missing page: {brief title}
- **Mentioned in:** wiki/the-shire.md:12, wiki/bilbo.md:8, wiki/frodo.md:23
- **Suggested fix:** create `wiki/sting.md` for the recurring entity

### [LOW] Orphan: wiki/old-notes.md
- No inbound links from any other wiki page.
- **Suggested fix:** link from a relevant page or remove.
```

After all findings, print `[OK]` lines for clean checks. Append a log entry summarizing the lint:

```markdown
## [{today}] lint | health check
- {N} HIGH, {M} MEDIUM, {L} LOW
```

---

## Portability and Obsidian decoupling

This skill produces wikis that **work without Obsidian**. The defaults below are non-negotiable:

- No `[[wikilinks]]` - standard markdown links only
- No required Obsidian plugins (Dataview, Marp, Web Clipper)
- No LLM-specific schema filename (we use `AGENTS.md`, which Claude, Codex, Cursor, and other agents all read)
- No required attachment-folder configuration
- No `tags::` or other Obsidian-only frontmatter syntax

### Optional integrations

If the user happens to use one of these viewers, the wiki layers cleanly on top:

- **Obsidian** - graph view works on standard markdown links. The user can opt into wikilinks afterward but the skill does not produce them.
- **VS Code / Cursor** - markdown preview and "go to file" navigation work natively.
- **GitHub web** - the wiki renders directly when pushed to a repo.
- **Dataview** (Obsidian) - if the wiki opted into YAML frontmatter during bootstrap, Dataview queries work over it.
- **Marp** - if "slide decks" was selected in bootstrap output formats, the query operation can produce Marp-compatible markdown.

The wiki is a git repo of markdown files. Version history, branching, diffs, and collaboration come for free.

---

## Ground rules

- **Read-only on `raw/`.** The LLM never modifies sources. Treat the directory as immutable.
- **The LLM owns `wiki/`.** The user reads it; the LLM writes it. The user can edit too, but the skill assumes LLM authorship.
- **The user owns `AGENTS.md`.** The skill seeds it during bootstrap; afterward both user and LLM co-evolve it.
- **One source at a time, by default.** Ingest is conversational. Batch ingestion is possible but the user must opt in explicitly.
- **Cite everything.** Every claim in the wiki should trace to a source summary or another wiki page. Lint catches drift.
- **Surface contradictions, do not hide them.** Use `> NOTE:` blockquotes during ingest. Lint elevates them.
- **No silent overwrites.** When new information conflicts with old, ask before replacing.
