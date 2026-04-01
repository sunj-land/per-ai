# System Expert Agent (智能系统专家)

该 Agent 是一个专门用于解答特定系统专业问题、支持多轮对话并具备主动澄清能力的智能助手。

## 核心能力
1. **意图识别与置信度评估**：准确分析用户意图，若问题模糊则触发澄清流程。
2. **主动澄清提问**：引导用户补充缺失的系统环境、错误码等必要信息。
3. **上下文记忆**：支持多轮对话，维持上下文连贯性。
4. **本地知识库集成**：内置系统常见问题（FAQ）和最佳实践文档检索。

## 工作流结构 (LangGraph)
- `analyze_intent`：分析用户输入，评估置信度并提取实体。
- `clarify` (条件分支)：当信息不足时，生成引导性的反问。
- `retrieve_knowledge` (条件分支)：当意图明确时，搜索知识库。
- `generate_response`：结合知识库内容生成专业答复。

## RESTful API 接口调用规范

LangGraph 提供了标准的 `/runs/stream` 和 `/runs/wait` 端点。

### 1. 发起流式对话 (Stream)

**POST** `http://localhost:2042/runs/stream`

**请求头 (Headers):**
```http
Content-Type: application/json
```

**请求体 (Request Body):**
```json
{
  "assistant_id": "system_expert_agent",
  "input": {
    "messages": [
      {
        "role": "user",
        "content": "API调用报错了怎么办？"
      }
    ]
  },
  "stream_mode": "values"
}
```

### 2. 响应格式规范 (NDJSON Stream)

Agent 将以事件流的形式返回状态更新。最终的回复将包含在 `generate_response` 或 `clarify` 节点中：

```json
{
  "event": "values",
  "data": {
    "messages": [
      {
        "content": "您好，请问您遇到的是哪个 API 的报错？是否能提供具体的 HTTP 状态码（如 429 或 500）？",
        "type": "ai"
      }
    ],
    "clarification_needed": true,
    "confidence": 0.4,
    "intent": "troubleshoot"
  }
}
```

### 3. 多轮对话示例

当被要求澄清后，客户端应携带完整的对话历史发起下一次请求：

**POST** `http://localhost:2042/runs/stream`
```json
{
  "assistant_id": "system_expert_agent",
  "input": {
    "messages": [
      {"role": "user", "content": "API调用报错了怎么办？"},
      {"role": "assistant", "content": "请问具体是什么错误码？"},
      {"role": "user", "content": "是 429 Too Many Requests"}
    ]
  }
}
```

**成功响应 (知识库匹配):**
```json
{
  "event": "values",
  "data": {
    "messages": [
      {
        "content": "根据系统规范，标准用户的 API 调用速率限制为每分钟 60 次。遇到 429 错误时，请在客户端实现退避重试机制（Exponential Backoff）。",
        "type": "ai"
      }
    ],
    "result": {
      "status": "success",
      "references": ["kb_002"]
    }
  }
}
```

## 错误码规范
- `400 Bad Request`: 请求参数格式错误或缺少必要的 `messages` 字段。
- `404 Not Found`: 找不到对应的 Assistant ID (`system_expert_agent`)。
- `500 Internal Server Error`: LLM 服务调用失败或知识库检索异常。在节点输出中会通过 `error` 字段返回具体的失败原因。
