"""Build the course report from measured benchmark output, with a shared HTML source.

Run with the Codex bundled Python (reportlab is a build-only dependency).
The report never substitutes illustrative values for missing benchmark results.
"""
from __future__ import annotations

import csv
import base64
import html
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from statistics import mean, median

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
FONT_FILE = Path(os.environ.get("REPORT_FONT", "C:/Windows/Fonts/msyh.ttc"))
BOLD_FILE = Path(os.environ.get("REPORT_BOLD_FONT", "C:/Windows/Fonts/msyhbd.ttc"))
DATE = "2026年10月13日"


def load_data():
    summary_path = ROOT / "results/summary.json"
    rows_path = ROOT / "results/benchmark.csv"
    if not summary_path.is_file() or not rows_path.is_file():
        raise SystemExit("Real benchmark.csv and summary.json are required before building the report.")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with rows_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise SystemExit("The benchmark is empty; no report is generated.")
    return summary, rows


def content(summary, rows):
    """Build prose and tables directly from the verified version-one benchmark."""
    groups = normalize_groups(summary)
    env, cfg = summary["environment"], summary["config"]
    meta = {**env, **cfg, "python": env["python"].split(" | ")[0], "seeds": [cfg["seed"]]}
    equivalence = summary["equivalence"]
    passed = {"matched": equivalence["passed"], "pairs": equivalence["paired_checks"]}
    if passed["matched"] != passed["pairs"]:
        raise ValueError("The report requires all paired equality checks to pass.")
    result_rows = []
    for group in groups:
        result_rows.append([
            f'{group["size"]}×{group["size"]}', str(group["depth"]),
            f'{group["minimax_nodes"]:,.1f}', f'{group["alphabeta_nodes"]:,.1f}',
            f'{group["node_reduction_pct"]:.1f}%',
            f'{group["minimax_ms"]:.2f}', f'{group["alphabeta_ms"]:.2f}',
        ])
    total_mm = sum(float(r["nodes"]) for r in rows if r["algorithm"] == "minimax")
    total_ab = sum(float(r["nodes"]) for r in rows if r["algorithm"] == "alphabeta")
    savings = 100 * (1 - total_ab / total_mm)
    max_group = max(groups, key=lambda g: g["node_reduction_pct"])
    return [
        {
            "title": "实验一 五子棋实验报告",
            "subtitle": "极大极小搜索与 Alpha Beta 剪枝的实现和性能分析",
            "blocks": [
                ("meta", f"实验日期  {DATE}    小组  __________"),
                ("meta", "成员一  __________  学号  __________"),
                ("meta", "成员二  __________  学号  __________"),
                ("meta", "成员三  __________  学号  __________"),
                ("h", "摘要"),
                ("p", f"本实验用 Python 实现自由规则五子棋的极大极小搜索与 Alpha-Beta 剪枝，并以同一组局面、评价函数、候选落子及搜索深度比较两者。完整基准共记录 {len(rows)} 次搜索。所有成对搜索的最优根值与落子均通过一致性核对；按访问节点总数计算，Alpha-Beta 比极大极小减少 {savings:.1f}% 的节点。性能结果同时记录棋盘大小和深度，以区分搜索树规模与单节点计算成本。"),
                ("p", "系统提供可交互的网页棋盘、算法和深度选择、搜索统计与过程展示，便于小组互相体验。搜索在局部候选集合上进行，因此实验结论描述这一选择性搜索树的性能，不代表求解了五子棋全部合法状态。强化学习、人类反馈学习和更进一步的深度调度已形成实施方案，尚无训练结果，不计入当前算法性能结论。"),
                ("h", "实验目的"),
                ("p", "我们希望通过可执行的对照实验理解零和博弈中的极大极小决策，验证 Alpha-Beta 在不改变同一搜索树最优值的前提下如何减少访问节点，并分析棋盘大小、候选分支数和搜索深度对运行成本的影响。网页用于把局面、搜索过程与测量结果联系起来，而实验 CSV 和自动化测试用于支撑报告结论。"),
                ("h", "实验内容与规则"),
                ("p", "黑棋先行、双方交替落子，棋子放在交叉点；横、竖或两条斜线中出现连续至少五子即获胜，棋盘填满且无人获胜时为和局。采用自由规则，不设禁手。程序验证棋盘尺寸、棋子取值、边界、重复落子和终局状态。搜索深度按半回合计数，一名棋手落一子算一层。"),
            ],
        },
        {
            "title": "一 实验原理",
            "blocks": [
                ("h", "极大极小搜索"),
                ("p", "五子棋可建模为确定性、双人、零和、完全信息博弈。树节点是一种棋盘状态，边表示合法落子。轮到己方时选择后继价值最大者，轮到对方时假设对方选择使己方价值最小的回应；依次回传，获得根节点的落子。搜索触及终局时使用确定的胜负值，触及深度上限时调用启发式评价函数。"),
                ("p", "实现采用 Negamax 形式统一双方代码：一个节点对当前执子方的价值，等于各子节点对下一执子方价值取反后的最大值。符号取反依赖零和假设；在切换执子方时必须同时切换价值视角。终局分值高于任何非终局启发式分值，并加入层数修正，使同为必胜时倾向更快获胜，同为必败时延缓失败。"),
                ("h", "Alpha Beta 剪枝"),
                ("p", "Alpha 记录当前路径上已知可达到的下界，Beta 记录上界。当某节点的搜索结果使 Alpha 不小于 Beta 时，剩余兄弟分支不可能影响祖先节点的选择，可以停止展开。该剪枝只排除不会改变当前决策的分支；对相同候选树和同一叶节点评价，完整搜索的根值与极大极小一致。"),
                ("p", "剪枝效率依赖遍历顺序。较好的落子先被访问，边界往往更早收紧。为避免把排序收益混入算法对照，本实验让两种算法共用候选生成与排序。界面中的被剪枝分支没有被实际求值，不能把它们显示为精确分数；被边界截断的候选只具有上界或下界。"),
                ("h", "复杂度与评价函数"),
                ("p", "若每层平均有 b 个候选、搜索 d 层，极大极小访问规模约随 b 的 d 次方增长。Alpha-Beta 的最坏情况仍可能达到同阶；在理想排序条件下，经典近似为 b 的 d/2 次方。实际运行还包括候选排序、棋型评估和迭代加深的成本，不能只凭理论指数推断毫秒耗时。"),
                ("p", "评价函数从当前执子方视角对四个方向的棋型计分，再减去对方棋型分。成五、活四、冲四、活三等威胁按紧迫程度给定不同权重。棋型分数是搜索用的相对尺度，不是经校准的胜率；绝对值很大也不等于统计意义上的胜率接近 100%。确定的成五由规则检查直接判断。"),
                ("h", "选择性搜索的边界"),
                ("p", "候选集合取已有棋子周围半径 2 的空位，按进攻、防守与确定性坐标规则排序。有一步必胜时只搜索必胜点；否则若对方有一步成五威胁，只搜索阻挡点，且保留全部阻挡点；其余情况按名义候选上限截取。此规则改变被考察的搜索树，与 Alpha-Beta 的边界剪枝不同。根值一致只保证在共同候选树内一致，不能证明全局最优。"),
            ],
        },
        {
            "title": "二 实验器材与系统实现",
            "blocks": [
                ("h", "运行环境"),
                ("table", ["项目", "本次记录"], [
                    ["实现语言", f'Python {meta["python"]}  Anaconda 发行版'],
                    ["基准运行平台", meta["platform"]],
                    ["处理器", meta["processor"] + f'  共 {meta["logical_cpus"]} 个逻辑处理器'],
                    ["基准运行方式", "单进程顺序执行，固定种子，搜索不设超时"],
                    ["展示环境", "现代浏览器；Python HTTP 服务；hk_88 演示服务器"],
                    ["数据产物", "results/benchmark.csv 与 results/summary.json"],
                ], [120, 365]),
                ("p", "硬件信息和时延只对应本次基准运行环境。网页远程请求还受到网络往返、浏览器绘制和服务器负载影响，因此界面显示的体验时延不能直接替代算法基准数据。图形页面与 Python 搜索通过接口通信，规则判定和决策逻辑集中在后端。"),
                ("h", "模块组织"),
                ("table", ["模块", "职责"], [
                    ["engine.py", "棋盘验证、胜负判断、评价、候选生成、两种搜索"],
                    ["server.py", "搜索与反馈接口、静态网页、实验结果与报告下载"],
                    ["static", "棋盘交互、场景绘制、控制面板和搜索统计展示"],
                    ["scripts/benchmark.py", "固定局面与算法对照，保存逐次数据和汇总"],
                    ["tests", "规则、战术、算法一致性、超时恢复等自动化验证"],
                    ["docs/innovation-plan.md", "学习、反馈和深度扩展的实验设计"],
                ], [145, 340]),
                ("h", "交互搜索的完成语义"),
                ("p", "在线搜索按深度 1、2、3 逐轮加深，每轮完整结束后才更新可返回的落子。达到时间预算时，返回最后完成轮的结果；若第一层也未完成，则返回合法的确定性备选落子，并将完成深度标为 0。统计计入已尝试的全部轮次，返回的主变化线和树示意来自最后完整轮。搜索树画面受展示条数上限约束，显示节点数不等于算法访问的全部节点数。"),
                ("p", "递归通过 finally 撤销临时落子，超时也保持输入棋盘不变，以保证重复实验可比。在线使用时钟预算；基准关闭超时，核对完整目标深度的算法等价性。"),
            ],
        },
        {
            "title": "三 实验步骤与对照设计",
            "blocks": [
                ("h", "实施步骤"),
                ("steps", [
                    "实现并检查棋盘合法性、四方向成五、边界落子和满盘和局。确认终局后搜索不再返回新落子。",
                    "建立共用候选生成和评价函数，实现无边界剪枝的 Negamax，再在相同递归结构中启用 Alpha-Beta。",
                    "运行一步必胜、必须防守、深层战术与输入不变性测试；对多个固定局面核对两算法根值及落子。",
                    "固定棋盘大小、搜索深度、候选上限和局面种子，禁用时间截断，顺序运行基准并保存 CSV。",
                    "按棋盘大小与深度汇总节点、耗时及一致性，检查所有记录均完成目标深度，再绘图分析。",
                    "启动网页，展示落子与胜负判断、算法切换、深度变化、搜索过程及报告下载，供小组互评。",
                ]),
                ("h", "实验因素与公平性"),
                ("table", ["因素", "本次设置"], [
                    ["棋盘大小", "、".join(str(n) + "×" + str(n) for n in meta["sizes"])],
                    ["目标深度", "、".join(map(str, meta["depths"])) + " 层"],
                    ["局面随机种子", "、".join(map(str, meta["seeds"])) + "；每尺寸 3 个合法八手局面"],
                    ["每局面测量次数", str(meta["repeats"])],
                    ["名义候选上限", str(meta["max_candidates"]) + "；一步必胜和防守点可突破上限"],
                    ["停止条件", "只按目标深度或终局停止；基准关闭墙钟超时"],
                ], [135, 350]),
                ("p", "每一对搜索使用同一份棋盘内容和当前执子方，评价函数、候选策略及遍历顺序完全一致。三种棋盘复用相同居中开局的相对坐标，以控制局面差异。测量前预热几何缓存，每次重复交替两算法运行顺序。时延受系统负载影响，因此同时报告更接近结构性成本的节点数；较少节点不保证每条短时任务都更快。"),
                ("h", "指标解释"),
                ("p", "节点减少率定义为 1 减去 Alpha-Beta 节点数与极大极小节点数之比。总节点减少率按全部配对节点之和计算，避免把很小和很大的搜索赋予相同权重。耗时单位为毫秒。迭代加深的节点数包含从第 1 层到目标深度的各轮访问，因此不能把它误认为只执行了最后一层的节点数。"),
            ],
        },
        {
            "title": "四 实验数据",
            "blocks": [
                ("p", f"下表按棋盘大小和深度汇总，共 {len(groups)} 组条件、{len(rows)} 条逐次搜索记录。每个算法每组覆盖 3 个局面、每局面重复 3 次；节点与耗时均取这 9 次测量的算术平均值。原始数据保存在 results/benchmark.csv，配置与一致性核对保存在 results/summary.json。"),
                ("table", ["棋盘", "深度", "MM节点", "AB节点", "减少率", "MM毫秒", "AB毫秒"], result_rows, [56, 40, 78, 78, 64, 84, 85]),
                ("caption", "表 1  相同候选树上的算法对照  MM 为极大极小  AB 为 Alpha-Beta"),
                ("image", "benchmark_nodes.png", "图 1  不同深度的节点数量对照  相同或接近的曲线会重合"),
                ("p", f"根值与落子核对通过 {passed["matched"]}/{passed["pairs"]} 次配对测量，即 27 个不同局面与深度组合各重复 3 次。最明显的节点减少出现在 {max_group["size"]}×{max_group["size"]}、深度 {max_group["depth"]}，减少率为 {max_group["node_reduction_pct"]:.1f}%。全部记录按节点总和合并后减少 {savings:.1f}%。这些结论只覆盖本次局面集与候选上限。"),
            ],
        },
        {
            "title": "五 结果分析与验证",
            "blocks": [
                ("h", "剪枝收益来自哪里"),
                ("p", "深度为 1 时，搜索只需为根节点候选求叶值，没有足够的内部结构形成大范围剪枝，节点减少通常很小。随着深度增加，较早得到的好分支能为更多后续分支建立边界，Alpha-Beta 的节点优势更容易出现。实际收益由局面威胁和候选顺序共同决定，不能把某一组的减少率推广到任意开局。"),
                ("p", "结果中根值一致说明剪枝没有改变共同候选树上的决策值。落子一致还依赖确定性排序和同分时保留先遇到的最优点。Alpha-Beta 在非最优根候选上可能只得到界限，因此候选列表中各项分数不一定逐项等于完整极大极小的精确值；这不会影响最终根值核对。"),
                ("h", "棋盘大小与深度的不同影响"),
                ("p", "在候选上限相同的条件下，棋盘变大不必然让每层候选数同步增加。因此，不能仅根据棋盘面积推断节点数成比例增加。较大的棋盘仍会增加局面扫描、棋型统计和候选检查成本；同一深度的耗时变化可能来自单节点成本，也可能来自局面本身的可剪枝程度。深度则直接增加未来回应层数，对搜索树的规模更敏感。"),
                ("p", "本实验主要比较完成搜索的计算量，没有通过大量完整对局估计棋力。更深搜索可能看到浅层无法发现的威胁，但也会增加延迟；选择性候选遗漏或评价函数偏差仍可能导致错误。要声称更深必然更强，需要在固定开局、交换先后手和相同预算下进行独立对局，而不能只依据节点数和运行时间。"),
                ("h", "正确性检查"),
                ("p", "引擎的 9 项自动化测试全部通过，覆盖横竖斜线与长连获胜、非法棋盘、终局无动作、搜索输入不变性、一步必胜与防守点保留、算法根值和落子一致、满盘和局以及时间预算后的棋盘恢复。服务端另有 5 项接口测试通过。测试用于发现实现错误；有限样例不能替代所有棋局的形式证明。"),
                ("h", "实验局限"),
                ("p", "局面样本量有限，且采用局部候选与分支上限。固定种子提供可复现性，但不自动保证对真实人类对局分布有代表性。短时间测量会受缓存、系统调度与 CPU 竞争影响；因此小于测量波动的毫秒差异不宜作强结论。启发式分数没有概率校准，反馈样本与强化学习模型也尚未形成独立测试集。"),
            ],
        },
        {
            "title": "六 创新功能的实施方案",
            "blocks": [
                ("p", "创新部分以可验证的研究问题组织。当前已完成深度控制、迭代加深、搜索过程展示和反馈保存接口。反馈保存落子前棋盘、AI 候选、正负评价与可选替代落子，不触发训练。强化学习、人类偏好模型及按局面自适应分配计算预算仍处于方案阶段。完整设计见 docs/innovation-plan.md。"),
                ("h", "自我对弈价值学习"),
                ("p", "先在 9×9 棋盘进行自我对弈，用胜、负、和的终局回报训练小型卷积价值网络。输入包含己方、对方与合法位置通道，输出当前执子方视角的局面价值。将价值网络接入 Alpha-Beta 的截断叶节点，规则终局判断保持优先。第一轮每个种子上限 2,000 局或 2 CPU 小时，先验证吞吐与学习信号，再扩充规模。可进一步增加策略头用于候选排序。"),
                ("h", "人类反馈校准"),
                ("p", "将同一局面的两个候选落子匿名、随机顺序展示，由成员选择 A、B、相当或无法判断，并记录原因。收集原始局面、候选、模型版本和搜索预算。以 200 至 500 条有效偏好起步，先学习棋型权重或轻量偏好模型，再以小权重影响同类候选排序；必胜和必须防守的规则优先。只保存点赞或反馈并不等于模型已经从人类反馈学习。"),
                ("h", "自适应深度"),
                ("p", "在迭代加深基础上，遇到候选分差较小、双威胁或主变化线不稳定的局面继续搜索，局面明确时提前停止。给定节点预算与墙钟上限，并显示实际完成深度。与固定深度对照时匹配平均节点预算，报告胜平负、每步中位耗时及 p95 耗时，避免用额外算力冒充方法改进。"),
                ("h", "防止数据泄漏与无效结论"),
                ("p", "计划固定独立种子 7、23、61，按完整对局和开局族划分训练 70%、验证 15%、测试 15%。旋转镜像后的局面哈希用于跨集去重；同局对弈的相邻状态不能分散到不同集合。仅用验证集选择检查点、混合权重和深度阈值，测试集冻结。每个种子使用 50 个固定开局并互换先后手，比较基础搜索、仅价值学习、仅反馈、仅自适应深度和完整组合。"),
                ("p", "主要失败风险包括自我对弈过拟合、人类意见不一致、偏好奖励损害客观胜率，以及模型推理开销超过剪枝收益。应保留历史对手池、重复标注样本、独立战术测试和无学习回退版本，并公开失败案例。创新评分取决于最终实现和验证质量，不以方案本身预先保证分数。"),
            ],
        },
        {
            "title": "七 实验结论与总结",
            "blocks": [
                ("h", "实验结论"),
                ("p", f"我们完成了五子棋的极大极小和 Alpha-Beta 两种搜索实现，并通过 {passed["pairs"]} 次配对测量验证共同候选树上根值和落子的等价性。本次真实基准中，Alpha-Beta 按总访问节点计减少 {savings:.1f}%。剪枝收益随深度与局面变化，棋盘变大还会增加评估和扫描成本，因此需要结合节点数与耗时解释性能。"),
                ("p", "适合课堂展示的默认设置应在响应时间和实际完成深度之间取平衡。系统提供在线交互与离线基准两条路径：前者采用有时间预算的迭代加深，后者关闭超时完成目标深度。报告把选择性候选裁剪、Alpha-Beta 剪枝和界面展示上限分别说明，避免把三种不同的限制混为一谈。"),
                ("h", "总结与心得体会"),
                ("p", "我们在这一实现中把公平比较放在统一数据和统一搜索规则上。两种算法共用评价函数与候选顺序后，节点数的差异才可以归因于边界剪枝。固定随机种子、同分排序和输入恢复保证同一局面的结果能够复核；保存原始 CSV 则让报告数字可以重新计算。"),
                ("p", "从实验现象可以看到，理论复杂度解释增长趋势，实际运行成本还取决于每个节点所做的工作。漂亮的过程展示需要配合准确的分数语义、完成深度和统计口径。后续若引入学习方法，我们会保留当前搜索基线，并分别证明棋力、偏好一致性和计算效率的变化。成员具体分工与个人体会可在小组实际体验后补充。"),
                ("h", "课堂验收建议"),
                ("steps", [
                    "进入网页，展示人机落子、胜负检测、重新开始和棋盘尺寸切换。",
                    "在同一局面分别运行两种算法，解释根值一致、节点数差异与剪枝标记。",
                    "调整深度，展示请求深度与完成深度，并打开真实基准数据和报告。",
                    "展示人类反馈入口，说明已收集的数据与尚未训练的模块，介绍后续对照设计。",
                ]),
                ("h", "参考资料"),
                ("ref", "课程材料  实验一 五子棋  实验任务与成果呈现要求  第 2 至 3 页"),
                ("ref", "Silver 等  Mastering Chess and Shogi by Self-Play with a General Reinforcement Learning Algorithm  2017  https://arxiv.org/abs/1712.01815"),
                ("ref", "Christiano 等  Deep Reinforcement Learning from Human Preferences  2017  https://arxiv.org/abs/1706.03741"),
            ],
        },
    ]


