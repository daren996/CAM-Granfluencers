# Project Notes

- Keep this file synchronized with `AGENTS.md` when either one is updated.
- Keep project instructions short, practical, and easy to maintain.
- Keep `.env` and `.env.example` synchronized. When variables are added, removed, renamed, or documented in one file, update the other in the same change.

# README

- The repository README is bilingual.
- English lives in `README.md`.
- Simplified Chinese lives in `README.zh-CN.md`.
- Both files should begin with this language switch:
  `[English](README.md) | [中文](README.zh-CN.md)`
- When one README is updated, sync the other one as well.

# Docs

- `docs/` is an HTML-based bilingual site. Do not add new Markdown docs under `docs/`.
- English docs use filenames such as `docs/index.html` and `docs/setup.html`.
- Simplified Chinese docs use matching `*.zh-CN.html` files.
- Every docs page must include a visible language switch linking its bilingual counterpart.
- `docs/index.html` is the project homepage and should expose navigation to pages such as wiki, collect, analysis, and results.
- When one docs page is updated, sync its counterpart as well.
- `docs/` is the source of truth for user-facing workflows and behavior. If code conflicts with `docs/`, fix the code or update both in the same change.
- Canonical project data lives under `data/`. The published site reads mirrored files under `docs/data/`, so keep those locations synchronized when data or export code changes.
- Keep the docs workflow able to run `src/` code locally for data refresh and site preparation.
- `README.md` and `README.zh-CN.md` should both mention the HTML docs site and the data sync workflow.
- For GitHub Pages, use the repository default branch and publish the `/docs` folder.
- The published URL will usually look like:
  `https://<your-github-username>.github.io/<repository-name>/`
