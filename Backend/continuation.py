"""
Text Generation (Rewrite & Continue)

Handles: LLM loading, prompt building, candidate generation, reranking, and the public API for rewrite/continue.
"""

import torch
from typing import List, Dict, Any, Tuple

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)

from author_rag import (
    # Config
    DEBUG_PRINT, DEVICE,
    EN_GEN_MODEL, NE_GEN_MODEL,
    MAX_EXEMPLARS, REWRITE_MAX_NEW_TOKENS, CONT_MAX_NEW_TOKENS,
    TEMPERATURE, TOP_P, REP_PENALTY, NO_REPEAT_NGRAM, NUM_CANDS,
    W_CONTENT, W_STYLE_DISCRIM, W_NOVELTY,
    REJECT_COPY6_AT, REJECT_JAC_AT,
    MIN_LEN_RATIO, MAX_LEN_RATIO,
    # RAG infrastructure
    AUTHORS, AUTHOR_LANG, AUTHOR_CENTROIDS,
    embedder, retrieve_exemplars, style_samples,
    validate_lang_or_raise, style_scores_discriminative,
    # Utils
    normalize_ws, clean_output, is_degenerate, dedupe_keep_order,
    ngram_overlap_frac, token_jaccard, strip_non_devanagari,
    added_digits_penalty, must_keep_ratio_en, is_questiony_junk,
)

import numpy as np


# LOAD GENERATORS
def load_llm_4bit(model_name: str, compute_dtype=torch.float16):
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

# English: Qwen 3B
print("[continuation] Loading EN generator (Qwen 3B, 4-bit) …")
tok_en, llm_en = load_llm_4bit(EN_GEN_MODEL)

# Nepali: Gemma 3 4B text-only
if NE_GEN_MODEL != EN_GEN_MODEL:
    print(f"[continuation] Loading NE generator (Gemma 3 4B, 4-bit) …")
    tok_ne, llm_ne = load_llm_4bit(NE_GEN_MODEL, compute_dtype=torch.bfloat16)
else:
    print("[continuation] Using same model for Nepali …")
    tok_ne, llm_ne = tok_en, llm_en


# PROMPTS (Rewrite / Continue)
def build_messages(task: str, user_text: str, author: str, style_lines: str, lang: str) -> List[Dict[str, str]]:
    """
    Returns chat messages for models that support chat templates.
    """
    if task == "rewrite":
        if lang == "en":
            sys = "You are a strict rewriting assistant that never hallucinates."
            user = (
                f"Rewrite the following text in the writing style of {author}.\n"
                f"CRITICAL RULES:\n"
                f"1. Preserve the original meaning exactly.\n"
                f"2. Keep all ORIGINAL names exactly as they are spelled in the input.\n"
                f"3. Do NOT add any new characters, dialogue, or events not present in the input.\n"
                f"4. The 'Style samples' below are ONLY for tone. DO NOT use any names or specific events from the style samples.\n"
                f"5. Output ONLY the rewritten text, starting immediately.\n\n"
                f"Style samples for tone ONLY:\n{style_lines}\n\n"
                f"Text to rewrite:\n{user_text}"
            )
        else:
            sys = (
                "You are a strict rewriting assistant. "
                "You MUST respond fully in Nepali (Devanagari). "
                "Do NOT output English. Output ONLY the rewritten text."
            )
            user = (
                f"{author} को लेखनशैलीमा तलको पाठ पुनर्लेखन गर।\n"
                f"कडा नियमहरू:\n"
                f"१. मूल अर्थ उस्तै राख।\n"
                f"२. दिइएको पाठका नामहरूलाई जस्ताको तस्तै राख।\n"
                f"३. पाठमा नभएका नयाँ पात्र, संवाद वा घटना नथप।\n"
                f"४. तलको 'शैली नमुना' केवल भाषा र टोनको लागि हो। नमुनामा भएका कुनै पनि नाम वा विषयवस्तु प्रयोग नगर।\n"
                f"५. केवल पुनर्लेखित पाठ मात्र देऊ।\n\n"
                f"शैली नमुना (टोनको लागि मात्र):\n{style_lines}\n\n"
                f"पुनर्लेखन गर्नुपर्ने पाठ:\n{user_text}"
            )
    elif task == "continue":
        if lang == "en":
            sys = "You are a careful writing assistant."
            user = (
                f"Continue the text in the writing style of {author}.\n"
                f"Hard constraints:\n"
                f"- Continue naturally from the last sentence.\n"
                f"- Do NOT add unrelated facts.\n"
                f"- Keep tense and viewpoint consistent.\n"
                f"- Output ONLY the continuation (no headings/explanations).\n\n"
                f"Style samples:\n{style_lines}\n\n"
                f"Text to continue:\n{user_text}"
            )
        else:
            sys = (
                "You are a careful writing assistant. "
                "You MUST respond fully in Nepali (Devanagari). "
                "Do NOT output English. Output ONLY the continuation."
            )
            user = (
                f"{author} को लेखनशैलीमा तलको पाठलाई अगाडि बढाऊ।\n"
                f"कडा नियमहरू:\n"
                f"- अन्तिम वाक्यबाट स्वाभाविक रूपमा निरन्तरता देऊ।\n"
                f"- असम्बन्धित नयाँ तथ्य नथप।\n"
                f"- काल/दृष्टिकोण उस्तै राख।\n"
                f"- केवल निरन्तरता मात्र देऊ (शीर्षक/व्याख्या होइन)।\n\n"
                f"शैली नमुना:\n{style_lines}\n\n"
                f"अगाडि बढाउनुपर्ने पाठ:\n{user_text}"
            )
    else:
        raise ValueError(f"Unknown task: {task}")

    return [{"role": "system", "content": sys}, {"role": "user", "content": user}]


