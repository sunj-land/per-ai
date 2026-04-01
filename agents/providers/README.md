# Providers Module (模型提供商模块)

## 模块概述 (Overview)
`agents.providers` 模块为不同的 LLM 后端提供了一个统一的抽象层。它使得 Agent 可以无缝切换使用 OpenAI, Anthropic, Azure, Google Gemini 以及各种本地模型 (Ollama, vLLM)。

## 核心功能 (Core Functions)
1.  **统一接口 (`base.py`)**:
    -   `LLMProvider`: 抽象基类，定义了标准化的 `chat()` 方法。
    -   `LLMResponse`: 统一的响应对象，封装了内容、工具调用和 Token 使用情况。
2.  **提供商注册 (`registry.py`)**:
    -   `ProviderSpec`: 定义每个提供商的元数据（环境变量名、模型前缀、网关行为等）。
    -   `PROVIDERS`: 单一事实来源的注册表，决定了配置加载和模型匹配的优先级。
3.  **具体实现**:
    -   `LiteLLMProvider`: 基于 `litellm` 库的通用实现，支持大多数商业模型。
    -   `AzureOpenAIProvider`: 针对 Azure 的特定实现。
    -   `OpenAICodexProvider`: 支持 OAuth 认证的 Codex 实现。

## 架构设计 (Architecture)
-   **适配器模式**: 将不同厂商的 API 差异屏蔽在 Provider 内部，Agent 核心逻辑只与 `LLMProvider` 接口交互。
-   **自动路由**: 通过 `config` 模块的 `_match_provider` 逻辑，根据模型名称自动选择合适的 Provider。

## 扩展指南 (Extension)
要添加新的提供商：
1.  在 `nanobot/providers/registry.py` 的 `PROVIDERS` 列表中添加一个新的 `ProviderSpec`。
2.  (可选) 如果需要特殊的处理逻辑（如非标准 API），可以继承 `LLMProvider` 实现自定义类。
3.  在 `nanobot/config/schema.py` 的 `ProvidersConfig` 中添加对应的配置字段。
