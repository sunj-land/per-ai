# PerAll Project

## 项目结构与职责

本项目采用微服务化架构，核心模块职责划分如下：

```
/
├── agents/                 # [NEW] 大模型与节点服务模块 (独立服务)
│   ├── api/                # 统一对外接口 (RESTful API)
│   ├── core/               # 核心 LLM 客户端与 Agent 基类
│   ├── nodes/              # 原子能力节点 (文本生成、分类、摘要等)
│   └── config/             # 模型与服务配置
│
├── backend/                # 业务后端 (FastAPI)
│   ├── app/
│   │   ├── service_client/ # [NEW] Agents 服务调用客户端 (所有 LLM 调用必须走此途径)
│   │   └── ...
│
├── frontend/               # 前端项目 (Vue3)
│
└── docs/                   # 项目文档
    ├── guides/             # 开发指南
    │   ├── agents_migration_guide.md   # Agents 服务迁移说明
    │   └── agents_integration_guide.md # Backend 调用开发指南
```

> **重要警告**: `backend` 模块严禁直接引用 `agents` 目录下的任何代码（如 `from agents.core...`）。所有大模型能力必须通过 `app.service_client.agents_sync_client` 提供的 HTTP 客户端进行调用。

## 附件中心配置

附件中心依赖以下组件，请确保安装或使用 Docker 运行：
- **LibreOffice**: 用于 Office 文档转 PDF
- **ClamAV**: 用于病毒扫描
- **python-magic**: 依赖 libmagic

开发环境配置：
```bash
# macOS
brew install --cask libreoffice
brew install clamav libmagic

# Ubuntu
sudo apt-get install libreoffice clamav clamav-daemon libmagic1
```
