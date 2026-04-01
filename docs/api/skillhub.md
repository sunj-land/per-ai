# SkillHub 管理 API 文档

## 基础规范
- Base URL: `/api/v1/agent-center`
- 返回结构：
```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

## 接口清单

### 1) 搜索 SkillHub
- `GET /skills/hub/search`
- Query:
  - `name` 可选，按名称模糊搜索
  - `tags` 可选，逗号分隔标签
  - `version` 可选，指定版本

### 2) 安装 Skill
- `POST /skills/install`
- Headers:
  - `X-User-Id` 可选
  - `X-Idempotency-Key` 可选
- Body:
```json
{
  "name": "weather",
  "version": "1.2.0",
  "url": "",
  "operation": "install"
}
```

### 3) 安装进度状态
- `GET /skills/install/{task_id}/status`

### 4) 安装进度流 (SSE)
- `GET /skills/install/{task_id}/stream`
- Content-Type: `text/event-stream`

### 5) 安装记录
- `GET /skills/install-records?offset=0&limit=20`

### 6) 卸载 Skill
- `POST /skills/{skill_id}/uninstall`

### 7) 更新 Skill
- `POST /skills/{skill_id}/upgrade`
- Headers:
  - `X-User-Id` 可选
  - `X-Idempotency-Key` 可选
- Body:
```json
{
  "version": "1.3.0"
}
```

### 8) 查询可用版本
- `GET /skills/{skill_id}/versions`
