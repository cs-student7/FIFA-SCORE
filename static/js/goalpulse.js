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
    const items = matches.filter(m => m.home_team && m.away_team).map(match => {
      const item = document.createElement('a');
      item.className = 'ticker-item text-decoration-none text-reset';
      item.href = `/matches/center/${encodeURIComponent(match.id)}/`;
      [
        [match.home_team.name || 'Team', ''],
        [`${match.home_score ?? 0} – ${match.away_score ?? 0}`, 'ticker-score'],
        [match.away_team.name || 'Team', ''],
        [match.display_minute || (match.status || '').toUpperCase(), 'ticker-min']
      ].forEach(([text, className]) => {
        const span = document.createElement('span');
        if (className) span.className = className;
        span.textContent = text;
        item.append(span);
      });
      return item;
    });

    if (!items.length) {
      this.track.innerHTML = '<span class="ticker-loading">No live matches right now</span>';
      return;
    }
    const ticker = document.createElement('div');
    ticker.className = 'ticker-inner';
    [...items, ...items.map(item => item.cloneNode(true))].forEach(item => ticker.append(item));
    this.track.replaceChildren(ticker);
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
    this.badge = document.getElementById('notif-count');
    if (!this.badge) return;
    this.load();
    setInterval(() => this.load(), 60000);
  }

  load() {
    fetch('/api/v1/matches/notifications/')
      .then(r => r.json())
      .then(data => {
        const count = Array.isArray(data) ? data.length : 0;
        this.badge.textContent = count > 9 ? '9+' : count;
        this.badge.style.display = count > 0 ? 'block' : 'none';
      })
      .catch(err => console.error('Match notification count error:', err));
  }
}

/* ── Global live score bar ── */
class LiveScoreBar {
  constructor() {
    this.bar = document.getElementById('liveBottomBar');
    this.matches = document.getElementById('liveBottomMatches');
    if (!this.bar || !this.matches) return;
    this.load();
    setInterval(() => this.load(), GP_CONFIG.updateInterval);
  }

  async load() {
    try {
      const response = await fetch('/api/v1/matches/live/', {
        headers: { Accept: 'application/json' }
      });
      if (!response.ok) throw new Error(`Live scores request failed (${response.status})`);
      const data = await response.json();
      this.render(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Live score bar error:', error);
    }
  }

  render(matches) {
    this.matches.replaceChildren();
    matches.forEach(match => {
      const link = document.createElement('a');
      link.className = 'px-2 py-1 rounded border border-secondary bg-black text-decoration-none text-light';
      link.href = `/matches/center/${encodeURIComponent(match.id)}/`;

      const home = document.createElement('strong');
      home.textContent = match.home_team?.name || 'Home';
      const score = document.createElement('span');
      score.className = 'text-warning fw-bold mx-1';
      score.textContent = `${match.home_score ?? 0} - ${match.away_score ?? 0}`;
      const away = document.createElement('strong');
      away.textContent = match.away_team?.name || 'Away';
      const minute = document.createElement('span');
      minute.className = 'text-danger ms-1';
      minute.textContent = `(${match.display_minute || match.status || 'LIVE'})`;
      link.append(home, score, away, minute);
      this.matches.append(link);
    });
    this.bar.classList.toggle('d-none', matches.length === 0);
  }
}

/* ── Init on DOM ready ── */
document.addEventListener('DOMContentLoaded', () => {
  new LiveTicker();
  new LiveMatchUpdater();
  new NotificationBadge();
  new LiveScoreBar();

  if (typeof bootstrap !== 'undefined') {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
  }
});
