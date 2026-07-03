// ---- PulTrack frontend configuration ----
// Edit the two production values below after you deploy.

// Backend API base URL.
window.PULTRACK_API =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "https://YOUR-BACKEND.onrender.com"; // <-- change after deploying backend

// Your Telegram bot username (without @), used by the Login Widget.
window.PULTRACK_BOT_USERNAME = "pul_track_finance_bot"; // <-- change after creating the bot
