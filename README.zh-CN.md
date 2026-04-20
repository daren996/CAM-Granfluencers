[English](README.md) | [中文](README.zh-CN.md)

# 数字媒体中的老年网红：关于内容、互动与用户回应的计算分析

## 项目目标
本项目使用计算传播与计算社会科学方法，研究社交媒体中的老年网红（granfluencers）。项目重点关注其内容生产、媒介呈现方式以及用户互动行为，并进一步探讨他们如何影响受众参与、感知与广告传播效果。通过对大规模社交媒体数据的分析，本项目旨在更系统地理解 granfluencers 在数字传播与说服中的角色。

## 研究流程

### 1. 数据收集
收集与 Instagram 平台 granfluencers 相关的大规模社交媒体数据，重点包括：

- Granfluencer 名单
- 帖子（Post）
- 标题文案（Caption）
- 图片（Image）
- 图片详细描述，如行为、颜色、物品、背景、人物存在、活动、身体暴露、面部表情等
- 话题标签（Hashtag）
- 发布时间与日期（Time / Date）
- 互动数据，包括点赞、评论、分享
- 创作者回复率（Creator Reply Rate）
- 广告内容（Ad）
- 产品信息（Product）
- 品牌信息（Brand）
- 商业内容占比（Percentage）
- Granfluencer 账号画像（Profile of Granfluencer）
- 帖子评论详情（Post Comments in Detail）

### 2. 数据预处理
采用计算方法对原始数据进行清洗、整理与结构化处理，包括但不限于：

- 文本预处理
- 图像内容描述与编码
- 评论数据整理
- 广告与品牌信息标注
- 时间与互动指标标准化

### 3. 计算分析
使用自然语言处理（NLP）、主题模型（Topic Modeling）或基于大语言模型（LLM-based Coding）的方法，分析内容特征与媒介呈现方式，例如：

- 温暖感（Warmth）
- 日常性（Everydayness）
- 创造力（Creativity）
- 商业意图（Commercial Intent）

### 4. 数据分析
结合内容特征、用户互动与广告变量，进一步分析：

- 哪些内容特征更容易引发较高互动
- 用户如何回应 granfluencer 的形象与表达
- 商业合作内容如何影响用户反应与传播效果

### 5. 结果解释
从数字传播、用户感知与社交媒体说服机制的角度，对分析结果进行解释，并讨论 granfluencers 在平台文化与品牌传播中的意义。

### 6. 潜在结论
本项目预期将帮助回答以下问题：

- Granfluencers 在社交媒体中通常呈现出怎样的内容风格与形象特征
- 哪些因素与更高的用户参与度相关
- 他们如何影响用户对内容、品牌与广告的感知
- 老年创作者在数字传播生态中的独特价值是什么

## 关键词

`granfluencers` `social media` `Instagram` `computational analysis` `digital communication` `engagement` `advertising` `user response`

---

## 文档站点

项目文档站点内容位于 [`docs/`](./docs/)，并已经改成中英双语的 HTML 站点。
`docs/` 是项目面向使用者的规范来源，代码变更也应与其中说明保持一致。

- 首页入口：[`docs/index.html`](./docs/index.html)
- 中文首页：[`docs/index.zh-CN.html`](./docs/index.zh-CN.html)
- Wiki：[`docs/wiki.html`](./docs/wiki.html)
- 中文 Wiki：[`docs/wiki.zh-CN.html`](./docs/wiki.zh-CN.html)
- 采集指南：[`docs/collect.zh-CN.html`](./docs/collect.zh-CN.html)
- Collection Guide：[`docs/collect.html`](./docs/collect.html)
- 分析页面：[`docs/analysis.html`](./docs/analysis.html)
- 中文分析页面：[`docs/analysis.zh-CN.html`](./docs/analysis.zh-CN.html)
- 结果页面：[`docs/results.html`](./docs/results.html)
- 中文结果页面：[`docs/results.zh-CN.html`](./docs/results.zh-CN.html)
- 配置说明：[`docs/setup.html`](./docs/setup.html)
- 中文配置说明：[`docs/setup.zh-CN.html`](./docs/setup.zh-CN.html)

项目的规范数据目录位于 `data/dashboard/`。
发布站点读取的是同步后的 `docs/data/` 镜像文件。

当采集代码或数据更新后，可以用下面的命令刷新站点数据：

```bash
python3 -m src.collect export-dashboard --input data/collect
python3 -m src.collect sync-docs-data
```

也可以直接使用组合命令：

```bash
make docs-data
```

如果要把它发布成 GitHub 项目主页，最简单的做法是：

1. 将仓库推送到 GitHub
2. 打开仓库的 **Settings**
3. 进入 **Pages**
4. 选择 **Deploy from a branch**
5. 分支选择 `main`（或你的默认分支）
6. 文件夹选择 `/docs`

发布后，地址通常会是：

`https://<你的 GitHub 用户名>.github.io/<仓库名>/`

## 测试

在仓库根目录可以使用统一测试入口：

- `make test` 或 `make test-all`：运行全部测试
- `make test-client`：只运行 TikHub client 单元测试
- `make test-collect`：运行采集层相关测试
- `make check-client-live`：使用 `.env` 中的 key 运行真实 TikHub 连通性检查

同样也可以直接使用：

`python3 scripts/run_tests.py <all|client|collect>`

如果要做真实的 TikHub 在线检查，可以运行：

`python3 -m src.collect check`

CLI 会在本地存在 `.env` 时自动读取它，并使用其中的 `TIKHUB_API_KEY`；如果当前 shell 已经设置了同名环境变量，则优先使用 shell 中的值。
