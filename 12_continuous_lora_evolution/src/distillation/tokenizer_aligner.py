"""
Cross-Family Tokenizer Alignment Validator & Dynamic ChatML/Header Formatter.

Supports:
- Qwen 2.5 / 3.8 Family (ChatML, Vocab 151,665)
- SmolLM2 Family (ChatML, Vocab 49,152)
- Llama 3.2 Family (Llama-3 Header, Vocab 128,256)
- Hermes 3 Family (ChatML on Llama-3 Vocab 128,256)

Validates vocabulary alignment, pad/eos/bos tokens, dynamic chat templates,
and detects cross-family token-ID incompatibilities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class TokenizerMismatchError(Exception):
    """Raised when incompatible tokenizers, token IDs, or vocabulary mismatches occur."""
    pass


@dataclass
class TokenizerProfile:
    """Canonical specifications for known model families."""
    name: str
    vocab_size: int
    format_type: str  # 'chatml' or 'llama3'
    default_bos_token: Optional[str]
    default_eos_token: str
    default_pad_token: str
    special_tokens: List[str] = field(default_factory=list)


KNOWN_PROFILES: Dict[str, TokenizerProfile] = {
    "qwen": TokenizerProfile(
        name="qwen",
        vocab_size=151665,
        format_type="chatml",
        default_bos_token=None,
        default_eos_token="<|im_end|>",
        default_pad_token="<|endoftext|>",
        special_tokens=["<|im_start|>", "<|im_end|>", "<|endoftext|>"],
    ),
    "smollm2": TokenizerProfile(
        name="smollm2",
        vocab_size=49152,
        format_type="chatml",
        default_bos_token="<|im_start|>",
        default_eos_token="<|im_end|>",
        default_pad_token="<|im_end|>",
        special_tokens=["<|im_start|>", "<|im_end|>", "<|endoftext|>"],
    ),
    "llama32": TokenizerProfile(
        name="llama32",
        vocab_size=128256,
        format_type="llama3",
        default_bos_token="<|begin_of_text|>",
        default_eos_token="<|eot_id|>",
        default_pad_token="<|finetune_right_pad_id|>",
        special_tokens=["<|begin_of_text|>", "<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>"],
    ),
    "hermes3": TokenizerProfile(
        name="hermes3",
        vocab_size=128256,
        format_type="chatml",
        default_bos_token="<|begin_of_text|>",
        default_eos_token="<|im_end|>",
        default_pad_token="<|im_end|>",
        special_tokens=["<|begin_of_text|>", "<|im_start|>", "<|im_end|>"],
    ),
}


def detect_model_family(name_or_obj: Union[str, Any]) -> str:
    """
    Detects the model family from a model name, path, or tokenizer object.
    Returns: 'qwen', 'smollm2', 'llama32', 'hermes3', or 'generic'.
    """
    identifier = ""
    if isinstance(name_or_obj, str):
        identifier = name_or_obj.lower()
    else:
        # Check tokenizer attributes
        name = getattr(name_or_obj, "name_or_path", "") or ""
        cls_name = name_or_obj.__class__.__name__.lower()
        identifier = f"{name} {cls_name}".lower()

    if "qwen" in identifier:
        return "qwen"
    elif "smollm" in identifier or "smol" in identifier:
        return "smollm2"
    elif "hermes" in identifier:
        return "hermes3"
    elif "llama" in identifier:
        return "llama32"
    return "generic"


class DynamicChatFormatter:
    """
    Dynamic ChatML / Header template renderer for multi-turn and DPO pairwise dialogues.
    """

    @staticmethod
    def render_chatml(
        messages: List[Dict[str, str]], add_generation_prompt: bool = False
    ) -> str:
        """Renders messages using the standard ChatML specification."""
        rendered = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            rendered.append(f"<|im_start|>{role}\n{content}<|im_end|>")

        result = "\n".join(rendered)
        if add_generation_prompt:
            result += "\n<|im_start|>assistant\n"
        return result

    @staticmethod
    def render_llama3(
        messages: List[Dict[str, str]], add_generation_prompt: bool = False
    ) -> str:
        """Renders messages using the Llama-3 header format."""
        rendered = ["<|begin_of_text|>"]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            rendered.append(
                f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
            )

        result = "".join(rendered)
        if add_generation_prompt:
            result += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        return result

    @classmethod
    def render(
        cls,
        messages: List[Dict[str, str]],
        tokenizer: Optional[Any] = None,
        family: Optional[str] = None,
        add_generation_prompt: bool = False,
    ) -> str:
        """
        Renders messages into a formatted prompt string.
        Prioritizes tokenizer's native `apply_chat_template` if available and working;
        otherwise falls back to model family template renderer.
        """
        # Try tokenizer's apply_chat_template first
        if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
            try:
                # Some tokenizers may require chat_template to be set
                if getattr(tokenizer, "chat_template", None) is not None:
                    out = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=add_generation_prompt,
                    )
                    if isinstance(out, str) and out.strip():
                        return out
            except Exception as e:
                logger.debug(f"apply_chat_template failed: {e}, falling back to built-in formatter")

        # Fallback based on family
        if family is None and tokenizer is not None:
            family = detect_model_family(tokenizer)
        family = family or "generic"

        if family == "llama32":
            return cls.render_llama3(messages, add_generation_prompt=add_generation_prompt)
        # Default to ChatML for qwen, smollm2, hermes3, generic
        return cls.render_chatml(messages, add_generation_prompt=add_generation_prompt)

    @classmethod
    def format_dpo_pair(
        cls,
        prompt: Union[str, List[Dict[str, str]]],
        chosen: str,
        rejected: str,
        tokenizer: Optional[Any] = None,
        family: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        Formats a DPO preference pair into (formatted_prompt, chosen_response, rejected_response).
        """
        if isinstance(prompt, list):
            prompt_str = cls.render(
                prompt, tokenizer=tokenizer, family=family, add_generation_prompt=True
            )
        else:
            prompt_msgs = [{"role": "user", "content": prompt}]
            prompt_str = cls.render(
                prompt_msgs, tokenizer=tokenizer, family=family, add_generation_prompt=True
            )

        chosen_str = chosen.strip()
        rejected_str = rejected.strip()
        return prompt_str, chosen_str, rejected_str


