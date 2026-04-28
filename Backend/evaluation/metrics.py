import numpy as np
from typing import List, Dict, Any, Optional

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    pass

try:
    from rouge_score import rouge_scorer
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    import nltk
    nltk.download('punkt', quiet=True)
except ImportError:
    pass

class MetricsCalculator:
    def __init__(self, embed_model: str):
        self.embed_model_name = embed_model
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = SentenceTransformer(self.embed_model_name)
        return self._model

    def compute_semantic_similarity(self, results: List[Dict[str, Any]], label: str) -> Optional[float]:
        success = [r for r in results if r["status"] == "success" and r["output"]]
        if not success:
            print(f"  No successful {label} results")
            return None
            
        try:
            model = self._get_model()
            inputs = [r["input"] for r in success]
            outputs = [r["output"] for r in success]
            inp_emb = model.encode(inputs)
            out_emb = model.encode(outputs)
            sims = [float(cosine_similarity([inp_emb[i]], [out_emb[i]])[0][0])
                    for i in range(len(inputs))]
            avg = round(float(np.mean(sims)), 4)
            print(f"  {label} per-sample: {[round(s,4) for s in sims]}")
            print(f"  {label} average   : {avg}")
            return avg
        except Exception as e:
            print(f"  Semantic similarity failed: {e}")
            return None

    def compute_rouge(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        success = [r for r in results if r.get("status") == "success" and r.get("output")]
        if not success:
            return {}

        scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
        rouge1_scores, rouge2_scores, rougeL_scores = [], [], []

        print("\n=== ROUGE SCORES (per sample) ===")
        for r in success:
            scores = scorer.score(r["input"], r["output"])
            rouge1_scores.append(scores['rouge1'].fmeasure)
            rouge2_scores.append(scores['rouge2'].fmeasure)
            rougeL_scores.append(scores['rougeL'].fmeasure)
            print(f"Input : {r['input'][:60]}...")
            print(f"Output: {r['output'][:60]}...")
            print(f"R1={scores['rouge1'].fmeasure:.4f} "
                  f"R2={scores['rouge2'].fmeasure:.4f} "
                  f"RL={scores['rougeL'].fmeasure:.4f}\n")

        avg_r1 = sum(rouge1_scores)/len(rouge1_scores) if rouge1_scores else 0
        avg_r2 = sum(rouge2_scores)/len(rouge2_scores) if rouge2_scores else 0
        avg_rl = sum(rougeL_scores)/len(rougeL_scores) if rougeL_scores else 0

        print("=== ROUGE AVERAGES ===")
        print(f"ROUGE-1 : {avg_r1:.4f}")
        print(f"ROUGE-2 : {avg_r2:.4f}")
        print(f"ROUGE-L : {avg_rl:.4f}")

        return {"rouge1": avg_r1, "rouge2": avg_r2, "rougeL": avg_rl}

    def compute_bleu(self, results: List[Dict[str, Any]]) -> float:
        success = [r for r in results if r.get("status") == "success" and r.get("output")]
        if not success:
            return 0.0

        print("\n=== BLEU SCORES (per sample) ===")
        bleu_scores = []
        smoothie = SmoothingFunction().method1

        for r in success:
            ref = [r["input"].split()]
            hyp = r["output"].split()
            bleu = sentence_bleu(ref, hyp, smoothing_function=smoothie)
            bleu_scores.append(bleu)
            print(f"BLEU={bleu:.4f} | {r['output'][:60]}...")

        avg_bleu = sum(bleu_scores)/len(bleu_scores) if bleu_scores else 0
        print(f"\nBLEU Average: {avg_bleu:.4f}")
        return avg_bleu

    def summarise(self, english_results: List[Dict], nepali_results: List[Dict]) -> None:
        print("\nComputing semantic similarity...")
        en_sem = self.compute_semantic_similarity(english_results, "English")
        np_sem = self.compute_semantic_similarity(nepali_results, "Nepali")

        en_latencies = [r["latency"] for r in english_results if r["status"] == "success"]
        np_latencies = [r["latency"] for r in nepali_results if r["status"] == "success"]
        en_sim_api = [r["similarity"] for r in english_results if r.get("similarity") is not None]
        np_sim_api = [r["similarity"] for r in nepali_results if r.get("similarity") is not None]

        print("\n========== FINAL METRICS ==========")
        print(f"English avg latency          : {round(sum(en_latencies)/len(en_latencies), 2)}s" if en_latencies else "No English results")
        print(f"Nepali avg latency           : {round(sum(np_latencies)/len(np_latencies), 2)}s" if np_latencies else "No Nepali results")
        print(f"English semantic sim (model) : {en_sem}")
        print(f"Nepali semantic sim (model)  : {np_sem}")
        print(f"English author sim (API)     : {round(sum(en_sim_api)/len(en_sim_api), 4)}" if en_sim_api else "No API similarity scores (English)")
        print(f"Nepali author sim (API)      : {round(sum(np_sim_api)/len(np_sim_api), 4)}" if np_sim_api else "No API similarity scores (Nepali)")
        total_cases = len(english_results) + len(nepali_results)
        passed_cases = len(en_latencies) + len(np_latencies)
        pass_rate = (passed_cases / total_cases * 100) if total_cases > 0 else 0
        print(f"Total test cases             : {total_cases}")
        print(f"Test cases passed            : {passed_cases} ({pass_rate:.0f}%)")
        print("====================================")
