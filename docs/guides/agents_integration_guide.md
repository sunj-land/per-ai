# Backend 调用 Agents 接口开发指南

## 1. 简介
Backend 不再直接引用 `agents` 目录下的代码，而是通过 `AgentsServiceSyncClient` 进行远程调用。

## 2. 客户端使用示例

### 2.1 获取客户端实例
通常不需要手动创建客户端，可以通过 `AgentService` 或 `AIProviderFactory` 间接使用。
如果需要直接使用：

```python
from app.service_client.agents_sync_client import AgentsServiceSyncClient
from app.service_client.models import ChatCompletionRequestContract

client = AgentsServiceSyncClient()
```

### 2.2 调用 LLM Chat
```python
request = ChatCompletionRequestContract(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-3.5-turbo",
    stream=True
)

# 流式调用
for chunk in client.chat_completion_stream(request):
    print(chunk)

# 非流式调用
response = client.chat_completion(request)
print(response)
```

### 2.3 调用节点能力
```python
from app.service_client.models import TextSummarizeRequestContract

request = TextSummarizeRequestContract(
    input_text="Long text...",
    max_tokens=100
)
result = client.text_summarize(request)
print(result.result)
```

## 3. 错误处理
客户端封装了熔断和重试机制。
- **AgentsServiceError**: 服务端返回 4xx/5xx 错误。
- **ServiceUnavailable**: 熔断器开启或服务不可达。

```python
try:
    client.chat_completion(req)
except AgentsServiceError as e:
    logger.error(f"Agent service error: {e.status_code} {e.payload}")
except Exception as e:
    logger.error(f"Network error: {e}")
```

## 4. 开发规范
1. **禁止直接导入**: Backend 代码中严禁出现 `from agents.core...` 或 `from agents.nodes...`。
2. **使用 Contracts**: 请求和响应数据结构应使用 `app.service_client.models` 中定义的 Pydantic 模型。
3. **超时设置**: 默认超时时间为 30s，可通过环境变量 `AGENTS_CLIENT_TIMEOUT_SECONDS` 调整。
