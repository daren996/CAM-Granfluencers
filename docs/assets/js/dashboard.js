const DASHBOARD_DATA_FILES = Object.freeze({
  siteSummary: "./assets/data/site-summary.json",
  accounts: "./assets/data/accounts.json",
  posts: "./assets/data/posts.json",
  hashtags: "./assets/data/hashtags.json",
  engagementTimeseries: "./assets/data/engagement-timeseries.json",
});

async function fetchDashboardData(key) {
  const url = DASHBOARD_DATA_FILES[key];

  if (!url) {
    throw new Error(`Unknown dashboard data key: ${key}`);
  }

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to load dashboard data: ${url}`);
  }

  return response.json();
}

window.granfluencersDashboard = {
  DASHBOARD_DATA_FILES,
  fetchDashboardData,
};
