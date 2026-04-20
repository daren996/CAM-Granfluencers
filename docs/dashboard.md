[English](./dashboard.md) | [中文](./dashboard.zh-CN.md)

# Dashboard Plan

This project will use a static dashboard approach for the GitHub Pages homepage.

## Decision

- Publish the site from the repository default branch and the `docs/` folder
- Keep the site static so it works cleanly with GitHub Pages
- Store prepared data files in `docs/assets/data/`
- Load those files from frontend code for tables and visualizations

## Planned Homepage Blocks

- Project overview
- Dataset summary cards
- Account or post table
- Engagement trend charts
- Hashtag or topic summaries
- Links to documentation and repository files

## Data Interfaces

The following placeholder files are reserved for the homepage:

- `docs/assets/data/site-summary.json`
- `docs/assets/data/accounts.json`
- `docs/assets/data/posts.json`
- `docs/assets/data/hashtags.json`
- `docs/assets/data/engagement-timeseries.json`

These files are intentionally empty or minimal for now. They will be filled after the data collection pipeline is ready.

## Frontend Interface

- `docs/assets/js/dashboard.js` provides a small data-loading interface
- Future homepage code can reuse the file map and loading helper from that script
- Visual components can be added later without changing the data file locations

## Notes

- The current repository only records the dashboard structure and file contracts
- Real records, tables, and charts will be added after Instagram data is collected and processed
