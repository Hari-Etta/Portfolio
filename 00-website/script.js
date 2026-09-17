/* ==========================================================================
   PORTFOLIO INTERACTIONS
   0. Boot screen (multi-line fake boot log + progress bar, first visit only)
   1. Remove no-js class (enables JS-only UI, incl. skill map)
   1b. Hero backdrop: animated scatter-plot field + cursor parallax
   3. Scroll-reveal for each .section
   4. Sticky sidebar active-state tracking
   5. Signature interactive element: animated skill/stack map, one mini
      canvas per tech-stack category panel (edges between nodes sharing
      that category + hover/click)
   6. Tech-stack category filter chips (show/hide whole panels)
   7. Project tag filter chips
   8. Beat the Algorithm — Rock/Paper/Scissors easter egg vs. "RHO", with
      two animated hands that shake then reveal each side's shape, plus
      small win/loss/tie feedback and live stats
   9. GitHub graph fallback if the embed image fails to load
   10. Recommend-a-project-idea form (Netlify Forms)
   11. Build / Create Your Own Bot — freeform lego-style block canvas
       with drag-to-move, more shapes, and a saved-bots gallery/count
   12. Space scene scroll animation — ship dodging asteroids (purely decorative)
   ========================================================================== */

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---------- 0. Boot screen ----------
   Only runs when the inline <script> in <head> added .boot-pending to <html>
   (i.e. first visit this browser session, and no prefers-reduced-motion).
   Types a short multi-line fake boot log while a progress bar fills, holds
   briefly, fades out, then removes itself and marks the session so it never
   shows again until a new browser session. */
(function bootSequence() {
  const screen = document.getElementById('boot-screen');
  const logEl = document.getElementById('boot-log');
  const barEl = document.getElementById('boot-progress-bar');
  const isPending = document.documentElement.classList.contains('boot-pending');

  if (!screen) return;
  if (!isPending) {
    screen.remove(); // reduced-motion visit or repeat-session visit — nothing to show
    return;
  }

  const LINES = [
    'initializing hari_etta.portfolio',
    'loading tech_stack.json',
    'connecting to github_api',
    'ready.'
  ];
  const CHAR_MS = 14;
  const LINE_PAUSE = 130;
  const totalDuration = LINES.reduce((sum, l) => sum + l.length * CHAR_MS + LINE_PAUSE, 0) + 300;

  const startTime = performance.now();
  function tickProgress(now) {
    const pct = Math.min(100, ((now - startTime) / totalDuration) * 100);
    if (barEl) barEl.style.width = pct + '%';
    if (pct < 100) requestAnimationFrame(tickProgress);
  }
  requestAnimationFrame(tickProgress);

  let lineIndex = 0;
  function typeLine() {
    if (lineIndex >= LINES.length) {
      setTimeout(finish, 300);
      return;
    }
    const lineText = LINES[lineIndex];
    const isLast = lineIndex === LINES.length - 1;
    const row = document.createElement('div');
    row.className = 'boot-log-line';
    row.innerHTML = '<span class="boot-prompt">' + (isLast ? '>' : '$') + '</span> ' +
      '<span class="boot-line-text"></span><span class="boot-cursor">▌</span>';
    logEl.appendChild(row);

    const textEl = row.querySelector('.boot-line-text');
    const cursorEl = row.querySelector('.boot-cursor');
    let i = 0;
    (function type() {
      if (i <= lineText.length) {
        textEl.textContent = lineText.slice(0, i);
        i++;
        setTimeout(type, CHAR_MS);
      } else {
        cursorEl.remove();
        lineIndex++;
        setTimeout(typeLine, LINE_PAUSE);
      }
    })();
  }

  function finish() {
    screen.classList.add('boot-fade');
    document.documentElement.classList.remove('boot-pending');
    try { sessionStorage.setItem('bootShown', '1'); } catch (e) {}
    setTimeout(() => screen.remove(), 400);
  }

  typeLine();
})();

