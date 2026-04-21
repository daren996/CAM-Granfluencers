(function () {
  const dashboard = window.granfluencersDashboard;

  if (!dashboard) {
    return;
  }

  const TEXT = {
    en: {
      updated: "Updated",
      projectStatus: "Project status",
      statusReady: "Data ready",
      statusWaiting: "Waiting for data",
      platforms: "Platforms",
      accounts: "Accounts",
      items: "Items",
      posts: "Posts",
      reels: "Reels",
      comments: "Comment records",
      topLevelComments: "Top-level comments",
      replies: "Replies",
      dateRange: "Date range",
      from: "from",
      to: "to",
      notAvailable: "Not available",
      noRows: "No records yet.",
      topHashtags: "Top hashtags",
      recentPosts: "Recent items",
      engagement: "Engagement timeline",
      collectionTree: "Collection tree",
      treeHint: "Expand platform, account, and post/reel nodes to inspect every exported field.",
      username: "Username",
      name: "Name",
      followers: "Followers",
      following: "Following",
      accountId: "Account ID",
      biography: "Biography",
      externalUrl: "External URL",
      caption: "Caption",
      likes: "Likes",
      commentsLabel: "Comments",
      repliesLabel: "Replies",
      plays: "Plays",
      date: "Date",
      postsLabel: "Posts",
      reelsLabel: "Reels",
      itemsLabel: "Items",
      mediaType: "Media type",
      hashtags: "Hashtags",
      url: "URL",
      code: "Code",
      itemType: "Item type",
      extractedAt: "Extracted at",
      metrics: "Metrics JSON",
      profile: "Profile JSON",
      postRecord: "Post JSON",
      requestLog: "Request log JSON",
      outputPaths: "Output paths JSON",
      mediaAssets: "Media assets JSON",
      commentThreads: "Comment threads",
      commentRecord: "Comment JSON",
      replyRecord: "Reply JSON",
      orphanReplies: "Orphan replies",
      creatorInteraction: "Creator interaction",
      profileLabel: "Profile",
      postLabel: "Post",
      reelLabel: "Reel",
      emptyHint: "Run the exporter and sync commands to publish fresh data into this page.",
      openJson: "Open JSON",
    },
    zh: {
      updated: "最近更新",
      projectStatus: "项目状态",
      statusReady: "数据已就绪",
      statusWaiting: "等待数据",
      platforms: "平台数",
      accounts: "账号数",
      items: "条目数",
      posts: "帖子数",
      reels: "Reels 数",
      comments: "评论记录数",
      topLevelComments: "顶级评论数",
      replies: "回复数",
      dateRange: "时间范围",
      from: "开始",
      to: "结束",
      notAvailable: "暂无",
      noRows: "当前还没有记录。",
      topHashtags: "高频标签",
      recentPosts: "最新条目",
      engagement: "互动时间线",
      collectionTree: "层级采集树",
      treeHint: "按 platform、account、post/reel 逐层展开，即可查看导出的全部字段。",
      username: "用户名",
      name: "名称",
      followers: "粉丝数",
      following: "关注数",
      accountId: "账号 ID",
      biography: "简介",
      externalUrl: "外链",
      caption: "文案",
      likes: "点赞",
      commentsLabel: "评论",
      repliesLabel: "回复",
      plays: "播放",
      date: "日期",
      postsLabel: "帖子数",
      reelsLabel: "Reels 数",
      itemsLabel: "条目数",
      mediaType: "媒体类型",
      hashtags: "标签",
      url: "链接",
      code: "短代码",
      itemType: "条目类型",
      extractedAt: "提取时间",
      metrics: "指标 JSON",
      profile: "资料 JSON",
      postRecord: "帖子 JSON",
      requestLog: "请求日志 JSON",
      outputPaths: "输出路径 JSON",
      mediaAssets: "媒体资产 JSON",
      commentThreads: "评论线程",
      commentRecord: "评论 JSON",
      replyRecord: "回复 JSON",
      orphanReplies: "孤立回复",
      creatorInteraction: "创作者互动",
      profileLabel: "账号资料",
      postLabel: "帖子",
      reelLabel: "Reel",
      emptyHint: "运行导出与同步命令后，这个页面会显示最新数据。",
      openJson: "展开 JSON",
    },
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatCount(value) {
    return Number(value || 0).toLocaleString();
  }

  function formatCountOrFallback(value, fallback) {
    if (value === null || value === undefined || value === "") {
      return fallback;
    }
    return Number(value).toLocaleString();
  }

  function truncateText(value, length) {
    const text = String(value ?? "").trim();
    if (!text) {
      return "";
    }
    if (text.length <= length) {
      return text;
    }
    return `${text.slice(0, length - 1)}…`;
  }

  function formatValue(value, fallback) {
    if (value === null || value === undefined || value === "") {
      return fallback;
    }
    return escapeHtml(value);
  }

  function buildSummaryMarkup(summary, lang) {
    const t = TEXT[lang];
    const counts = summary.counts || {};
    const dateRange = summary.date_range || {};
    const statusClass =
      summary.project_status === "ready_with_data" ? "status" : "status is-empty";
    const statusText =
      summary.project_status === "ready_with_data" ? t.statusReady : t.statusWaiting;
    const countRows = [
      [t.platforms, counts.platforms],
      [t.accounts, counts.accounts],
      [t.items, counts.items],
      [t.posts, counts.posts],
      [t.reels, counts.reels],
      [t.comments, counts.comments],
      [t.topLevelComments, counts.top_level_comments],
      [t.replies, counts.replies],
    ];

    return `
      <dl class="summary-list">
        <div class="summary-row">
          <dt>${t.projectStatus}</dt>
          <dd><span class="${statusClass}">${statusText}</span></dd>
        </div>
        <div class="summary-row">
          <dt>${t.updated}</dt>
          <dd>${escapeHtml(summary.updated_at || t.notAvailable)}</dd>
        </div>
        ${countRows
          .map(
            ([label, value]) => `
              <div class="summary-row">
                <dt>${label}</dt>
                <dd><span class="metric-value">${formatCount(value)}</span></dd>
              </div>
            `,
          )
          .join("")}
        <div class="summary-row">
          <dt>${t.dateRange}</dt>
          <dd>${escapeHtml(dateRange.start || t.notAvailable)} ${t.to} ${escapeHtml(
            dateRange.end || t.notAvailable,
          )}</dd>
        </div>
      </dl>
    `;
  }

  function buildAccountsTable(accounts, lang) {
    const t = TEXT[lang];

    if (!accounts.length) {
      return `<p class="muted">${t.noRows}</p>`;
    }

    const rows = accounts
      .slice(0, 8)
      .map(
        (account) => `
          <tr>
            <td>${escapeHtml(account.username || t.notAvailable)}</td>
            <td>${formatCountOrFallback(account.followers, t.notAvailable)}</td>
            <td>${escapeHtml(account.full_name || t.notAvailable)}</td>
            <td>${formatCount(account.stored_items)}</td>
          </tr>
        `,
      )
      .join("");

    return `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>${t.username}</th>
              <th>${t.followers}</th>
              <th>${t.name}</th>
              <th>${t.items}</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  function buildPostsTable(posts, lang) {
    const t = TEXT[lang];

    if (!posts.length) {
      return `<p class="muted">${t.noRows}</p>`;
    }

    const rows = posts
      .slice(0, 8)
      .map(
        (post) => `
          <tr>
            <td>${escapeHtml(post.username || t.notAvailable)}</td>
            <td>${escapeHtml((post.caption || "").slice(0, 110) || t.notAvailable)}</td>
            <td>${formatCount(post.likes)}</td>
            <td>${formatCount(post.comments)}</td>
            <td>${formatCount(post.plays)}</td>
            <td>${escapeHtml((post.taken_at || "").slice(0, 10) || t.notAvailable)}</td>
          </tr>
        `,
      )
      .join("");

    return `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>${t.username}</th>
              <th>${t.caption}</th>
              <th>${t.likes}</th>
              <th>${t.commentsLabel}</th>
              <th>${t.plays}</th>
              <th>${t.date}</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  function buildHashtagList(hashtags, lang) {
    const t = TEXT[lang];

    if (!hashtags.length) {
      return `<p class="muted">${t.noRows}</p>`;
    }

    return `
      <ul class="data-list">
        ${hashtags
          .slice(0, 12)
          .map(
            (item) =>
              `<li><span>#${escapeHtml(item.hashtag)}</span><strong>${formatCount(
                item.post_count,
              )}</strong></li>`,
          )
          .join("")}
      </ul>
    `;
  }

  function buildTimeseriesTable(series, lang) {
    const t = TEXT[lang];

    if (!series.length) {
      return `<p class="muted">${t.emptyHint}</p>`;
    }

    const rows = series
      .slice(-8)
      .reverse()
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.date || t.notAvailable)}</td>
            <td>${formatCount(row.items)}</td>
            <td>${formatCount(row.posts)}</td>
            <td>${formatCount(row.reels)}</td>
            <td>${formatCount(row.likes)}</td>
            <td>${formatCount(row.comments)}</td>
            <td>${formatCount(row.plays)}</td>
          </tr>
        `,
      )
      .join("");

    return `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>${t.date}</th>
              <th>${t.itemsLabel}</th>
              <th>${t.postsLabel}</th>
              <th>${t.reelsLabel}</th>
              <th>${t.likes}</th>
              <th>${t.commentsLabel}</th>
              <th>${t.plays}</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  function buildChipList(entries) {
    const visible = entries.filter((entry) => entry.value !== null && entry.value !== undefined);
    if (!visible.length) {
      return "";
    }

    return `
      <ul class="chip-list">
        ${visible
          .map(
            (entry) => `
              <li class="chip">
                <span>${escapeHtml(entry.label)}</span>
                <strong>${escapeHtml(entry.value)}</strong>
              </li>
            `,
          )
          .join("")}
      </ul>
    `;
  }

  function buildFactGrid(facts, lang) {
    const t = TEXT[lang];
    const visible = facts.filter((fact) => fact.value !== null && fact.value !== undefined && fact.value !== "");

    if (!visible.length) {
      return `<p class="muted">${t.noRows}</p>`;
    }

    return `
      <dl class="definition-list compact-definition-list">
        ${visible
          .map(
            (fact) => `
              <div class="definition-row">
                <dt>${escapeHtml(fact.label)}</dt>
                <dd>${fact.isCode ? `<code>${formatValue(fact.value, t.notAvailable)}</code>` : formatValue(fact.value, t.notAvailable)}</dd>
              </div>
            `,
          )
          .join("")}
      </dl>
    `;
  }

  function buildJsonDetails(title, value, lang, open) {
    const t = TEXT[lang];
    const hasValue =
      value !== null &&
      value !== undefined &&
      (!(Array.isArray(value)) || value.length > 0) &&
      (typeof value !== "object" || Array.isArray(value) || Object.keys(value).length > 0);

    if (!hasValue) {
      return "";
    }

    const payload = JSON.stringify(value, null, 2);
    return `
      <details class="json-details"${open ? " open" : ""}>
        <summary>${escapeHtml(title)}</summary>
        <pre class="json-block"><code>${escapeHtml(payload)}</code></pre>
      </details>
    `;
  }

  function buildCommentNode(comment, lang, typeLabel, creatorUsername, childrenMarkup) {
    const t = TEXT[lang];
    const user = comment.user || {};
    const title = `${escapeHtml(user.username || t.notAvailable)} · ${escapeHtml(
      truncateText(comment.text || t.notAvailable, 96),
    )}`;

    return `
      <details class="tree-node tree-comment">
        <summary>${title}</summary>
        <div class="tree-node-body">
          ${buildFactGrid(
            [
              { label: t.username, value: user.username },
              { label: t.name, value: user.full_name },
              { label: t.date, value: comment.created_at },
              { label: t.likes, value: comment.like_count },
              { label: t.commentsLabel, value: comment.child_comment_count },
              {
                label: t.creatorInteraction,
                value:
                  creatorUsername && user.username && creatorUsername === user.username ? "yes" : undefined,
              },
            ],
            lang,
          )}
          ${buildJsonDetails(typeLabel, comment, lang, false)}
          ${childrenMarkup || ""}
        </div>
      </details>
    `;
  }

  function buildCommentThreads(threads, lang, creatorUsername) {
    const t = TEXT[lang];

    if (!threads.length) {
      return `<p class="muted">${t.noRows}</p>`;
    }

    return `
      <div class="tree-children">
        ${threads
          .map((thread) => {
            const replies = (thread.replies || [])
              .map((reply) => buildCommentNode(reply, lang, t.replyRecord, creatorUsername, ""))
              .join("");

            if (thread.comment) {
              return buildCommentNode(
                thread.comment,
                lang,
                t.commentRecord,
                creatorUsername,
                replies ? `<div class="tree-children">${replies}</div>` : "",
              );
            }

            return `
              <details class="tree-node tree-comment">
                <summary>${t.orphanReplies}: ${escapeHtml(thread.parent_comment_id || t.notAvailable)}</summary>
                <div class="tree-node-body">
                  ${replies ? `<div class="tree-children">${replies}</div>` : `<p class="muted">${t.noRows}</p>`}
                </div>
              </details>
            `;
          })
          .join("")}
      </div>
    `;
  }

  function buildItemNode(item, lang) {
    const t = TEXT[lang];
    const post = item.post || {};
    const metrics = post.metrics || {};
    const author = post.author || {};
    const itemLabel = item.item_type === "reel" ? t.reelLabel : t.postLabel;

    return `
      <details class="tree-node tree-item">
        <summary>
          <span>${escapeHtml(itemLabel)} · ${escapeHtml(item.item_key || t.notAvailable)}</span>
          <span class="tree-summary-meta">${formatCount(metrics.likes)} ${t.likes} · ${formatCount(
            metrics.comments,
          )} ${t.commentsLabel} · ${formatCount(metrics.plays)} ${t.plays}</span>
        </summary>
        <div class="tree-node-body">
          ${buildChipList([
            { label: t.itemType, value: item.item_type },
            { label: t.mediaType, value: post.media_type },
            { label: t.likes, value: formatCount(metrics.likes) },
            { label: t.commentsLabel, value: formatCount(metrics.comments) },
            { label: t.plays, value: formatCount(metrics.plays) },
            { label: t.repliesLabel, value: formatCount((item.summary || {}).replies) },
          ])}
          ${buildFactGrid(
            [
              { label: t.username, value: author.username },
              { label: t.name, value: author.full_name },
              { label: t.code, value: post.code, isCode: true },
              { label: t.url, value: post.url },
              { label: t.date, value: post.taken_at },
              { label: t.extractedAt, value: item.extracted_at },
              { label: t.caption, value: post.caption },
              { label: t.hashtags, value: (post.hashtags || []).map((tag) => `#${tag}`).join(" ") },
            ],
            lang,
          )}
          ${buildJsonDetails(t.postRecord, post, lang, false)}
          ${buildJsonDetails(t.mediaAssets, post.media_assets || [], lang, false)}
          ${buildJsonDetails(t.requestLog, item.request_log || [], lang, false)}
          ${buildJsonDetails(t.outputPaths, item.output_paths || {}, lang, false)}
          <section class="tree-subsection">
            <h3>${t.commentThreads}</h3>
            ${buildCommentThreads(item.comment_threads || [], lang, author.username)}
          </section>
        </div>
      </details>
    `;
  }

  function buildAccountNode(account, lang) {
    const t = TEXT[lang];
    const profile = account.profile || {};
    const metrics = account.metrics || {};
    const summary = account.summary || {};

    return `
      <details class="tree-node tree-account">
        <summary>
          <span>${escapeHtml(profile.username || t.notAvailable)} · ${escapeHtml(
            profile.full_name || t.notAvailable,
          )}</span>
          <span class="tree-summary-meta">${formatCountOrFallback(profile.followers_count, t.notAvailable)} ${t.followers} · ${formatCount(
            summary.items,
          )} ${t.itemsLabel}</span>
        </summary>
        <div class="tree-node-body">
          ${buildChipList([
            { label: t.followers, value: formatCountOrFallback(profile.followers_count, t.notAvailable) },
            { label: t.following, value: formatCountOrFallback(profile.following_count, t.notAvailable) },
            { label: t.items, value: formatCount(summary.items) },
            { label: t.posts, value: formatCount(summary.posts) },
            { label: t.reels, value: formatCount(summary.reels) },
            { label: t.comments, value: formatCount(summary.comments) },
            { label: t.replies, value: formatCount(summary.replies) },
            { label: t.plays, value: formatCount(metrics.stored_plays) },
          ])}
          ${buildFactGrid(
            [
              { label: t.accountId, value: profile.account_id, isCode: true },
              { label: t.username, value: profile.username },
              { label: t.name, value: profile.full_name },
              { label: t.biography, value: profile.biography },
              { label: t.externalUrl, value: profile.external_url },
              { label: t.extractedAt, value: account.extracted_at },
            ],
            lang,
          )}
          ${buildJsonDetails(t.profile, profile, lang, false)}
          ${buildJsonDetails(t.metrics, metrics, lang, false)}
          ${buildJsonDetails(t.requestLog, account.request_log || [], lang, false)}
          ${buildJsonDetails(t.outputPaths, account.output_paths || {}, lang, false)}
          <div class="tree-children">
            ${(account.items || []).map((item) => buildItemNode(item, lang)).join("")}
          </div>
        </div>
      </details>
    `;
  }

  function buildCollectionTree(tree, lang) {
    const t = TEXT[lang];
    const platforms = tree.platforms || [];

    if (!platforms.length) {
      return `<p class="muted">${t.emptyHint}</p>`;
    }

    return `
      <p class="muted">${t.treeHint}</p>
      <div class="tree-root">
        ${platforms
          .map(
            (platformNode) => `
              <details class="tree-node tree-platform" open>
                <summary>
                  <span>${escapeHtml(platformNode.platform || t.notAvailable)}</span>
                  <span class="tree-summary-meta">${formatCount(
                    (platformNode.summary || {}).accounts,
                  )} ${t.accounts} · ${formatCount((platformNode.summary || {}).items)} ${t.itemsLabel}</span>
                </summary>
                <div class="tree-node-body">
                  ${buildChipList([
                    { label: t.accounts, value: formatCount((platformNode.summary || {}).accounts) },
                    { label: t.items, value: formatCount((platformNode.summary || {}).items) },
                    { label: t.posts, value: formatCount((platformNode.summary || {}).posts) },
                    { label: t.reels, value: formatCount((platformNode.summary || {}).reels) },
                    { label: t.comments, value: formatCount((platformNode.summary || {}).comments) },
                    { label: t.replies, value: formatCount((platformNode.summary || {}).replies) },
                  ])}
                  <div class="tree-children">
                    ${(platformNode.accounts || []).map((account) => buildAccountNode(account, lang)).join("")}
                  </div>
                </div>
              </details>
            `,
          )
          .join("")}
      </div>
    `;
  }

  async function renderSummaryBlocks() {
    const blocks = document.querySelectorAll("[data-site-summary]");

    if (!blocks.length) {
      return;
    }

    const summary = await dashboard.fetchDashboardData("siteSummary");

    blocks.forEach((block) => {
      const lang = block.dataset.lang === "zh-CN" ? "zh" : "en";
      block.innerHTML = buildSummaryMarkup(summary, lang);
    });
  }

  async function renderAnalysisBlocks() {
    const blocks = document.querySelectorAll("[data-analysis-root]");

    if (!blocks.length) {
      return;
    }

    const [accounts, posts, hashtags, engagementTimeseries, collectionTree] = await Promise.all([
      dashboard.fetchDashboardData("accounts"),
      dashboard.fetchDashboardData("posts"),
      dashboard.fetchDashboardData("hashtags"),
      dashboard.fetchDashboardData("engagementTimeseries"),
      dashboard.fetchDashboardData("collectionTree"),
    ]);

    blocks.forEach((block) => {
      const lang = block.dataset.lang === "zh-CN" ? "zh" : "en";
      const accountRoot = block.querySelector("[data-analysis-accounts]");
      const postRoot = block.querySelector("[data-analysis-posts]");
      const hashtagRoot = block.querySelector("[data-analysis-hashtags]");
      const timelineRoot = block.querySelector("[data-analysis-timeline]");
      const treeRoot = block.querySelector("[data-analysis-tree]");

      if (accountRoot) {
        accountRoot.innerHTML = buildAccountsTable(accounts, lang);
      }

      if (postRoot) {
        postRoot.innerHTML = buildPostsTable(posts, lang);
      }

      if (hashtagRoot) {
        hashtagRoot.innerHTML = buildHashtagList(hashtags, lang);
      }

      if (timelineRoot) {
        timelineRoot.innerHTML = buildTimeseriesTable(engagementTimeseries, lang);
      }

      if (treeRoot) {
        treeRoot.innerHTML = buildCollectionTree(collectionTree, lang);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    try {
      await renderSummaryBlocks();
      await renderAnalysisBlocks();
    } catch (error) {
      console.error(error);
    }
  });
})();
