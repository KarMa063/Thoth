import torch
from typing import List, Dict, Any

from config import Config
from rag import AuthorRegistry, RetrieverService
from utils import normalize_ws, clean_output, dedupe_keep_order, strip_non_devanagari
from .llm_loader import LLMLoader
from .prompt_builder import PromptBuilder
from .reranker import Reranker

class GenerationService:
    def __init__(
        self,
        config: Config,
        registry: AuthorRegistry,
        retriever: RetrieverService,
        loader: LLMLoader,
        prompt_builder: PromptBuilder,
        reranker: Reranker
    ):
        self._config = config
        self._registry = registry
        self._retriever = retriever
        self._loader = loader
        self._prompt_builder = prompt_builder
        self._reranker = reranker

    def _gen_candidates(self, tok, model, messages: List[Dict[str, str]], max_new_tokens: int, n: int) -> List[str]:
        inputs = self._prompt_builder.apply_chat_template(tok, messages).to(next(model.parameters()).device)
        input_ids = inputs["input_ids"]
        attention_mask = inputs["attention_mask"]
        inp_len = input_ids.shape[-1]

        pad_id = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id

        with torch.inference_mode():
            outs = model.generate(
                input_ids=input_ids,    
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=self._config.temperature,
                top_p=self._config.top_p,
                repetition_penalty=self._config.rep_penalty,
                no_repeat_ngram_size=self._config.no_repeat_ngram,
                num_return_sequences=n,
                pad_token_id=pad_id,
                eos_token_id=tok.eos_token_id,
            )

        cands = []
        for seq in outs:
            gen_ids = seq[inp_len:]
            txt = tok.decode(gen_ids, skip_special_tokens=True)
            txt = clean_output(txt)
            if txt:
                cands.append(txt)
        return dedupe_keep_order(cands)

    def generate(self, text: str, author: str, task: str = "rewrite") -> Dict[str, Any]:
        if author not in self._registry.get_authors():
            raise ValueError(f"Unknown author: {author}")

        text = normalize_ws(text)
        if not text:
            return {"language": "en", "author": author, "task": task, "output": ""}

        src_lang, author_lang = self._registry.validate_lang_or_raise(text, author)

        exemplars = self._retriever.retrieve_exemplars(text, author, self._config.max_exemplars)
        style_lines = self._retriever.style_samples(exemplars, max_lines=3)

        max_tokens = self._config.rewrite_max_new_tokens if task == "rewrite" else self._config.cont_max_new_tokens

        if author_lang == "en":
            messages = self._prompt_builder.build_messages(task, text, author, style_lines, "en")
            tok, model = self._loader.en_pair
            cands = self._gen_candidates(tok, model, messages, max_tokens, self._config.num_cands)
        else:
            messages = self._prompt_builder.build_messages(task, text, author, style_lines, "ne")
            tok, model = self._loader.ne_pair
            cands = self._gen_candidates(tok, model, messages, max_tokens, self._config.num_cands)
            cands = [strip_non_devanagari(c) for c in cands]
            cands = [c for c in cands if c.strip()]

        chosen, scored = self._reranker.rerank(text, cands, exemplars, author)

        if self._config.debug_print:
            print(f"\n[{task.upper()}] author={author} lang={author_lang} candidates={len(cands)}")
            for i, c in enumerate(cands, 1):
                print(f"  {i}. {c[:160]}{'...' if len(c) > 160 else ''}")
            print(f"[CHOSEN] {chosen}\n")

            if scored:
                top = sorted(scored, key=lambda r: r["score"], reverse=True)[:5]
                print("[TOP SCORES]")
                for r in top:
                    print(f"  score={r['score']:.3f} sd={r['style_discrim']:.3f} cont={r['content']:.3f} nov={r['novelty']:.3f} -> {r['text'][:120]}...")

        return {
            "task": task,
            "language": author_lang,
            "detected_input_language": src_lang,
            "author": author,
            "output": chosen,
            "candidates": cands if self._config.debug_print else [],
            "exemplars_used": [e.get("path", "") for e in exemplars],
        }

    def rewrite(self, text: str, author: str) -> Dict[str, Any]:
        return self.generate(text, author, task="rewrite")

    def continue_text(self, text: str, author: str) -> Dict[str, Any]:
        return self.generate(text, author, task="continue")
