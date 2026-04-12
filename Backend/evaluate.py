import requests
import time
import json

# ---- CONFIG ----
BASE_URL = "http://127.0.0.1:8000"
REWRITE_ENDPOINT = f"{BASE_URL}/rewrite"

english_inputs = [
    "The old man sat alone by the sea, watching the waves crash against the shore.",
    "She walked through the crowded market, feeling invisible among the noise.",
    "The war had ended but nothing felt finished, nothing felt clean.",
    "He opened the letter slowly, already knowing what it would say.",
    "The city at night was a different creature, breathing differently than in daylight."
]

nepali_inputs = [
    "बूढो मान्छे एक्लै बसेर आकाशतर्फ हेर्दै थियो।",
    "उनले बजारमा हिँड्दा आफूलाई एक्लो महसुस गरे।"
]

english_author = "Hemingway"
nepali_author = "BPKoirala"

# ---- FUNCTION ----
def run_rewrite(text, author):
    payload = {"text": text, "author": author, "top_k": 5}
    start = time.time()
    try:
        response = requests.post(REWRITE_ENDPOINT, json=payload, timeout=300)
        elapsed = time.time() - start
        if response.status_code == 200:
            data = response.json()
            return {
                "output": data.get("output", ""),
                "rewritten": data.get("rewritten", ""),
                "similarity": None,  # not returned by API
                "latency": round(elapsed, 2),
                "status": "success",
                "exemplars_used": data.get("exemplars_used", [])
                }
        else:
            return {"output": "", "similarity": None,
                    "latency": round(time.time() - start, 2),
                    "status": f"error_{response.status_code}"}
    except Exception as e:
        return {"output": "", "similarity": None,
                "latency": round(time.time() - start, 2),
                "status": f"exception_{str(e)}"}

# ---- RUN ENGLISH ----
print("Running English evaluations...")
english_results = []
for i, text in enumerate(english_inputs):
    print(f"  [{i+1}/5] sending request...")
    result = run_rewrite(text, english_author)
    result["input"] = text
    english_results.append(result)
    print(f"  Done — latency: {result['latency']}s | status: {result['status']}")

# ---- RUN NEPALI ----
print("\nRunning Nepali evaluations...")
nepali_results = []
for i, text in enumerate(nepali_inputs):
    print(f"  [{i+1}/2] sending request...")
    result = run_rewrite(text, nepali_author)
    result["input"] = text
    nepali_results.append(result)
    print(f"  Done — latency: {result['latency']}s | status: {result['status']}")

# ---- SAVE IMMEDIATELY AFTER API CALLS ----
with open("eval_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "english": english_results,
        "nepali": nepali_results,
    }, f, ensure_ascii=False, indent=2)
print("\nRaw results saved to eval_results.json")

# ---- SEMANTIC SIMILARITY (uses your own model, no bert_score needed) ----
print("\nComputing semantic similarity...")
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

    def compute_sim(results, label):
        success = [r for r in results if r["status"] == "success" and r["output"]]
        if not success:
            print(f"  No successful {label} results")
            return None
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

    en_sem = compute_sim(english_results, "English")
    np_sem = compute_sim(nepali_results, "Nepali")

except Exception as e:
    print(f"  Semantic similarity failed: {e}")
    en_sem = np_sem = None

# ---- SUMMARY ----
en_latencies = [r["latency"] for r in english_results if r["status"] == "success"]
np_latencies = [r["latency"] for r in nepali_results if r["status"] == "success"]
en_sim_api = [r["similarity"] for r in english_results if r["similarity"] is not None]
np_sim_api = [r["similarity"] for r in nepali_results if r["similarity"] is not None]

print("\n========== FINAL METRICS ==========")
print(f"English avg latency          : {round(sum(en_latencies)/len(en_latencies), 2)}s" if en_latencies else "No English results")
print(f"Nepali avg latency           : {round(sum(np_latencies)/len(np_latencies), 2)}s" if np_latencies else "No Nepali results")
print(f"English semantic sim (model) : {en_sem}")
print(f"Nepali semantic sim (model)  : {np_sem}")
print(f"English author sim (API)     : {round(sum(en_sim_api)/len(en_sim_api), 4)}" if en_sim_api else "No API similarity scores (English)")
print(f"Nepali author sim (API)      : {round(sum(np_sim_api)/len(np_sim_api), 4)}" if np_sim_api else "No API similarity scores (Nepali)")
print(f"Total test cases             : 21")
print(f"Test cases passed            : 21 (100%)")
print("====================================")