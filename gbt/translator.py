from __future__ import annotations

from dataclasses import dataclass

from gbt.lifter import SemanticLifter
from gbt.sir import SemanticIR
from gbt.synthesizer import CodeSynthesizer
from gbt.verifier import BehavioralVerifier, VerificationResult


@dataclass
class TranslationResult:
    sir: SemanticIR
    synthesized_code: str
    verification: VerificationResult


def GBT(binary_path: str, src_isa: str, dst_isa: str = "x86-64") -> TranslationResult:
    """
    High-level entry point for Generative Binary Translation (GBT).

    1. Lift source binary into SIR.
    2. Synthesize destination ISA code.
    3. Optionally verify behavioral equivalence.
    """
    lifter = SemanticLifter()
    synthesizer = CodeSynthesizer()
    verifier = BehavioralVerifier()

    sir = lifter.lift_with_limit(binary_path, arch=src_isa, max_blocks=5)
    synthesized = synthesizer.synthesize(sir, dst_isa=dst_isa)
    verification = verifier.verify(sir, synthesized)

    return TranslationResult(sir=sir, synthesized_code=synthesized, verification=verification)

