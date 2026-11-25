/* Let It Flow - small bits of JavaScript (all optional enhancements):
   mobile menu, dismissible messages, confirm dialogs, pain slider, chat. */
(function () {
  'use strict';

  // ---- dismiss + auto-hide flash messages
  document.querySelectorAll('[data-dismiss]').forEach(function (b) {
    b.addEventListener('click', function () { b.parentElement.remove(); });
  });
  setTimeout(function () {
    document.querySelectorAll('.flash').forEach(function (f) { f.style.display = 'none'; });
  }, 7000);

  // ---- mobile drawer
  var sidebar = document.getElementById('sidebar');
  var scrim = document.getElementById('scrim');
  function toggleMenu(open) {
    if (!sidebar) return;
    sidebar.classList.toggle('open', open);
    if (scrim) scrim.classList.toggle('open', open);
  }
  var menuBtn = document.getElementById('menuBtn');
  var moreBtn = document.getElementById('moreBtn');
  if (menuBtn) menuBtn.addEventListener('click', function () { toggleMenu(true); });
  if (moreBtn) moreBtn.addEventListener('click', function (e) { e.preventDefault(); toggleMenu(true); });
  if (scrim) scrim.addEventListener('click', function () { toggleMenu(false); });

  // ---- "are you sure?" on destructive forms
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!window.confirm(form.getAttribute('data-confirm'))) e.preventDefault();
    });
  });

  // ---- pain slider (value label + "don't log pain" switch)
  var slider = document.getElementById('pain_severity');
  var unset = document.getElementById('painUnset');
  if (slider) {
    var out = document.getElementById('painOut');
    function syncSlider() { slider.disabled = unset && unset.checked; }
    slider.addEventListener('input', function () {
      out.textContent = slider.value;
      if (unset) { unset.checked = false; syncSlider(); }
    });
    if (unset) { unset.addEventListener('change', syncSlider); syncSlider(); }
  }

  // ---- chat
  var chat = document.getElementById('chat');
  if (chat) {
    var log = document.getElementById('chatLog');
    var form = document.getElementById('chatForm');
    var input = document.getElementById('chatInput');
    var convId = chat.getAttribute('data-conv') || null;
    log.scrollTop = log.scrollHeight;

    function addBubble(text, who) {
      var d = document.createElement('div');
      d.className = 'bubble ' + who;
      d.textContent = text;            // textContent: user/bot text can never inject HTML
      log.appendChild(d);
      log.scrollTop = log.scrollHeight;
      return d;
    }
    function send(message) {
      addBubble(message, 'user');
      var typing = addBubble('Thinking…', 'bot typing');
      fetch(chat.getAttribute('data-api'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': chat.getAttribute('data-csrf') },
        body: JSON.stringify({ message: message, conversation_id: convId })
      }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
        .then(function (res) {
          typing.remove();
          if (!res.ok) { addBubble(res.body.error || 'Something went wrong. Please try again.', 'bot'); return; }
          if (!convId) {
            convId = res.body.conversation_id;
            history.replaceState(null, '', '?c=' + convId);
          }
          addBubble(res.body.reply, 'bot');
        })
        .catch(function () { typing.remove(); addBubble('Could not reach the server. Please try again.', 'bot'); });
    }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var m = input.value.trim();
      if (!m) return;
      input.value = '';
      send(m);
    });
    document.querySelectorAll('[data-suggest]').forEach(function (b) {
      b.addEventListener('click', function () { send(b.getAttribute('data-suggest')); });
    });
  }
})();
