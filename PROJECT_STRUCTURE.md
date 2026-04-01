# 项目结构和规范

本文档详细介绍了本项目的目录结构、命名规范和开发流程，旨在帮助团队成员理解和遵循项目的统一标准。

## 根目录结构

```
.
├── backend/         # 后端服务 (Python, FastAPI)
├── docs/            # 项目文档
├── frontend/        # 前端 Monorepo (pnpm, Vite, Vue)
├── ops/             # 运维和部署 (Docker, CI/CD)
├── .editorconfig    # 编辑器配置
├── .gitignore       # Git 忽略文件
├── commitlint.config.js # Commitlint 配置
├── package.json     # 根 package.json (用于 scripts)
├── pnpm-lock.yaml   # pnpm 锁定文件
├── pnpm-workspace.yaml # pnpm 工作区配置
├── .prettierrc      # Prettier 配置
└── README.md        # 项目总览
```

### `backend`

后端服务目录，基于 Python 和 FastAPI。

- `app/`: FastAPI 应用核心代码。
  - `api/`: API 路由。
  - `core/`: 核心配置。
  - `models/`: 数据模型。
  - `services/`: 业务逻辑。
  - `main.py`: 应用入口。
- `tests/`: 测试代码。
- `migrations/`: 数据库迁移脚本。
- `.env`: 环境变量。
- `requirements.txt`: Python 依赖。

### `docs`

项目文档目录。

- `api/`: API 文档。
- `architecture/`: 架构设计文档。
- `guides/`: 开发指南和部署手册。

### `frontend`

前端 Monorepo 目录。

- `packages/`: 存放所有子包。
  - `apps/`: 存放应用 (例如 `web`)。
  - `ui/`: 通用 UI 组件。
  - `utils/`: 通用工具函数。
  - `hooks/`: 通用 React Hooks。
  - `services/`: 业务逻辑和 API 请求。
- `package.json`: `frontend` 的根 `package.json`。
- `pnpm-workspace.yaml`: pnpm 工作区配置。

### `ops`

运维和部署目录。

- `.github/workflows/`: GitHub Actions CI/CD 配置。
- `docker/`: Dockerfile 和 docker-compose.yml。
- `scripts/`: 运维脚本。
- `env/`: 不同环境的配置文件。

## 代码规范

- **代码风格**: 使用 Prettier 和 Biome (在前端) 进行自动格式化。
- **Commit Message**: 遵循 Conventional Commits 规范。
- **命名规范**:
  - 文件名和目录名：使用 kebab-case (例如 `my-component.vue`)。
  - 变量和函数名：使用 camelCase (例如 `myFunction`)。
  - 类名：使用 PascalCase (例如 `MyClass`)。
