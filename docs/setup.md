[English](./setup.md) | [中文](./setup.zh-CN.md)

# GitHub Pages Setup

If you want the content inside `docs/` to become your project website, use the following setup in GitHub:

## Recommended Configuration

1. Push this repository to GitHub.
2. Open the repository on GitHub.
3. Go to **Settings** -> **Pages**.
4. Under **Build and deployment**, choose **Deploy from a branch**.
5. Select:
   - **Branch:** `main` (or your default branch)
   - **Folder:** `/docs`
6. Click **Save**.

After GitHub finishes building the site, your documentation will usually be available at:

`https://<your-github-username>.github.io/<repository-name>/`

## Important Notes

- The homepage file should be `docs/index.md` or `docs/index.html`.
- GitHub Pages can render Markdown files in the `docs/` folder.
- If you later want a more polished docs site, you can switch to tools like MkDocs, Docusaurus, or a static site generator, but this current structure already works for a simple project homepage.

## 中文步骤

如果你希望 `docs/` 里的内容直接变成 GitHub 项目主页，请这样设置：

1. 先把仓库推送到 GitHub
2. 进入仓库页面
3. 打开 **Settings**
4. 点击 **Pages**
5. 在发布来源里选择 **Deploy from a branch**
6. 分支选择 `main`，目录选择 `/docs`
7. 保存后等待 GitHub 构建完成

构建完成后，`docs/index.md` 就会作为主页显示。
