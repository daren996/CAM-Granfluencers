(function () {
  const dashboard = window.granfluencersDashboard;

  if (!dashboard) {
    return;
  }

  const TEXT = {
    en: {
      updated: "Updated",
      statusReady: "Data ready",
      statusWaiting: "Waiting for data",
      accounts: "Accounts",
      posts: "Posts",
      comments: "Comments",
      dateRange: "Date range",
      from: "from",
      to: "to",
      notAvailable: "Not available",
      noRows: "No records yet.",
      topHashtags: "Top hashtags",
      recentPosts: "Recent posts",
      engagement: "Engagement timeline",
      username: "Username",
      name: "Name",
      followers: "Followers",
      caption: "Caption",
      likes: "Likes",
      commentsLabel: "Comments",
      date: "Date",
      postsLabel: "Posts",
      emptyHint: "Run the exporter and sync commands to publish fresh data into this page.",
    },
    zh: {
      updated: "最近更新",
      statusReady: "数据已就绪",
      statusWaiting: "等待数据",
      accounts: "账号数",
      posts: "帖子数",
      comments: "评论数",
      dateRange: "时间范围",
      from: "开始",
      to: "结束",
      notAvailable: "暂无",
      noRows: "当前还没有记录。",
      topHashtags: "高频标签",
      recentPosts: "最新帖子",
      engagement: "互动时间线",
      username: "用户名",
      name: "名称",
      followers: "粉丝数",
      caption: "文案",
      likes: "点赞",
      commentsLabel: "评论",
      date: "日期",
      postsLabel: "帖子数",
      emptyHint: "运行导出与同步命令后，这个页面会显示最新数据。",
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

  function buildSummaryMarkup(summary, lang) {
    const t = TEXT[lang];
    const counts = summary.counts || {};
    const dateRange = summary.date_range || {};
    const statusClass =
      summary.project_status === "ready_with_data" ? "status" : "status is-empty";
    const statusText =
      summary.project_status === "ready_with_data" ? t.statusReady : t.statusWaiting;

    return `
      <div class="metric-card">
        <span class="${statusClass}">${statusText}</span>
        <p class="footer-note">${t.updated}: ${escapeHtml(summary.updated_at || t.notAvailable)}</p>
      </div>
      <div class="metric-card">
        <span class="kicker">${t.accounts}</span>
        <p class="metric-value">${formatCount(counts.accounts)}</p>
      </div>
      <div class="metric-card">
        <span class="kicker">${t.posts}</span>
        <p class="metric-value">${formatCount(counts.posts)}</p>
      </div>
      <div class="metric-card">
        <span class="kicker">${t.comments}</span>
        <p class="metric-value">${formatCount(counts.comments)}</p>
      </div>
      <div class="metric-card">
        <span class="kicker">${t.dateRange}</span>
        <p class="muted">${escapeHtml(dateRange.start || t.notAvailable)} ${t.to} ${escapeHtml(
          dateRange.end || t.notAvailable,
        )}</p>
      </div>
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
            <td>${formatCount(account.followers)}</td>
            <td>${escapeHtml(account.full_name || t.notAvailable)}</td>
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
      <ul class="pill-list">
        ${hashtags
          .slice(0, 12)
          .map(
            (item) =>
              `<li>#${escapeHtml(item.hashtag)} <strong>${formatCount(item.post_count)}</strong></li>`,
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
            <td>${formatCount(row.posts)}</td>
            <td>${formatCount(row.likes)}</td>
            <td>${formatCount(row.comments)}</td>
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
              <th>${t.postsLabel}</th>
              <th>${t.likes}</th>
              <th>${t.commentsLabel}</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
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

    const [accounts, posts, hashtags, engagementTimeseries] = await Promise.all([
      dashboard.fetchDashboardData("accounts"),
      dashboard.fetchDashboardData("posts"),
      dashboard.fetchDashboardData("hashtags"),
      dashboard.fetchDashboardData("engagementTimeseries"),
    ]);

    blocks.forEach((block) => {
      const lang = block.dataset.lang === "zh-CN" ? "zh" : "en";
      const accountRoot = block.querySelector("[data-analysis-accounts]");
      const postRoot = block.querySelector("[data-analysis-posts]");
      const hashtagRoot = block.querySelector("[data-analysis-hashtags]");
      const timelineRoot = block.querySelector("[data-analysis-timeline]");

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
