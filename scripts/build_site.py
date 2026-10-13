"""Compose the continuous project homepage from the verified report and data.

The homepage remains readable without JavaScript. Figures are built separately
with render_site_figures.mjs; JavaScript only changes the displayed board size.
"""
from __future__ import annotations
import html
import json
from pathlib import Path

from build_report import load_data, content

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static/index.html"
esc = html.escape


def table(headers, rows):
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="实验数据表，可横向滚动"><table><thead><tr>' + ''.join('<th scope="col">'+esc(str(x))+'</th>' for x in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+esc(str(x))+'</td>' for x in row)+'</tr>' for row in rows) + '</tbody></table></div>'


def blocks_html(blocks, analysis=False):
    parts=[]
    for block in blocks:
        kind=block[0]
        if kind == 'meta':
            continue
        if kind == 'h':
            parts.append('<h3>'+esc(block[1])+'</h3>')
        elif kind == 'p':
            parts.append('<p>'+esc(block[1])+'</p>')
        elif kind == 'steps':
            parts.append('<ol class="report-steps">'+''.join('<li>'+esc(t)+'</li>' for t in block[1])+'</ol>')
        elif kind == 'table':
            rendered=table(block[1],block[2])
            if analysis:
                parts.append('<details class="data-details"><summary>查看全部棋盘与深度的实测均值<span aria-hidden="true">＋</span></summary>'+rendered+'</details>')
            else:
                parts.append(rendered)
        elif kind == 'caption':
            parts.append('<p class="source-note">'+esc(block[1])+'</p>')
        elif kind == 'ref':
            text=esc(block[1])
            for url in ('https://arxiv.org/abs/1712.01815','https://arxiv.org/abs/1706.03741'):
                text=text.replace(url,f'<a href="{url}" target="_blank" rel="noopener">论文原文 ↗</a>')
            parts.append('<p class="reference">'+text+'</p>')
        # Quantitative evidence is replaced by the same measurements in SVG below.
    return '\n'.join(parts)