/* ---------- 1. Remove no-js class ---------- */
document.documentElement.classList.remove('no-js');

/* ---------- 1b. Hero backdrop: animated scatter-plot field ----------
   Signature hero moment (inspired by an animated low-poly hero seen on a
   reference site, reworked here as a literal scatter plot to match the
   data-analyst identity). Dots drift slowly; a faint regression line
   fades in and out periodically. Frozen to a single static frame when
   prefers-reduced-motion is set. */
(function heroScatterField() {
  const canvas = document.getElementById('hero-canvas');
  const hero = document.getElementById('hero');
  if (!canvas || !hero) return;
  const ctx = canvas.getContext('2d');

  const POINT_COUNT = 70;
  const CONNECT_DIST = 90;
  const CYCLE_MS = 9000; // how often the trend line fades in and back out
  const MAX_PARALLAX = 16; // px of drift at the extreme edge of the hero
  let points = [];
  let width = 0, height = 0;
  let targetX = 0, targetY = 0, driftX = 0, driftY = 0;

  function seedPoints() {
    points = Array.from({ length: POINT_COUNT }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.12,
      vy: (Math.random() - 0.5) * 0.12,
      r: 1 + Math.random() * 1.8
    }));
  }

  function resize() {
    const rect = hero.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    canvas.width = width * devicePixelRatio;
    canvas.height = height * devicePixelRatio;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    seedPoints();
  }

  function trendLine(alpha) {
    // simple least-squares fit over current point positions
    const n = points.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
    points.forEach(p => { sumX += p.x; sumY += p.y; sumXY += p.x * p.y; sumXX += p.x * p.x; });
    const denom = (n * sumXX - sumX * sumX) || 1;
    const slope = (n * sumXY - sumX * sumY) / denom;
    const intercept = (sumY - slope * sumX) / n;
    ctx.beginPath();
    ctx.moveTo(0, intercept);
    ctx.lineTo(width, slope * width + intercept);
    ctx.strokeStyle = `rgba(177, 120, 97, ${alpha * 0.55})`;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  function drawStatic() {
    ctx.clearRect(0, 0, width, height);
    points.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(177, 120, 97, 0.35)';
      ctx.fill();
    });
    trendLine(0.6);
  }

  function frame(t) {
    ctx.clearRect(0, 0, width, height);

    points.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0) p.x = width; else if (p.x > width) p.x = 0;
      if (p.y < 0) p.y = height; else if (p.y > height) p.y = 0;
    });

    // faint connective lines between nearby points
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const dx = points[i].x - points[j].x;
        const dy = points[i].y - points[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < CONNECT_DIST) {
          ctx.beginPath();
          ctx.moveTo(points[i].x, points[i].y);
          ctx.lineTo(points[j].x, points[j].y);
          ctx.strokeStyle = `rgba(154, 164, 174, ${0.08 * (1 - dist / CONNECT_DIST)})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    }

    points.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(177, 120, 97, 0.5)';
      ctx.fill();
    });

    // periodic trend line: fades in over first half of cycle, out over second half
    const phase = (t % CYCLE_MS) / CYCLE_MS;
    const alpha = Math.sin(phase * Math.PI); // 0 -> 1 -> 0
    if (alpha > 0.02) trendLine(alpha);

    // cursor parallax: whole canvas drifts gently toward the pointer, easing each frame
    driftX += (targetX - driftX) * 0.05;
    driftY += (targetY - driftY) * 0.05;
    canvas.style.transform = `translate(${driftX.toFixed(2)}px, ${driftY.toFixed(2)}px)`;

    requestAnimationFrame(frame);
  }

  function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

  // Tracked globally (not just over .hero) so the drift is based on where the
  // cursor is relative to the hero at all times, with no "leave/enter" edge
  // cases to worry about — it naturally clamps once the cursor is far away.
  function onPointerMove(e) {
    const rect = hero.getBoundingClientRect();
    const relX = (e.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
    const relY = (e.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);
    targetX = clamp(-relX * MAX_PARALLAX, -MAX_PARALLAX, MAX_PARALLAX);
    targetY = clamp(-relY * MAX_PARALLAX, -MAX_PARALLAX, MAX_PARALLAX);
  }

  resize();
  window.addEventListener('resize', resize, { passive: true });

  if (prefersReducedMotion) {
    drawStatic();
  } else {
    window.addEventListener('mousemove', onPointerMove, { passive: true });
    requestAnimationFrame(frame);
  }
})();

/* ---------- 3. Scroll-reveal ---------- */
(function scrollReveal() {
  const targets = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window) || prefersReducedMotion) {
    targets.forEach(t => t.classList.add('is-visible'));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  targets.forEach(t => io.observe(t));
})();

/* ---------- 4. Nav dot active-state tracking ---------- */
(function navDots() {
  const dots = document.querySelectorAll('.navdot');
  const sections = Array.from(dots).map(d => document.querySelector(d.getAttribute('href')));
  if (!sections.length) return;

  function updateActive() {
    let currentIndex = 0;
    const scrollPos = window.scrollY + window.innerHeight / 3;
    sections.forEach((sec, i) => {
      if (sec && sec.offsetTop <= scrollPos) currentIndex = i;
    });
    dots.forEach((d, i) => d.classList.toggle('active', i === currentIndex));
  }
  window.addEventListener('scroll', updateActive, { passive: true });
  updateActive();
})();

/* ---------- 5. Signature element: skill/stack map ----------
   One mini connecting-line canvas per category panel (was a single canvas
   over one big flat cloud of ~44 tags, which read as chaotic). Each panel
   only ever connects its own nodes, so the "map" idea stays but reads as
   organized. Filter chips now show/hide whole panels instead of dimming
   individual tags. */
(function skillMap() {
  const panelsGrid = document.getElementById('stack-panels');
  if (!panelsGrid) return;
  const panels = Array.from(panelsGrid.querySelectorAll('.stack-panel'));
  if (!panels.length) return;

  const panelData = panels.map(panel => {
    const mapEl = panel.querySelector('.stack-panel-map');
    const canvas = panel.querySelector('canvas');
    const nodeEls = Array.from(panel.querySelectorAll('.node'));
    const ctx = canvas.getContext('2d');
    return { panel, mapEl, canvas, ctx, nodeEls, hoveredNode: null };
  });

  function nodeCenter(mapEl, el) {
    const wrapRect = mapEl.getBoundingClientRect();
    const rect = el.getBoundingClientRect();
    return {
      x: rect.left - wrapRect.left + rect.width / 2,
      y: rect.top - wrapRect.top + rect.height / 2
    };
  }

  function drawPanel(pd) {
    const rect = pd.mapEl.getBoundingClientRect();
    pd.ctx.clearRect(0, 0, rect.width, rect.height);
    pd.nodeEls.forEach((a, i) => {
      pd.nodeEls.slice(i + 1).forEach(b => {
        const p1 = nodeCenter(pd.mapEl, a);
        const p2 = nodeCenter(pd.mapEl, b);
        const isHoverEdge = pd.hoveredNode && (a === pd.hoveredNode || b === pd.hoveredNode);
        pd.ctx.beginPath();
        pd.ctx.moveTo(p1.x, p1.y);
        pd.ctx.lineTo(p2.x, p2.y);
        pd.ctx.strokeStyle = isHoverEdge ? 'rgba(177,120,97,0.7)' : 'rgba(154,164,174,0.15)';
        pd.ctx.lineWidth = isHoverEdge ? 1.6 : 1;
        pd.ctx.stroke();
      });
    });
  }

  function resizePanel(pd) {
    const rect = pd.mapEl.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    pd.canvas.width = rect.width * devicePixelRatio;
    pd.canvas.height = rect.height * devicePixelRatio;
    pd.canvas.style.width = rect.width + 'px';
    pd.canvas.style.height = rect.height + 'px';
    pd.ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    drawPanel(pd);
  }

  function resizeAll() { panelData.forEach(resizePanel); }

  panelData.forEach(pd => {
    pd.nodeEls.forEach(node => {
      node.setAttribute('tabindex', '0');
      node.addEventListener('mouseenter', () => { pd.hoveredNode = node; drawPanel(pd); });
      node.addEventListener('mouseleave', () => { pd.hoveredNode = null; drawPanel(pd); });
      node.addEventListener('focus', () => { pd.hoveredNode = node; drawPanel(pd); });
      node.addEventListener('blur', () => { pd.hoveredNode = null; drawPanel(pd); });
      node.addEventListener('click', () => node.classList.toggle('active'));
    });
  });

  function setActiveGroup(group) {
    panels.forEach(panel => {
      const show = group === 'all' || panel.dataset.group === group;
      panel.classList.toggle('hidden-panel', !show);
    });
    // Canvases inside a panel that just became visible had a 0×0 rect while
    // hidden, so their line coordinates need recomputing now that it has size.
    requestAnimationFrame(resizeAll);
  }

  document.querySelectorAll('.stack-filter').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.stack-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      setActiveGroup(btn.dataset.group);
    });
  });

  // Only window resize needs to recompute canvas size/lines — unlike the old
  // hand-placed absolute layout, this flex-wrap layout doesn't reflow on
  // scroll, so no scroll listener is needed here.
  window.addEventListener('resize', resizeAll, { passive: true });

  resizeAll();
})();

/* ---------- 6 & 7. Project tag filters (stack filters handled above) ---------- */
(function projectFilters() {
  const buttons = document.querySelectorAll('.project-filter');
  const cards = document.querySelectorAll('.project-card');
  if (!buttons.length) return;

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tag = btn.dataset.tag;
      cards.forEach(card => {
        const tags = (card.dataset.tags || '').split(',');
        const show = tag === 'all' || tags.includes(tag);
        card.classList.toggle('hidden', !show);
      });
    });
  });
})();

/* ---------- Footer year ---------- */
(function footerYear() {
  const el = document.querySelector('.footer-year');
  if (el) el.textContent = new Date().getFullYear();
})();

/* ---------- 8. Beat the Algorithm — Rock/Paper/Scissors easter egg ----------
   Low-key bonus game near the footer. "The algorithm" picks purely at random.
   Score is saved to the visitor's own browser only (localStorage), never sent
   anywhere — wrapped in try/catch since some browsers block storage access. */
(function rpsGame() {
  const BOT_NAME = 'RHO'; // short, catchy — plays purely at random, no ML involved
  const buttons = document.querySelectorAll('.rps-btn');
  const resultEl = document.getElementById('rps-result');
  const resetBtn = document.getElementById('rps-reset');
  const cardEl = document.getElementById('rps-card');
  const winsEl = document.getElementById('rps-wins');
  const lossesEl = document.getElementById('rps-losses');
  const tiesEl = document.getElementById('rps-ties');
  const winrateEl = document.getElementById('rps-winrate');
  const streakEl = document.getElementById('rps-streak');
  const handsEl = document.getElementById('rps-hands');
  const playerHand = document.getElementById('rps-hand-player');
  const botHand = document.getElementById('rps-hand-bot');
  if (!buttons.length || !resultEl || !winsEl) return;

  const SHAKE_MS = 620;
  let animating = false;

  // Shake both hands like a real countdown, then reveal what each side
  // played, then hand off to the caller to update text/stats/score once
  // the reveal lands. Falls back to an instant reveal under
  // prefers-reduced-motion or if the hand markup isn't present.
  function playHandsRound(player, bot, onRevealed) {
    if (prefersReducedMotion || !handsEl || !playerHand || !botHand) {
      if (playerHand) playerHand.dataset.shape = player;
      if (botHand) botHand.dataset.shape = bot;
      onRevealed();
      return;
    }
    animating = true;
    buttons.forEach(b => { b.disabled = true; });
    handsEl.classList.remove('rps-hands-reveal');
    playerHand.dataset.shape = 'rock';
    botHand.dataset.shape = 'rock';
    void handsEl.offsetWidth;
    handsEl.classList.add('rps-hands-shaking');

    setTimeout(() => {
      handsEl.classList.remove('rps-hands-shaking');
      playerHand.dataset.shape = player;
      botHand.dataset.shape = bot;
      void handsEl.offsetWidth;
      handsEl.classList.add('rps-hands-reveal');
      onRevealed();
      animating = false;
      buttons.forEach(b => { b.disabled = false; });
    }, SHAKE_MS);
  }

  // Small, reduced-motion-aware feedback: a press animation on the clicked
  // button, a colour-coded pop-in on the result text, and a brief shake on
  // the card for a loss. Classes are removed after their animation ends so
  // they can replay on the next round.
  function playOutcomeAnimation(outcome) {
    if (prefersReducedMotion) return;
    resultEl.classList.remove('rps-pop', 'result-win', 'result-loss', 'result-tie');
    void resultEl.offsetWidth; // restart animation if the same outcome repeats
    resultEl.classList.add('rps-pop', 'result-' + outcome);
    if (outcome === 'loss' && cardEl) {
      cardEl.classList.remove('rps-shake');
      void cardEl.offsetWidth;
      cardEl.classList.add('rps-shake');
    }
  }

  const BEATS = { rock: 'scissors', paper: 'rock', scissors: 'paper' };
  const CHOICES = Object.keys(BEATS);
  const LABELS = { rock: 'Rock', paper: 'Paper', scissors: 'Scissors' };

  let score = { wins: 0, losses: 0, ties: 0, streak: 0, bestStreak: 0 };
  try {
    const saved = JSON.parse(localStorage.getItem('rpsScore') || 'null');
    if (saved && typeof saved.wins === 'number') {
      score = Object.assign({ streak: 0, bestStreak: 0 }, saved); // fills in the two new fields for anyone with an older saved score
    }
  } catch (e) {}

  function renderScore() {
    const played = score.wins + score.losses + score.ties;
    winsEl.textContent = score.wins;
    lossesEl.textContent = score.losses;
    tiesEl.textContent = score.ties;
    winrateEl.textContent = played ? Math.round((score.wins / played) * 100) + '%' : '—';
    streakEl.textContent = score.bestStreak;
  }
  function saveScore() {
    try { localStorage.setItem('rpsScore', JSON.stringify(score)); } catch (e) {}
  }

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      if (animating) return;
      const player = btn.dataset.choice;
      const bot = CHOICES[Math.floor(Math.random() * CHOICES.length)];
      let message, outcome;

      if (player === bot) {
        score.ties++;
        score.streak = 0;
        message = `Both played ${LABELS[player]} — tie.`;
        outcome = 'tie';
      } else if (BEATS[player] === bot) {
        score.wins++;
        score.streak++;
        score.bestStreak = Math.max(score.bestStreak, score.streak);
        message = `You played ${LABELS[player]}, ${BOT_NAME} played ${LABELS[bot]} — you win.`;
        outcome = 'win';
      } else {
        score.losses++;
        score.streak = 0;
        message = `You played ${LABELS[player]}, ${BOT_NAME} played ${LABELS[bot]} — ${BOT_NAME} wins.`;
        outcome = 'loss';
      }

      if (!prefersReducedMotion) {
        btn.classList.add('pressed');
        setTimeout(() => btn.classList.remove('pressed'), 150);
      }

      playHandsRound(player, bot, () => {
        resultEl.textContent = message;
        renderScore();
        saveScore();
        playOutcomeAnimation(outcome);
      });
    });
  });

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      score = { wins: 0, losses: 0, ties: 0, streak: 0, bestStreak: 0 };
      renderScore();
      saveScore();
      resultEl.classList.remove('rps-pop', 'result-win', 'result-loss', 'result-tie');
      resultEl.textContent = 'Score reset. Make your move.';
      if (handsEl && playerHand && botHand) {
        handsEl.classList.remove('rps-hands-reveal', 'rps-hands-shaking');
        playerHand.dataset.shape = 'rock';
        botHand.dataset.shape = 'rock';
      }
    });
  }

  renderScore();
})();

/* ---------- 9. GitHub graph fallback ----------
   The embeddable graph services this relies on have proven flaky (see the
   comment above the section in index.html). If the image fails to load,
   swap in a plain text link instead of leaving a broken-image icon. */
(function githubGraphFallback() {
  const link = document.getElementById('github-heatmap-link');
  const img = document.getElementById('github-heatmap-img');
  if (!link || !img) return;
  img.addEventListener('error', () => link.classList.add('embed-failed'), { once: true });
})();

/* ---------- 10. Recommend-a-project-idea form ----------
   Submits to Netlify Forms (see the form's data-netlify attribute in
   index.html). Netlify handles the actual POST and redirect; this just
   intercepts it so the visitor sees an inline "sent" message instead of
   leaving the page, which Netlify Forms supports via a fetch submission. */
(function ideaForm() {
  const form = document.getElementById('idea-form');
  const successEl = document.getElementById('idea-success');
  if (!form || !successEl) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const data = new FormData(form);
    fetch('/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(data).toString()
    })
      .then(() => {
        form.reset();
        successEl.style.display = 'block';
      })
      .catch(() => {
        // Network/Netlify issue — fall back to a normal form submission so
        // the idea isn't silently lost.
        form.submit();
      });
  });
})();

/* ---------- 11. Build Something — lego-style block stack ----------
   Purely playful, in the same spirit as the hero's placeholder avatar art.
   Fixed-size blocks; clicking one cycles through shape+colour combos drawn
   from the site's own palette. Add/remove grows or shrinks the stack;
   shuffle re-randomizes every block. Nothing here is saved — it's a fidget
   toy, not state worth persisting. */
(function legoBuilder() {
  const canvas = document.getElementById('lego-canvas');
  const shapeBtns = document.querySelectorAll('.lego-shape-btn');
  const recolorBtn = document.getElementById('lego-recolor');
  const clearBtn = document.getElementById('lego-clear');
  const saveBtn = document.getElementById('lego-save');
  const countEl = document.getElementById('lego-count');
  const galleryEl = document.getElementById('lego-gallery');
  if (!canvas) return;

  const COLORS = ['#B17861', '#4F587F', '#C9A392', '#7C8AA6'];
  const MAX_BLOCKS = 14;
  const BLOCK_PX = 46; // must match .lego-block's width/height in style.css
  const DRAG_THRESHOLD_PX = 4; // movement below this counts as a click (remove), not a drag

  let blocks = []; // { shape, color, xPct, yPct } — xPct/yPct are % of canvas size, top-left based

  function randomColor() { return COLORS[Math.floor(Math.random() * COLORS.length)]; }
  function randomPosition() {
    // Keep the whole block inside the canvas with a small margin, expressed
    // as a % so saved bots redraw correctly at any canvas/gallery size.
    return { xPct: 8 + Math.random() * 70, yPct: 8 + Math.random() * 65 };
  }

  function renderCanvas() {
    canvas.innerHTML = '';
    blocks.forEach((b, i) => {
      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'lego-block';
      el.dataset.shape = b.shape;
      el.style.background = b.color;
      el.style.borderColor = b.color;
      el.style.left = b.xPct + '%';
      el.style.top = b.yPct + '%';
      el.setAttribute('aria-label', b.shape + ' block — click to remove, drag to move');
      wireDrag(el, i);
      canvas.appendChild(el);
    });
  }

  function wireDrag(el, index) {
    let startX, startY, moved, pointerId;

    el.addEventListener('pointerdown', (e) => {
      pointerId = e.pointerId;
      el.setPointerCapture(pointerId);
      startX = e.clientX;
      startY = e.clientY;
      moved = false;
      el.style.zIndex = 5;
    });

    el.addEventListener('pointermove', (e) => {
      if (startX === undefined) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (Math.abs(dx) > DRAG_THRESHOLD_PX || Math.abs(dy) > DRAG_THRESHOLD_PX) moved = true;
      if (!moved) return;
      const rect = canvas.getBoundingClientRect();
      const maxXPct = 100 - (BLOCK_PX / rect.width) * 100;
      const maxYPct = 100 - (BLOCK_PX / rect.height) * 100;
      let xPct = ((e.clientX - rect.left - BLOCK_PX / 2) / rect.width) * 100;
      let yPct = ((e.clientY - rect.top - BLOCK_PX / 2) / rect.height) * 100;
      xPct = Math.max(0, Math.min(maxXPct, xPct));
      yPct = Math.max(0, Math.min(maxYPct, yPct));
      el.style.left = xPct + '%';
      el.style.top = yPct + '%';
      blocks[index].xPct = xPct;
      blocks[index].yPct = yPct;
    });

    el.addEventListener('pointerup', () => {
      el.style.zIndex = '';
      startX = undefined;
      if (!moved) {
        // A click rather than a drag — remove this block.
        blocks.splice(index, 1);
        renderCanvas();
      }
    });
  }

  function addBlock(shape) {
    if (blocks.length >= MAX_BLOCKS) return;
    blocks.push(Object.assign({ shape, color: randomColor() }, randomPosition()));
    renderCanvas();
  }

  function recolorAll() {
    blocks.forEach(b => { b.color = randomColor(); });
    renderCanvas();
  }

  function clearCanvas() {
    blocks = [];
    renderCanvas();
  }

  // ---- Saved bots (persisted count + tiny preview gallery) ----
  let savedBots = [];
  try {
    const saved = JSON.parse(localStorage.getItem('legoSavedBots') || 'null');
    if (Array.isArray(saved)) savedBots = saved;
  } catch (e) {}

  function renderCount() {
    if (countEl) countEl.textContent = `Bots created so far: ${savedBots.length}`;
  }

  function renderGalleryItem(bot) {
    const item = document.createElement('div');
    item.className = 'lego-gallery-item';
    bot.forEach(b => {
      const mini = document.createElement('div');
      mini.className = 'lego-block';
      mini.dataset.shape = b.shape;
      mini.style.background = b.color;
      mini.style.borderColor = b.color;
      mini.style.left = b.xPct + '%';
      mini.style.top = b.yPct + '%';
      item.appendChild(mini);
    });
    if (galleryEl) galleryEl.appendChild(item);
  }

  function renderGallery() {
    if (!galleryEl) return;
    galleryEl.innerHTML = '';
    savedBots.forEach(renderGalleryItem);
  }

  function saveBot() {
    if (!blocks.length) return;
    savedBots.push(blocks.map(b => ({ shape: b.shape, color: b.color, xPct: b.xPct, yPct: b.yPct })));
    try { localStorage.setItem('legoSavedBots', JSON.stringify(savedBots)); } catch (e) {}
    renderCount();
    renderGalleryItem(savedBots[savedBots.length - 1]);
  }

  shapeBtns.forEach(btn => btn.addEventListener('click', () => addBlock(btn.dataset.shape)));
  if (recolorBtn) recolorBtn.addEventListener('click', recolorAll);
  if (clearBtn) clearBtn.addEventListener('click', clearCanvas);
  if (saveBtn) saveBtn.addEventListener('click', saveBot);

  // Seed a little starter bot so the canvas isn't empty on first visit
  ['circle', 'square', 'triangle'].forEach(addBlock);
  renderCount();
  renderGallery();
})();

/* ---------- 12. Space scene scroll animation ----------
   Purely decorative. The ship follows ONE fixed, smooth S-curve down the
   left side of the viewport as you scroll through the whole page (0% =
   near the top, 100% = near the bottom) — PATH_AMPLITUDE/PATH_CYCLES
   below define that single curve, and nothing else changes the ship's
   target position. Each asteroid sits at its own fixed point along the
   page (data-progress) offset a little to one side of wherever the
   curve is at that point (data-lane, now a small +/- offset rather than
   an absolute position) — so the ship's fixed path naturally threads
   past it, without any reactive "if an asteroid is near, dodge" branch
   that could otherwise make the motion look erratic. Every value is
   still recalculated every animation frame and eased toward with a
   lerp, so it stays smooth regardless of how choppy the underlying
   scroll events are — this runs on its own rAF loop rather than only
   reacting to the scroll event. Hidden under prefers-reduced-motion and
   below 900px width (see style.css) — bails out immediately in both
   cases so the loop never starts. */
(function spaceScene() {
  const scene = document.getElementById('space-scene');
  const ship = document.getElementById('spaceship');
  if (!scene || !ship || prefersReducedMotion) return;
  if (window.matchMedia && matchMedia('(max-width: 900px)').matches) return;

  const asteroids = Array.from(scene.querySelectorAll('.asteroid')).map(el => ({
    el,
    progress: parseFloat(el.dataset.progress),
    offset: parseFloat(el.dataset.lane),
  }));

  const SHIP_HEIGHT = 68 * (70 / 60); // matches rendered width:68px against the 60x70 viewBox
  const PATH_CENTER = 17;   // the curve's centre lane, as a % of viewport width
  const PATH_AMPLITUDE = 12; // how far it swings either side of centre
  const PATH_CYCLES = 2;     // full S-curve repeats over the whole page

  // The one fixed path both the ship and the asteroids read from.
  function pathLane(progress) {
    return PATH_CENTER + Math.sin(progress * Math.PI * 2 * PATH_CYCLES) * PATH_AMPLITUDE;
  }

  let currentX = 0;
  let currentY = 20;
  let currentRotate = 0;

  function scrollProgress() {
    const scrollableHeight = document.documentElement.scrollHeight - window.innerHeight;
    return scrollableHeight > 0 ? Math.min(1, Math.max(0, window.scrollY / scrollableHeight)) : 0;
  }

  function update() {
    const progress = scrollProgress();
    const vh = window.innerHeight;
    const vw = window.innerWidth;

    // Ship's overall vertical travel: top of the page to the bottom.
    const travelRange = vh - SHIP_HEIGHT - 40;
    const targetY = 20 + progress * Math.max(0, travelRange);
    const targetX = (pathLane(progress) / 100) * vw;

    asteroids.forEach(a => {
      // Position along the page: drifts down past the viewport as scroll
      // approaches its fixed point, then continues past and off the top —
      // so it reads as flowing by rather than popping in.
      const distance = progress - a.progress;
      const pxPerProgress = vh * 3.4;
      const aY = vh * 0.5 - distance * pxPerProgress;
      // Fixed a little to one side of wherever the ship's curve sits at
      // this same point in the page, so the ship visibly threads past it.
      const aX = ((pathLane(a.progress) + a.offset) / 100) * vw;
      a.el.style.transform = `translate(${aX.toFixed(1)}px, ${aY.toFixed(1)}px)`;
      a.el.style.opacity = (aY > -80 && aY < vh + 80) ? '1' : '0';
    });

    // Smooth toward the target a little each frame instead of jumping —
    // this is what keeps the motion feeling fluid rather than mechanical.
    const velX = targetX - currentX;
    currentX += velX * 0.05;
    currentY += (targetY - currentY) * 0.1;
    const tiltTarget = Math.max(-14, Math.min(14, velX * 0.4));
    currentRotate += (tiltTarget - currentRotate) * 0.08;

    ship.style.transform = `translate(${currentX.toFixed(1)}px, ${currentY.toFixed(1)}px) rotate(${currentRotate.toFixed(1)}deg)`;

    requestAnimationFrame(update);
  }

  requestAnimationFrame(update);
})();