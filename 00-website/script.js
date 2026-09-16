/* ==========================================================================
   PORTFOLIO INTERACTIONS
   1. Remove no-js class (enables JS-only UI, incl. skill map)
   2. Terminal-style typed intro in the hero
   3. Scroll-reveal for each .section
   4. Sticky nav-dot active-state tracking
   5. Signature interactive element: animated skill/stack map
      (canvas edges between nodes sharing a category + hover/click)
   6. Tech-stack category filter chips
   7. Project tag filter chips
   ========================================================================== */

document.documentElement.classList.remove('no-js');

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---------- 2. Terminal typed intro ---------- */
(function typedIntro() {
  const el = document.getElementById('terminal-text');
  if (!el) return;

  const lines = [
    'whoami',
    '> [Your Name] — Data Analyst / BI Analyst / Data Scientist'
  ];

  if (prefersReducedMotion) {
    el.textContent = lines[1].replace('> ', '');
    return;
  }

  let lineIndex = 0;
  let charIndex = 0;

  function type() {
    const current = lines[lineIndex];
    if (charIndex <= current.length) {
      el.textContent = current.slice(0, charIndex);
      charIndex++;
      setTimeout(type, lineIndex === 0 ? 70 : 28);
    } else if (lineIndex < lines.length - 1) {
      lineIndex++;
      charIndex = 0;
      setTimeout(type, 500);
    }
  }
  type();
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

/* ---------- 5. Signature element: skill/stack map ---------- */
(function skillMap() {
  const wrap = document.querySelector('.stack-map-wrap');
  const canvas = document.getElementById('stack-canvas');
  const nodesList = document.getElementById('stack-nodes');
  if (!wrap || !canvas || !nodesList) return;

  const ctx = canvas.getContext('2d');
  const nodeEls = Array.from(nodesList.querySelectorAll('.node'));
  let activeGroup = 'all';
  let hoveredNode = null;

  function resizeCanvas() {
    const rect = wrap.getBoundingClientRect();
    canvas.width = rect.width * devicePixelRatio;
    canvas.height = rect.height * devicePixelRatio;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    draw();
  }

  function nodeCenter(el) {
    const wrapRect = wrap.getBoundingClientRect();
    const rect = el.getBoundingClientRect();
    return {
      x: rect.left - wrapRect.left + rect.width / 2,
      y: rect.top - wrapRect.top + rect.height / 2
    };
  }

  function draw() {
    const rect = wrap.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);

    const visible = nodeEls.filter(n => activeGroup === 'all' || n.dataset.group === activeGroup);

    // draw edges between nodes that share a category
    visible.forEach((a, i) => {
      visible.slice(i + 1).forEach(b => {
        if (a.dataset.group !== b.dataset.group) return;
        const p1 = nodeCenter(a);
        const p2 = nodeCenter(b);
        const isHoverEdge = hoveredNode && (a === hoveredNode || b === hoveredNode);

        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.strokeStyle = isHoverEdge ? 'rgba(245,166,35,0.7)' : 'rgba(154,164,174,0.15)';
        ctx.lineWidth = isHoverEdge ? 1.6 : 1;
        ctx.stroke();
      });
    });
  }

  function setActiveGroup(group) {
    activeGroup = group;
    nodeEls.forEach(n => {
      const show = group === 'all' || n.dataset.group === group;
      n.classList.toggle('dimmed', !show);
      n.style.pointerEvents = show ? 'auto' : 'none';
    });
    draw();
  }

  nodeEls.forEach(node => {
    node.setAttribute('tabindex', '0');
    node.addEventListener('mouseenter', () => { hoveredNode = node; draw(); });
    node.addEventListener('mouseleave', () => { hoveredNode = null; draw(); });
    node.addEventListener('focus', () => { hoveredNode = node; draw(); });
    node.addEventListener('blur', () => { hoveredNode = null; draw(); });
    node.addEventListener('click', () => {
      node.classList.toggle('active');
    });
  });

  document.querySelectorAll('.stack-filter').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.stack-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      setActiveGroup(btn.dataset.group);
    });
  });

  window.addEventListener('resize', resizeCanvas, { passive: true });
  // Redraw on scroll too, since node positions are percentage-based and reflow with layout
  window.addEventListener('scroll', () => window.requestAnimationFrame(draw), { passive: true });

  resizeCanvas();
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