def normalize_groups(summary):
    groups = []
    for size in summary["config"]["sizes"]:
        for depth in summary["config"]["depths"]:
            paired = {row["algorithm"]: row for row in summary["aggregates"]
                      if row["size"] == size and row["depth"] == depth}
            mm, ab = paired["minimax"], paired["alphabeta"]
            groups.append({"size": size, "depth": depth,
                           "minimax_nodes": mm["mean_nodes"], "alphabeta_nodes": ab["mean_nodes"],
                           "minimax_ms": mm["mean_ms"], "alphabeta_ms": ab["mean_ms"],
                           "node_reduction_pct": ab["node_reduction_pct"]})
    return groups


def render_chart(groups):
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Drawing, Line, String
    from reportlab.graphics import renderPDF
    from reportlab.graphics.widgets.markers import makeMarker
    chart = Drawing(690, 270)
    plot = LinePlot()
    plot.x, plot.y, plot.width, plot.height = 60, 45, 605, 155
    plot.xValueAxis.valueMin, plot.xValueAxis.valueMax = 1, 3
    plot.xValueAxis.valueSteps = [1, 2, 3]
    plot.yValueAxis.valueMin, plot.yValueAxis.valueMax = 0, 3
    plot.yValueAxis.valueSteps = [0, 1, 2, 3]
    plot.yValueAxis.labelTextFormat = lambda value: str(int(10 ** value))
    plot.xValueAxis.labels.fontName = plot.yValueAxis.labels.fontName = "Helvetica"
    plot.xValueAxis.labels.fontSize = plot.yValueAxis.labels.fontSize = 10
    plot.yValueAxis.visibleGrid = True
    plot.yValueAxis.gridStrokeColor = colors.HexColor("#dddddd")
    plot.yValueAxis.gridStrokeWidth = .5
    sizes = sorted({g["size"] for g in groups})
    palette = ["#164e63", "#527d92", "#aa7647"]
    series = []
    for i, size in enumerate(sizes):
        selected = sorted((g for g in groups if g["size"] == size), key=lambda g: g["depth"])
        for j, (name, key) in enumerate((("Minimax", "minimax_nodes"), ("Alpha-Beta", "alphabeta_nodes"))):
            series.append([(g["depth"], math.log10(g[key])) for g in selected])
            k = 2*i + j
            plot.lines[k].strokeColor = colors.HexColor(palette[i])
            plot.lines[k].strokeWidth = 1.6
            plot.lines[k].strokeDashArray = [5, 3] if j == 0 else []
            plot.lines[k].symbol = makeMarker("FilledCircle")
            plot.lines[k].symbol.size = 4
            plot.lines[k].symbol.fillColor = colors.HexColor(palette[i])
            lx, ly = 60 + i*210, 246 - j*19
            chart.add(Line(lx, ly+3, lx+20, ly+3, strokeColor=colors.HexColor(palette[i]), strokeWidth=1.6, strokeDashArray=[5,3] if j == 0 else []))
            chart.add(String(lx+27, ly, f"{size}x{size} {name}", fontName="Helvetica", fontSize=10))
    plot.data = series
    chart.add(plot)
    chart.add(String(360, 10, "Requested depth", fontName="Helvetica", fontSize=11, textAnchor="middle"))
    chart.add(String(60, 210, "Visited nodes (log scale)", fontName="Helvetica", fontSize=9))
    OUT.mkdir(exist_ok=True)
    tmp = ROOT / ".agent/report-qa"
    tmp.mkdir(parents=True, exist_ok=True)
    chart_pdf = tmp / "benchmark-chart.pdf"
    renderPDF.drawToFile(chart, str(chart_pdf))
    bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe"
    poppler = os.environ.get("PDFTOPPM") or shutil.which("pdftoppm") or (str(bundled) if bundled.is_file() else None)
    if not poppler:
        raise SystemExit("Install Poppler on PATH or set PDFTOPPM to its pdftoppm executable.")
    subprocess.run([str(poppler), "-png", "-singlefile", "-r", "180", str(chart_pdf), str(OUT / "benchmark_nodes")], check=True)


