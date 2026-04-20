[English](./dashboard.md) | [中文](./dashboard.zh-CN.md)

# 数据展示方案

这个项目计划在 GitHub Pages 首页上采用静态 dashboard 的方式展示数据。

## 已定方案

- 使用仓库默认分支与 `docs/` 目录发布站点
- 保持站点为静态结构，方便直接部署到 GitHub Pages
- 将准备好的数据文件放在 `docs/assets/data/`
- 由前端代码读取这些文件，展示表格和可视化内容

## 计划中的首页模块

- 项目简介
- 数据概览卡片
- 账号或帖子表格
- 互动趋势图
- 标签或主题汇总
- 文档与仓库入口链接

## 数据接口

下面这些占位文件已经为主页预留：

- `docs/assets/data/site-summary.json`
- `docs/assets/data/accounts.json`
- `docs/assets/data/posts.json`
- `docs/assets/data/hashtags.json`
- `docs/assets/data/engagement-timeseries.json`

这些文件目前只保留空结构或最小结构，等数据采集与处理完成后再填入真实内容。

## 前端接口

- `docs/assets/js/dashboard.js` 提供了一个简单的数据读取接口
- 后续首页代码可以直接复用其中的文件映射和加载方法
- 以后补图表和表格时，不需要先改动数据文件位置约定

## 说明

- 当前仓库阶段先记录 dashboard 结构与文件约定
- 等 Instagram 数据采集与处理完成后，再把真实表格和图表接入进去
