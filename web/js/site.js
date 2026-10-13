(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const NS = "http://www.w3.org/2000/svg";
  const C = { fg: "#1f1d1a", fg2: "#4a463f", fg3: "#7a7367", line: "rgba(31,29,26,.13)", accent: "#b03a2e", accent2: "#c7473a", bg: "#f4f0e8", bg3: "#e1d9cb", faint: "rgba(31,29,26,.16)", ghost: "rgba(31,29,26,.28)", bar: "rgba(31,29,26,.2)" };
  const el = (tag, attrs = {}, parent) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  };
  const text = (parent, x, y, s, attrs = {}) => { const t = el("text", { x, y, ...attrs }, parent); t.textContent = s; return t; };

  /* 顶栏与目录 */
  const topbar = $("#topbar");
  const onScroll = () => topbar && topbar.classList.toggle("scrolled", scrollY > 40);
  addEventListener("scroll", onScroll, { passive: true }); onScroll();

  const menu = $("#menu"), openBtn = $("#menu-open"), closeBtn = $("#menu-close");
  const setMenu = open => {
    if (!menu) return;
    menu.classList.toggle("open", open);
    openBtn.setAttribute("aria-expanded", String(open));
    document.body.style.overflow = open ? "hidden" : "";
    if (open) closeBtn.focus(); else openBtn.focus();
  };
  openBtn && openBtn.addEventListener("click", () => setMenu(true));
  closeBtn && closeBtn.addEventListener("click", () => setMenu(false));
  addEventListener("keydown", e => { if (e.key === "Escape" && menu && menu.classList.contains("open")) setMenu(false); });
  menu && $$("nav a", menu).forEach(a => a.addEventListener("click", () => setMenu(false)));

  // 当前所在章节在目录中加笔刷高亮
  const menuLinks = menu ? $$("nav a[href^='#']", menu) : [];
  const sections = menuLinks.map(a => $(a.getAttribute("href"))).filter(Boolean);
  if (sections.length && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(entries => {
      entries.forEach(en => {
        if (!en.isIntersecting) return;
        menuLinks.forEach(a => a.classList.toggle("current", a.getAttribute("href") === "#" + en.target.id));
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    sections.forEach(s => io.observe(s));
  }

  /* 首屏飘散的朱红墨点 */
  const canvas = $("#embers");
  if (canvas && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const ctx = canvas.getContext("2d");
    let w = 0, h = 0, running = true;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    const resize = () => {
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize(); addEventListener("resize", resize);
    const spawn = (init) => ({
      x: Math.random() * w, y: init ? Math.random() * h : -20,
      r: 1 + Math.random() * 3, vx: .1 + Math.random() * .35, vy: .15 + Math.random() * .4,
      rot: Math.random() * Math.PI, vr: (Math.random() - .5) * .03,
      a: .18 + Math.random() * .4, red: Math.random() < .22,
    });
    const flecks = Array.from({ length: 26 }, () => spawn(true));
    const tick = () => {
      if (!running) return;
      ctx.clearRect(0, 0, w, h);
      for (const f of flecks) {
        f.x += f.vx; f.y += f.vy; f.rot += f.vr;
        if (f.y > h + 20 || f.x > w + 20) Object.assign(f, spawn(false));
        ctx.save(); ctx.translate(f.x, f.y); ctx.rotate(f.rot);
        ctx.globalAlpha = f.a; ctx.fillStyle = f.red ? C.accent2 : C.fg;
        ctx.beginPath(); ctx.ellipse(0, 0, f.r * 1.8, f.r * .7, 0, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
      }
      requestAnimationFrame(tick);
    };
    new IntersectionObserver(([en]) => { const was = running; running = en.isIntersecting; if (running && !was) tick(); }).observe(canvas);
    tick();
  }

  /* 水墨笔触所需的渐变与滤镜，两页共用 */
  document.body.insertAdjacentHTML("afterbegin", `<svg class="defs" aria-hidden="true" focusable="false" width="0" height="0"><defs>
    <radialGradient id="stone-black" cx="36%" cy="30%" r="72%"><stop offset="0" stop-color="#57524b"/><stop offset=".45" stop-color="#26231f"/><stop offset="1" stop-color="#100f0d"/></radialGradient>
    <radialGradient id="stone-white" cx="36%" cy="30%" r="78%"><stop offset="0" stop-color="#fffdf8"/><stop offset=".65" stop-color="#f1ebe0"/><stop offset="1" stop-color="#d6cdbd"/></radialGradient>
    <radialGradient id="blot"><stop offset="0" stop-color="#1f1d1a" stop-opacity=".17"/><stop offset=".72" stop-color="#1f1d1a" stop-opacity=".1"/><stop offset="1" stop-color="#1f1d1a" stop-opacity="0"/></radialGradient>
    <filter id="ink-bleed" x="-40%" y="-40%" width="180%" height="180%">
      <feTurbulence type="fractalNoise" baseFrequency=".09" numOctaves="3" seed="8" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="5" xChannelSelector="R" yChannelSelector="G" result="d"/>
      <feGaussianBlur in="d" stdDeviation="2.6" result="halo"/>
      <feComponentTransfer in="halo" result="soft"><feFuncA type="linear" slope=".42"/></feComponentTransfer>
      <feMerge><feMergeNode in="soft"/><feMergeNode in="d"/></feMerge>
    </filter>
    <filter id="brush-line" x="-10%" y="-30%" width="120%" height="160%">
      <feTurbulence type="fractalNoise" baseFrequency=".04" numOctaves="2" seed="2" result="w"/>
      <feDisplacementMap in="SourceGraphic" in2="w" scale="4" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="dry-v" x="-10%" y="-5%" width="120%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency=".5 .012" numOctaves="2" seed="6" result="s"/>
      <feColorMatrix in="s" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -2.4 2.3" result="m"/>
      <feComposite in="SourceGraphic" in2="m" operator="in" result="k"/>
      <feTurbulence type="fractalNoise" baseFrequency=".05" numOctaves="2" seed="3" result="w"/>
      <feDisplacementMap in="k" in2="w" scale="5" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="dry-h" x="-5%" y="-20%" width="110%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency=".012 .5" numOctaves="2" seed="7" result="s"/>
      <feColorMatrix in="s" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -2.6 2.4" result="m"/>
      <feComposite in="SourceGraphic" in2="m" operator="in" result="k"/>
      <feTurbulence type="fractalNoise" baseFrequency=".04" numOctaves="2" seed="4" result="w"/>
      <feDisplacementMap in="k" in2="w" scale="6" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
  </defs></svg>`);
  const BRUSH = "font-family: var(--brush)";

  // 一笔两头尖、中间饱满的笔画
  const stroke = (x1, y1, x2, y2, w) => {
    const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy), nx = -dy / len, ny = dx / len;
    const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
    return `M${x1} ${y1}Q${mx + nx * w} ${my + ny * w} ${x2} ${y2}Q${mx - nx * w * .55} ${my - ny * w * .55} ${x1} ${y1}Z`;
  };
  // 略带弧度的手绘连线
  const curve = (x1, y1, x2, y2, bend = 4) => {
    const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy) || 1;
    return `M${x1} ${y1}Q${(x1 + x2) / 2 - dy / len * bend} ${(y1 + y2) / 2 + dx / len * bend} ${x2} ${y2}`;
  };
  const whiteStone = (parent, cx, cy, r, turn = 0) => {
    el("ellipse", { cx, cy: cy + r * .45, rx: r * 1.15, ry: r * .55, fill: "url(#blot)", opacity: .7 }, parent);
    el("circle", { cx, cy, r, fill: "url(#stone-white)" }, parent);
    el("circle", { cx, cy, r, fill: "none", stroke: C.fg, "stroke-width": 1.7, opacity: .78, pathLength: 100, "stroke-dasharray": "93 7", "stroke-linecap": "round", transform: `rotate(${turn} ${cx} ${cy})`, filter: "url(#brush-line)" }, parent);
  };
  const blackStone = (parent, cx, cy, r) => {
    el("circle", { cx, cy, r, fill: "url(#stone-black)", filter: "url(#ink-bleed)" }, parent);
    el("ellipse", { cx: cx - r * .32, cy: cy - r * .38, rx: r * .28, ry: r * .16, fill: "#fff", opacity: .18, transform: `rotate(-30 ${cx - r * .32} ${cy - r * .38})` }, parent);
  };
  const inkDot = (parent, cx, cy, r, color) => el("circle", { cx, cy, r, fill: color, filter: "url(#ink-bleed)" }, parent);

  /* 搜索规模 */
  const growth = $("#growth");
  if (growth) {
    const rows = [[1, 221, "221"], [2, 221 * 220, "4.9 万"], [3, 221 * 220 * 219, "1065 万"], [4, 221 * 220 * 219 * 218, "23.2 亿"]];
    const max = Math.log10(rows[3][1]);
    growth.innerHTML = rows.map(([d, v, label]) =>
      `<div class="growth-row${d === 3 ? " hot" : ""}"><span>${d} 手</span><div class="growth-bar"><b style="width:${(Math.log10(v) / max * 100).toFixed(1)}%"></b><strong>${label}</strong></div></div>`).join("");
  }

  /* 博弈树示意：AIMA 经典例子。己方为黑棋，对方为白棋，叶子是淡墨点上的估值 */
  const drawTree = (svg, pruneMode) => {
    if (!svg) return;
    const leaves = [[3, 12, 8], [2, 4, 6], [14, 5, 2]];
    const mins = [3, 2, 2];
    const root = { x: 262, y: 38 }, minY = 132, leafY = 228, minX = [124, 262, 400];
    const pruned = (i, j) => pruneMode && i === 1 && j > 0;
    const lines = el("g", { fill: "none", stroke: C.fg, "stroke-linecap": "round", filter: "url(#brush-line)" }, svg);
    const marks = el("g", {}, svg);
    minX.forEach((mx, i) => {
      el("path", { d: curve(root.x, root.y + 18, mx, minY - 16, i === 1 ? 0 : 5 * (i - 1)), "stroke-width": 2.4, opacity: .42 }, lines);
      leaves[i].forEach((v, j) => {
        const lx = mx + (j - 1) * 42, cut = pruned(i, j);
        el("path", { d: curve(mx, minY + 16, lx, leafY - 14, (j - 1) * 3), "stroke-width": cut ? 2.6 : 2, opacity: cut ? .2 : .38, "stroke-dasharray": cut ? "1 7" : "none" }, lines);
        el("ellipse", { cx: lx, cy: leafY, rx: 19, ry: 16, fill: "url(#blot)", filter: "url(#ink-bleed)", opacity: cut ? .3 : 1 }, marks);
        text(marks, lx, leafY + 8, String(v), { "text-anchor": "middle", "font-size": 23, fill: C.fg, opacity: cut ? .22 : 1, style: BRUSH });
      });
      whiteStone(marks, mx, minY, 17, i * 120 + 40);
      const side = 30, anchor = "start";
      if (pruneMode && i === 1) {
        const t = text(marks, mx + side, minY + 8, "", { "text-anchor": anchor, fill: C.accent });
        const a = el("tspan", { "font-size": 17, "font-weight": 700 }, t); a.textContent = "≤";
        const b = el("tspan", { "font-size": 23, style: BRUSH }, t); b.textContent = "2";
      } else {
        text(marks, mx + side, minY + 8, String(mins[i]), { "text-anchor": anchor, "font-size": 23, fill: C.fg2, style: BRUSH });
      }
    });
    blackStone(marks, root.x, root.y, 19);
    text(marks, root.x + 32, root.y + 9, "3", { "font-size": 28, fill: C.accent, style: BRUSH });
    text(marks, 4, root.y + 5, "己方 · 取最大", { "font-size": 13, fill: C.fg3 });
    text(marks, 4, minY + 5, "对方 · 取最小", { "font-size": 13, fill: C.fg3 });
    if (pruneMode) {
      // 朱笔一划，划去两条被剪掉的分支
      el("path", { d: stroke(256, 166, 320, 186, 7), fill: C.accent, filter: "url(#dry-h)" }, marks);
      inkDot(marks, 327, 185, 2.2, C.accent);
      text(marks, minX[1] + 22, leafY + 40, "剪掉 2 个叶子", { "text-anchor": "middle", "font-size": 17, fill: C.accent, style: BRUSH });
    }
  };
  drawTree($("#tree-mm"), false);
  drawTree($("#tree-ab"), true);

  /* 实验图表：毛笔折线、棋子数据点、干笔柱 */
  const data = window.GOMOKU_DATA;
  const axisText = { "font-size": 13, fill: C.fg3 };
  const fmt = v => v >= 1000 ? (v / 1000).toFixed(1).replace(/\.0$/, "") + "k" : String(Math.round(v * 10) / 10);

  const chartNodes = (svg, size) => {
    svg.innerHTML = "";
    const b = data.bench[size], W = 520, H = 320, L = 56, R = 24, T = 24, B = 44;
    const x = d => L + (d - 1) * (W - L - R) / 2;
    const lo = 0, hi = 3; // log10 1..1000
    const y = v => T + (H - T - B) * (1 - (Math.log10(v) - lo) / (hi - lo));
    [1, 10, 100, 1000].forEach(v => {
      el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: C.line }, svg);
      text(svg, L - 12, y(v) + 4, fmt(v), { ...axisText, "text-anchor": "end" });
    });
    [1, 2, 3].forEach(d => text(svg, x(d), H - 14, `深度 ${d}`, { ...axisText, "text-anchor": "middle" }));
    text(svg, L, 12, "访问节点", { ...axisText });
    [["minimax", C.fg2], ["alphabeta", C.accent]].forEach(([algo, color]) => {
      const pts = b[algo].map(p => [x(p.depth), y(p.nodes)]);
      const d = pts.map((p, i) => (i ? "L" : "M") + p.join(" ")).join("");
      const isAB = algo === "alphabeta";
      el("path", { d, fill: "none", stroke: color, "stroke-width": isAB ? 3.6 : 2.8, opacity: isAB ? .92 : .7, "stroke-linecap": "round", "stroke-linejoin": "round", "stroke-dasharray": isAB ? "none" : "9 8", filter: "url(#brush-line)" }, svg);
      b[algo].forEach((p, i) => {
        if (isAB) inkDot(svg, pts[i][0], pts[i][1], 6.5, C.accent); else whiteStone(svg, pts[i][0], pts[i][1], 7.5, i * 90);
        if (p.depth > 1) text(svg, pts[i][0] + (p.depth === 3 ? -14 : 0), pts[i][1] + (isAB ? 30 : -16), fmt(p.nodes), { "font-size": 19, fill: color, "text-anchor": p.depth === 3 ? "end" : "middle", style: BRUSH });
      });
    });
  };

  const bars = (svg, groups, opts) => {
    svg.innerHTML = "";
    const W = 520, H = opts.h || 320, L = 56, R = 16, T = 28, B = 44;
    const max = Math.max(...groups.flatMap(g => g.values.map(v => v.v + (v.sd || 0)))) * 1.12;
    const step = niceStep(max);
    const y = v => T + (H - T - B) * (1 - v / max);
    for (let v = 0; v <= max; v += step) {
      el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: C.line }, svg);
      text(svg, L - 12, y(v) + 4, String(v), { ...axisText, "text-anchor": "end" });
    }
    text(svg, L, 14, opts.unit, { ...axisText });
    const gw = (W - L - R) / groups.length, bw = Math.min(46, gw / 3.2);
    groups.forEach((g, gi) => {
      const cx = L + gw * (gi + .5);
      text(svg, cx, H - 14, g.label, { ...axisText, "text-anchor": "middle" });
      g.values.forEach((v, vi) => {
        const bx = cx + (vi - .5) * (bw + 8) - bw / 2, isAB = vi === 1;
        const top = y(v.v), hgt = Math.max(2, y(0) - top);
        // 干笔一刷：上端略收，底部压实
        el("path", { d: `M${bx + 2} ${top + 3}Q${bx + bw / 2} ${top - 4} ${bx + bw - 1} ${top + 1}L${bx + bw} ${top + hgt}L${bx} ${top + hgt}Z`,
          fill: isAB ? C.accent : C.fg, "fill-opacity": isAB ? .88 : .3, filter: "url(#dry-v)" }, svg);
        if (v.sd) {
          const mx = bx + bw / 2, c = isAB ? C.accent : C.fg2;
          el("path", { d: `M${mx} ${y(v.v + v.sd)}L${mx} ${y(Math.max(0, v.v - v.sd))}M${mx - 5} ${y(v.v + v.sd)}L${mx + 5} ${y(v.v + v.sd)}`, stroke: c, "stroke-width": 1.5, "stroke-linecap": "round", fill: "none", opacity: .8, filter: "url(#brush-line)" }, svg);
        }
        if (v.v >= max * .06) text(svg, bx + bw / 2, y(v.v + (v.sd || 0)) - 9, String(Math.round(v.v)), { "font-size": 17, fill: isAB ? C.accent : C.fg2, "text-anchor": "middle", style: BRUSH });
      });
    });
  };
  function niceStep(max) {
    const raw = max / 4, p = 10 ** Math.floor(Math.log10(raw));
    return [1, 2, 2.5, 5, 10].map(m => m * p).find(s => s >= raw);
  }

  const timeChart = (svg, size) => {
    const b = data.bench[size];
    bars(svg, [1, 2, 3].map(d => ({
      label: `深度 ${d}`,
      values: ["minimax", "alphabeta"].map(a => { const p = b[a].find(q => q.depth === d); return { v: p.ms, sd: p.sd }; }),
    })), { unit: "毫秒" });
  };

  if (data) {
    const nodesSvg = $("#chart-nodes"), timeSvg = $("#chart-time");
    const show = size => { chartNodes(nodesSvg, size); timeChart(timeSvg, size); };
    $$(".tabs button").forEach(btn => btn.addEventListener("click", () => {
      $$(".tabs button").forEach(b => b.setAttribute("aria-pressed", String(b === btn)));
      show(btn.dataset.size);
    }));
    if (nodesSvg) show("15");
    const sizeSvg = $("#chart-size");
    if (sizeSvg) bars(sizeSvg, ["9", "13", "15"].map(s => ({
      label: `${s} 路`,
      values: ["minimax", "alphabeta"].map(a => { const p = data.bench[s][a].find(q => q.depth === 3); return { v: p.ms, sd: p.sd }; }),
    })), { unit: "毫秒", h: 300 });
  }

  /* 报告页目录高亮 */
  const toc = $$(".toc a");
  if (toc.length && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(entries => entries.forEach(en => {
      if (en.isIntersecting) toc.forEach(a => a.classList.toggle("current", a.getAttribute("href") === "#" + en.target.id));
    }), { rootMargin: "-30% 0px -60% 0px" });
    toc.forEach(a => { const s = $(a.getAttribute("href")); if (s) io.observe(s); });
  }
})();
