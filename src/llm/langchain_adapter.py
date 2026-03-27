"""
LangChain LLM 适配器
支持多提供商统一接口
"""
import json
from typing import List, Dict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage
)


class LangChainLLMAdapter:
    """LangChain LLM 适配器 - 统一接口封装"""

    def __init__(self, llm: BaseChatModel, provider: str = "unknown"):
        self.llm = llm
        self.provider = provider

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        统一的对话接口

        Args:
            messages: 消息列表
            tools: 工具定义列表
            tool_choice: 工具选择策略
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            {
                "content": str,
                "tool_calls": List[Dict],
                "tokens": Dict
            }
        """
        # 转换消息格式
        langchain_messages = self._convert_messages(messages)

        # 构建调用参数
        invoke_kwargs = {
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # 添加工具调用参数
        if tools:
            invoke_kwargs["tools"] = tools
            invoke_kwargs["tool_choice"] = tool_choice

        try:
            # 调用 LangChain
            response = await self.llm.ainvoke(langchain_messages, **invoke_kwargs)

            # 解析响应
            return self._parse_response(response)

        except Exception as e:
            raise Exception(f"LLM调用失败 ({self.provider}): {str(e)}")

    def _convert_messages(self, messages: List[Dict]) -> List[BaseMessage]:
        """将标准格式转换为 LangChain 消息格式"""
        result = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "user":
                # 支持多模态内容（文本+图片）
                if isinstance(content, list):
                    result.append(HumanMessage(content=content))
                else:
                    result.append(HumanMessage(content=content))
            elif role == "assistant":
                # 处理可能包含 tool_calls 的 assistant 消息
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    # 转换 tool_calls 格式以适配 LangChain
                    # trading_agent 存储的格式: {"id", "type", "function": {"name", "arguments"}}
                    # LangChain 期望的格式: {"id", "name", "args"}
                    converted_tool_calls = []
                    for tc in tool_calls:
                        if "function" in tc:
                            # 从 trading_agent 格式转换
                            args_str = tc["function"].get("arguments", "{}")
                            try:
                                args = json.loads(args_str) if isinstance(args_str, str) else args_str
                            except json.JSONDecodeError:
                                args = {}
                            converted_tool_calls.append({
                                "id": tc.get("id", ""),
                                "name": tc["function"].get("name", ""),
                                "args": args
                            })
                        else:
                            # 已经是 LangChain 格式
                            converted_tool_calls.append(tc)
                    result.append(AIMessage(content=content, tool_calls=converted_tool_calls))
                else:
                    result.append(AIMessage(content=content))
            elif role == "tool":
                result.append(ToolMessage(
                    content=content,
                    tool_call_id=msg.get("tool_call_id", "")
                ))

        return result

    def _parse_response(self, response) -> Dict[str, Any]:
        """解析 LangChain 响应为统一格式"""
        tool_calls = []

        # 提取工具调用
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls.append({
                    "id": tc.get("id", ""),
                    "name": tc.get("name", ""),
                    "arguments": tc.get("args", {})
                })

        # 提取 token 使用量
        tokens = {}
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            tokens = {
                "input": response.usage_metadata.get('input_tokens', 0),
                "output": response.usage_metadata.get('output_tokens', 0),
                "total": response.usage_metadata.get('total_tokens', 0)
            }

        return {
            "content": response.content or "",
            "tool_calls": tool_calls,
            "tokens": tokens
        }
