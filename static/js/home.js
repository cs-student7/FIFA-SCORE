/* LEAGUE PLUS — Home Page JS */
'use strict';

document.addEventListener('DOMContentLoaded', () => {
  // Poll live match section every N seconds as fallback
  const liveContainer = document.getElementById('live-matches-container');
  if (liveContainer && document.querySelectorAll('[data-status="live"]').length > 0) {
    setInterval(() => {
      fetch('/api/v1/matches/live/')
        .then(r => r.json())
        .then(data => {
          if (data && data.length === 0) {
            const section = document.querySelector('[aria-labelledby="live-heading"]');
            if (section) section.style.display = 'none';
          }
        })
        .catch(() => {});
    }, GP_CONFIG.updateInterval);
  }
});