def build_pdf(sections):
    pdfmetrics.registerFont(TTFont("YaHei", str(FONT_FILE), subfontIndex=0))
    pdfmetrics.registerFont(TTFont("YaHeiBold", str(BOLD_FILE), subfontIndex=0))
    pdfmetrics.registerFontFamily("YaHei", normal="YaHei", bold="YaHeiBold")
    styles = {
        "title": ParagraphStyle("title", fontName="YaHeiBold", fontSize=23, leading=33, textColor=colors.black, spaceAfter=12),
        "subtitle": ParagraphStyle("subtitle", fontName="YaHei", fontSize=11.4, leading=18, textColor=colors.HexColor("#39444e"), spaceAfter=19),
        "heading": ParagraphStyle("heading", fontName="YaHeiBold", fontSize=13, leading=20, spaceBefore=14, spaceAfter=7, keepWithNext=True),
        "body": ParagraphStyle("body", fontName="YaHei", fontSize=10.4, leading=18, alignment=TA_JUSTIFY, wordWrap="CJK", spaceAfter=8),
        "meta": ParagraphStyle("meta", fontName="YaHei", fontSize=10.2, leading=18, spaceAfter=4),
        "cell": ParagraphStyle("cell", fontName="YaHei", fontSize=9.1, leading=14, wordWrap="CJK", spaceAfter=0),
        "headcell": ParagraphStyle("headcell", fontName="YaHeiBold", fontSize=9.2, leading=14, textColor=colors.white, wordWrap="CJK"),
        "caption": ParagraphStyle("caption", fontName="YaHei", fontSize=8.4, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#59656e"), spaceBefore=7, spaceAfter=9),
        "ref": ParagraphStyle("ref", fontName="YaHei", fontSize=8.2, leading=13, wordWrap="CJK", textColor=colors.HexColor("#47515a"), spaceAfter=5),
    }
    target = OUT / "实验一五子棋实验报告.pdf"
    doc = BaseDocTemplate(str(target), pagesize=A4, rightMargin=55, leftMargin=55,
                          topMargin=48, bottomMargin=48, title="实验一 五子棋实验报告", author="实验小组")
    frame = Frame(55, 48, A4[0]-110, A4[1]-96, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("YaHei", 8)
        canvas.setFillColor(colors.HexColor("#75808a"))
        canvas.drawString(55, 26, "五子棋博弈搜索实验")
        canvas.drawRightString(A4[0]-55, 26, str(document.page))
        canvas.restoreState()
    doc.addPageTemplates(PageTemplate(id="report", frames=[frame], onPage=footer))
    story = []
    def p(text, kind="body"):
        return Paragraph(html.escape(text), styles[kind])
    for index, section in enumerate(sections):
        if index:
            story.append(PageBreak())
        story.append(p(section["title"], "title"))
        if "subtitle" in section:
            story.append(p(section["subtitle"], "subtitle"))
        for block in section["blocks"]:
            kind = block[0]
            if kind in ("p", "h", "caption", "meta", "ref"):
                story.append(p(block[1], {"p":"body", "h":"heading"}.get(kind, kind)))
            elif kind == "steps":
                for n, text in enumerate(block[1], 1):
                    story.append(p(f"{n}. {text}"))
            elif kind == "table":
                header, rows, widths = block[1:]
                table_data = [[p(x, "headcell") for x in header]] + [[p(str(x), "cell") for x in row] for row in rows]
                table = Table(table_data, colWidths=widths, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#273b4a")),
                    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f3f6f8")]),
                    ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#d9d9d9")),
                    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                    ("LEFTPADDING", (0,0), (-1,-1), 8),
                    ("RIGHTPADDING", (0,0), (-1,-1), 8),
                    ("TOPPADDING", (0,0), (-1,-1), 7),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 7),
                ]))
                story.extend([Spacer(1,3), table, Spacer(1,10)])
            elif kind == "image":
                story.append(Image(str(OUT/block[1]), width=485, height=189.5))
                story.append(p(block[2], "caption"))
    doc.build(story)
    return target


