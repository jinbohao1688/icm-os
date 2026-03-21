
import os
import sys
import inspect
from typing import Any, Dict
from dotenv import load_dotenv
from openai import OpenAI
from core.primitive import CapabilityPrimitive, TypeSignature

# 缓存目录
CACHE_DIR = os.environ.get("ICM_PRIMITIVE_CACHE", os.path.expanduser("~/.icm-os/primitives"))

class DynamicPrimitiveGenerator:
    """
    当 AMS 找不到合适的原语时，动态生成并注册新原语。
    生成的原语会缓存到磁盘，重启后直接加载。
    """

    def __init__(self, registry):
        self.registry = registry
        load_dotenv()
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _cache_path(self, primitive_id: str) -> str:
        return os.path.join(CACHE_DIR, f"{primitive_id}.py")

    def _load_from_cache(self, primitive_id: str):
        """从磁盘缓存加载原语，返回实例或 None。"""
        path = self._cache_path(primitive_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                code = f.read()
            namespace = {
                "CapabilityPrimitive": CapabilityPrimitive,
                "TypeSignature": TypeSignature,
            }
            exec(code, namespace)
            for name, obj in namespace.items():
                if (inspect.isclass(obj) and
                    issubclass(obj, CapabilityPrimitive) and
                    obj is not CapabilityPrimitive):
                    instance = obj()
                    self.registry.register(instance)
                    print(f"[DynGen] Loaded from cache: {primitive_id}")
                    return instance
        except Exception as e:
            print(f"[DynGen] Cache load failed: {e}")
        return None

    def _save_to_cache(self, primitive_id: str, code: str):
        """保存原语代码到磁盘缓存。"""
        path = self._cache_path(primitive_id)
        with open(path, "w") as f:
            f.write(code)
        print(f"[DynGen] Cached: {path}")

    def generate(self, primitive_id: str, intent: str) -> CapabilityPrimitive:
        """根据意图动态生成一个新原语并注册，优先从缓存加载。"""

        # 先尝试从缓存加载
        cached = self._load_from_cache(primitive_id)
        if cached:
            return cached

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
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1])

        print(f"[DynGen] Generated code:\n{code[:200]}...")

        namespace = {
            "CapabilityPrimitive": CapabilityPrimitive,
            "TypeSignature": TypeSignature,
        }
        exec(code, namespace)

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

        # 保存到缓存
        self._save_to_cache(primitive_id, code)

        print(f"[DynGen] Registered: {instance.id}")
        return instance

    def load_all_cached(self):
        """启动时加载所有缓存的原语。"""
        if not os.path.exists(CACHE_DIR):
            return
        count = 0
        for fname in os.listdir(CACHE_DIR):
            if fname.endswith(".py"):
                pid = fname[:-3]
                try:
                    self.registry.get(pid)
                except KeyError:
                    if self._load_from_cache(pid):
                        count += 1
        if count:
            print(f"[DynGen] Loaded {count} cached primitives")
