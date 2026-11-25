/* Let It Flow - Chart.js drawings. Data comes from JSON blocks in the page.
   If Chart.js could not load (offline), a short message is shown instead. */
(function () {
  'use strict';
  function readJSON(id) {
    var el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }
  function fallback(canvasId) {
    var c = document.getElementById(canvasId);
    if (c) c.parentElement.innerHTML = '<p class="muted small">The chart needs an internet connection to load. Your data is shown in the table.</p>';
  }
  var ORCHID = '#8B78B8', ROSE = '#D9738B', SAGE = '#6FA391';

  var hist = readJSON('hist-data');
  if (hist && document.getElementById('histChart')) {
    if (typeof Chart === 'undefined') { fallback('histChart'); }
    else new Chart(document.getElementById('histChart'), {
      type: 'line',
      data: { labels: hist.map(function (h) { return h.label; }),
              datasets: [{ label: 'Cycle length (days)', data: hist.map(function (h) { return h.days; }),
                           borderColor: ORCHID, backgroundColor: 'rgba(139,120,184,.15)', fill: true, tension: .35,
                           pointBackgroundColor: ROSE, pointRadius: 5 }] },
      options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
                 scales: { y: { title: { display: true, text: 'days' }, suggestedMin: 15 } } }
    });
  }

  var inte = readJSON('int-data');
  if (inte && document.getElementById('intChart')) {
    if (typeof Chart === 'undefined') { fallback('intChart'); }
    else {
      var labels = inte.points.map(function (p) { return p.label; });
      new Chart(document.getElementById('intChart'), {
        type: 'line',
        data: { labels: labels, datasets: [
          { label: 'Cycle length', data: inte.points.map(function (p) { return p.days; }), borderColor: ORCHID,
            backgroundColor: ORCHID, tension: .3, pointRadius: 6,
            pointBackgroundColor: inte.points.map(function (p) { return p.flag === 'ok' ? SAGE : ROSE; }) },
          { label: 'Usual minimum (' + inte.low + ')', data: labels.map(function () { return inte.low; }),
            borderColor: 'rgba(111,163,145,.7)', borderDash: [6, 6], pointRadius: 0, fill: false },
          { label: 'Usual maximum (' + inte.high + ')', data: labels.map(function () { return inte.high; }),
            borderColor: 'rgba(111,163,145,.7)', borderDash: [6, 6], pointRadius: 0,
            backgroundColor: 'rgba(111,163,145,.10)', fill: '-1' }
        ] },
        options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } },
                   scales: { y: { title: { display: true, text: 'days' }, suggestedMin: 15 } } }
      });
    }
  }
})();