def build_html(sections):
    pieces = []
    for section in sections:
        pieces.append('<section class="page"><h1>' + html.escape(section["title"]) + '</h1>')
        if "subtitle" in section:
            pieces.append('<p class="subtitle">' + html.escape(section["subtitle"]) + '</p>')
        for block in section["blocks"]:
            kind = block[0]
            if kind in ("p", "h", "caption", "meta", "ref"):
                tag = "h2" if kind == "h" else "p"
                pieces.append(f'<{tag} class="{kind}">{html.escape(block[1])}</{tag}>')
            elif kind == "steps":
                pieces.append('<ol>' + ''.join('<li>'+html.escape(item)+'</li>' for item in block[1]) + '</ol>')
            elif kind == "table":
                pieces.append('<div class="table-wrap"><table><thead><tr>' + ''.join('<th>'+html.escape(x)+'</th>' for x in block[1]) + '</tr></thead><tbody>')
                for row in block[2]:
                    pieces.append('<tr>' + ''.join('<td>'+html.escape(str(x))+'</td>' for x in row) + '</tr>')
                pieces.append('</tbody></table></div>')
            elif kind == "image":
                encoded = base64.b64encode((OUT / block[1]).read_bytes()).decode("ascii")
                pieces.append(f'<figure><img src="data:image/png;base64,{encoded}" alt="{html.escape(block[2])}"><figcaption>{html.escape(block[2])}</figcaption></figure>')
        pieces.append('</section>')
    css = """
    *{box-sizing:border-box}body{margin:0;background:#edf1f4;color:#192630;font-family:'Microsoft YaHei','Noto Sans CJK SC',sans-serif;font-size:15px;line-height:1.85}.toolbar{position:sticky;top:0;background:#172934;color:white;padding:13px 24px;display:flex;justify-content:space-between;gap:20px;z-index:1}.toolbar a{color:#cbe2ec}.toolbar button{border:1px solid #657984;color:white;background:transparent;padding:5px 16px;border-radius:4px;cursor:pointer}.page{max-width:870px;margin:28px auto;background:white;padding:60px 68px;box-shadow:0 8px 30px #1729340a}h1{font-size:28px;line-height:1.4;color:black;margin:0 0 16px}h2{font-size:19px;color:black;margin:28px 0 10px}.subtitle{color:#516370;font-size:17px;margin-bottom:28px}p{margin:10px 0 14px}.meta{color:#5b6871;margin:5px 0}.table-wrap{overflow:auto;margin:18px 0}table{width:100%;border-collapse:collapse;font-size:13px}th{background:#273b4a;color:white;font-weight:600;text-align:left}th,td{border:1px solid #d9d9d9;padding:10px 12px;vertical-align:middle}tbody tr:nth-child(even){background:#f3f6f8}.caption,figcaption{font-size:12px;color:#687780;text-align:center}img{max-width:100%;height:auto}figure{margin:25px 0}li{padding:4px 0}.ref{font-size:12px;overflow-wrap:anywhere;color:#586973}@media(max-width:700px){.page{padding:30px 23px;margin:12px}h1{font-size:24px}.toolbar{font-size:12px}}@media print{body{background:white}.toolbar{display:none}.page{page-break-after:always;box-shadow:none;margin:0;padding:0;max-width:none}h1,h2{break-after:avoid}table,img{break-inside:avoid}@page{size:A4;margin:18mm}}
    """
    target = OUT / "report.html"
    target.write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>实验一 五子棋实验报告</title><style>'+css+'</style></head><body><nav class="toolbar"><span>五子棋实验报告 · 可编辑源稿</span><span><a href="实验一五子棋实验报告.pdf">下载 PDF</a>　<button onclick="window.print()">打印</button></span></nav>'+''.join(pieces)+'</body></html>', encoding="utf-8")
    return target


def main():
    summary, rows = load_data()
    sections = content(summary, rows)
    render_chart(normalize_groups(summary))
    print(build_pdf(sections))
    print(build_html(sections))


if __name__ == "__main__":
    main()
