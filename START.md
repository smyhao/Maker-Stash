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

## 常用参数

```bash
python start.py --no-browser
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
- 后端 API Token 仍需在前端“设置”里填写
