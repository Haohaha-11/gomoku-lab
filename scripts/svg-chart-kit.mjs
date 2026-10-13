// Offline, build-time SVG helpers for continuous research reports.
// Copy this file beside a report-specific render-figures.mjs, import the helpers,
// define the real experiment arrays, and write the generated SVGs into visuals/.

export const academicPalette = {
  ink: "#101c2c",
  text: "#2e3b4e",
  muted: "#68778a",
  line: "#d8e0e9",
  axis: "#95a3b3",
  paper: "#fffefb",
  blue: "#1f5f8b",
  cyan: "#147b82",
  green: "#14745a",
  red: "#b74747",
  purple: "#6d4b8c",
};

export const bilingualFontStack = `"Times New Roman", Times, "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Source Han Sans SC", sans-serif`;

export const escapeXml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;");

export const round = (value) => Number(value.toFixed(2));

export const linearScale = ([d0, d1], [r0, r1]) =>
  (value) => r0 + ((value - d0) / (d1 - d0)) * (r1 - r0);

export const logScale = ([d0, d1], [r0, r1]) => {
  const lo = Math.log10(d0);
  const span = Math.log10(d1) - lo;
  return (value) => r0 + ((Math.log10(value) - lo) / span) * (r1 - r0);
};

export const pathFrom = (points, x, y) => points
  .map((point, index) => `${index ? "L" : "M"}${round(x(point[0]))} ${round(y(point[1]))}`)
  .join(" ");

export function svgDocument({ width, height, title, description, body, palette = academicPalette }) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title desc">
  <title id="title">${escapeXml(title)}</title>
  <desc id="desc">${escapeXml(description)}</desc>
  <style>
    text { font-family: ${bilingualFontStack}; }
    .axis { fill: ${palette.muted}; font-size: 16px; }
    .axis-title { fill: ${palette.text}; font-size: 17px; }
    .label { fill: ${palette.ink}; font-size: 18px; font-weight: 700; }
    .value { font-size: 18px; font-weight: 700; }
  </style>
  ${body}
</svg>
`;
}

export function axes({ width, height, margin, xTicks, yTicks, x, y, xFormat, yFormat, xTitle, yTitle, palette = academicPalette }) {
  const left = margin.left;
  const right = width - margin.right;
  const top = margin.top;
  const bottom = height - margin.bottom;
  const yGrid = yTicks.map((tick) => `<g>
    <line x1="${left}" y1="${round(y(tick))}" x2="${right}" y2="${round(y(tick))}" stroke="${palette.line}" stroke-width="1.5"/>
    <text class="axis" x="${left - 14}" y="${round(y(tick) + 5)}" text-anchor="end">${escapeXml(yFormat(tick))}</text>
  </g>`).join("");
  const xLabels = xTicks.map((tick) => `<text class="axis" x="${round(x(tick))}" y="${bottom + 31}" text-anchor="middle">${escapeXml(xFormat(tick))}</text>`).join("");
  return `${yGrid}${xLabels}
    <line x1="${left}" y1="${top}" x2="${left}" y2="${bottom}" stroke="${palette.axis}" stroke-width="2"/>
    <line x1="${left}" y1="${bottom}" x2="${right}" y2="${bottom}" stroke="${palette.axis}" stroke-width="2"/>
    <text class="axis-title" x="${(left + right) / 2}" y="${height - 12}" text-anchor="middle">${escapeXml(xTitle)}</text>
    <text class="axis-title" transform="translate(24 ${(top + bottom) / 2}) rotate(-90)" text-anchor="middle">${escapeXml(yTitle)}</text>`;
}

export function series(points, x, y, { color, width = 4, dash = "", opacity = 1, radius = 6 }) {
  const markers = points.map((point) => `<circle cx="${round(x(point[0]))}" cy="${round(y(point[1]))}" r="${radius}" fill="${color}" opacity="${opacity}"/>`).join("");
  return `<path d="${pathFrom(points, x, y)}" fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round" ${dash ? `stroke-dasharray="${dash}"` : ""} opacity="${opacity}"/>${markers}`;
}

export function badge({ x, y, width, label, fill, stroke, color, height = 34 }) {
  return `<g>
    <rect x="${x}" y="${y}" width="${width}" height="${height}" rx="${height / 2}" fill="${fill}" stroke="${stroke}"/>
    <text x="${x + 15}" y="${y + height * 0.68}" fill="${color}" font-size="17" font-weight="700">${escapeXml(label)}</text>
  </g>`;
}
