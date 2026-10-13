// Reproducible figures from measured benchmark aggregates. No simulated values.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { svgDocument, escapeXml as esc, linearScale, round } from './svg-chart-kit.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const summary = JSON.parse(fs.readFileSync(path.join(root, 'results/summary.json'), 'utf8'));
const output = path.join(root, 'static/figures');
fs.mkdirSync(output, { recursive: true });
const colors = { minimax:'#3b4441', alphabeta:'#a53629', grid:'#dad8d0', label:'#313732' };

function chart(size, metric) {
  const groups = summary.aggregates.filter(g => g.size === size);
  const timing = metric === 'time';
  const key = timing ? 'mean_ms' : 'mean_nodes';
  const max = timing ? Math.max(...groups.map(g => g.mean_ms + g.std_ms)) : Math.max(...groups.map(g => g.mean_nodes));
  const step = timing ? (max > 600 ? 250 : 100) : 200;
  const ymax = Math.ceil(max / step) * step;
  const width=940, height=430, left=84, right=914, top=42, bottom=350;
  const y = linearScale([0, ymax], [bottom, top]);
  let body = `<rect width="${width}" height="${height}" fill="#f9f8f3"/>`;
  for(let tick=0; tick<=ymax; tick+=step){
    body += `<line x1="${left}" y1="${round(y(tick))}" x2="${right}" y2="${round(y(tick))}" stroke="${colors.grid}" stroke-width="1"/>`;
    body += `<text x="${left-14}" y="${round(y(tick)+7)}" text-anchor="end" fill="${colors.label}" font-size="23">${tick}</text>`;
  }
  body += `<text x="${left}" y="24" font-size="21" fill="${colors.label}">${timing?'平均耗时 / 毫秒':'平均访问节点数'}</text>`;
  for (let depth=1; depth<=3; depth++) {
    const center=220 + (depth-1)*285;
    for(const [i, algo] of ['minimax','alphabeta'].entries()) {
      const item=groups.find(g => g.depth===depth && g.algorithm===algo);
      const xpos=center + (i===0?-83:9), barwidth=74;
      const yy=y(item[key]);
      body += `<rect x="${xpos}" y="${round(yy)}" width="${barwidth}" height="${round(bottom-yy)}" fill="${colors[algo]}"${i===0?' fill-opacity=".9"':''}/>`;
      let labelY=yy-10;
      if(timing){
        const lo=y(Math.max(0,item.mean_ms-item.std_ms)), hi=y(item.mean_ms+item.std_ms), mid=xpos+barwidth/2;
        body+=`<path d="M${mid} ${round(hi)}V${round(lo)}M${mid-9} ${round(hi)}H${mid+9}M${mid-9} ${round(lo)}H${mid+9}" fill="none" stroke="${colors[algo]}" stroke-width="2"/>`;
        labelY=hi-10;
      }
      body+=`<text x="${xpos+barwidth/2}" y="${round(labelY)}" text-anchor="middle" font-size="23" fill="${colors[algo]}" font-weight="700">${item[key].toFixed(1)}</text>`;
    }
    body+=`<text x="${center}" y="389" text-anchor="middle" fill="${colors.label}" font-size="24">深度 ${depth}</text>`;
  }
  const svg=svgDocument({width,height,title:`${size}×${size} ${timing?'耗时':'节点数'}对照`,description:`相同局面、候选和评价函数；目标深度1至3；${timing?'误差线为9次测量的样本标准差':'平均值包含迭代加深全部轮次'}`,body});
  fs.writeFileSync(path.join(output,`${metric}-${size}.svg`),svg);
}
for(const size of summary.config.sizes){chart(size,'nodes');chart(size,'time');}
fs.writeFileSync(path.join(root,'static/benchmark-data.js'),`// Source: results/summary.json; generated at ${summary.generated_at_utc}\nwindow.GOMOKU_BENCHMARKS=${JSON.stringify({config:summary.config,environment:summary.environment,aggregates:summary.aggregates,equivalence:{paired_checks:summary.equivalence.paired_checks,passed:summary.equivalence.passed}})};\n`);
console.log(`Generated ${summary.config.sizes.length*2} SVG figures and benchmark-data.js`);
