// ============================================================
// Polla Mundialera 2026 — app.js
// ============================================================

document.addEventListener('DOMContentLoaded', () => {

  // ── Auto-dismiss flash toasts ──────────────────────────────
  const toasts = document.querySelectorAll('.flash-toast');
  toasts.forEach(toast => {
    const bsToast = new bootstrap.Toast(toast, { delay: 4500 });
    bsToast.show();
  });

  // ── Score input validation (only 0-99) ────────────────────
  document.querySelectorAll('.score-input').forEach(input => {
    input.addEventListener('input', () => {
      let val = parseInt(input.value);
      if (isNaN(val) || val < 0) input.value = '';
      if (val > 99) input.value = 99;
    });
    input.addEventListener('keydown', (e) => {
      // Allow tab to move to next input
      if (e.key === 'Tab') return;
    });
  });

  // ── Predictions form: prevent double-submit ────────────────
  const predForm = document.getElementById('predictions-form');
  if (predForm) {
    predForm.addEventListener('submit', (e) => {
      const btn = predForm.querySelector('[type=submit]');
      if (btn) {
        setTimeout(() => {
          btn.disabled = true;
          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';
        }, 0);
      }
    });
  }

  // ── Animate elements on scroll ─────────────────────────────
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.match-card, .kpi-card, .event-card').forEach(el => {
    observer.observe(el);
  });

  // ── Phase countdown ────────────────────────────────────────
  const countdownEls = document.querySelectorAll('[data-countdown]');
  if (countdownEls.length > 0) {
    function updateCountdowns() {
      countdownEls.forEach(el => {
        const target = new Date(el.dataset.countdown).getTime();
        const now = Date.now();
        const diff = target - now;
        if (diff <= 0) {
          el.textContent = 'Cerrado';
          el.classList.add('text-danger');
          return;
        }
        const d = Math.floor(diff / 86400000);
        const h = Math.floor((diff % 86400000) / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        const s = Math.floor((diff % 60000) / 1000);
        el.textContent = d > 0
          ? `${d}d ${h}h ${m}m`
          : `${h}h ${m}m ${s}s`;
      });
    }
    updateCountdowns();
    setInterval(updateCountdowns, 1000);
  }

  // ── Mobile sidebar toggle ──────────────────────────────────
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('admin-sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('show-mobile');
    });
  }

  // ── Match group filter ─────────────────────────────────────
  const phaseFilter = document.getElementById('phase-filter-select');
  if (phaseFilter) {
    phaseFilter.addEventListener('change', () => {
      const phaseId = phaseFilter.value;
      const url = new URL(window.location);
      url.searchParams.set('phase_id', phaseId);
      window.location.href = url.toString();
    });
  }

  // ── Team type filter (admin teams page) ───────────────────
  document.querySelectorAll('[data-type-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      const type = btn.dataset.typeFilter;
      const url = new URL(window.location);
      url.searchParams.set('type', type);
      window.location.href = url.toString();
    });
  });

  // ── Highlight active sidebar link ──────────────────────────
  const currentPath = window.location.pathname;
  document.querySelectorAll('.admin-sidebar .nav-link').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

});
