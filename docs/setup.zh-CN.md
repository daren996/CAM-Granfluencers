[English](./setup.md) | [中文](./setup.zh-CN.md)

# GitHub Pages 配置

如果你希望 `docs/` 目录中的内容直接成为项目网站，可以在 GitHub 中使用下面的设置。

## 推荐配置

1. 先把仓库推送到 GitHub。
2. 打开 GitHub 上的仓库页面。
3. 进入 **Settings** -> **Pages**。
4. 在 **Build and deployment** 中选择 **Deploy from a branch**。
5. 选择：
   - **Branch:** `main`（或你的默认分支）
   - **Folder:** `/docs`
6. 点击 **Save**。

GitHub 完成构建后，文档站点通常会发布到：

`https://<你的 GitHub 用户名>.github.io/<仓库名>/`

## 重要说明

- 首页文件通常应为 `docs/index.md` 或 `docs/index.html`。
- GitHub Pages 可以渲染 `docs/` 目录中的 Markdown 文件。
- 如果以后需要更完整的文档站点，也可以迁移到 MkDocs、Docusaurus 或其他静态站点生成器，但当前结构已经足够作为简单项目主页使用。
