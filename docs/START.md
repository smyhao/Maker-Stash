# Maker Stash 一键启动

## Windows

双击 `start.bat`，或在项目根目录执行：

```powershell
.\start.bat
```

## Linux / macOS

在项目根目录执行：

```bash
sh ./start.sh
```

如果希望直接 `./start.sh` 启动，需要先赋予执行权限：

```bash
chmod +x ./start.sh
./start.sh
```

## 通用方式

```bash
python start.py
```

启动后会：

- 启动后端：`http://127.0.0.1:8000`
- 启动前端：`http://127.0.0.1:5173`
- 自动打开前端页面

## 配置文件

可以复制示例配置并修改端口：

```bash
cp config/start.example.toml start.toml
```

`start.toml` 示例：

```toml
lan = false
host = "127.0.0.1"
backend_port = 8000
frontend_port = 5173
no_browser = false
```

启动器默认读取项目根目录的 `start.toml`。命令行参数优先级更高，例如 `python start.py --backend-port 8010` 会覆盖配置文件里的 `backend_port`。

## Orange Pi / 局域网开发

在 Orange Pi Zero 3 等局域网设备上临时开发或调试时，用 `--lan` 让后端和 Vite 前端监听所有网卡：

```bash
python start.py --lan --no-browser
```

也可以直接写入 `start.toml`：

```toml
lan = true
backend_port = 8000
frontend_port = 5173
no_browser = true
```

这等价于绑定 `0.0.0.0`，启动日志会同时打印本机地址和局域网地址，例如：

```text
http://127.0.0.1:5173
http://192.168.1.23:5173
```

同一局域网内的电脑或手机访问 `http://<OrangePi局域网IP>:5173`。前端「设置 → 连接」里的 API 地址建议留空，让前端通过 `/api` 代理访问同机后端；如果要直接填写 `http://<OrangePi局域网IP>:8000`，需要在 `backend/.env` 中配置允许的前端来源：

```env
CORS_ALLOWED_ORIGINS=http://192.168.1.23:5173
```

不要在公网直接暴露开发服务；至少保留 API Token，并优先只在可信局域网内开放端口。

## Orange Pi 生产部署

生产部署不运行 Vite。先构建 `frontend/dist`，再让 FastAPI 后端直接托管静态前端和 `/api`。项目根目录准备好 `start.toml` 后执行：

```bash
chmod +x ./start-prod.sh ./update-prod.sh
cd frontend && npm run build && cd ..
./start-prod.sh
```

生产模式只监听后端端口，例如：

```text
http://<OrangePi局域网IP>:8000
```

如果 `start.toml` 设置了其他 `backend_port`，访问对应端口。正常生产进程中应该只看到 `uvicorn`，不应该看到 `vite` 或 `esbuild`。

后续在部署端快速更新：

```bash
cd /opt/Maker-Stash
./update-prod.sh
```

`update-prod.sh` 会按顺序执行：

- `git pull --ff-only`
- 后端数据库迁移
- `npm run build`
- 如果存在 `maker-stash.service`，通过 systemd 重启生产服务
- 如果没有 systemd 服务，停止旧的 `start.py` / `uvicorn` / Vite 开发服务并后台启动 `start.py --skip-frontend`

生产服务日志写入 `.codex-runtime/maker-stash-production.log`。

## 常用参数

```bash
python start.py --no-browser
python start.py --lan --no-browser
python start.py --config ./start.toml
python start.py --backend-port 8010 --frontend-port 5174
python start.py --skip-backend
python start.py --skip-frontend
```

## 关闭服务

Windows：

```powershell
.\stop.bat
```

Linux / macOS：

```bash
sh ./stop.sh
```

通用方式：

```bash
python stop.py
```

默认会关闭 `8000` 和 `5173` 端口上的服务。指定端口：

```bash
python stop.py --ports 8000 5173
```

## 前置条件

- 根目录已有 `.venv`
- `backend` 依赖已安装
- `frontend/node_modules` 已存在
- Web 前端默认免填 API Token；CLI 和外部模块接入仍需单独配置 Token
