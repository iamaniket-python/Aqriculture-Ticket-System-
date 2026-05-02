// ================= CSRF (SAFE METHOD) =================
function getCSRF() {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
}


// ================= PANEL TOGGLE =================
function togglePanel(id) {
  const panels = ['msgPanel', 'notifPanel', 'profilePanel'];

  panels.forEach(p => {
    const el = document.getElementById(p);
    if (!el) return;

    if (p === id) {
      const isOpen = el.classList.contains('open');
      el.classList.toggle('open', !isOpen);
    } else {
      el.classList.remove('open');
    }
  });

  // Mark messages read when opening
  if (id === 'msgPanel') {
    const badge = document.getElementById('msgBadge');
    if (badge) markAllMessagesRead();
  }
}


// ================= CLICK OUTSIDE CLOSE =================
document.addEventListener('click', function(e) {
  const navRight = document.querySelector('.navbar-right');
  if (navRight && !navRight.contains(e.target)) {
    ['msgPanel','notifPanel','profilePanel'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('open');
    });
  }
});


// ================= MARK ALL READ =================
function markAllMessagesRead() {
  const badge = document.getElementById('msgBadge');
  if (!badge) return;

  fetch("/mark-notifications-read/", {
    method: "POST",
    headers: {
      "X-CSRFToken": getCSRF(),
      "Content-Type": "application/json"
    }
  })
  .then(r => r.json())
  .then(data => {
    if (data.status === "ok") {
      badge.classList.add('fade-out');

      setTimeout(() => badge.remove(), 250);

      const label = document.getElementById('msgCountLabel');
      if (label) label.textContent = '';

      document.querySelectorAll('.msg-item .panel-dot')
        .forEach(d => d.remove());
    }
  })
  .catch(err => console.error("Mark read error:", err));
}


// ================= SINGLE MESSAGE =================
function markMsgRead(event, el) {
  el.classList.add('fade-out');

  setTimeout(() => {
    el.remove();
    updateMsgCount();
  }, 250);
}


function updateMsgCount() {
  const items = document.querySelectorAll('.msg-item');
  const remaining = items.length;

  const badge = document.getElementById('msgBadge');
  const label = document.getElementById('msgCountLabel');

  if (remaining === 0) {
    if (badge) badge.remove();
    if (label) label.textContent = '';

    const list = document.getElementById('msgList');
    if (list) {
      list.innerHTML = '<div class="panel-empty"><div>📭</div>No new messages</div>';
    }
  } else {
    if (badge) badge.textContent = remaining;
    if (label) label.textContent = remaining + ' unread';
  }
}


// ================= NOTIFICATIONS =================
function markNotifRead(event, el) {
  el.classList.add('fade-out');

  setTimeout(() => {
    el.remove();
    updateNotifCount();
  }, 250);
}


function updateNotifCount() {
  const items = document.querySelectorAll('.notif-ticket-item');
  const remaining = items.length;

  const badge = document.getElementById('notifBadge');
  const label = document.getElementById('notifCountLabel');

  if (remaining === 0) {
    if (badge) badge.remove();
    if (label) label.textContent = '';

    const list = document.getElementById('notifList');
    if (list) {
      list.innerHTML = '<div class="panel-empty"><div>🔕</div>No new notifications</div>';
    }
  } else {
    if (badge) badge.textContent = remaining;
    if (label) label.textContent = remaining + ' new';
  }
}


// ================= BELL ANIMATION =================
const bellIcon = document.getElementById('bellIcon');

if (bellIcon) {
  let bellInterval = setInterval(() => {
    bellIcon.classList.add('bell-ring');
    setTimeout(() => bellIcon.classList.remove('bell-ring'), 500);
  }, 5000);

  // Stop after 30 sec
  setTimeout(() => clearInterval(bellInterval), 30000);
}


// ================= CHAT AUTO SCROLL =================
const chatBox = document.getElementById("chatBox");
if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;


// ================= MODAL =================
function showModal() {
  const modal = document.getElementById("closeModal");
  if (modal) modal.classList.add("open");
}

function hideModal() {
  const modal = document.getElementById("closeModal");
  if (modal) modal.classList.remove("open");
}

const modal = document.getElementById("closeModal");
if (modal) {
  modal.addEventListener("click", function(e) {
    if (e.target === this) hideModal();
  });
}


// ================= IMAGE POPUP =================
function openImg(src) {
  const img = document.getElementById("popupImgSrc");
  const modal = document.getElementById("imgPopup");

  if (img && modal) {
    img.src = src;
    modal.classList.add("active");
  }
}

function closeImg() {
  const modal = document.getElementById("imgPopup");
  if (modal) modal.classList.remove("active");
}


// ================= AUTO REFRESH (SMART) =================
// Instead of full reload → fetch small updates
setInterval(() => {
  fetch("/api/get-latest-counts/")
    .then(res => res.json())
    .then(data => {
      // Example:
      if (data.msg_count !== undefined) {
        const badge = document.getElementById('msgBadge');
        if (badge) badge.textContent = data.msg_count;
      }
    })
    .catch(err => console.error("Auto refresh error:", err));
}, 15000);