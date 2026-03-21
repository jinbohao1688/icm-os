from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from core.graph import CapabilityGraph
from core.registry import CapabilityPrimitiveRegistry
from core.validator import GraphValidator, ValidationResult


class ParseError(Exception):
    """Raised when the AMS response cannot be parsed as a valid graph JSON."""


class DecompositionError(Exception):
    """Raised when AMS intent decomposition fails after retries."""


class IntentDecomposer:
    def __init__(
        self,
        registry: CapabilityPrimitiveRegistry,
        model: str = "deepseek-chat",
    ) -> None:
        self.registry = registry
        self.model = model
        self.validator = GraphValidator()

        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            # Defer network call until the first decompose, but fail fast on missing key.
            raise DecompositionError("DEEPSEEK_API_KEY is not set in environment or .env")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

    def _build_system_prompt(self, available_primitives: List[Dict[str, Any]]) -> str:
        """
        Build the system prompt that instructs the model how to produce a capability graph.
        """
        lines: List[str] = []
        lines.append("你是 ICM-OS 的意图分解器。")
        lines.append("你的任务是根据用户意图，构建一个由原语组成的能力图（有向无环图，DAG）。")
        lines.append("")
        lines.append("你只能使用以下已注册的原语：")
        for desc in available_primitives:
            pid = desc.get("id")
            semantic = desc.get("semantic_descriptor", "")
            lines.append(f"- {pid}: {semantic}")
        lines.append("")
        lines.append(
            "你必须返回严格的 JSON，格式为："
            '{"nodes": ["ID1", "ID2", ...], "edges": [["FROM", "TO"], ...], "params": {"key": "value"}}'
        )
        lines.append("params 字段用于提取意图中的关键参数，例如：")
        lines.append("- 翻译意图：{\"text\": \"要翻译的内容\", \"target_lang\": \"目标语言(English/Chinese/Japanese等)\"}")
        lines.append("- 写文件意图：{\"content\": \"要写入的内容\", \"path\": \"/文件路径\"}")
        lines.append("- 抓取意图：{\"url\": \"完整URL\", \"domain\": \"域名\"}")
        lines.append("params 中的值直接从用户意图中提取，不要编造。如果没有相关参数则留空 {}。")
        lines.append("要求：")
        lines.append("- 图必须是有向无环图（DAG）。")
        lines.append("- nodes 中的 ID 必须全部来自上述原语列表，不得创造新的原语。")
        lines.append("- edges 中的 FROM 和 TO 也必须来自 nodes。")
        lines.append("- 不要输出任何 JSON 以外的内容，不要添加注释、解释或 Markdown。")
        return "\n".join(lines)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the model response into a Python dict, handling optional markdown fences.
        """
        text = response_text.strip()

        # Strip markdown code fences if present.
        if text.startswith("```"):
            # Remove starting fence line.
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1 :]
            # Remove closing fence.
            if "```" in text:
                text = text.rsplit("```", 1)[0].strip()

        try:
            data = json.loads(text)
        except Exception as e:
            raise ParseError(f"Failed to parse AMS response as JSON: {e}") from e

        if not isinstance(data, dict):
            raise ParseError("Parsed AMS response is not a JSON object.")
        return data

    def _call_model(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        return response.choices[0].message.content  # type: ignore[return-value]

    def _build_user_prompt(self, intent: str, extra_feedback: Optional[str]) -> str:
        lines: List[str] = []
        lines.append(f"用户意图：{intent}")
        if extra_feedback:
            lines.append("")
            lines.append("上一轮生成的图未通过验证，失败原因如下：")
            lines.append(extra_feedback)
            lines.append("")
            lines.append("请根据上述错误信息修正你的图，并重新输出符合要求的 JSON。")
        return "\n".join(lines)

    def _validate_graph(
        self,
        graph: CapabilityGraph,
        principal: str,
        registry: CapabilityPrimitiveRegistry,
    ) -> ValidationResult:
        return self.validator.validate(graph, principal=principal, registry=registry)

    def decompose(
        self,
        intent: str,
        principal: str = "default",
        max_retries: int = 3,
    ) -> CapabilityGraph:
        print(f"[AMS] Decomposing intent: {intent[:50]}...")

        descriptors = self.registry.get_all_descriptors()
        system_prompt = self._build_system_prompt(descriptors)

        attempt = 0
        last_error: Optional[str] = None

        while attempt < max_retries:
            attempt += 1
            print(f"[AMS] Attempt {attempt}/{max_retries}")

            user_prompt = self._build_user_prompt(intent, last_error)
            response_text = self._call_model(system_prompt, user_prompt)

            try:
                graph_dict = self._parse_response(response_text)
            except ParseError as e:
                last_error = f"Parse error: {e}"
                if attempt >= max_retries:
                    raise DecompositionError(last_error)
                continue

            graph = CapabilityGraph.from_dict(graph_dict, registry=self.registry)
            validation = self._validate_graph(graph, principal, self.registry)

            if validation.passed:
                node_count = graph.graph.number_of_nodes()
                edge_count = graph.graph.number_of_edges()
                print(
                    f"[AMS] Graph validated: {node_count} nodes, {edge_count} edges"
                )
                # 把 AMS 提取的参数附加到 graph 上
                graph.params = graph_dict.get("params", {})
                return graph

            messages = "; ".join(validation.failed_checks)
            last_error = f"Validation failed: {messages}"

            if not validation.can_retry or attempt >= max_retries:
                raise DecompositionError(last_error)

        # Should not reach here, but keep for safety.
        raise DecompositionError(last_error or "Unknown decomposition failure")

    def decompose_with_dynamic(
        self,
        intent: str,
        principal: str = "default",
        max_retries: int = 3,
    ) -> "CapabilityGraph":
        """
        先尝试正常分解，如果图中有未知原语则动态生成。
        """
        from ams.dynamic_gen import DynamicPrimitiveGenerator
        gen = DynamicPrimitiveGenerator(self.registry)

        # 让 AMS 返回所需原语列表（含可能不存在的）
        descriptors = self.registry.get_all_descriptors()
        system_prompt = self._build_system_prompt(descriptors)
        system_prompt += """