def apply_chat_template(tok, messages: List[Dict[str, str]]) -> Dict[str, torch.Tensor]:
    """
    Use model chat template if available. If not, fallback to a simple format.
    """
    if hasattr(tok, "apply_chat_template"):
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        # fallback
        sys = messages[0]["content"]
        user = messages[1]["content"]
        text = f"System: {sys}\nUser: {user}\nAssistant:"
    return tok(text, return_tensors="pt", padding=True, truncation=True)


# CANDIDATE GENERATION
def gen_candidates(tok, model, messages: List[Dict[str, str]], max_new_tokens: int, n: int) -> List[str]:
    inputs = apply_chat_template(tok, messages).to(next(model.parameters()).device)
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
            temperature=TEMPERATURE,
            top_p=TOP_P,
            repetition_penalty=REP_PENALTY,
            no_repeat_ngram_size=NO_REPEAT_NGRAM,
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


# RERANK
def rerank(user_text: str, candidates: List[str], exemplars: List[Dict[str, Any]], author: str) -> Tuple[str, List[Dict[str, Any]]]:
    if not candidates:
        return "", []

    u = normalize_ws(user_text)
    L = len(u)

    u_emb = embedder.encode([u], normalize_embeddings=True)[0]
    c_embs = embedder.encode(candidates, normalize_embeddings=True)

    scored = []
    best_text, best_score = "", -1e9

    for t, emb in zip(candidates, c_embs):
        if not t:
            continue
        if is_questiony_junk(t):
            continue
        if len(t) < int(L * MIN_LEN_RATIO) or len(t) > int(L * MAX_LEN_RATIO):
            continue
        if added_digits_penalty(u, t):
            continue

        copy6 = ngram_overlap_frac(u, t, 6)
        jac = token_jaccard(u, t)
        if copy6 >= REJECT_COPY6_AT or jac >= REJECT_JAC_AT:
            continue

        keep = must_keep_ratio_en(u, t)
        if keep < 0.35:
            continue

        style_t, style_other, style_discrim = style_scores_discriminative(author, emb)
        content = float(np.dot(u_emb, emb))
        novelty = 1.0 - max(copy6, jac)

        score = W_CONTENT * content + W_STYLE_DISCRIM * style_discrim + W_NOVELTY * novelty
        row = {
            "text": t,
            "score": score,
            "copy6": copy6,
            "jac": jac,
            "keep": keep,
            "style_discrim": style_discrim,
            "content": content,
            "novelty": novelty,
        }
        scored.append(row)

        if score > best_score:
            best_score = score
            best_text = t

    if not best_text and candidates:
        for fallback in candidates:
            fallback = clean_output(fallback)
            if not fallback or is_questiony_junk(fallback) or is_degenerate(fallback):
                continue
            if DEBUG_PRINT:
                print(f"[RERANK] All candidates filtered; using cleaned fallback.")
            return fallback, scored

    return best_text, scored


# PUBLIC API
def rag_author_generate(text: str, author: str, task: str = "rewrite") -> Dict[str, Any]:
    """
    task: "rewrite" or "continue"
    """
    if author not in AUTHORS:
        raise ValueError(f"Unknown author: {author}")

    text = normalize_ws(text)
    if not text:
        return {"language": "en", "author": author, "task": task, "output": ""}

    src_lang, author_lang = validate_lang_or_raise(text, author)

    exemplars = retrieve_exemplars(text, author, MAX_EXEMPLARS)
    style_lines = style_samples(exemplars, max_lines=3)

    if author_lang == "en":
        messages = build_messages(task, text, author, style_lines, "en")
        cands = gen_candidates(tok_en, llm_en, messages, REWRITE_MAX_NEW_TOKENS if task == "rewrite" else CONT_MAX_NEW_TOKENS, NUM_CANDS)
    else:
        messages = build_messages(task, text, author, style_lines, "ne")
        cands = gen_candidates(tok_ne, llm_ne, messages, REWRITE_MAX_NEW_TOKENS if task == "rewrite" else CONT_MAX_NEW_TOKENS, NUM_CANDS)
        # Strip non-Devanagari Indic scripts (Gujarati, Bengali, etc.)
        cands = [strip_non_devanagari(c) for c in cands]
        cands = [c for c in cands if c.strip()]

    chosen, scored = rerank(text, cands, exemplars, author)

    if DEBUG_PRINT:
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
        "candidates": cands if DEBUG_PRINT else [],
        "exemplars_used": [e.get("path", "") for e in exemplars],
    }

def rag_author_rewrite(text: str, author: str) -> Dict[str, Any]:
    return rag_author_generate(text, author, task="rewrite")

def rag_author_continue(text: str, author: str) -> Dict[str, Any]:
    return rag_author_generate(text, author, task="continue")
