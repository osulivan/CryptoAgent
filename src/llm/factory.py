"""
LLM 客户端工厂
支持多提供商统一创建
"""
from typing import Optional
from langchain_openai import ChatOpenAI

from .langchain_adapter import LangChainLLMAdapter


def create_llm_client(
    provider: str,
    api_key: str,
    model: str,
    base_url: Optional[str] = None,
    **kwargs
) -> LangChainLLMAdapter:
    """
    创建LLM客户端工厂函数

    Args:
        provider: 提供商类型 (openai-compatible, azure, anthropic, google)
        api_key: API密钥
        model: 模型名称或endpoint_id
        base_url: 自定义API地址（可选）
        **kwargs: 其他参数

    Returns:
        LangChainLLMAdapter 实例
    """
    provider = provider.lower()

    if provider == "openai-compatible":
        # OpenAI 兼容接口
        # 支持：OpenAI、火山引擎、DeepSeek、通义千问、智谱GLM 等
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=kwargs.get("temperature", 0.3),
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return LangChainLLMAdapter(llm, provider="openai-compatible")

    elif provider == "azure":
        # Azure OpenAI
        from langchain_openai import AzureChatOpenAI
        llm = AzureChatOpenAI(
            azure_deployment=model,
            api_key=api_key,
            azure_endpoint=base_url,
            temperature=kwargs.get("temperature", 0.3),
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return LangChainLLMAdapter(llm, provider="azure")

    elif provider == "anthropic":
        # Anthropic Claude
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "使用 Anthropic 需要安装: pip install langchain-anthropic"
            )

        # 支持自定义 base_url（用于第三方兼容 Anthropic 协议的 API）
        anthropic_kwargs = {
            "model": model,
            "api_key": api_key,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if base_url:
            # 第三方兼容接口需要添加 Bearer 认证头
            anthropic_kwargs["anthropic_api_url"] = base_url
            anthropic_kwargs["default_headers"] = {
                "Authorization": f"Bearer {api_key}"
            }

        llm = ChatAnthropic(**anthropic_kwargs)
        return LangChainLLMAdapter(llm, provider="anthropic")

    elif provider == "google":
        # Google Gemini
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "使用 Google Gemini 需要安装: pip install langchain-google-genai"
            )

        # 支持自定义 base_url
        google_kwargs = {
            "model": model,
            "api_key": api_key,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if base_url:
            google_kwargs["base_url"] = base_url

        llm = ChatGoogleGenerativeAI(**google_kwargs)
        return LangChainLLMAdapter(llm, provider="google")

    else:
        raise ValueError(
            f"不支持的LLM提供商: {provider}\n"
            f"支持的提供商: openai-compatible, azure, anthropic, google"
        )
