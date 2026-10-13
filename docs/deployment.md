# 运行与部署

## 本机运行

Python 3.10 或更高版本即可运行对局服务，无需安装第三方 Python 库。Three.js 已随静态文件本地打包。

```powershell
cd D:\learning\gomoku-lab
python server.py --port 8767
```

浏览器访问 `http://127.0.0.1:8767/` 查看展示首页，`/game.html` 进入对弈。执行 `python -m unittest discover -s tests -v` 验证规则、搜索和 HTTP 接口。执行 `python scripts/benchmark.py` 会重新测量当前机器并覆盖 results 下的基准数据；交付版本中的数据是在本机 Windows 上测得。

## hk_88 服务

已部署地址为 `https://haoceanlab.cn/gomoku/`。Python 服务仅监听 `127.0.0.1:8767`，Caddy 将该子路径转发到服务，现有网站仍使用原来的根路径。服务使用 systemd 独立低权限动态用户运行，反馈数据保存在 `/var/lib/gomoku-lab/feedback.sqlite3`。

每次部署将文件放入 `/opt/gomoku-lab/releases/<UTC时间>/`，`/opt/gomoku-lab/current` 指向正在运行的版本。首次变更 Caddy 前保存原配置并运行配置校验。

```powershell
python scripts/package.py
scp dist/gomoku-lab-release.tar.gz hk_88:/tmp/gomoku-lab-release.tar.gz
scp scripts/deploy_server.py hk_88:/tmp/deploy-gomoku.py
ssh hk_88 'python3 /tmp/deploy-gomoku.py'
```

```sh
systemctl status gomoku-lab
journalctl -u gomoku-lab -n 50 --no-pager
curl http://127.0.0.1:8767/api/health
```

更新静态文件或算法后重新打包部署即可。回滚时将 current 符号链接切回保留的上一版本，再执行 `systemctl restart gomoku-lab`。反馈数据库位于版本目录之外，更新和回滚不覆盖它。

## 反馈数据

每条反馈保存 AI 落子前的局面、执子方、AI 落点、认可或改进评价、可选的替代落点和文字。当前阶段仅采集，不会在线更新算法。匿名提交还没有经过人工审核，训练前应去重、核验合法性，并按开局族或完整对局分组拆分数据。

```sh
cd /opt/gomoku-lab/current
python3 scripts/export_feedback.py --db /var/lib/gomoku-lab/feedback.sqlite3 --output /tmp/gomoku-feedback.jsonl
```

反馈数据库与导出文件不通过网页提供下载，也不进入源码提交包。源码 ZIP 在本机交付，网页提供实验报告与基准 CSV。

## 公开源码与录像

源码仓库为 `https://github.com/Haohaha-11/gomoku-lab`，设为公开。提交内容包含代码、报告、固定基准数据和演示录像；不包含匿名反馈数据库、原始课堂附件、本机录制临时文件或内部 QA 资料。

生产服务通过字节范围响应提供 MP4，支持网页播放和进度拖动。`scripts/make_demo_receiver.py` 是本机录制辅助服务，仅监听 loopback；生产 systemd 始终运行 `server.py`。
