const DASHBOARD_DATA_FILES = Object.freeze({
  siteSummary: "./data/site-summary.json",
  accounts: "./data/accounts.json",
  posts: "./data/posts.json",
  comments: "./data/comments.json",
  hashtags: "./data/hashtags.json",
  engagementTimeseries: "./data/engagement-timeseries.json",
  collectionTree: "./data/collection-tree.json",
});

async function fetchDashboardData(key) {
  const url = DASHBOARD_DATA_FILES[key];

  if (!url) {
    throw new Error(`Unknown dashboard data key: ${key}`);
  }

  const response = await fetch(url, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Failed to load dashboard data: ${url}`);
  }

  return response.json();
}

window.granfluencersDashboard = {
  DASHBOARD_DATA_FILES,
  fetchDashboardData,
};
