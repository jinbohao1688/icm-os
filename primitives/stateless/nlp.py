from __future__ import annotations

from typing import Any, Dict, List

from core.primitive import CapabilityPrimitive, TypeSignature


class NLPTranslatePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="NLP_TRANSLATE",
            type_signature=TypeSignature(
                type_in=["NLPTranslateInput"], type_out=["NLPTranslateOutput"]
            ),
            semantic_descriptor="Translate text into a target language.",
        )

    def invoke(self, input_data: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
        print(f"[{self.id}] invoked with: {input_data}")
        text = input_data.get("text", "")
        target_lang = input_data.get("target_lang", "en")
        return {
            "translated": f"[{target_lang}] {text}",
            "confidence": 0.99,
        }


class NLPEncodePrimitive(CapabilityPrimitive):
    def __init__(self) -> None:
        super().__init__(
            id="NLP_ENCODE",
            type_signature=TypeSignature(
                type_in=["NLPEncodeInput"], type_out=["NLPEncodeOutput"]
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

