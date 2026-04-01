# CLAUDE.md — Frontend

Vue 3 SPA. Entry point: `src/main.js`. Dev server on port 3000.

```bash
pnpm install
pnpm dev       # dev server (port 3000)
pnpm build     # production build → dist/
pnpm test      # Vitest unit tests
pnpm cypress:open  # Cypress E2E
```

---

## Directory Layout

```
frontend/
├── src/
│   ├── main.js           # Vue app bootstrap (plugins, i18n, router, pinia)
│   ├── App.vue           # Root component
│   ├── router.js         # Vue Router route definitions
│   ├── style.css         # Global styles
│   ├── api/              # Axios API modules (one per backend domain)
│   ├── pages/            # Route-level page components
│   ├── components/       # Reusable UI components
│   ├── store/            # Pinia state stores
│   ├── locales/          # i18n JSON files
│   └── utils/
│       └── request.js    # Axios instance (base URL, auth headers, interceptors)
├── index.html
├── vite.config.js        # Vite config + dev proxy
├── tailwind.config.cjs
├── biome.json            # Linter/formatter (replaces ESLint + Prettier)
├── cypress.config.js     # E2E test config
└── package.json
```

---

## Key Libraries

| Library | Version | Role |
|---------|---------|------|
| `vue` | ^3.5 | UI framework |
| `vue-router` | ^5 | Client-side routing |
| `pinia` | ^3 | State management |
| `@arco-design/web-vue` | ^2.57 | UI component library (primary) |
| `axios` | ^1.13 | HTTP client |
| `tailwindcss` | ^3.4 | Utility CSS |
| `vue-i18n` | ^11 | Internationalisation |
| `echarts` | ^6 | Charts |
| `md-editor-v3` | ^6.4 | Markdown editor |
| `dayjs` | ^1.11 | Date formatting |
| `lodash-es` | ^4.17 | Utility functions |
| `vuedraggable` | — | Drag-and-drop lists |
| `biome` | ^2.4 | Lint + format (use instead of ESLint) |
| `vitest` | ^2 | Unit tests |
| `cypress` | ^13 | E2E tests |

---

## Pages (`src/pages/`)

Each page directory maps to one or more routes:

| Directory | Key Files | Purpose |
|-----------|-----------|---------|
| `auth/` | `Login.vue`, `ForgotPassword.vue`, `ResetPassword.vue` | Auth flows |
| `homePage/` | `HomePage.vue` | Dashboard home |
| `rss/` | `RSSFeeds.vue`, `RSSArticles.vue`, `ArticleDetail.vue` | RSS management |
| `agent-center/` | `index.vue`, `AgentList.vue`, `AgentDetail.vue`, `SkillList.vue`, `SkillDetail.vue`, `RssQualityPanel.vue` | Agent & skill management |
| `agent-test/` | `AgentInterruptTest.vue` | Dev test page for interrupt flow |
| `chat/` | (via `message/`) | Chat interface |
| `message/` | `index.vue` | Messaging UI |
| `channel/` | `index.vue` | Channel configuration |
| `plan/` | `PlanDashboard.vue`, `PlanCreate.vue` | Learning plans |
| `schedule/` | `index.vue` | Task scheduling |
| `task/` | `TaskCenter.vue` | Task management |
| `attachment/` | `index.vue` | File management |
| `card-center/` | `CardCenter.vue` | Dashboard cards |
| `user/` | `index.vue` | User management (admin) |
| `user-profile/` | `UserProfile.vue` | Current user profile |
| `vector/` | `VectorAdmin.vue` | Vector DB admin |

---

## Components (`src/components/`)

| Directory | Components | Purpose |
|-----------|-----------|---------|
| `cards/` | `StatCard`, `ChartCard`, `TableCard`, `NewsCard`, `FormCard`, `MediaCard`, `GuideCard`, `ProductCard`, `UserProfileCard`, `AsyncCardRenderer`, `DynamicCardPreview` | Dynamic dashboard cards |
| `cards/registry.js` | — | Card type → component mapping |
| `chat/` | `MessageContent`, `MessageActions`, `ThinkingDisplay` | Chat message rendering |
| `channel/` | `ChannelSelectorModal` | Channel picker modal |
| `layout/` | `Sidebar` | App navigation sidebar |
| `loading/` | `BlockLoading`, `GlobalLoading`, `SkeletonLoading` | Loading states (exported via `index.js`) |
| `note/` | `NoteList`, `NoteToolbar`, `SummaryEditor` | Note-taking UI |

---

## Pinia Stores (`src/store/`)

| Store | State |
|-------|-------|
| `auth.js` | Current user, JWT tokens, login/logout actions |
| `chat.js` | Active chat session, message list, SSE stream state |
| `loading.js` | Global loading overlay toggle |
| `note.js` | Note list, active note |

---

## API Modules (`src/api/`)

One file per backend domain. Each exports functions that call `utils/request.js`.

`agent-center.js`, `agents-interrupt.js`, `attachment.js`, `auth.js`, `card-center.js`, `channel.js`, `chat.js`, `note.js`, `plan.js`, `rss.js`, `schedule.js`, `task.js`, `user-profile.js`, `user.js`, `vector.js`

The Axios instance in `utils/request.js` handles:
- Base URL (`/api`)
- Attaches `Authorization: Bearer <token>` from `auth` store
- Redirects to login on 401

---

## Internationalisation

- Config: `src/i18n.js`
- Locales: `src/locales/en.json`, `src/locales/zh-CN.json`
- Usage: `{{ $t('key') }}` in templates, `i18n.global.t('key')` in scripts
- Default locale: `zh-CN`

---

## Dev Proxy

Configured in `vite.config.js`:

```js
'/api'        → 'http://localhost:8000'   // backend
'/agents-api' → 'http://localhost:8001/api'  // agents
```

In production, no proxy — the FastAPI backend serves `dist/` at `/` and proxies API calls itself.

---

## Code Style

Linting and formatting is handled by **Biome** (`biome.json`), not ESLint or Prettier.

```bash
pnpm biome check src/   # lint
pnpm biome format src/  # format
```

---

## Testing

```bash
# Unit tests (Vitest)
pnpm test

# Unit tests with UI
pnpm test --ui

# E2E (Cypress)
pnpm cypress:open   # interactive
pnpm cypress:run    # headless (CI)
```

Component tests live alongside the component (e.g. `chat/MessageContent.spec.js`).
