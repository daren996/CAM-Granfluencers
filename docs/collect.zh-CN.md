[English](./collect.md) | [中文](./collect.zh-CN.md)

# TikHub 采集指南

本项目目前暂时使用 [TikHub](https://tikhub.io/) 作为上游社交媒体数据提供方。仓库中第一批落地的平台是 Instagram，但采集层已经按统一接口设计，后续可以在同一套结构下继续接入其他平台。

## 为什么使用 TikHub

TikHub 的特点是一个 API key 覆盖多个社媒平台，并且已经提供了本项目当前最需要的 Instagram 接口，包括：

- 账号资料查询
- 账号帖子分页
- 帖子详情
- 帖子评论
- 评论回复
- 用户搜索

对这个项目来说，TikHub 适合作为数据获取入口，而数据规范化、存储和 dashboard 导出逻辑仍然保留在我们自己的仓库里。

## API Key 配置

1. 注册或登录 TikHub 账号。
2. 在用户 dashboard 中创建 API key。
3. 把它写入本地 `.env`：

```bash
TIKHUB_API_KEY=your_real_api_key
```

采集器会从环境变量读取 `TIKHUB_API_KEY`，并按下面的方式发送请求：

```http
Authorization: Bearer <token>
```

不要把真实 API key 提交到仓库中。

## 采集层结构

本项目把“数据采集”和“dashboard 发布”拆成两个阶段：

- `src/collect/`：TikHub client、统一 collector 接口、Instagram 实现、CLI 和 dashboard 导出
- `data/collect/`：原始 API 快照与规范化后的采集 bundle
- `docs/assets/data/`：仅保存最终给静态站点读取的 JSON 文件

当前对外的主要入口有：

- `collect_account_bundle(account_ref, include_comments=False, max_posts=None, max_comment_pages=None)`
- `export_dashboard_data(input_path, output_dir="docs/assets/data")`

各平台共用的引用对象为：

- `AccountRef(platform, username=..., user_id=...)`
- `PostRef(platform, media_id=..., shortcode=..., url=...)`

分页 cursor 会被当作不透明值原样传递，不在项目内部做二次解释。

## 本地运行方式

按用户名采集一个 Instagram 账号：

```bash
python -m src.collect collect-account \
  --platform instagram \
  --username nasa \
  --max-posts 5
```

同时采集评论和二级回复：

```bash
python -m src.collect collect-account \
  --platform instagram \
  --username nasa \
  --include-comments \
  --max-posts 3 \
  --max-comment-pages 2
```

把采集结果导出为 GitHub Pages dashboard 所需的数据文件：

```bash
python -m src.collect export-dashboard \
  --input data/collect \
  --output-dir docs/assets/data
```

## 会写入 `data/` 的内容

每次采集都会写入一个带时间戳的运行目录：

```text
data/collect/<platform>/<account-slug>/<run-id>/
```

该目录中包括：

- `bundle.json`：规范化后的 profile、posts、comments、replies 以及请求元数据
- `raw/account/profile.json`：账号资料接口的原始返回
- `raw/account_posts/*.json`：帖子分页接口的原始返回
- `raw/post_detail/*.json`：帖子详情接口的原始返回
- `raw/comments/*.json`：评论分页接口的原始返回
- `raw/replies/*.json`：回复分页接口的原始返回

这样可以保留原始采集轨迹，后续排查问题或回放数据时更方便；同时 dashboard 导出仍然保持独立步骤。

## Dashboard 导出约定

`export-dashboard` 会把采集 bundle 转换成当前文档站点已经约定好的静态数据文件：

- `docs/assets/data/site-summary.json`
- `docs/assets/data/accounts.json`
- `docs/assets/data/posts.json`
- `docs/assets/data/hashtags.json`
- `docs/assets/data/engagement-timeseries.json`

不要把 TikHub 的原始响应直接写进 `docs/assets/data/`。

## 计费与频率限制说明

TikHub 当前采用按量付费。根据 2026 年 4 月 19 日查到的公开页面，本项目引用的若干 Instagram 接口文档页标注为 `0.002 USD/request`。在执行大规模采集前，仍然建议重新确认最新价格和接口说明：

- [TikHub pricing](https://tikhub.io/pricing)
- [TikHub docs](https://docs.tikhub.io/)

更安全的使用方式包括：

- 先用较小的 `--max-posts` 试跑
- 在测试阶段限制 `--max-comment-pages`
- 先抓 profile 和 posts，需要时再加 comments
- 在大批量任务前先检查余额和当日使用情况

## 错误处理

TikHub client 会把常见失败状态映射为明确的错误类型：

- `401`：认证失败，通常表示 API key 缺失、无效或已过期
- `402`：余额不足，当前接口需要付费额度
- `429`：请求过快触发限流；client 会先做退避重试，再决定失败

补充说明：

- 分页重试是安全的，因为 cursor 会按原值保留
- `429` 和 `5xx` 响应会在配置的重试次数内自动重试
- 规范化记录会保留请求元数据，方便后续追溯采集来源

## 当前范围

当前采集层只负责数据获取和规范化。

它暂时不负责：

- 广告或赞助内容标注
- 品牌或产品编码
- 图像描述或内容编码
- 创作者回复率这类衍生研究变量计算

这些内容应放在后续的 preprocess、labeling 和 analysis 阶段处理。
