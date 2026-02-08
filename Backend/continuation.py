import torch
import numpy as np
import re
import author_rag
from author_rag import (
    llama_model, tok_llama, DEVICE, 
    retrieve_exemplars, style_samples, truncate_to_tokens, 
    clean_output, dedupe_keep_order, 
    embedder, AUTHOR_CENTROIDS,
    _safe_terminators,
    flan, tok_flan,
    style_scores_discriminative
)

# Config for continuation
CONTINUE_MAX_NEW_TOKENS = 320
CONTINUE_TEMPERATURE = 0.75
CONTINUE_TOP_P = 0.9
CONTINUE_REP_PENALTY = 1.1

def compute_local_metrics(text: str) -> dict:
    """
    Computes simple stylometric features:
    - asl: Average Sentence Length (words)
    - ttr: Type-Token Ratio (unique/total words)
    - punct_density: Punctuation chars per 100 chars
    """
    if not text:
        return {"asl": 0, "ttr": 0, "punct_density": 0}
    
    # ASL
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    num_sents = max(1, len(sentences))
    words = text.split()
    num_words = len(words)
    asl = num_words / num_sents
    
    # TTR
    unique_words = set(w.lower() for w in words)
    ttr = len(unique_words) / max(1, num_words)
    
    # Punctuation Density
    punct_chars = len(re.findall(r'[.,;:"\'!?()-]', text))
    punct_density = (punct_chars / max(1, len(text))) * 100
    
    return {"asl": asl, "ttr": ttr, "punct_density": punct_density}

def gen_continuation_candidates(text: str, author: str, exemplars: list, n: int) -> list:
    if llama_model is None or tok_llama is None:
        return []

    styles = style_samples(exemplars, max_lines=3)
    user_trim = truncate_to_tokens(tok_llama, text, 400) 

    sys_msg = (
        "You are a creative writing assistant. "
        "You MUST continue the story or text in the exact style of the requested author. "
        "Do not rewrite the input; only add new text that flows naturally from it."
    )
    user_msg = (
        f"Continue the following text in the style of {author}.\n"
        f"Style samples:\n{styles}\n\n"
        f"Input Text:\n{user_trim}\n\n"
        f"Continuation:"
    )

    formatted_prompt = f"<|system|>{sys_msg}<|user|>{user_msg}<|assistant|>"

    inputs = tok_llama(
        formatted_prompt,
        return_tensors="pt",
        truncation=True,
        max_length=1024,
        padding=False
    ).to(DEVICE)

    inp_len = inputs.input_ids.shape[-1]
    terminators = _safe_terminators(tok_llama)
    
    model_to_run = llama_model.module if hasattr(llama_model, "module") else llama_model

    print(f"Generating continuation candidates for {author}...", flush=True)
    with torch.inference_mode():
        outputs = model_to_run.generate(
            **inputs,
            max_new_tokens=CONTINUE_MAX_NEW_TOKENS,
            do_sample=True,
            temperature=CONTINUE_TEMPERATURE,
            top_p=CONTINUE_TOP_P,
            repetition_penalty=CONTINUE_REP_PENALTY,
            num_return_sequences=n,
            eos_token_id=terminators if terminators else tok_llama.eos_token_id,
            pad_token_id=tok_llama.eos_token_id,
        )
    print("Generation candidates produced.", flush=True)

    cands = []
    for seq in outputs:
        resp_ids = seq[inp_len:]
        resp = clean_output(tok_llama.decode(resp_ids, skip_special_tokens=True))
        if resp:
            cands.append(resp)

    return dedupe_keep_order(cands)

