# 运行与部署

## 本机

```sh
python -m gomoku.server --port 8767
```

`/` 为主页，`/game.html` 为对弈，`/report.html` 为网页版报告。服务只用 Python 标准库；反馈默认写入 `data/feedback.sqlite3`（可用环境变量 `GOMOKU_DATA_DIR` 指定，已被 Git 忽略）。

## hk_88（haoceanlab.cn/gomoku/）

| 项目 | 位置 |
|---|---|
| 当前版本 | `/opt/gomoku-lab/current` → `/opt/gomoku-lab/releases/<UTC 时间>/` |
| 服务 | systemd `gomoku-lab`，`python3 -m gomoku.server --host 127.0.0.1 --port 8767`，动态低权限用户 |
| 反馈数据 | `/var/lib/gomoku-lab/feedback.sqlite3`（实际路径 `/var/lib/private/gomoku-lab/`），不随版本更新 |
| 反向代理 | Caddy：`haoceanlab.cn/gomoku/*` → `127.0.0.1:8767` |

发布新版本：

```sh
python scripts/package.py
scp dist/gomoku-lab-release.tar.gz hk_88:/tmp/gomoku-lab-release.tar.gz
scp scripts/deploy_server.py hk_88:/tmp/deploy-gomoku.py
ssh hk_88 'python3 /tmp/deploy-gomoku.py'
```

部署脚本解压到新的 release 目录，在服务器上跑完测试后切换 `current` 并重启服务。上线确认无误后可删除旧 release 与 `/tmp` 里的两个文件；需要回滚时，用旧提交重新打包部署即可。

```sh
systemctl status gomoku-lab
journalctl -u gomoku-lab -n 50 --no-pager
curl http://127.0.0.1:8767/api/health
```

导出反馈：

```sh
cd /opt/gomoku-lab/current
python3 scripts/export_feedback.py --db /var/lib/gomoku-lab/feedback.sqlite3 --output /tmp/gomoku-feedback.jsonl
```

## GitHub Pages

推送到 `main` 且改动了 `web/`、PDF 或实验数据时，`.github/workflows/pages.yml` 把 `web/` 发布到 https://haohaha-11.github.io/gomoku-lab/ ，同时放入 `downloads/report.pdf` 与 `downloads/benchmark.csv`，并把对弈页的接口地址改为 `https://haoceanlab.cn/gomoku/api/`。

服务端只对 `GOMOKU_ALLOWED_ORIGINS`（默认 `https://haohaha-11.github.io`）放开跨域请求，其他来源的提交仍被拒绝。

## 素材

录像（`scripts/record_demo.py`）和 PDF（`scripts/export_report_pdf.py`）都从本机运行的网页生成，需要先启动 `python -m gomoku.server --port 8801`。生产服务以字节范围响应提供 MP4，支持拖动进度。
