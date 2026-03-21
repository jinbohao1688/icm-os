
import os
import sys
import inspect
from typing import Any, Dict
from dotenv import load_dotenv
from openai import OpenAI
from core.primitive import CapabilityPrimitive, TypeSignature


class DynamicPrimitiveGenerator:
    """
    当 AMS 找不到合适的原语时，动态生成并注册新原语。
    """

    def __init__(self, registry):
        self.registry = registry
        load_dotenv()
        self.api_key = os.getenv("DEEPSEEK_API_KEY")

    def generate(self, primitive_id: str, intent: str) -> CapabilityPrimitive:
        """根据意图动态生成一个新原语并注册。"""
        print(f"[DynGen] Generating primitive: {primitive_id}")

        client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")

        prompt = f"""你是 ICM-OS 原语生成器。
用户意图是：{intent}
需要生成一个名为 {primitive_id} 的 Python 原语类。

要求：
1. 继承 CapabilityPrimitive
2. 实现 invoke(self, input_data, session_id=None) 方法
3. 从 input_data 获取所需参数
4. 返回 dict 结果
5. 只用 Python 标准库或已安装的包（requests, bs4, openai等）
6. 不要有任何注释以外的说明文字
7. 只返回类定义代码，不要其他内容

示例格式：
class {primitive_id}Primitive(CapabilityPrimitive):
    def __init__(self):
        super().__init__(
            id="{primitive_id}",
            type_signature=TypeSignature(type_in=["text"], type_out=["text"]),
            semantic_descriptor="描述这个原语的功能",
        )
    def invoke(self, input_data, session_id=None):
        # 实现逻辑
        return {{"result": "..."}}
"""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        code = response.choices[0].message.content.strip()
        # 去掉 markdown 代码块
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1])

        print(f"[DynGen] Generated code:\n{code[:200]}...")

        # 动态执行代码
        namespace = {
            "CapabilityPrimitive": CapabilityPrimitive,
            "TypeSignature": TypeSignature,
        }
        exec(code, namespace)

        # 找到生成的类
        primitive_class = None
        for name, obj in namespace.items():
            if (inspect.isclass(obj) and
                issubclass(obj, CapabilityPrimitive) and
                obj is not CapabilityPrimitive):
                primitive_class = obj
                break

        if not primitive_class:
            raise ValueError(f"No CapabilityPrimitive subclass found in generated code")

        instance = primitive_class()
        self.registry.register(instance)
        print(f"[DynGen] Registered: {instance.id}")
        return instance
