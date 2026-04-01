# CLAUDE.md — Backend

FastAPI REST API. Entry point: `app/main.py`. Runs on port 8000.

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Directory Layout

```
backend/
├── app/
│   ├── main.py               # App factory, lifespan, router registration
│   ├── api/                  # Route handlers (thin — delegate to services)
│   ├── core/                 # Cross-cutting infrastructure
│   │   ├── auth.py           # JWT creation/validation, OAuth2 scheme
│   │   ├── database.py       # Engine, session factory, startup migrations
│   │   ├── dependencies.py   # FastAPI Depends() helpers (get_current_user, etc.)
│   │   ├── scheduler.py      # APScheduler AsyncIOScheduler setup
│   │   ├── logging_config.py # JSON structured logging, trace ID, daily rotation
│   │   ├── init_data.py      # Seed data on first run
│   │   ├── html_utils.py     # HTML → text helpers for RSS
│   │   ├── bus/              # Event bus (dispatcher, events, queue)
│   │   └── channel/          # Multi-channel adapters (factory + 8 adapters)
│   ├── models/               # SQLModel ORM models (= DB tables + Pydantic schemas)
│   ├── services/             # Business logic layer
│   └── service_client/       # HTTP clients to the agents service
├── data/database.db          # SQLite (WAL mode)
├── tests/                    # pytest suite (in-memory SQLite fixtures)
├── alembic.ini               # Alembic config (present but migrations are manual — see below)
└── requirements.txt
```

---

## API Routes

All routes are prefixed `/api/v1/`. Modules in `app/api/`:

| Module | Prefix | Purpose |
|--------|--------|---------|
| `auth.py` | `/auth` | Login, register, token refresh |
| `users.py` | `/users` | User CRUD |
| `user_profile.py` | `/user-profile` | Extended profile settings |
| `rss.py` | `/rss` | Feeds, articles, groups |
| `rss_quality.py` | `/rss/quality` | AI quality scoring |
| `chat.py` | `/chat` | Sessions, SSE streaming responses |
| `agents.py` | `/agent-center/agents` | Agent catalog |
| `skill.py` | `/agent-center/skills` | Skill install/uninstall (SSE progress) |
| `channel.py` | `/channels` | Multi-channel config and messaging |
| `attachment.py` | `/attachments` | Upload, virus scan, format conversion |
| `plan.py` | `/plans` | Learning plan management |
| `card_center.py` | `/cards` | Dashboard card components |
| `schedule.py` | `/schedule` | Task scheduling |
| `schedule_ai.py` | `/schedule-ai` | AI-assisted scheduling |
| `task.py` | `/tasks` | Task management |
| `content.py` | `/content` | Content generation |
| `note.py` | `/notes` | Note management |
| `progress.py` | `/progress` | Learning progress tracking |
| `reminder.py` | `/reminders` | Reminder management |
| `agent.py` | `/agent` | Direct agent invocation |
| `endpoints.py` | `/` | Health check + static file serving |

---

## Models (`app/models/`)

Each file defines one or more SQLModel classes that serve as both ORM table and Pydantic schema.

`agent_store`, `attachment`, `card`, `channel`, `chat`, `content`, `note`, `plan`, `progress`, `reminder`, `rss`, `rss_quality`, `schedule`, `task`, `user`, `user_profile`

---

## Services (`app/services/`)

Business logic lives here. API routers import module-level singletons — no `Depends()` injection.

