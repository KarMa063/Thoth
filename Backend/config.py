import torch
from dataclasses import dataclass

@dataclass
class Config:
    model_dir: str = "./model"
    embed_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    en_gen_model: str = "Qwen/Qwen2.5-3B-Instruct"
    ne_gen_model: str = "google/gemma-3-4b-it"
    max_exemplars: int = 8
    rewrite_max_new_tokens: int = 180
    cont_max_new_tokens: int = 220
    temperature: float = 0.6
    top_p: float = 0.90
    rep_penalty: float = 1.15
    no_repeat_ngram: int = 4
    num_cands: int = 2
    w_content: float = 0.30
    w_style_discrim: float = 0.45
    w_novelty: float = 0.25
    reject_copy6_at: float = 0.95
    reject_jac_at: float = 0.95
    min_len_ratio: float = 0.30
    max_len_ratio: float = 2.00
    debug_print: bool = True
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
