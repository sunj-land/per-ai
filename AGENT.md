# 项目名称：个人智能助理 (Personal Intelligent Assistant)
版本：2.0.0
适用框架：Trae AI
文件用途：项目技术介绍、架构规范、代码生成规则、功能要求

================================================================================
# 一、项目整体介绍
本项目是一个**全栈本地运行**的 个人智能助理，采用现代化的前后端分离架构。
所有数据存储在本地 SQLite 数据库中，支持：
- RSS 订阅源管理（增删改查、分组、OPML导入、批量操作）
- 文章自动抓取、解析、去重、本地保存
- 文章查看、筛选、搜索、Markdown 渲染
- 支持后台定时任务更新 (APScheduler)
- 提供现代化的 Web 界面 (Vue 3 + Arco Design)

目标：高效、美观、功能强大的个人信息聚合中心。

================================================================================
# 二、技术栈（必须严格遵守）

## 后端 (Backend)
- **开发语言**：Python 3.12+
- **Web 框架**：FastAPI
- **ORM 框架**：SQLModel (基于 SQLAlchemy + Pydantic)
- **数据库**：SQLite (文件存储，轻量级)
- **RSS 解析**：feedparser
- **任务调度**：APScheduler (AsyncIOScheduler)
- **网络请求**：httpx / requests
- **数据验证**：Pydantic V2

## 前端 (Frontend)
- **核心框架**：Vue 3 (Composition API)
- **构建工具**：Vite
- **UI 组件库**：Arco Design Vue
- **样式框架**：Tailwind CSS (用于布局和原子样式)
- **状态管理**：Pinia
- **路由管理**：Vue Router
- **HTTP 客户端**：Axios
- **Markdown 渲染**：markdown-it + github-markdown-css
- **时间处理**：dayjs

================================================================================
# 三、项目目录结构（参考标准）

项目根目录
├── AGENT.md             # 本项目规范文件
├── backend/             # 后端项目目录
│   ├── app/             # 应用核心代码
│   │   ├── api/         # API 路由定义 (endpoints)
│   │   ├── core/        # 核心配置 (database, config)
│   │   ├── models/      # SQLModel 数据模型
│   │   ├── services/    # 业务逻辑服务 (RSS抓取, 数据处理)
│   │   └── main.py      # FastAPI 入口文件
│   ├── data/            # 数据存储目录 (自动创建)
│   │   └── database.db  # SQLite 数据库文件
│   ├── logs/            # 日志目录 (自动创建)
│   │   └── app.log      # 应用运行日志
│   └── requirements.txt # Python 依赖清单
├── frontend/            # 前端项目目录
│   └── packages/
│       └── web/         # Web 端应用
│           ├── src/
│           │   ├── api/         # API 接口封装
│           │   ├── assets/      # 静态资源
│           │   ├── components/  # 公共组件
│           │   ├── pages/       # 页面组件 (RSS, Home等)
│           │   ├── router/      # 路由配置
│           │   ├── store/       # Pinia 状态管理
│           │   └── main.js      # Vue 入口
│           ├── index.html
│           ├── package.json
│           ├── vite.config.js
│           └── tailwind.config.cjs
└── README.md            # 项目通用说明

================================================================================
# 四、代码生成规范（强制要求）

## 1. 命名规范
- **Python**:
  - 文件/模块：小写 + 下划线 (snake_case)，如 `rss_service.py`
  - 类名：大驼峰 (PascalCase)，如 `RSSFeed`
  - 函数/变量：小写 + 下划线，如 `get_all_feeds`
- **Vue/JS**:
  - 文件名：组件使用大驼峰 (e.g., `ArticleDetail.vue`)，工具文件使用小写 (e.g., `rss.js`)
  - 变量/函数：小驼峰 (camelCase)，如 `fetchData`
  - 常量：全大写 + 下划线 (UPPER_SNAKE_CASE)

## 2. 后端开发规范 (FastAPI)
- **API 设计**：遵循 RESTful 风格，但复杂查询或带参数的操作优先使用 POST 请求。
- **类型注解**：所有函数参数和返回值必须添加 Type Hint。
- **异步编程**：IO 密集型操作（数据库、网络请求）必须使用 `async/await`。
- **错误处理**：使用 `HTTPException` 返回标准 HTTP 错误码和消息。
- **数据模型**：使用 `SQLModel` 定义数据库表结构，使用 `Pydantic` 定义 API 请求/响应 Schema。

## 3. 前端开发规范 (Vue 3)
- **组件风格**：统一使用 `<script setup>` 语法糖。
- **UI 组件**：优先使用 Arco Design 组件，避免重复造轮子。
- **样式**：优先使用 Tailwind CSS 类，复杂自定义样式使用 `<style scoped>`。
- **响应式**：页面布局需考虑移动端适配 (使用 `sm:`, `md:`, `lg:` 前缀)。
- **API 调用**：所有 API 请求封装在 `src/api/` 目录下，禁止在组件中直接调用 `axios`。

## 4. 存储与日志规范
- **数据持久化**：所有业务数据存入 SQLite 数据库。
- **目录自动创建**：程序启动时，必须检查并自动创建 `data/` 和 `logs/` 目录（如果不存在）。
- **日志记录**：关键操作（如 RSS 抓取任务、数据变更）必须记录日志到 `logs/app.log`，包含时间戳和日志级别。

================================================================================
# 六、生成代码指令 (给 AI Agent 的规则)

当我让你生成功能或修改代码时，请：
1. **严格遵守**上述技术栈和目录结构。
2. **自动处理**文件路径，确保在正确的目录下创建或修改文件。
3. **优先修改**现有文件，避免创建重复文件。
4. **添加中文注释**，解释关键逻辑。
5. **保持前后端一致性**，修改后端 API 后需同步更新前端 API 定义。
6. **确保目录存在**，在执行文件写入前，检查并创建目标目录（尤其是 `data/` 和 `logs/`）。

【强制规范】
1. 所有代码必须完整、可直接运行。
2. 所有函数必须加中文注释。
3. 所有业务逻辑必须写在 service 层。
4. 不生成多余代码，不擅自扩展功能。
