from __future__ import annotations

import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

from core.primitive import CapabilityPrimitive, TypeSignature


class NLPTranslatePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="NLP_TRANSLATE",
            type_signature=TypeSignature(
                type_in=["text", "file_content"], type_out=["text", "translated_text"]
            ),
            semantic_descriptor="Translate text into a target language.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        text = input_data.get("text") or input_data.get("content") or ""
        if not isinstance(text, str):
            text = str(text)
        target_lang = input_data.get("target_lang", "French")
        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            try:
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com",
                )
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a translator. Translate the following text to {target_lang}. Return only the translated text, nothing else.",
                        },
                        {"role": "user", "content": text},
                    ],
                    temperature=0,
                )
                translated = (response.choices[0].message.content or "").strip()
                return {
                    "translated": translated,
                    "confidence": 1.0,
                    "target_lang": target_lang,
                }
            except Exception as e:
                print(f"[NLP_TRANSLATE] API error, using fallback: {e}")
        return {
            "translated": f"[{target_lang}] {text}",
            "confidence": 0.99,
            "target_lang": target_lang,
        }


class NLPEncodePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="NLP_ENCODE",
            type_signature=TypeSignature(
                type_in=["text", "file_content"], type_out=["embedding", "text"]
            ),
            semantic_descriptor="Encode text into a vector embedding.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        text = input_data.get("text", "")
        dim = 8
        # simple deterministic mock embedding based on character ordinals
        embedding: List[float] = [float((ord(c) % 10)) for c in (text[:dim].ljust(dim))]  # type: ignore[arg-type]
        return {
            "embedding": embedding,
            "dim": dim,
        }



class NLPSummarizePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="NLP_SUMMARIZE",
            type_signature=TypeSignature(
                type_in=["text", "file_content", "dom_tree"],
                type_out=["text", "summary"],
            ),
            semantic_descriptor="Summarize text or webpage content into a concise summary.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {list(input_data.keys())}")
        # 从多个可能的字段获取文本
        text = (
            input_data.get("text") or
            input_data.get("content") or
            input_data.get("body") or
            ""
        )
        # 如果是 dom_tree，提取文本
        dom = input_data.get("dom_tree")
        if dom and isinstance(dom, dict):
            text = dom.get("text") or dom.get("title") or text

        if not isinstance(text, str):
            text = str(text)

        # 截断太长的文本
        if len(text) > 3000:
            text = text[:3000]

        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key and text.strip():
            try:
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com",
                )
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个内容总结助手。请用简洁的中文总结以下内容，不超过100字。只返回总结内容，不要其他说明。",
                        },
                        {"role": "user", "content": text},
                    ],
                    temperature=0,
                )
                summary = (response.choices[0].message.content or "").strip()
                return {"summary": summary, "text": summary}
            except Exception as e:
                print(f"[NLP_SUMMARIZE] API error: {e}")

        # fallback
        sentences = text.split(".")[:3]
        summary = ". ".join(s.strip() for s in sentences if s.strip())
        return {"summary": summary[:200], "text": summary[:200]}


class NLPSummarizePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="NLP_SUMMARIZE",
            type_signature=TypeSignature(
                type_in=["text", "file_content", "dom_tree"],
                type_out=["text", "summary"],
            ),
            semantic_descriptor="Summarize text or webpage content into a concise summary.",
        )

    def invoke(self, input_data, session_id=None):
        print(f"[{self.id}] invoked with: {list(input_data.keys())}")
        text = (input_data.get("text") or input_data.get("content") or input_data.get("body") or "")
        dom = input_data.get("dom_tree")
        if dom and isinstance(dom, dict):
            text = dom.get("text") or dom.get("title") or text
        if not isinstance(text, str):
            text = str(text)
        if len(text) > 3000:
            text = text[:3000]
        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key and text.strip():
            try:
                client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是内容总结助手。用简洁中文总结以下内容，不超过100字。只返回总结，不要其他说明。"},
                        {"role": "user", "content": text},
                    ],
                    temperature=0,
                )
                summary = (response.choices[0].message.content or "").strip()
                return {"summary": summary, "text": summary}
            except Exception as e:
                print(f"[NLP_SUMMARIZE] error: {e}")
        summary = text[:200]
        return {"summary": summary, "text": summary}
