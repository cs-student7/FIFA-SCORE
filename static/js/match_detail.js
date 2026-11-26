/* LEAGUE PLUS — Match Detail Page JS (polling edition) */
'use strict';

class MatchDetailPage {
  constructor(matchId, isLive) {
    this.matchId = matchId;
    this.isLive = isLive;
    this.chart = null;
    this.momentumData = window.MOMENTUM_DATA || [];

    this.initMomentumChart();
    if (isLive) {
      this.poll();
      setInterval(() => this.poll(), GP_CONFIG.updateInterval);
    }
  }

  poll() {
    fetch(`/api/v1/matches/${this.matchId}/`)
      .then(r => r.json())
      .then(data => this.applyUpdate(data))
      .catch(() => {});
  }

  applyUpdate(data) {
    // Score
    const h = document.getElementById('sb-home-score');
    const a = document.getElementById('sb-away-score');
    if (h && a) {
      if (parseInt(h.textContent) !== data.home_score || parseInt(a.textContent) !== data.away_score) {
        h.textContent = data.home_score;
        a.textContent = data.away_score;
        document.getElementById('scoreboard-score')?.classList.add('score-bump');
        setTimeout(() => document.getElementById('scoreboard-score')?.classList.remove('score-bump'), 700);
        document.getElementById('match-header')?.classList.add('goal-flash');
        setTimeout(() => document.getElementById('match-header')?.classList.remove('goal-flash'), 1500);
      }
    }

    // Clock
    const clock = document.getElementById('match-clock');
    if (clock && data.display_minute) clock.textContent = data.display_minute;

    // Momentum (with null check)
    if (data.statistics && typeof data.statistics === 'object') {
      const hBar = document.getElementById('home-momentum-bar');
      const aBar = document.getElementById('away-momentum-bar');
      const hVal = document.getElementById('home-momentum-val');
      const aVal = document.getElementById('away-momentum-val');
      if (hBar && data.statistics.home_momentum !== undefined) hBar.style.width = data.statistics.home_momentum + '%';
      if (aBar && data.statistics.away_momentum !== undefined) aBar.style.width = data.statistics.away_momentum + '%';
      if (hVal && data.statistics.home_momentum !== undefined) hVal.textContent = data.statistics.home_momentum + '%';
      if (aVal && data.statistics.away_momentum !== undefined) aVal.textContent = data.statistics.away_momentum + '%';
    }

    if (data.momentum_data && Array.isArray(data.momentum_data) && data.momentum_data.length > 0) {
      this.momentumData = data.momentum_data;
      this.updateMomentumChart();
    }
  }

  initMomentumChart() {
    const canvas = document.getElementById('momentum-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    const labels = this.momentumData.map(d => d.minute);
    const values = this.momentumData.map(d => d.home_value);

    this.chart = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: values.map(v => v >= 0 ? 'rgba(255,77,109,0.6)' : 'rgba(76,201,240,0.6)'),
          borderColor: values.map(v => v >= 0 ? '#FF4D6D' : '#4CC9F0'),
          borderWidth: 1, borderRadius: 2,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: items => `Minute ${items[0].label}'`,
              label: item => item.raw > 0 ? `Home +${item.raw}` : `Away ${Math.abs(item.raw)}`
            }
          }
        },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8892B0', font: { family: 'JetBrains Mono', size: 10 }, maxTicksLimit: 10 } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8892B0', font: { family: 'JetBrains Mono', size: 10 } }, min: -100, max: 100 }
        }
      }
    });
  }

  updateMomentumChart() {
    if (!this.chart) return;
    const labels = this.momentumData.map(d => d.minute);
    const values = this.momentumData.map(d => d.home_value);
    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = values;
    this.chart.data.datasets[0].backgroundColor = values.map(v => v >= 0 ? 'rgba(255,77,109,0.6)' : 'rgba(76,201,240,0.6)');
    this.chart.update('none');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (typeof MATCH_ID !== 'undefined') new MatchDetailPage(MATCH_ID, MATCH_IS_LIVE);
});