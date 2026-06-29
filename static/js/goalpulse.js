/* GoalPulse — Main JavaScript (polling edition, no WebSocket required) */
'use strict';

/* ── Live Score Ticker via polling ── */
class LiveTicker {
  constructor() {
    this.track = document.getElementById('ticker-track');
    if (!this.track) return;
    this.load();
    setInterval(() => this.load(), GP_CONFIG.updateInterval);
  }

 load() {
    fetch('/api/v1/matches/live/', {
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    })
    .then(data => this.render(data))
    .catch(err => {
        console.error('Live scores error:', err);
    });
}

  render(matches) {
    if (!this.track) return;
    if (!matches || matches.length === 0) {
      this.track.innerHTML = '<span class="ticker-loading">No live matches right now</span>';
      return;
    }
    try {
      const items = matches.map(m => {
        if (!m.home_team || !m.away_team) return '';
        return `<span class="ticker-item" style="cursor:default;">
          <span>${m.home_team.name || 'Team'}</span>
          <span class="ticker-score">${m.home_score || 0} – ${m.away_score || 0}</span>
          <span>${m.away_team.name || 'Team'}</span>
          <span class="ticker-min">${m.display_minute || (m.status && m.status.toUpperCase()) || ''}</span>
        </span>`;
      }).filter(item => item).join('');
      
      if (!items) {
        this.track.innerHTML = '<span class="ticker-loading">No live matches right now</span>';
        return;
      }
      this.track.innerHTML = `<div class="ticker-inner">${items}${items}</div>`;
    } catch (err) {
      console.error('Ticker render error:', err);
      this.track.innerHTML = '<span class="ticker-loading">Error loading live scores</span>';
    }
  }
}

/* ── Live Match Cards Updater via polling ── */
class LiveMatchUpdater {
  constructor() {
    this.cards = document.querySelectorAll('[data-match-id][data-status="live"], [data-match-id][data-status="ht"]');
    if (this.cards.length === 0) return;
    setInterval(() => this.poll(), GP_CONFIG.updateInterval);
  }

  poll() {
    fetch('/api/v1/matches/live/')
      .then(r => r.json())
      .then(data => this.updateCards(data))
      .catch(() => {});
  }

  updateCards(matches) {
    const map = {};
    matches.forEach(m => { map[m.id] = m; });

    this.cards.forEach(card => {
      const id = card.dataset.matchId;
      const m = map[id];
      if (!m) return;

      const scoreEl = card.querySelector('.score-display');
      if (scoreEl) {
        const home = scoreEl.querySelector('.home-score');
        const away = scoreEl.querySelector('.away-score');
        if (home && away) {
          const prevHome = parseInt(home.textContent);
          const prevAway = parseInt(away.textContent);
          if (m.home_score !== prevHome || m.away_score !== prevAway) {
            home.textContent = m.home_score;
            away.textContent = m.away_score;
            card.classList.add('goal-flash');
            scoreEl.classList.add('score-bump');
            setTimeout(() => { card.classList.remove('goal-flash'); scoreEl.classList.remove('score-bump'); }, 2000);
          }
        }
      }
      const minEl = card.querySelector(`.match-minute[data-match-id="${id}"]`);
      if (minEl && m.display_minute) minEl.textContent = m.display_minute;
    });
  }
}

/* ── Notification Badge via polling ── */
class NotificationBadge {
  constructor() {
    if (!GP_CONFIG.isAuthenticated) return;
    this.badge = document.getElementById('notif-count');
    this.load();
    setInterval(() => this.load(), 60000);
  }

  load() {
    fetch('/api/v1/notifications/')
      .then(r => r.json())
      .then(data => {
        const unread = (data.results || data).filter(n => !n.is_read).length;
        if (this.badge) {
          this.badge.textContent = unread > 9 ? '9+' : unread;
          this.badge.style.display = unread > 0 ? 'block' : 'none';
        }
      })
      .catch(() => {});
  }
}

/* ── Init on DOM ready ── */
document.addEventListener('DOMContentLoaded', () => {
  new LiveTicker();
  new LiveMatchUpdater();
  new NotificationBadge();

  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
});
