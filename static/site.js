'use strict';
(() => {
  const menu = document.getElementById('brush-menu');
  const toggle = document.getElementById('menu-toggle');
  const menuLinks = [...menu.querySelectorAll('nav a')];
  let previousFocus = null;
  function closeMenu() {
    menu.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('menu-open');
    if (previousFocus) previousFocus.focus({ preventScroll: true });
  }
  toggle.addEventListener('click', () => {
    if (!menu.hidden) return closeMenu();
    previousFocus = document.activeElement;
    menu.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('menu-open');
    menuLinks[0].focus({ preventScroll: true });
  });
  menuLinks.forEach(link => link.addEventListener('click', closeMenu));
  document.addEventListener('keydown', event => {
    if (menu.hidden) return;
    if (event.key === 'Escape') closeMenu();
    if (event.key === 'Tab') {
      const controls = [toggle, ...menu.querySelectorAll('a')];
      const current = controls.indexOf(document.activeElement);
      if (event.shiftKey && current <= 0) { event.preventDefault(); controls.at(-1).focus(); }
      else if (!event.shiftKey && current === controls.length - 1) { event.preventDefault(); toggle.focus(); }
    }
  });
  const tocLinks = [...document.querySelectorAll('#report-toc a')];
  const sections = tocLinks.map(a => document.querySelector(a.getAttribute('href')));
  const progress = document.getElementById('reading-progress');
  let queued = false;
  function updateScroll() {
    const height = document.documentElement.scrollHeight - innerHeight;
    progress.style.transform = `scaleX(${height > 0 ? Math.min(1, scrollY / height) : 0})`;
    let active = null;
    for (const section of sections) if (section.getBoundingClientRect().top < 210) active = section.id;
    tocLinks.forEach(link => {
      const selected = link.getAttribute('href') === `#${active}`;
      link.classList.toggle('is-active', selected);
      if (selected) link.setAttribute('aria-current','location'); else link.removeAttribute('aria-current');
    });
    let main = scrollY < 450 ? 'top' : 'film';
    if (document.getElementById('report').getBoundingClientRect().top < 250) main = 'report';
    if (document.getElementById('analysis').getBoundingClientRect().top < 250) main = 'analysis';
    if (document.getElementById('innovation').getBoundingClientRect().top < 250) main = 'innovation';
    menuLinks.forEach(link => link.classList.toggle('active', link.getAttribute('href') === `#${main}`));
    queued = false;
  }
  addEventListener('scroll', () => { if (!queued) { queued = true; requestAnimationFrame(updateScroll); } }, { passive: true });
  addEventListener('resize', updateScroll);
  updateScroll();

  const benchmark = window.GOMOKU_BENCHMARKS;
  document.querySelectorAll('[data-board-size]').forEach(button => {
    button.addEventListener('click', () => {
      const size = Number(button.dataset.boardSize);
      if (!benchmark || !benchmark.config.sizes.includes(size)) return;
      document.querySelectorAll('[data-board-size]').forEach(other => {
        const selected = other === button;
        other.classList.toggle('active', selected);
        other.setAttribute('aria-pressed', String(selected));
      });
      for (const metric of ['nodes','time']) {
        const chart = document.getElementById(`${metric}-chart`);
        chart.src = `./figures/${metric}-${size}.svg`;
        chart.alt = `${size}乘${size}棋盘，深度1至3，两种算法的${metric==='time'?'平均耗时与样本标准差':'平均访问节点数'}对照`;
      }
      document.querySelectorAll('.figure-board').forEach(label => { label.textContent = `${size} × ${size}`; });
      const data = benchmark.aggregates.filter(row => row.size === size && row.depth === 3);
      const mm = data.find(row => row.algorithm === 'minimax');
      const ab = data.find(row => row.algorithm === 'alphabeta');
      document.getElementById('node-finding').innerHTML = `在 ${size} × ${size} 棋盘、深度 3 下，Alpha-Beta 平均访问 ${ab.mean_nodes.toFixed(1)} 个节点，极大极小为 ${mm.mean_nodes.toFixed(1)} 个，减少 <strong>${ab.node_reduction_pct.toFixed(1)}%</strong>。`;
      document.getElementById('time-finding').innerHTML = `同一条件下，平均耗时从 ${mm.mean_ms.toFixed(2)} ms 降至 ${ab.mean_ms.toFixed(2)} ms，约加速 <strong>${ab.speedup_vs_minimax.toFixed(2)} 倍</strong>。浅层搜索中的毫秒差异仍可能受运行时波动影响。`;
    });
  });
})();