def main():
    summary, rows=load_data()
    sections=content(summary,rows)
    ids=['overview','principles','implementation','protocol','analysis','discussion','innovation','conclusion']
    titles=['实验目的与内容','两种搜索的决策原理','系统实现与运行环境','可复现的对照实验','搜索深度与剪枝收益','结果分析与正确性验证','从搜索走向学习','实验结论与总结']
    navnames=['目的与内容','算法原理','系统实现','对照设计','实验数据','结果分析','创新计划','结论与总结']
    toc=''.join(f'<a href="#{id}"><span>{i+1:02}</span>{name}</a>' for i,(id,name) in enumerate(zip(ids,navnames)))
    chart='''
      <div class="analysis-controls"><span>选择棋盘</span><div class="board-size-switch" role="group" aria-label="选择图表棋盘大小"><button type="button" data-board-size="9" aria-pressed="false">9 × 9</button><button type="button" data-board-size="13" aria-pressed="false">13 × 13</button><button type="button" data-board-size="15" aria-pressed="true" class="active">15 × 15</button></div></div>
      <div class="chart-legend"><span><i class="legend-mm"></i>极大极小 Minimax</span><span><i class="legend-ab"></i>Alpha-Beta</span></div>
      <p class="mobile-chart-hint">横向滑动查看完整图表 <span aria-hidden="true">↔</span></p>
      <figure class="result-figure"><div class="figure-heading"><h3>完整搜索所访问的节点</h3><span class="figure-board">15 × 15</span></div><div class="chart-scroll"><img id="nodes-chart" src="./figures/nodes-15.svg" alt="15乘15棋盘，搜索深度1到3时两种算法的平均访问节点数" width="940" height="430"></div><figcaption>纵轴从 0 开始。每组为 3 个固定局面各重复 3 次的均值，包含迭代加深的全部轮次。</figcaption></figure>
      <p class="chart-finding" id="node-finding">在 15 × 15 棋盘、深度 3 下，Alpha-Beta 平均访问 175.0 个节点，极大极小为 643.7 个，减少 <strong>72.8%</strong>。</p>
      <figure class="result-figure"><div class="figure-heading"><h3>运行耗时与测量波动</h3><span class="figure-board">15 × 15</span></div><div class="chart-scroll"><img id="time-chart" src="./figures/time-15.svg" alt="15乘15棋盘两种算法的平均耗时，误差线为九次测量的样本标准差" width="940" height="430"></div><figcaption>误差线为 9 次测量的样本标准差，包含局面差异与重复测量波动，<strong>不是置信区间</strong>。测量平台为 Windows / Python 3.12.7，非在线服务器时延。</figcaption></figure>
      <p class="chart-finding" id="time-finding">同一条件下，平均耗时从 1087.67 ms 降至 283.93 ms，约加速 <strong>3.83 倍</strong>。浅层搜索中的毫秒差异仍可能受运行时波动影响。</p>
      <p class="source-note">数据源：<a href="./downloads/benchmark.csv">逐次测量 CSV</a> · <a href="./api/benchmarks">完整配置与汇总 JSON</a>。候选上限 8，固定种子 20261013，基准不设超时。</p>
    '''
    body=[]
    for i,(section,id,title) in enumerate(zip(sections,ids,titles)):
        body.append(f'<section class="report-section" id="{id}" aria-labelledby="heading-{id}"><header class="section-heading"><span class="section-number">{i+1:02}</span><h2 id="heading-{id}">{title}</h2></header>')
        if id=='analysis':
            intro=section['blocks'][0]
            body.append('<p>'+esc(intro[1])+'</p>')
            body.append(chart)
            body.append(blocks_html(section['blocks'][1:],True))
        else:
            body.append(blocks_html(section['blocks']))
        if id=='principles':
            body.append('''<div class="method-comparison"><div><h4>极大极小</h4><p>遍历共同候选树中的全部分支，逐层回传最优值。</p></div><span aria-hidden="true">→</span><div><h4>Alpha-Beta</h4><p>增加上下界，停止搜索已不可能改变祖先决策的分支。</p></div></div><p class="source-note">共享同一候选树和评价函数，完整搜索的根值保持一致。候选裁剪会改变搜索范围，需单独说明。</p>''')
        body.append('</section>')
    doc='''<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="description" content="Python 五子棋实验：极大极小与 Alpha-Beta 搜索、真实对局回放、实验报告和可复现的性能数据。"><title>五子棋博弈搜索实验 · 弈境</title><link rel="icon" type="image/svg+xml" href="./assets/favicon.svg"><link rel="stylesheet" href="./site.css"></head>
<body>
<a class="skip-link" href="#report">跳到实验报告</a>
<div class="reading-progress" aria-hidden="true"><span id="reading-progress"></span></div>
<header class="site-header"><a class="wordmark" href="#top" aria-label="弈境首页"><span class="seal" aria-hidden="true">弈</span>弈境</a><nav class="desktop-nav" aria-label="主导航"><a href="#film">对局演示</a><a href="#report">实验报告</a><a href="#analysis">数据分析</a><a href="#innovation">创新计划</a></nav><div class="header-actions"><a class="header-play" href="./game.html">开始对弈 <span aria-hidden="true">↗</span></a><button class="menu-toggle" id="menu-toggle" type="button" aria-expanded="false" aria-controls="brush-menu"><span>目录</span><span class="menu-glyph" aria-hidden="true"><i></i><i></i></span></button></div></header>
<div id="brush-menu" class="brush-menu" hidden><div class="menu-landscape" aria-hidden="true"></div><div class="brush-menu-panel"><p>五子棋实验</p><nav aria-label="展开导航"><a href="#top" class="active">首页</a><a href="#film">对局演示</a><a href="#report">实验报告</a><a href="#analysis">数据分析</a><a href="#innovation">创新计划</a><a href="./game.html">进入棋局 ↗</a></nav><a class="menu-code" href="https://github.com/Haohaha-11/gomoku-lab" target="_blank" rel="noopener">GitHub 源码 ↗</a></div></div>
<noscript><nav class="no-script-nav" aria-label="章节导航"><a href="#film">对局演示</a><a href="#report">实验报告</a><a href="#analysis">数据分析</a><a href="#innovation">创新计划</a></nav></noscript>
<main>
  <section class="hero" id="top" aria-labelledby="hero-title"><div class="hero-art" aria-hidden="true"></div><div class="hero-content"><p class="hero-kicker"><span></span>实验一 · 人工智能博弈搜索</p><h1 id="hero-title">五子棋<br>博弈搜索实验</h1><p class="hero-lead">极大极小与 Alpha-Beta<br>在同一棋局中，观察搜索与剪枝。</p><div class="hero-actions"><a class="brush-button" href="./game.html">开始对弈 <span aria-hidden="true">↗</span></a><a class="text-link" href="#film">观看演示 <span aria-hidden="true">↓</span></a></div><div class="resource-links"><a href="./downloads/report.pdf" download>实验报告 PDF <span aria-hidden="true">↗</span></a><a href="https://github.com/Haohaha-11/gomoku-lab" target="_blank" rel="noopener">GitHub <span aria-hidden="true">↗</span></a><a href="./downloads/benchmark.csv" download>实验数据 <span aria-hidden="true">↗</span></a></div></div><p class="hero-footnote">Python 实现　·　9 / 13 / 15 路棋盘　·　水墨对弈</p><a class="scroll-cue" href="#film" aria-label="向下阅读"><span></span>向下阅读</a></section>
  <section class="film-section wide-section" id="film" aria-labelledby="film-title"><div class="editorial-heading"><div><p class="section-overline">对局演示</p><h2 id="film-title">一局棋，看见搜索的选择。</h2></div><a class="underlined-link" href="./game.html">自己下一局 <span aria-hidden="true">↗</span></a></div><p class="film-intro">在水墨场景中落子，切换算法与搜索深度，查看候选分数、主变化线和剪枝过程。</p><figure class="film-figure"><video id="demo-video" controls playsinline preload="metadata" poster="./media/gomoku-demo-poster.jpg" aria-label="五子棋真实引擎对局回放"><source src="./media/gomoku-demo.mp4" type="video/mp4">浏览器不支持视频播放。<a href="./media/gomoku-demo.mp4">下载对局回放</a></video><figcaption><span>前七手为预设开局，后续白方落子由实际搜索计算。已加速回放，不作为棋力评测。</span><a href="./media/gomoku-demo.mp4" download>下载录像 ↗</a></figcaption></figure></section>
  <div class="report-intro wide-section" id="report"><div><p class="section-overline">实验报告</p><h2>实现、比较，再解释结果。</h2><p>同一局面、同一评价函数、同一候选集合。<br>比较两种算法的计算成本，以及棋盘大小和搜索深度的影响。</p></div><a class="underlined-link" href="./downloads/report.pdf" download>下载完整 PDF ↗</a></div>
  <div class="evidence-strip wide-section" aria-label="实验结果概览"><div><strong>162</strong><span>次完整搜索测量</span></div><div><strong>81 / 81</strong><span>配对根值与落子一致</span></div><div><strong>70.2<span>%</span></strong><span>总访问节点减少</span></div><p>27 个不同局面与深度组合，各重复 3 次。<br>结论针对共同候选树，不代表全局最优或棋力胜率。</p></div>
  <div class="report-shell"><aside class="report-toc" aria-label="报告目录"><p>报告目录</p><nav id="report-toc">__TOC__</nav><a class="toc-pdf" href="./downloads/report.pdf">PDF 报告 ↗</a></aside><article class="report-content">__BODY__<footer class="report-footer"><p>五子棋博弈搜索实验 · 2026 年 10 月 13 日</p><div><a href="./game.html">进入棋局 ↗</a><a href="https://github.com/Haohaha-11/gomoku-lab" target="_blank" rel="noopener">GitHub ↗</a><a href="#top">回到顶部 ↑</a></div></footer></article></div>
</main><script src="./benchmark-data.js"></script><script src="./site.js"></script></body></html>'''
    rendered = doc.replace('__TOC__',toc).replace('__BODY__','\n'.join(body))
    OUT.write_text('\n'.join(line.rstrip() for line in rendered.splitlines()).rstrip()+'\n',encoding='utf-8')
    print(OUT)


if __name__ == '__main__':
    main()
