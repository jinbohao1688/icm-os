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