| Service | Responsibility |
|---------|---------------|
| `chat_service.py` | Chat session management, SSE streaming, LLM calls |
| `rss_service.py` | Feed fetch, parse, article storage |
| `rss_quality_service.py` | Quality scoring via agents |
| `task_service.py` | APScheduler task lifecycle, `FUNCTION_REGISTRY` |
| `skill_service.py` | Skill install/uninstall, progress SSE |
| `channel_service.py` | Multi-channel message dispatch |
| `agent_center_catalog_service.py` | Agent catalog reads from agents service |
| `attachment_service.py` | File storage, virus scan, conversion |
| `card_service.py` / `ai_card_service.py` | Dashboard card rendering |
| `user_profile_service.py` | User profile CRUD |
| `schedule_service.py` | Schedule management |
| `learning_scheduler.py` | Learning plan scheduling |
| `backup_service.py` | DB backup |
| `storage_service.py` | File storage abstraction |
| `file_processor.py` | Attachment processing pipeline |
| `protocols.py` | Shared Protocol type definitions |
| `skillhub_client.py` | Skill Hub HTTP client |

---

## Architecture Patterns

### Service Instantiation (Singletons)

All services are module-level singletons instantiated at import time:
```python
# bottom of each service file
task_service = TaskService()
```
Routes import them directly. **No FastAPI `Depends()` injection.** Consequence: services cannot be swapped without monkey-patching. Known coupling:
- `task_service` → `chat_service`, `channel_service`
- `chat_service` → `user_profile_service`
- `skill_service` → `skillhub_client`

### Session Management

Sessions opened **per-method** with `with Session(engine) as session:`. No single session-per-request boundary. Inconsistency exists: some methods open their own sessions, others accept a session parameter.

**Risk**: `chat_service.py` holds a session open across an async generator (SSE streaming) — can pin a SQLite write lock.

### Event Bus (`core/bus/`)

`dispatcher.py` decouples SSE delivery and channel notification from message-producing services. Producers emit events to the queue; the dispatcher fans out to registered handlers.

### Multi-Channel Adapters (`core/channel/`)

Factory pattern: `factory.py` + `base.py` (ABC). Eight adapters: QQ bot, Slack, Discord, DingTalk, Teams, Feishu, WeChat Work, Email. Adding a new channel = one new file implementing `BaseAdapter`.

### Task Function Registry

`task_service.py` has a hardcoded `FUNCTION_REGISTRY` dict (lines ~91–94) mapping task-type strings to callables. Adding a new schedulable function requires editing this dict directly.

---

## Authentication

- **Scheme**: OAuth2 Bearer, JWT HS256
- **Access token**: 7-day expiry
- **Refresh token**: 30-day expiry
- **Password hashing**: Argon2 via `passlib`
- **Inter-service**: `SERVICE_JWT_TOKEN` request header
- **`SECRET_KEY`**: defaults to `YOUR_SECRET_KEY_CHANGE_ME_IN_PROD` — must be changed before deploying

---

## Database

- **Engine**: SQLite, WAL mode — `backend/data/database.db`
- **ORM**: SQLModel (SQLAlchemy + Pydantic v2)
- **Migrations**: Startup-time `ALTER TABLE ADD COLUMN` in `core/database.py` (`migrate_skill_schema`, `migrate_user_schema`). No Alembic versioning. Cannot rename columns, change types, or roll back.

When adding a new column: add it to the model **and** add a corresponding `ALTER TABLE ADD COLUMN IF NOT EXISTS` call in `database.py`.

---

## Known Technical Debt

| # | Issue | Location |
|---|-------|----------|
| 1 | No DI — singletons imported directly by routes | `api/` + `services/` |
| 2 | Inconsistent session scope; streaming holds session open | `chat_service.py` |
| 3 | Service-to-service direct imports | `task_service.py`, `chat_service.py` |
| 4 | Startup `ALTER TABLE` instead of Alembic | `core/database.py` |
| 5 | Sync DB writes inside async handlers without `run_in_executor` | `rss_service.py`, others |
| 6 | Hardcoded `FUNCTION_REGISTRY` | `task_service.py:91–94` |
| 7 | No `Protocol` contracts for service interfaces | `services/protocols.py` (partial) |

---

## Testing

```bash
cd backend

# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov=app

# Single file
pytest tests/test_rss.py -v
```

Fixtures use in-memory SQLite — no external services needed for unit tests.
