import torch
from typing import Tuple, Any
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

from config import Config

class LLMLoader:
    def __init__(self, config: Config):
        self._config = config
        self._tok_en = None
        self._llm_en = None
        self._tok_ne = None
        self._llm_ne = None

    def _load_llm_4bit(self, model_name: str, compute_dtype=torch.float16):
        bnb_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=compute_dtype,
        )
        tok = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        if tok.pad_token is None and tok.eos_token is not None:
            tok.pad_token = tok.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_cfg,
            device_map="auto",
            dtype=compute_dtype,
        ).eval()
        return tok, model

    def load(self) -> None:
        if self._config.debug_print:
            print("[LLMLoader] Loading EN generator (Qwen 3B, 4-bit) …")
        self._tok_en, self._llm_en = self._load_llm_4bit(self._config.en_gen_model)

        if self._config.ne_gen_model != self._config.en_gen_model:
            if self._config.debug_print:
                print(f"[LLMLoader] Loading NE generator (Gemma 3 4B, 4-bit) …")
            self._tok_ne, self._llm_ne = self._load_llm_4bit(self._config.ne_gen_model, compute_dtype=torch.bfloat16)
        else:
            if self._config.debug_print:
                print("[LLMLoader] Using same model for Nepali …")
            self._tok_ne, self._llm_ne = self._tok_en, self._llm_en

    @property
    def en_pair(self) -> Tuple[Any, Any]:
        return self._tok_en, self._llm_en

    @property
    def ne_pair(self) -> Tuple[Any, Any]:
        return self._tok_ne, self._llm_ne
