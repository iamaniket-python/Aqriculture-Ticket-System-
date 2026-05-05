document.addEventListener("DOMContentLoaded", function () {

  // ── CHAT AUTO SCROLL ──
  const chatBoxEl = document.getElementById('chatBox');
  if (chatBoxEl) {
    chatBoxEl.scrollTop = chatBoxEl.scrollHeight;
  }

  // ── MODAL ──
  const modal = document.getElementById('closeModal');

  window.showModal = function () {
    if (!modal) return;

    modal.style.display = "flex";
    modal.style.visibility = "visible";
    modal.style.opacity = "1";
    modal.style.pointerEvents = "auto";
  };

  window.hideModal = function () {
    if (!modal) return;

    modal.style.display = "none";
    modal.style.visibility = "hidden";
    modal.style.opacity = "0";
    modal.style.pointerEvents = "none";
  };

  if (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target === modal) hideModal();
    });
  }

  // ── LIGHTBOX ──
  window.openLb = function (src) {
    const img = document.getElementById('lb-img');
    const lb = document.getElementById('lb');
    if (img && lb) {
      img.src = src;
      lb.classList.add('open');
    }
  };

  window.closeLb = function () {
    const lb = document.getElementById('lb');
    if (lb) lb.classList.remove('open');
  };

  // ── NAV PANELS ──
  window.togglePanel = function (id) {
    const panels = ['msgPanel', 'notifPanel', 'profilePanel'];

    panels.forEach(p => {
      const el = document.getElementById(p);
      if (!el) return;

      if (p === id) {
        el.classList.toggle('open');
      } else {
        el.classList.remove('open');
      }
    });
  };

  document.addEventListener('click', function (e) {
    const nav = document.querySelector('.navbar-right');
    if (nav && !nav.contains(e.target)) {
      document.querySelectorAll('.nav-panel').forEach(p => p.classList.remove('open'));
    }
  });

});