'use strict';

class FixtureCenter {
  constructor(root) {
    this.root = root;
    this.endpoint = root.dataset.endpoint;
    this.previousScore = null;
    this.poll();
    this.timer = window.setInterval(() => this.poll(), 30000);
  }

  async poll() {
    try {
      const response = await fetch(this.endpoint, { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`Match data request failed (${response.status})`);
      const match = await response.json();
      this.render(match);
      const status = match.fixture?.status?.short;
      if (['FT', 'AET', 'PEN', 'CANC', 'ABD', 'AWD', 'WO'].includes(status)) {
        window.clearInterval(this.timer);
      }
    } catch (error) {
      document.getElementById('center-status').textContent =
        'Live match data is unavailable. Please try again shortly.';
      console.error(error);
    }
  }

  render(match) {
    const home = match.teams?.home || {};
    const away = match.teams?.away || {};
    const fixture = match.fixture || {};
    const status = fixture.status || {};
    const homeScore = match.goals?.home;
    const awayScore = match.goals?.away;
    const score = `${homeScore ?? 0} : ${awayScore ?? 0}`;

    document.getElementById('center-league').textContent =
      [match.league?.name, match.league?.round].filter(Boolean).join(' · ');
    this.setTeamLink('center-home-link', home.name);
    this.setTeamLink('center-away-link', away.name);
    document.getElementById('center-score').textContent =
      status.short === 'NS' ? 'VS' : score;
    document.getElementById('center-status').textContent =
      status.short === 'NS'
        ? `${new Date(fixture.date).toLocaleString()}`
        : [status.long, status.elapsed ? `${status.elapsed}'` : ''].filter(Boolean).join(' · ');

    if (this.previousScore && this.previousScore !== score) {
      document.getElementById('center-score').classList.add('text-warning');
      window.setTimeout(() => document.getElementById('center-score').classList.remove('text-warning'), 1500);
    }
    this.previousScore = score;

    this.renderEvents(match.events || []);
    this.renderScorers(match.events || [], home, away);
    this.renderStats(match.statistics || []);
    this.renderLineups(match.lineups || [], match.players || []);
  }

  setTeamLink(id, name) {
    const link = document.getElementById(id);
    link.textContent = name || 'Team';
    link.href = `/teams/?q=${encodeURIComponent(name || '')}`;
  }

  renderEvents(events) {
    const container = document.getElementById('center-events');
    container.replaceChildren();
    if (!events.length) {
      container.append(this.message('No match events are available yet.'));
      return;
    }

    events.forEach(event => {
      const row = document.createElement('article');
      row.className = 'd-flex align-items-start gap-3 border-bottom border-secondary py-2';
      const minute = document.createElement('strong');
      minute.className = 'text-warning text-nowrap';
      const time = event.time || {};
      minute.textContent = `${time.elapsed ?? ''}${time.extra ? `+${time.extra}` : ''}'`;
      const detail = document.createElement('div');
      detail.className = 'flex-grow-1';
      const summary = document.createElement('div');
      summary.textContent = [event.team?.name, event.detail || event.type].filter(Boolean).join(' · ');
      detail.append(summary);
      const people = [event.player?.name, event.assist?.name ? `Assist: ${event.assist.name}` : '']
        .filter(Boolean).join(' · ');
      if (people) {
        const sub = document.createElement('div');
        sub.className = 'text-muted small';
        sub.textContent = people;
        detail.append(sub);
      }
      row.append(minute, detail);
      container.append(row);
    });
  }

  renderScorers(events, home, away) {
    const homeScorers = [];
    const awayScorers = [];
    events.filter(event =>
      event.type === 'Goal' && event.detail !== 'Missed Penalty'
    ).forEach(event => {
      const time = event.time || {};
      const minute = `${time.elapsed ?? ''}${time.extra ? `+${time.extra}` : ''}'`;
      const suffix = event.detail === 'Own Goal' ? ' (OG)' : event.detail === 'Penalty' ? ' (P)' : '';
      const text = `${event.player?.name || 'Unknown scorer'} ${minute}${suffix}`;
      (event.team?.id === home.id ? homeScorers : awayScorers).push(text);
    });
    document.getElementById('center-home-scorers').textContent = homeScorers.join(' · ');
    document.getElementById('center-away-scorers').textContent = awayScorers.join(' · ');
  }

  renderStats(statistics) {
    const container = document.getElementById('center-statistics');
    container.replaceChildren();
    if (statistics.length < 2) {
      container.append(this.message('Statistics are not available yet.'));
      return;
    }

    const homeStats = statistics[0].statistics || [];
    const awayStats = statistics[1].statistics || [];
    const rows = new Map(homeStats.map(item => [item.type, { home: item.value }]));
    awayStats.forEach(item => {
      const row = rows.get(item.type) || {};
      row.away = item.value;
      rows.set(item.type, row);
    });
    rows.forEach((values, label) => {
      const row = document.createElement('div');
      row.className = 'row align-items-center border-bottom border-secondary py-2';
      const home = document.createElement('div');
      home.className = 'col-3 text-end fw-semibold';
      home.textContent = values.home ?? '–';
      const name = document.createElement('div');
      name.className = 'col-6 text-center text-muted small';
      name.textContent = label;
      const away = document.createElement('div');
      away.className = 'col-3 fw-semibold';
      away.textContent = values.away ?? '–';
      row.append(home, name, away);
      container.append(row);
    });
  }

  renderLineups(lineups, playerRatings) {
    const container = document.getElementById('center-lineups-content');
    container.replaceChildren();
    if (!lineups.length) {
      container.append(this.message('Lineups and player ratings have not been published by the provider yet.'));
      return;
    }

    const ratingByPlayer = new Map();
    playerRatings.forEach(team => {
      (team.players || []).forEach(item => {
        const rating = item.statistics?.[0]?.games?.rating;
        if (item.player?.id) ratingByPlayer.set(item.player.id, rating);
      });
    });

    const columns = document.createElement('div');
    columns.className = 'row g-4';
    lineups.forEach(lineup => {
      const column = document.createElement('section');
      column.className = 'col-12 col-lg-6';
      const heading = document.createElement('h3');
      heading.className = 'h5 mb-1';
      heading.textContent = `${lineup.team?.name || 'Team'}${lineup.formation ? ` · ${lineup.formation}` : ''}`;
      column.append(heading);
      const startingTitle = document.createElement('h4');
      startingTitle.className = 'small text-uppercase text-muted mt-3';
      startingTitle.textContent = 'Starting XI';
      column.append(startingTitle);
      column.append(this.playerList(lineup.startXI || [], ratingByPlayer));
      const substitutesTitle = document.createElement('h4');
      substitutesTitle.className = 'small text-uppercase text-muted mt-3';
      substitutesTitle.textContent = 'Substitutes';
      column.append(substitutesTitle);
      column.append(this.playerList(lineup.substitutes || [], ratingByPlayer));
      columns.append(column);
    });
    container.append(columns);
  }

  playerList(players, ratings) {
    const list = document.createElement('ul');
    list.className = 'list-group list-group-flush';
    if (!players.length) {
      const item = document.createElement('li');
      item.className = 'list-group-item bg-transparent text-muted px-0';
      item.textContent = 'Not available';
      list.append(item);
      return list;
    }
    players.forEach(entry => {
      const player = entry.player || {};
      const item = document.createElement('li');
      item.className = 'list-group-item bg-transparent text-light px-0 d-flex justify-content-between gap-2';
      const name = document.createElement('a');
      name.className = 'text-decoration-none text-reset';
      name.href = `/players/?q=${encodeURIComponent(player.name || '')}`;
      name.textContent = [entry.number, player.name, player.pos].filter(Boolean).join(' · ');
      const rating = document.createElement('span');
      rating.className = 'badge bg-secondary';
      const value = player.id ? ratings.get(player.id) : null;
      rating.textContent = value ? Number(value).toFixed(1) : '—';
      rating.title = value ? 'Provider player rating' : 'Rating not available';
      item.append(name, rating);
      list.append(item);
    });
    return list;
  }

  message(text) {
    const element = document.createElement('p');
    element.className = 'text-muted mb-0';
    element.textContent = text;
    return element;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('fixture-center');
  if (root) new FixtureCenter(root);
});
