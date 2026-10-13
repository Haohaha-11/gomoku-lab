# 弈境 五子棋博弈搜索实验

Python 五子棋引擎、连续滚动的项目展示页、立体水墨对局、可复现实验与课程报告。展示首页包含对局录像、完整网页版报告、实测图表与资源下载；独立游戏页的棋盘和棋子由 Three.js 实时绘制，山水与对面的侠客是背景画面，落子会调用 Python 搜索服务。

## 页面组织

- `/`：项目首页，朱砂笔触目录、对局演示录像、完整实验报告与数据分析。顶部菜单和左侧报告目录支持章节跳转。
- `/game.html`：独立对局页面，保留清晰棋盘、对弈控制和搜索信息。
- 获胜时，墨迹沿五子连线方向贯穿棋盘，再沉淀为细墨胜线；悔棋和重开会清除效果，系统减少动态效果设置下直接显示静态胜线。
- 首页的数据区可切换 9×9、13×13、15×15；节点图与耗时图均来自 `results/summary.json`。耗时误差线为九次测量的样本标准差，不是置信区间。
- `static/figures/` 为离线可用的 SVG 图，`static/benchmark-data.js` 为同源汇总数据。关闭 JavaScript 后，默认图、完整表格和报告正文仍可阅读。
- `scripts/render_site_figures.mjs` 从真实测量生成图表，`scripts/build_site.py` 从已验证报告内容生成首页。首页样式和交互分别位于 `static/site.css` 与 `static/site.js`。

## 开始使用

```sh
python server.py --port 8767
```

访问 http://127.0.0.1:8767/ 。需要 Python 3.10+，运行服务不需要 pip 依赖。在线演示部署于 https://haoceanlab.cn/gomoku/ 。

公开源码仓库：https://github.com/Haohaha-11/gomoku-lab 。

规则：黑棋先手，交替落子；横、竖、两种斜向连续五子或以上获胜；无禁手，满盘无人胜为和棋。支持 9×9、13×13、15×15，人机与本地双人、悔棋、提示、手数、候选热区和棋谱导出。

## 课堂演示顺序

1. 开启 13×13 人机对局，执黑落子。观察 AI 应答与本轮节点、耗时、完成深度。
2. 切换 Minimax / Alpha-Beta 或深度，使用提示查看推荐落点。打开博弈树，讲解主变化线与剪枝记录。
3. 返回展示首页的数据分析章节，查看同一局面、同一深度的真实对照数据和完整报告。现场交互有时间预算，报告基准关闭超时，二者口径不同。
4. 记录一次认可或改进反馈，说明它目前只保存数据；回到首页的创新计划章节，说明自我对弈、偏好模型和自适应深度的实施与验证路线。

## 实验与测试

```sh
python -m unittest discover -s tests -v
python scripts/benchmark.py
```

基准使用种子 20261013、3 种棋盘、3 个深度、3 个固定合法开局、3 次重复和两种算法，共 162 次测量。原始记录为 `results/benchmark.csv`，环境、完整局面、汇总与源码哈希为 `results/summary.json`。所有 81 次配对都检查评分与落点一致。

两种算法共享相同评分、候选生成和走法排序；搜索实现使用零和游戏等价的 Negamax 形式。普通局面采用半径 2 邻域及候选上限，立即胜点与强制堵点优先。它们在相同选择性搜索树上等价，不代表枚举全棋盘的完全搜索。网页默认 cap=10，基准 cap=8。

节点与耗时累计迭代加深的全部尝试，落点与候选评分来自最后完成的深度。超时可能只完成请求深度的一部分；完成深度为 0 时为合法回退走法。候选评分里的上界不是精确值，也不是获胜概率。搜索树显示最多 320 项，不改变搜索本身。

## 报告与创新

- `docs/实验一五子棋实验报告.pdf`：8 页正式报告，小组成员与学号留空供填写。
- `docs/report.html`：自包含可编辑源稿。
- `docs/innovation-plan.md`：强化学习、人类偏好与深度的实施规划。
- `scripts/build_report.py`：由真实基准生成报告，需要报告生成环境中的 ReportLab、中文字体与 Poppler。

报告生成器默认使用 Windows 微软雅黑；其他环境可通过 `REPORT_FONT`、`REPORT_BOLD_FONT` 指定支持中文的 TrueType 字体，通过 `PDFTOPPM` 指定 Poppler 可执行文件。网页、对弈服务和已生成报告的使用不依赖这些构建工具。

当前没有训练好的强化学习或偏好模型。反馈进入 SQLite，标记为未经核验的人类提交；不会在线改变 AI。收集、人工核验、训练和独立测试是后续不同阶段。

## 对局录像

`static/media/gomoku-demo.mp4` 是 33.3 秒、1280×800 的真实网页渲染回放。前七手为预设合法开局，之后黑方按示例棋谱落子、白方由 Python Alpha-Beta 搜索计算，展示堵四与斜线成五；播放节奏经过加速，不作为棋力评测。

`demo-game.json` 保存每手局面、搜索结果及实测耗时，`demo-provenance.json` 保存文件哈希与编码信息。需要重录时，执行 `python scripts/make_demo_game.py` 生成棋谱，运行 `python scripts/make_demo_receiver.py` 并在浏览器打开它打印的本机地址；录制结束后，以 PATH 中的 FFmpeg 运行 `python scripts/make_demo_video.py`。本机接收器仅绑定 loopback，不用于公开部署。录制临时文件与运行反馈均不进入 Git。

## 文件结构

```text
engine.py              规则、评分、Minimax / Alpha-Beta、搜索记录
server.py              HTTP 接口、输入校验、SQLite 反馈保存
static/index.html      项目展示首页和完整网页版报告
static/game.html       立体水墨对局
static/site.css/js     展示页样式与导航、图表选择
static/figures/        真实测量生成的 SVG 图表
static/media/          对局录像、封面与示例棋谱
static/vendor/         本地 Three.js
third_party/           实际使用的评分表及许可证
tests/                 引擎与 API 测试
scripts/               基准、报告、打包、部署、反馈导出
results/               原始 CSV 和完整 JSON 汇总
docs/                  报告、创新方案与部署说明
```

部署、更新、回滚和反馈导出见 `docs/deployment.md`。`python scripts/package.py` 生成本机源码交付包；运行数据、反馈和内部 QA 文件不进入源码包。第三方组件许可证位于 `third_party/` 与 `static/vendor/`。