@dataclass
class TokenizerValidationResult:
    """Results of pre-flight tokenizer alignment validation."""
    is_valid: bool
    family: str
    vocab_size: int
    pad_token: Optional[str]
    pad_token_id: Optional[int]
    eos_token: Optional[str]
    eos_token_id: Optional[int]
    bos_token: Optional[str]
    bos_token_id: Optional[int]
    padding_side: str
    chat_template_present: bool
    issues: List[str] = field(default_factory=list)


class TokenizerAligner:
    """
    Validates and aligns tokenizer configurations across model families.
    """

    @classmethod
    def align_tokenizer(
        cls, tokenizer: Any, model_family: Optional[str] = None
    ) -> Any:
        """
        Configures pad_token, pad_token_id, and padding_side for the given tokenizer.
        """
        if model_family is None:
            model_family = detect_model_family(tokenizer)

        profile = KNOWN_PROFILES.get(model_family)

        # Set padding side to right for causal language modeling / DPO
        if hasattr(tokenizer, "padding_side"):
            tokenizer.padding_side = "right"

        # Handle PAD token assignment
        if getattr(tokenizer, "pad_token", None) is None:
            if profile and profile.default_pad_token:
                # Check if default_pad_token exists in vocab or can be added
                pad_tok = profile.default_pad_token
                try:
                    tokenizer.pad_token = pad_tok
                except Exception:
                    pass

            # Fallback to eos_token if still None
            if getattr(tokenizer, "pad_token", None) is None:
                if getattr(tokenizer, "eos_token", None) is not None:
                    tokenizer.pad_token = tokenizer.eos_token
                elif getattr(tokenizer, "pad_token_id", None) is None:
                    tokenizer.pad_token_id = 0

        # Sync pad_token_id
        if getattr(tokenizer, "pad_token_id", None) is None and getattr(tokenizer, "pad_token", None) is not None:
            try:
                tokenizer.pad_token_id = tokenizer.convert_tokens_to_ids(tokenizer.pad_token)
            except Exception:
                pass

        return tokenizer

    @classmethod
    def validate_tokenizer(
        cls,
        tokenizer: Any,
        model_config: Optional[Any] = None,
        expected_family: Optional[str] = None,
    ) -> TokenizerValidationResult:
        """
        Runs comprehensive pre-flight verification on a tokenizer.
        """
        issues: List[str] = []
        family = detect_model_family(tokenizer) if expected_family is None else expected_family
        profile = KNOWN_PROFILES.get(family)

        # 1. Vocab size check
        vocab_size = getattr(tokenizer, "vocab_size", None)
        if vocab_size is None and hasattr(tokenizer, "get_vocab"):
            vocab_size = len(tokenizer.get_vocab())
        elif vocab_size is None and hasattr(tokenizer, "__len__"):
            vocab_size = len(tokenizer)
        vocab_size = vocab_size or 0

        if model_config is not None:
            config_vocab = getattr(model_config, "vocab_size", None)
            if config_vocab is not None and vocab_size != config_vocab:
                issues.append(
                    f"VOCAB_SIZE_MISMATCH: Tokenizer vocab ({vocab_size}) != Model config vocab ({config_vocab})"
                )

        # 2. PAD token check
        pad_token = getattr(tokenizer, "pad_token", None)
        pad_token_id = getattr(tokenizer, "pad_token_id", None)
        if pad_token is None and pad_token_id is None:
            issues.append("MISSING_PAD_TOKEN: Tokenizer has no pad_token or pad_token_id configured")

        # 3. EOS token check
        eos_token = getattr(tokenizer, "eos_token", None)
        eos_token_id = getattr(tokenizer, "eos_token_id", None)
        if eos_token is None and eos_token_id is None:
            issues.append("MISSING_EOS_TOKEN: Tokenizer has no eos_token or eos_token_id configured")

        # 4. BOS token check
        bos_token = getattr(tokenizer, "bos_token", None)
        bos_token_id = getattr(tokenizer, "bos_token_id", None)

        # 5. Padding side check
        padding_side = getattr(tokenizer, "padding_side", "right")

        # 6. Template render check
        chat_template_present = getattr(tokenizer, "chat_template", None) is not None
        test_messages = [
            {"role": "system", "content": "You are an autonomous AI optimizer."},
            {"role": "user", "content": "Run continuous DPO distillation."},
        ]
        try:
            rendered = DynamicChatFormatter.render(
                test_messages, tokenizer=tokenizer, family=family, add_generation_prompt=True
            )
            if not rendered or len(rendered) < 10:
                issues.append("TEMPLATE_RENDER_FAILED: Output was empty or truncated")
        except Exception as e:
            issues.append(f"TEMPLATE_RENDER_EXCEPTION: {e}")

        is_valid = len(issues) == 0

        return TokenizerValidationResult(
            is_valid=is_valid,
            family=family,
            vocab_size=vocab_size,
            pad_token=str(pad_token) if pad_token else None,
            pad_token_id=pad_token_id,
            eos_token=str(eos_token) if eos_token else None,
            eos_token_id=eos_token_id,
            bos_token=str(bos_token) if bos_token else None,
            bos_token_id=bos_token_id,
            padding_side=padding_side,
            chat_template_present=chat_template_present,
            issues=issues,
        )

    @classmethod
    def assert_cross_family_compatibility(
        cls, source_family: str, target_family: str
    ) -> None:
        """
        Asserts whether two tokenizers or token ID streams are compatible.
        Raises TokenizerMismatchError if vocabularies/token IDs are disjoint.
        """
        src = detect_model_family(source_family)
        tgt = detect_model_family(target_family)

        if src != tgt and src != "generic" and tgt != "generic":
            src_prof = KNOWN_PROFILES.get(src)
            tgt_prof = KNOWN_PROFILES.get(tgt)
            src_v = src_prof.vocab_size if src_prof else "unknown"
            tgt_v = tgt_prof.vocab_size if tgt_prof else "unknown"
            raise TokenizerMismatchError(
                f"CROSS_FAMILY_INCOMPATIBILITY: Cannot share pre-tokenized IDs between '{src}' (vocab {src_v}) "
                f"and '{tgt}' (vocab {tgt_v}). Always store datasets as raw text and tokenize dynamically."
            )