\n\n【动态原语模式】
你现在处于动态原语模式。除了使用已有原语外，你可以并且应该在需要时创建新原语。
规则：
1. 如果现有原语能精确完成任务，使用它
2. 如果现有原语只是勉强凑合（如用SHA256来生成UUID），必须创建新原语
3. 新原语命名：大写+下划线，如 UUID_GENERATE、MD5_HASH、RANDOM_PASSWORD
4. 对于"生成随机X"、"计算X哈希"、"格式转换"等任务，优先创建专用新原语
"""

        user_prompt = self._build_user_prompt(intent, None)
        response_text = self._call_model(system_prompt, user_prompt)

        try:
            graph_dict = self._parse_response(response_text)
        except Exception as e:
            raise DecompositionError(str(e))

        # 检查哪些原语不存在，动态生成
        nodes = graph_dict.get("nodes", [])
        for node in nodes:
            pid = node if isinstance(node, str) else node.get("id")
            try:
                self.registry.get(pid)
            except KeyError:
                # 动态生成这个原语
                gen.generate(pid, intent)

        # 现在所有原语都存在了，正常构建图
        graph = CapabilityGraph.from_dict(graph_dict, registry=self.registry)
        graph.params = graph_dict.get("params", {})
        validation = self._validate_graph(graph, principal, self.registry)
        if validation.passed:
            node_count = graph.graph.number_of_nodes()
            edge_count = graph.graph.number_of_edges()
            print(f"[AMS] Graph validated: {node_count} nodes, {edge_count} edges")
            return graph
        raise DecompositionError(f"Validation failed after dynamic generation")

