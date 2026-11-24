'use strict';

document.addEventListener('DOMContentLoaded', async () => {
  const feed = document.getElementById('match-notification-feed');
  if (!feed) return;

  async function loadNotifications() {
    try {
      const response = await fetch('/api/v1/matches/notifications/', {
        headers: { Accept: 'application/json' }
      });
      if (!response.ok) throw new Error(`Notification request failed (${response.status})`);
      const notifications = await response.json();
      feed.replaceChildren();

      if (!Array.isArray(notifications) || notifications.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'section-block p-4 text-center text-muted';
        empty.textContent = 'No recent match events.';
        feed.append(empty);
        return;
      }

      notifications.forEach(event => {
        const card = document.createElement('a');
        card.className = 'section-block d-block text-decoration-none text-reset p-3 mb-2';
        card.href = `/matches/center/${encodeURIComponent(event.fixture_id)}/`;

        const title = document.createElement('strong');
        title.textContent = [event.type, event.detail].filter(Boolean).join(' · ') || 'Match event';
        const teams = document.createElement('div');
        teams.className = 'small mt-1';
        teams.textContent = `${event.home_team} vs ${event.away_team}`;
        const meta = document.createElement('div');
        meta.className = 'text-muted small mt-1';
        const minute = event.minute == null ? '' : `${event.minute}${event.extra_minute ? `+${event.extra_minute}` : ''}'`;
        meta.textContent = [event.league, event.team, event.player, minute].filter(Boolean).join(' · ');
        card.append(title, teams, meta);
        feed.append(card);
      });
    } catch (error) {
      const message = document.createElement('p');
      message.className = 'section-block p-4 text-center text-danger';
      message.textContent = 'Could not load match notifications. Please try again.';
      feed.replaceChildren(message);
      console.error('Match notifications error:', error);
    }
  }

  await loadNotifications();
  window.setInterval(loadNotifications, 30000);
});
