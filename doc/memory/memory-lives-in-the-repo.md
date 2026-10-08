---
name: memory-lives-in-the-repo
description: Durable lessons and owner rulings live in doc/memory/, never only in one tool's private memory
type: feedback
status: active
date: 2026-10-08
source: framework scar — a tool-private memory index grew to 253 lines against a 200-line load limit, hiding its newest 53 entries at every session start, and no other tool or teammate could read it
---

Write every durable lesson or owner ruling to `doc/memory/` with this frontmatter, and list it in `INDEX.md`.
A tool's own memory feature may cache it, but the repo copy is the one that counts.

**Why:** a private, append-only memory silently truncates and is invisible to every other tool and person.

**How to apply:** when a ruling replaces another, set the old one `status: superseded` with
`superseded_by: <new slug>` and drop it from `INDEX.md` — never leave two contradicting rulings both active.
