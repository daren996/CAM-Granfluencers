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

Project documentation for GitHub Pages lives in [`docs/`](./docs/).
Files in `docs/` are bilingual and should be kept in sync.

- Homepage: [`docs/index.md`](./docs/index.md)
- Chinese homepage: [`docs/index.zh-CN.md`](./docs/index.zh-CN.md)
- Collection guide: [`docs/collect.md`](./docs/collect.md)
- Chinese collection guide: [`docs/collect.zh-CN.md`](./docs/collect.zh-CN.md)
- Dashboard plan: [`docs/dashboard.md`](./docs/dashboard.md)
- Chinese dashboard plan: [`docs/dashboard.zh-CN.md`](./docs/dashboard.zh-CN.md)
- Setup guide: [`docs/setup.md`](./docs/setup.md)
- Chinese setup guide: [`docs/setup.zh-CN.md`](./docs/setup.zh-CN.md)

The project homepage is planned to use a static dashboard approach on GitHub Pages.
Data will be exported into files under `docs/assets/data/`, and the frontend layer will read those JSON files for tables and visualizations after the data collection pipeline is ready.

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

The CLI automatically loads the repository `.env` when present and uses `TIKHUB_API_KEY` from there unless the variable is already set in your shell.
