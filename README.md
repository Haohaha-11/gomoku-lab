# 弈境 · 五子棋博弈搜索

电子科技大学人工智能实验一：用 Python 实现五子棋的极大极小搜索与 Alpha-Beta 剪枝，比较两者在不同棋盘大小和搜索深度下的性能，并做成一个水墨风格的对弈网页。

- 在线：https://haoceanlab.cn/gomoku/
- 组员：江浩、路仕腾、郭展羽

## 页面

| 地址 | 内容 |
|---|---|
| `/` | 项目主页：对局录像、搜索规模、博弈树示意、实验数据、创新、报告入口 |
| `/game.html` | 对弈：水墨庭院里的 3D 棋盘，可切换算法、深度、棋盘大小，查看候选与搜索树 |
| `/report.html` | 网页版实验报告（课程要求的各部分） |
| `/downloads/report.pdf` | 由网页版报告导出的 PDF |
| `/downloads/benchmark.csv` | 162 次测量的原始数据 |

## 运行

```sh
python server.py --port 8767
```

打开 http://127.0.0.1:8767/ 。服务只依赖 Python 3.10+ 标准库，Three.js 和字体都在 `static/` 里。

规则为自由五子棋：黑先，横竖斜连成五子或以上获胜，无禁手，满盘为和。

## 实验

```sh
python -m unittest discover -s tests -v      # 规则、搜索与接口测试
python scripts/benchmark.py                  # 重新测量，写入 results/
python scripts/export_site_data.py           # 由 results/benchmark.csv 生成 static/data.js
```

两种算法共用同一评价函数、候选生成与走法排序（Negamax 写法），节点数的差别只来自剪枝。81 组配对搜索的根值与落子全部一致；深度 3 时 Alpha-Beta 少访问约 73% 的节点。

## 重新生成素材

以下脚本需要 Playwright 与本机 Chrome，先在另一个终端用 `python server.py --port 8801` 启动服务：

```sh
python scripts/record_demo.py          # 录制对局视频 static/media/gomoku-demo.mp4（需要 ffmpeg）
python scripts/export_report_pdf.py    # 把 report.html 打印成 docs/实验一五子棋实验报告.pdf
python tools/build_fonts.py            # 改动页面笔刷字后，重新子集化字体（需要 fonttools）
```

录像为实时录制：黑棋由脚本调用同一引擎搜索 4 层后用键盘落子，白棋是网页默认设置的 AI（Alpha-Beta，3 层）。

## 目录

```text
engine.py            规则、评价函数、极大极小 / Alpha-Beta、搜索记录
server.py            HTTP 接口、输入校验、反馈保存（SQLite）
static/              主页、对弈页、报告页、样式、Three.js、字体、录像
results/             基准原始数据与汇总
tests/               引擎与接口测试
scripts/             基准、数据导出、录像、PDF、打包、部署、反馈导出
tools/               字体子集化；probe/ 为引擎测速与连续冲四题集
docs/                PDF 报告、创新方案、引擎审查、部署说明
third_party/         评分表来源及许可证
```

部署与回滚见 `docs/deployment.md`。字体为 OFL 授权（马善政楷书、思源宋体），许可证见 `static/fonts/OFL.txt`。
