# 开发指南

本指南旨在帮助开发者快速地在本地搭建开发环境，并开始为项目贡献代码。

## 前端开发

1.  进入 `frontend` 目录：`cd frontend`
2.  安装依赖：`pnpm install`
3.  启动开发服务器：`pnpm dev`

## 后端开发

1.  进入 `backend` 目录：`cd backend`
2.  创建并激活虚拟环境：`python -m venv venv && source venv/bin/activate`
3.  安装依赖：`pip install -r requirements.txt`
4.  启动开发服务器：`uvicorn app.main:app --reload`
