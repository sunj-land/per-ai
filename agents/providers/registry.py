"""
提供商注册表 (Provider Registry) — LLM 提供商元数据的唯一事实来源。

添加新的提供商：
  1. 在下方的 PROVIDERS 中添加一个 ProviderSpec。
  2. 在 config/schema.py 中的 ProvidersConfig 添加对应字段。
  完成。环境变量、前缀处理、配置匹配、状态显示都基于此处派生。

顺序很重要 — 它控制匹配优先级和回退逻辑。网关排在前面。
每个条目都写明了所有字段，因此你可以直接复制粘贴作为模板。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderSpec:
    """
    单个 LLM 提供商的元数据定义。
    包含身份标识、环境变量映射、模型前缀处理和网关行为配置。
    """

    # ========== 身份标识 ==========
    # 配置字段名, 如 "dashscope"
    name: str  
    # 用于匹配模型名称的关键词 (小写元组)
    keywords: tuple[str, ...]  
    # LiteLLM 使用的环境变量名, 如 "DASHSCOPE_API_KEY"
    env_key: str  
    # 用于状态显示的展示名称
    display_name: str = ""  

    # ========== 模型前缀处理 ==========
    # 传递给 LiteLLM 的前缀: "dashscope" -> "dashscope/{model}"
    litellm_prefix: str = ""  
    # 如果模型已包含这些前缀则跳过处理
    skip_prefixes: tuple[str, ...] = ()  

    # ========== 额外的环境变量映射 ==========
    # 元组形式，包含额外的环境变量键值对
    env_extras: tuple[tuple[str, str], ...] = ()

    # ========== 网关/本地检测 ==========
    # 是否为网关 (可路由任何模型, 如 OpenRouter)
    is_gateway: bool = False  
    # 是否为本地部署 (如 vLLM, Ollama)
    is_local: bool = False  
    # 通过 API Key 前缀进行检测的标记
    detect_by_key_prefix: str = ""  
    # 通过 API Base URL 关键词进行检测的标记
    detect_by_base_keyword: str = ""  
    # 默认的 API Base URL
    default_api_base: str = ""  

    # ========== 网关行为配置 ==========
    # 是否剥离 "provider/" 这样的前缀
    strip_model_prefix: bool = False  
    # 传递给 LiteLLM 的额外参数字典
    litellm_kwargs: dict[str, Any] = field(default_factory=dict)  

    # ========== 模型特定参数覆盖 ==========
    # 针对特定模型的参数覆盖配置
    model_overrides: tuple[tuple[str, dict[str, Any]], ...] = ()

    # ========== 认证方式 ==========
    # 是否使用 OAuth 流程进行认证
    is_oauth: bool = False  
    # 是否绕过 LiteLLM 直接调用提供商 API
    is_direct: bool = False  

    # ========== 功能支持 ==========
    # 是否支持提示词缓存 (Prompt Caching)
    supports_prompt_caching: bool = False  

    @property
    def label(self) -> str:
        """
        获取展示标签。
        
        :return: 显示名称或首字母大写的字段名
        """
        return self.display_name or self.name.title()


# ---------------------------------------------------------------------------
# PROVIDERS — 注册表主体。顺序即优先级。可复制任意条目作为模板。
# ---------------------------------------------------------------------------

PROVIDERS: tuple[ProviderSpec, ...] = (
    # === 自定义提供商 (直接调用兼容 OpenAI 的端点，绕过 LiteLLM) ======
    ProviderSpec(
        name="custom",
        keywords=(),
        env_key="",
        display_name="Custom",
        litellm_prefix="",
        is_direct=True,
    ),

    # === Azure OpenAI (使用 2024-10-21 API 版本的直接调用) =====
    ProviderSpec(
        name="azure_openai",
        keywords=("azure", "azure-openai"),
        env_key="",
        display_name="Azure OpenAI",
        litellm_prefix="",
        is_direct=True,
    ),
    
    # === 网关 (通过 api_key / api_base 检测，而非模型名称) =========
    # 网关可以路由任何模型，所以在回退中胜出。
    # OpenRouter: 全局网关，密钥以 "sk-or-" 开头
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        display_name="OpenRouter",
        litellm_prefix="openrouter",  # anthropic/claude-3 → openrouter/anthropic/claude-3
        skip_prefixes=(),
        env_extras=(),
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="sk-or-",
        detect_by_base_keyword="openrouter",
        default_api_base="https://openrouter.ai/api/v1",
        strip_model_prefix=False,
        model_overrides=(),
        supports_prompt_caching=True,
    ),
    # AiHubMix: 全局网关，兼容 OpenAI 接口。
    ProviderSpec(
        name="aihubmix",
        keywords=("aihubmix",),
        env_key="OPENAI_API_KEY",
        display_name="AiHubMix",
        litellm_prefix="openai",  # → openai/{model}
        skip_prefixes=(),
        env_extras=(),
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="aihubmix",
        default_api_base="https://aihubmix.com/v1",
        strip_model_prefix=True,  # anthropic/claude-3 → claude-3 → openai/claude-3
        model_overrides=(),
    ),
    # 硅基流动 (SiliconFlow): 兼容 OpenAI 接口的网关
    ProviderSpec(
        name="siliconflow",
        keywords=("siliconflow",),
        env_key="OPENAI_API_KEY",
        display_name="SiliconFlow",
        litellm_prefix="openai",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="siliconflow",
        default_api_base="https://api.siliconflow.cn/v1",
        strip_model_prefix=False,
        model_overrides=(),
    ),
    # 火山引擎 (VolcEngine): 兼容 OpenAI 接口的网关，按量计费模型
    ProviderSpec(
        name="volcengine",
        keywords=("volcengine", "volces", "ark"),
        env_key="OPENAI_API_KEY",
        display_name="VolcEngine",
        litellm_prefix="volcengine",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="volces",
        default_api_base="https://ark.cn-beijing.volces.com/api/v3",
        strip_model_prefix=False,
        model_overrides=(),
    ),
    # 火山引擎 Coding Plan: 与 volcengine 相同的密钥
    ProviderSpec(
        name="volcengine_coding_plan",
        keywords=("volcengine-plan",),
        env_key="OPENAI_API_KEY",
        display_name="VolcEngine Coding Plan",
        litellm_prefix="volcengine",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://ark.cn-beijing.volces.com/api/coding/v3",
        strip_model_prefix=True,
        model_overrides=(),
    ),
    # BytePlus: 火山引擎国际版，按量计费模型
    ProviderSpec(
        name="byteplus",
        keywords=("byteplus",),
        env_key="OPENAI_API_KEY",
        display_name="BytePlus",
        litellm_prefix="volcengine",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="bytepluses",
        default_api_base="https://ark.ap-southeast.bytepluses.com/api/v3",
        strip_model_prefix=True,
        model_overrides=(),
    ),
    # BytePlus Coding Plan
    ProviderSpec(
        name="byteplus_coding_plan",
        keywords=("byteplus-plan",),
        env_key="OPENAI_API_KEY",
        display_name="BytePlus Coding Plan",
        litellm_prefix="volcengine",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://ark.ap-southeast.bytepluses.com/api/coding/v3",
        strip_model_prefix=True,
        model_overrides=(),
    ),

    # === 标准提供商 (通过模型名称关键词匹配) ===============
    # Anthropic: LiteLLM 原生识别 "claude-*"，无需前缀
    ProviderSpec(
        name="anthropic",
        keywords=("anthropic", "claude"),
        env_key="ANTHROPIC_API_KEY",
        display_name="Anthropic",
        litellm_prefix="",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
        supports_prompt_caching=True,
    ),
    # OpenAI: LiteLLM 原生识别 "gpt-*"，无需前缀
    ProviderSpec(
        name="openai",
        keywords=("openai", "gpt"),
        env_key="OPENAI_API_KEY",
        display_name="OpenAI",
        litellm_prefix="",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),
    # OpenAI Codex: 使用 OAuth，而不是 API Key
    ProviderSpec(
        name="openai_codex",
        keywords=("openai-codex",),
        env_key="",
        display_name="OpenAI Codex",
        litellm_prefix="",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="codex",
        default_api_base="https://chatgpt.com/backend-api",
        strip_model_prefix=False,
        model_overrides=(),
        is_oauth=True,
    ),
    # Github Copilot: 使用 OAuth，而不是 API Key
    ProviderSpec(
        name="github_copilot",
        keywords=("github_copilot", "copilot"),
        env_key="",
        display_name="Github Copilot",
        litellm_prefix="github_copilot",
        skip_prefixes=("github_copilot/",),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
        is_oauth=True,
    ),
    # DeepSeek: LiteLLM 路由需要 "deepseek/" 前缀
    ProviderSpec(
        name="deepseek",
        keywords=("deepseek",),
        env_key="DEEPSEEK_API_KEY",
        display_name="DeepSeek",
        litellm_prefix="deepseek",
        skip_prefixes=("deepseek/",),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),
    # Gemini: LiteLLM 需要 "gemini/" 前缀
    ProviderSpec(
        name="gemini",
        keywords=("gemini",),
        env_key="GEMINI_API_KEY",
        display_name="Gemini",
        litellm_prefix="gemini",
        skip_prefixes=("gemini/",),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),
    # Zhipu: LiteLLM 使用 "zai/" 前缀
    ProviderSpec(
        name="zhipu",
        keywords=("zhipu", "glm", "zai"),
        env_key="ZAI_API_KEY",
        display_name="Zhipu AI",
        litellm_prefix="zai",
        skip_prefixes=("zhipu/", "zai/", "openrouter/", "hosted_vllm/"),
        env_extras=(("ZHIPUAI_API_KEY", "{api_key}"),),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),
    # DashScope: Qwen 模型，需要 "dashscope/" 前缀
    ProviderSpec(
        name="dashscope",
        keywords=("qwen", "dashscope"),
        env_key="DASHSCOPE_API_KEY",
        display_name="DashScope",
        litellm_prefix="dashscope",
        skip_prefixes=("dashscope/", "openrouter/"),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),
    # Moonshot: Kimi 模型，需要 "moonshot/" 前缀
    ProviderSpec(
        name="moonshot",
        keywords=("moonshot", "kimi"),
        env_key="MOONSHOT_API_KEY",
        display_name="Moonshot",
        litellm_prefix="moonshot",
        skip_prefixes=("moonshot/", "openrouter/"),
        env_extras=(("MOONSHOT_API_BASE", "{api_base}"),),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://api.moonshot.ai/v1",
        strip_model_prefix=False,
        model_overrides=(("kimi-k2.5", {"temperature": 1.0}),),
    ),
    # MiniMax: LiteLLM 路由需要 "minimax/" 前缀
    ProviderSpec(
        name="minimax",
        keywords=("minimax",),
        env_key="MINIMAX_API_KEY",
        display_name="MiniMax",
        litellm_prefix="minimax",
        skip_prefixes=("minimax/", "openrouter/"),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://api.minimax.io/v1",
        strip_model_prefix=False,
        model_overrides=(),
    ),
    # === 本地部署 (通过配置键匹配，而不是 api_base) =========
    # vLLM / 任何兼容 OpenAI 的本地服务器
    ProviderSpec(
        name="vllm",
        keywords=("vllm",),
        env_key="HOSTED_VLLM_API_KEY",
        display_name="vLLM/Local",
        litellm_prefix="hosted_vllm",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=False,
        is_local=True,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),
    # === Ollama (本地, 兼容 OpenAI) ===================================
    ProviderSpec(
        name="ollama",
        keywords=("ollama", "nemotron"),
        env_key="OLLAMA_API_KEY",
        display_name="Ollama",
        litellm_prefix="ollama_chat",
        skip_prefixes=("ollama/", "ollama_chat/"),
        env_extras=(),
        is_gateway=False,
        is_local=True,
        detect_by_key_prefix="",
        detect_by_base_keyword="11434",
        default_api_base="http://localhost:11434",
        strip_model_prefix=False,
        model_overrides=(),
    ),
    # === 辅助提供商 (非主要 LLM 提供商) ============================
    # Groq: 主要用于 Whisper 语音转录
    ProviderSpec(
        name="groq",
        keywords=("groq",),
        env_key="GROQ_API_KEY",
        display_name="Groq",
        litellm_prefix="groq",
        skip_prefixes=("groq/",),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),
)


# ---------------------------------------------------------------------------
# 查找助手函数
# ---------------------------------------------------------------------------


def find_by_model(model: str) -> ProviderSpec | None:
    """
    通过模型名称的关键词（不区分大小写）匹配标准提供商。
    跳过网关和本地部署 —— 它们是通过 api_key/api_base 匹配的。
    
    :param model: 模型名称
    :return: 匹配到的 ProviderSpec，若未找到则返回 None
    """
    # 将模型名称转为小写并处理分隔符
    model_lower = model.lower()
    model_normalized = model_lower.replace("-", "_")
    model_prefix = model_lower.split("/", 1)[0] if "/" in model_lower else ""
    normalized_prefix = model_prefix.replace("-", "_")
    
    # 获取所有的标准提供商（非网关且非本地）
    std_specs = [s for s in PROVIDERS if not s.is_gateway and not s.is_local]

    # ========== 步骤1：优先匹配显式的提供商前缀 ==========
    for spec in std_specs:
        if model_prefix and normalized_prefix == spec.name:
            return spec

    # ========== 步骤2：根据关键词匹配 ==========
    for spec in std_specs:
        if any(
            kw in model_lower or kw.replace("-", "_") in model_normalized for kw in spec.keywords
        ):
            return spec
    return None


def find_gateway(
    provider_name: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
) -> ProviderSpec | None:
    """
    检测网关/本地提供商。

    匹配优先级：
      1. provider_name — 如果它映射到网关/本地规范，则直接使用。
      2. api_key 前缀 — 例如 "sk-or-" → OpenRouter。
      3. api_base 关键词 — 例如 URL 中的 "aihubmix" → AiHubMix。

    :param provider_name: 提供商名称
    :param api_key: API 密钥
    :param api_base: API 基础 URL
    :return: 匹配到的 ProviderSpec，若未找到则返回 None
    """
    # ========== 步骤1：直接通过配置键匹配 ==========
    if provider_name:
        spec = find_by_name(provider_name)
        if spec and (spec.is_gateway or spec.is_local):
            return spec

    # ========== 步骤2：通过 api_key 前缀或 api_base 关键词自动检测 ==========
    for spec in PROVIDERS:
        if spec.detect_by_key_prefix and api_key and api_key.startswith(spec.detect_by_key_prefix):
            return spec
        if spec.detect_by_base_keyword and api_base and spec.detect_by_base_keyword in api_base:
            return spec

    return None


def find_by_name(name: str) -> ProviderSpec | None:
    """
    通过配置字段名查找提供商规范，例如 "dashscope"。
    
    :param name: 提供商配置名称
    :return: 匹配到的 ProviderSpec，若未找到则返回 None
    """
    for spec in PROVIDERS:
        if spec.name == name:
            return spec
    return None
