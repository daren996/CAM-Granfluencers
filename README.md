[English](README.md) | [中文](README.zh-CN.md)

# Granfluencers in Digital Media: A Computational Analysis of Content, Engagement, and User Response

### Project Aim
This project uses computational methods to study granfluencers on social media. It focuses on their content, portrayal, and user interactions, and explores how they influence audience engagement, perception, and advertising outcomes. By analyzing large-scale social media data, the project aims to better understand the role of granfluencers in digital communication and persuasion.

### Workflow

#### 1. Data Collection
Collect large-scale Instagram data related to granfluencers, including:

- List of granfluencers
- Posts
- Captions
- Images
- Detailed image descriptions, such as behaviors, colors, items, backgrounds, human presence, activities, body exposure, and facial expressions
- Hashtags
- Posting time and date
- Engagement metrics, including likes, comments, and shares
- Creator reply rate
- Advertising content
- Product information
- Brand information
- Percentage of commercial content
- Profile of each granfluencer
- Detailed post comments

#### 2. Data Preprocessing
Apply computational preprocessing methods to clean, organize, and structure the data, including:

- Text preprocessing
- Image description and coding
- Comment organization
- Ad and brand annotation
- Standardization of time and engagement variables

#### 3. Computational Coding and Content Analysis
Use computational methods such as Natural Language Processing (NLP), topic modeling, or LLM-based coding to analyze content features and media portrayal, including:

- Warmth
- Everydayness
- Creativity
- Commercial intent

#### 4. Data Analysis
Examine the relationships among content features, user engagement, and advertising variables, including:

- Which content features are associated with higher engagement
- How users respond to the portrayal and expression of granfluencers
- How branded or sponsored content affects user reactions and communication outcomes

#### 5. Data Interpretation
Interpret the findings through the lens of digital communication, audience perception, and persuasion on social media, and discuss the broader significance of granfluencers in platform culture and brand communication.

#### 6. Potential Conclusions
This project is expected to help answer questions such as:

- What kinds of content styles and self-presentation patterns are common among granfluencers
- Which factors are associated with stronger user engagement
- How granfluencers shape user perceptions of content, brands, and advertising
- What unique role older creators play in the digital media ecosystem

---

## Keywords

`granfluencers` `social media` `Instagram` `computational analysis` `digital communication` `engagement` `advertising` `user response`

---

## Documentation Site

Project documentation for GitHub Pages lives in [`docs/`](./docs/) as a bilingual HTML site.
Files in `docs/` are the source of truth for user-facing behavior and should be kept in sync with code changes.

- Homepage: [`docs/index.html`](./docs/index.html)
- Chinese homepage: [`docs/index.zh-CN.html`](./docs/index.zh-CN.html)
- Wiki: [`docs/wiki.html`](./docs/wiki.html)
- Chinese wiki: [`docs/wiki.zh-CN.html`](./docs/wiki.zh-CN.html)
- Interactive collect page: [`docs/collect.html`](./docs/collect.html)
- Chinese interactive collect page: [`docs/collect.zh-CN.html`](./docs/collect.zh-CN.html)
- Wiki collection chapter: [`docs/wiki-collection.html`](./docs/wiki-collection.html)
- Chinese wiki collection chapter: [`docs/wiki-collection.zh-CN.html`](./docs/wiki-collection.zh-CN.html)
- Analysis page: [`docs/analysis.html`](./docs/analysis.html)
- Chinese analysis page: [`docs/analysis.zh-CN.html`](./docs/analysis.zh-CN.html)
- Results page: [`docs/results.html`](./docs/results.html)
- Chinese results page: [`docs/results.zh-CN.html`](./docs/results.zh-CN.html)
- Setup guide: [`docs/setup.html`](./docs/setup.html)
- Chinese setup guide: [`docs/setup.zh-CN.html`](./docs/setup.zh-CN.html)

Canonical dashboard data lives under `data/dashboard/`.
The published site reads a synchronized copy under `docs/data/`.
Raw collection data under `data/collect/` is organized by account, with `account.json` plus per-item
`posts/*/item.json` and `reels/*/item.json` files. Each JSON stores its own extraction timestamp, and
downloaded profile and item media are saved alongside those records, including single videos and
all assets from mixed carousels.

To refresh site data after running the collector:

```bash
python3 -m src.collect export-dashboard --input data/collect
python3 -m src.collect sync-docs-data
```

Or use the combined helper:

```bash
make docs-data
```

To open the interactive local collect page that calls Python functions directly, run:

```bash
python3 -m src.collect serve
```

Then open `http://127.0.0.1:8000/collect.html`. The older collection documentation now lives in the wiki chapter `docs/wiki-collection.html`.

To publish it as the project website on GitHub:

1. Open the repository on GitHub
2. Go to **Settings** -> **Pages**
3. Choose **Deploy from a branch**
4. Select `main` (or your default branch)
5. Select the `/docs` folder

The site URL will usually look like:

`https://<your-github-username>.github.io/<repository-name>/`

## Testing

Use the shared test entrypoints from the repository root:

- `make test` or `make test-all` runs the full test suite
- `make test-client` runs only the TikHub client unit tests
- `make test-collect` runs the collection-layer tests
- `make check-client-live` runs a real TikHub API key smoke check using `.env`

The same suites are also available through:

`python3 scripts/run_tests.py <all|client|collect>`

For a live TikHub connectivity check, run:

`python3 -m src.collect check`

`python3 -m src.collect serve`

The CLI automatically loads the repository `.env` when present and uses `TIKHUB_API_KEY` from there unless the variable is already set in your shell.
