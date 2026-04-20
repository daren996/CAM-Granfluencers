# Project Notes

- Keep this file synchronized with `CLAUDE.md` when either one is updated.
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

- All files in `docs/` should be maintained in bilingual pairs.
- English docs use the default filenames such as `docs/index.md` and `docs/setup.md`.
- Simplified Chinese docs use matching `*.zh-CN.md` files.
- Each docs file should begin with a language switch like:
  `[English](./index.md) | [中文](./index.zh-CN.md)`
- When one docs file is updated, sync its counterpart as well.
- `docs/index.md` is the documentation homepage and future project site entry.
- `docs/setup.md` documents the GitHub Pages setup steps.
- `README.md` and `README.zh-CN.md` should both mention the docs site.
- For GitHub Pages, use the repository default branch and publish the `/docs` folder.
- The published URL will usually look like:
  `https://<your-github-username>.github.io/<repository-name>/`
