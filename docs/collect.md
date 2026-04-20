[English](./collect.md) | [中文](./collect.zh-CN.md)

# TikHub Collection Guide

This project currently uses [TikHub](https://tikhub.io/) as the upstream social media data provider. The first implemented platform in this repository is Instagram, but the collector layer is designed so other platforms can be added behind the same interface later.

## Why TikHub

TikHub provides one API key across multiple social platforms and documents Instagram endpoints for:

- account profile lookup
- account post pagination
- post detail lookup
- post comments
- comment replies
- user search

For this project, that makes TikHub a practical acquisition layer while we keep our own normalization, storage, and dashboard export logic in-repo.

## API Key Setup

1. Create or sign in to your TikHub account.
2. Open the user dashboard and generate an API key.
3. Store it in your local `.env` as:

```bash
TIKHUB_API_KEY=your_real_api_key
```

The collector reads `TIKHUB_API_KEY` from the environment and sends requests with:

```http
Authorization: Bearer <token>
```

Do not commit real API keys into the repository.

## Collector Architecture

The project separates data acquisition from dashboard publishing:

- `src/collect/`: TikHub client, collector interfaces, Instagram implementation, CLI, and dashboard export
- `data/collect/`: raw API snapshots plus normalized collection bundles
- `docs/assets/data/`: final dashboard-facing JSON files only

The current public entrypoints are:

- `collect_account_bundle(account_ref, include_comments=False, max_posts=None, max_comment_pages=None)`
- `export_dashboard_data(input_path, output_dir="docs/assets/data")`

Supported account and post references are shared across collectors:

- `AccountRef(platform, username=..., user_id=...)`
- `PostRef(platform, media_id=..., shortcode=..., url=...)`

Pagination cursors are treated as opaque values and passed through unchanged.

## Local Usage

Collect one Instagram account by username:

```bash
python -m src.collect collect-account \
  --platform instagram \
  --username nasa \
  --max-posts 5
```

Collect with comments and second-level replies:

```bash
python -m src.collect collect-account \
  --platform instagram \
  --username nasa \
  --include-comments \
  --max-posts 3 \
  --max-comment-pages 2
```

Export collected bundles into the GitHub Pages dashboard data files:

```bash
python -m src.collect export-dashboard \
  --input data/collect \
  --output-dir docs/assets/data
```

## Data Written to `data/`

Each collection run writes into a timestamped run directory:

```text
data/collect/<platform>/<account-slug>/<run-id>/
```

That run directory contains:

- `bundle.json`: normalized records for profile, posts, comments, replies, and request metadata
- `raw/account/profile.json`: raw TikHub profile response
- `raw/account_posts/*.json`: raw post page responses
- `raw/post_detail/*.json`: raw post detail responses
- `raw/comments/*.json`: raw comment page responses
- `raw/replies/*.json`: raw reply page responses

This keeps the raw acquisition trail available for debugging and replay, while the dashboard export remains a separate step.

## Dashboard Export Contract

`export-dashboard` transforms collected bundle data into the static files already used by the docs site:

- `docs/assets/data/site-summary.json`
- `docs/assets/data/accounts.json`
- `docs/assets/data/posts.json`
- `docs/assets/data/hashtags.json`
- `docs/assets/data/engagement-timeseries.json`

Raw TikHub payloads should not be written directly into `docs/assets/data/`.

## Cost and Rate Limit Notes

TikHub's pricing page uses pay-as-you-go billing, and several Instagram endpoints referenced by this project are documented at `0.002 USD/request` as of April 19, 2026. Always re-check the live pricing and endpoint docs before large collection runs:

- [TikHub pricing](https://tikhub.io/pricing)
- [TikHub docs](https://docs.tikhub.io/)

Safe usage suggestions:

- start with a small `--max-posts`
- cap `--max-comment-pages` during test runs
- collect profiles and posts first, then add comments only when needed
- monitor account balance and daily usage before large jobs

## Error Handling

The TikHub client maps common failure states into explicit collector errors:

- `401`: authentication failure, usually missing, invalid, or expired API key
- `402`: insufficient balance for a paid endpoint
- `429`: rate limited; the client retries with backoff before failing

Other notes:

- pagination retries are safe because cursors are preserved as opaque values
- `429` and `5xx` responses are retried automatically up to the configured limit
- request metadata is stored with normalized records so collection provenance is not lost

## Current Scope

The collector layer only handles acquisition and normalization.

It does not yet perform:

- ad or sponsorship labeling
- brand or product coding
- image description or content coding
- creator reply rate calculation as a derived research metric

Those belong in later preprocessing, labeling, and analysis stages.
