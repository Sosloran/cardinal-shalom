// Cardinal Shalom - WebSocket / live updates (placeholder for ranking live)

// En esta beta usamos HTTP polling para actualizacion en tiempo real del ranking.
// Cuando se visite /student/ranking, el script incluido en la plantilla iniciara
// polling cada 10s y actualizara la tabla sin recargar la pagina.

(function () {
  'use strict';

  let pollTimer = null;
  let currentUrl = null;

  function startPolling(url, onUpdate) {
    stopPolling();
    currentUrl = url;
    pollTimer = setInterval(async () => {
      try {
        const data = await fetchJSON(url);
        if (onUpdate) onUpdate(data);
      } catch (e) {
        console.warn('[Ranking live] poll error:', e.message);
      }
    }, 10000);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
    currentUrl = null;
  }

  function renderRankingTable(containerSelector, rankingData, opts) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    const {
      showBest = true,
      showMe = true,
      gradeName = '',
    } = opts || {};

    let html = '';

    if (showBest && rankingData.length > 0) {
      const best = rankingData[0];
      html += `
        <tr class="best-student-row rank-animate">
          <td class="py-3 text-center w-10">🥇</td>
          <td class="font-semibold">${best.name}</td>
          <td>${best.section}</td>
          <td class="font-semibold text-[#f5b342]">${best.score.toFixed(2)}</td>
          <td class="text-xs text-slate-400">${best.email}</td>
        </tr>`;
    }

    let startIndex = showBest && rankingData.length > 0 ? 1 : 0;
    let rankNumber = showBest && rankingData.length > 0 ? 2 : 1;

    const items = rankingData.slice(startIndex);
    if (!showMe) {
      // ocultar row del user actual
      const myId = parseInt(sessionStorage.getItem('user_id') || '0');
      items.filter(r => r.id !== myId);
    }

    items.forEach((r, i) => {
      const isMe = r.is_me;
      const cellClass = isMe ? 'font-semibold bg-[#e8f0f8]' : '';
      html += `
        <tr class="rank-animate ${cellClass}" style="animation-delay:${i * 0.05}s">
          <td class="py-3 text-center w-10 text-slate-400">${rankNumber++}</td>
          <td class="${cellClass}">${isMe ? '👤 ' : ''}${r.name}</td>
          <td>${r.section}</td>
          <td class="font-semibold ${r.score >= 80 ? 'text-green-600' : r.score >= 60 ? 'text-[#f5b342]' : 'text-slate-500'}">${r.score.toFixed(2)}</td>
          <td class="text-xs text-slate-400">${r.email}</td>
        </tr>`;
    });

    container.innerHTML = html;
  }

  // Exponer para uso en pages
  window.RankingLive = {
    startPolling,
    stopPolling,
    renderRankingTable,
  };
})();
