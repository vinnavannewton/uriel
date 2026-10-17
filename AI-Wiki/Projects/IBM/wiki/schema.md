---
title: "Wiki maintenance schema"
project: IBM-Uriel
tags: [ibm, uriel]
---

# Wiki maintenance schema

## Model

This project adapts [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): preserve source material, maintain linked summaries, and use written rules to guide agents. The index organizes topics; the log records changes over time.

## Authority and evidence

User instructions govern the current task. The PRD describes requirements; live source code describes implementation. Test outputs establish only the behaviour they actually exercised. Resolve conflicts explicitly: never turn a requirement, hypothesis or previous chat claim into a verified result.

Page frontmatter includes title, project, updated date and tags. Use short descriptive kebab-case filenames and Obsidian wiki-style links. Every topic page has a Sources section and links to related pages. Link external sources directly and live repository files using relative Markdown links.

## Ingest

1. Read [[index]] and relevant pages.
2. Preserve a dated source snapshot or provenance note in `../raw/`. Existing raw files are immutable; create a new dated snapshot for updates. Code is authoritative in the workspace and can change normally; snapshots record what was inspected.
3. Update existing topics, including any contradictions or superseded claims.
4. Update [[sources]], [[index]] if navigation changes, and append [[log]].

## Query

Use the index to find pages, verify drift-prone claims against current code or evidence, and cite sources. File useful durable findings in existing pages. Do not retain transient conversational noise or secrets.

## Maintenance

Check broken links, missing citations, orphan pages, contradictory status and stale code pointers. Keep validation limits explicit. Record observed defects as static concerns unless reproduced. Maintenance is not permission to change executable code, run deferred tests, deploy, commit or push.

## Logging

Append meaningful completed work as `## [YYYY-MM-DD] kind | title`, oldest first. Put future work in [[open-questions]], not completion records. Never rewrite previous log entries to claim later success.