def gen_flan_continuation(text: str, author: str, exemplars: list, n: int) -> list:
    if flan is None or tok_flan is None:
        return []

    styles = style_samples(exemplars, max_lines=3)
    user_trim = truncate_to_tokens(tok_flan, text, 400)
    
    # Flan prompt for continuation
    prompt = (
        f"Continue the following text in the style of {author}.\n"
        f"Style samples:\n{styles}\n\n"
        f"Text:\n{user_trim}\n\n"
        f"Continuation:"
    )
    
    inp = tok_flan(prompt, return_tensors="pt", truncation=True, max_length=1024).to(flan.device)
    
    with torch.no_grad():
        outs = flan.generate(
            **inp,
            max_new_tokens=260,
            do_sample=True,
            temperature=0.9,
            top_p=0.9,
            repetition_penalty=1.15,
            num_return_sequences=n,
        )
    cands = [clean_output(tok_flan.decode(o, skip_special_tokens=True)) for o in outs]
    return dedupe_keep_order(cands)

def rag_author_continue(text: str, author: str) -> str:
    """
    Continues the text in the style of the author using ensemble generation (Flan + Llama).
    """
    if author not in author_rag.AUTHORS:
         pass

    exemplars = retrieve_exemplars(text, author, 5)
    
    
    # 1. Generate Candidates from Multiple Models
    cands_llama = gen_continuation_candidates(text, author, exemplars, n=3)
    cands_flan = gen_flan_continuation(text, author, exemplars, n=5)
    
    # Combine (Flan 5 + Llama 3 = 8 candidates)
    all_cands = []
    for c in cands_llama:
        all_cands.append({"text": c, "src": "llama"})
    for c in cands_flan:
        all_cands.append({"text": c, "src": "flan"})
        
    if not all_cands:
        return "Unable to generate continuation."

    # ENHANCED RAG RERANKING
    # Calculate exemplar metrics on the fly
    exemplar_metrics = []
    for ex in exemplars:
         txt = ex.get("chunk", "")
         if txt:
             exemplar_metrics.append(compute_local_metrics(txt))

    # Target Profile from Exemplars
    target_asl = np.mean([m["asl"] for m in exemplar_metrics]) if exemplar_metrics else 15.0
    target_ttr = np.mean([m["ttr"] for m in exemplar_metrics]) if exemplar_metrics else 0.7
    target_punct = np.mean([m["punct_density"] for m in exemplar_metrics]) if exemplar_metrics else 2.0
    
    print(f"Target Profile (from RAG): ASL={target_asl:.1f}, TTR={target_ttr:.2f}, Punct={target_punct:.1f}", flush=True)

    best_cand = all_cands[0]["text"]
    best_score = -1e9
    
    cand_texts = [c["text"] for c in all_cands]
    cand_embs = embedder.encode(cand_texts, normalize_embeddings=True)
    
    for i, c_obj in enumerate(all_cands):
        cand_text = c_obj["text"]
        src = c_obj["src"]
        
        # A. Style Discriminative Score (Robust Author Matching)
        # Using author_rag's discriminative logic (Target Author vs Other Authors)
        _, _, style_discrim = style_scores_discriminative(author, cand_embs[i])
            
        # B. Local Stylometric Match
        cm = compute_local_metrics(cand_text)
        diff_asl = abs(cm["asl"] - target_asl) / max(1, target_asl)
        diff_ttr = abs(cm["ttr"] - target_ttr) / max(0.01, target_ttr)
        diff_punct = abs(cm["punct_density"] - target_punct) / max(0.1, target_punct)
        local_match_score = 1.0 - (0.4 * diff_asl + 0.3 * diff_ttr + 0.3 * diff_punct)
        
        # C. Source Bonus (Llama is generally better at continuation than Flan)
        src_bonus = 0.05 if src == "llama" else 0.0
        
        # Combined Score
        # Style Discriminative (0.5) + Local Match (0.4) + Bonus (0.1)
        final_score = (0.5 * style_discrim) + (0.4 * local_match_score) + src_bonus
        
        print(f"[{src}] Cand {i+1}: Discrim={style_discrim:.3f} Local={local_match_score:.3f} -> Final={final_score:.3f}", flush=True)
        
        if final_score > best_score:
            best_score = final_score
            best_cand = cand_text
            
    return best_cand
