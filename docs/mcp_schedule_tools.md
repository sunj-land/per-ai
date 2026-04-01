# Schedule Management MCP Tools

This document describes the Model Context Protocol (MCP) tools available for the Schedule Management module. These tools allow AI agents to query, create, update, and delete schedules.

## Base URL

All tool endpoints are available under `/api/v1/schedule-ai/mcp`.

- **List Tools**: `GET /api/v1/schedule-ai/mcp/tools`
- **Call Tool**: `POST /api/v1/schedule-ai/mcp/call`

## Available Tools

### 1. ScheduleQuerySkill

Query schedules based on time range and keyword.

**Input Schema:**

```json
{
  "start_time": "string (ISO 8601, optional)",
  "end_time": "string (ISO 8601, optional)",
  "keyword": "string (optional, search in title and description)",
  "limit": "integer (optional, default 10)"
}
```

**Example Usage:**

Query schedules for the next week containing "meeting":

```json
{
  "start_time": "2023-10-27T00:00:00",
  "end_time": "2023-11-03T00:00:00",
  "keyword": "meeting"
}
```

### 2. ScheduleCreateSkill

Create a new schedule.

**Input Schema:**

```json
{
  "title": "string (required)",
  "description": "string (optional)",
  "start_time": "string (ISO 8601, required)",
  "end_time": "string (ISO 8601, optional)",
  "priority": "string (high/medium/low, optional)",
  "reminders": "list of reminder objects (optional)"
}
```

**Example Usage:**

Create a high priority meeting:

```json
{
  "title": "Important Strategy Meeting",
  "description": "Discuss Q4 roadmap",
  "start_time": "2023-10-30T10:00:00",
  "end_time": "2023-10-30T11:30:00",
  "priority": "high",
  "reminders": [
    {
      "remind_at": "2023-10-30T09:45:00",
      "type": "notification"
    }
  ]
}
```

### 3. ScheduleUpdateSkill

Update an existing schedule.

**Input Schema:**

```json
{
  "schedule_id": "string (UUID, required)",
  "title": "string (optional)",
  "description": "string (optional)",
  "start_time": "string (ISO 8601, optional)",
  "end_time": "string (ISO 8601, optional)",
  "priority": "string (optional)",
  "reminders": "list (optional)"
}
```

### 4. ScheduleDeleteSkill

Delete a schedule.

**Input Schema:**

```json
{
  "schedule_id": "string (UUID, required)"
}
```

## AI Integration API

In addition to MCP tools, a natural language search API is provided:

**Endpoint**: `POST /api/v1/schedule-ai/search`

**Request:**

```json
{
  "query": "Show me meetings next week",
  "limit": 5
}
```

**Response:**

```json
{
  "query": "Show me meetings next week",
  "parsed_time_range": {
    "start_time": "2023-10-30T00:00:00",
    "end_time": "2023-11-06T00:00:00"
  },
  "results": [
    {
      "id": "...",
      "title": "Strategy Meeting",
      "start": "2023-10-30T10:00:00",
      ...
    }
  ]
}
```
