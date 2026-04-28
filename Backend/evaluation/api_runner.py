import requests
import time
import json
from typing import Dict, Any, List

class EvaluationRunner:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.rewrite_endpoint = f"{self.base_url}/rewrite"

    def run_rewrite(self, text: str, author: str) -> Dict[str, Any]:
        payload = {"text": text, "author": author, "top_k": 5}
        start = time.time()
        try:
            response = requests.post(self.rewrite_endpoint, json=payload, timeout=300)
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
                return {
                    "output": "",
                    "similarity": None,
                    "latency": round(time.time() - start, 2),
                    "status": f"error_{response.status_code}"
                }
        except Exception as e:
            return {
                "output": "",
                "similarity": None,
                "latency": round(time.time() - start, 2),
                "status": f"exception_{str(e)}"
            }

    def run_all(self, english_inputs: List[str], nepali_inputs: List[str], en_author: str, ne_author: str) -> Dict[str, List[Dict[str, Any]]]:
        print("Running English evaluations...")
        english_results = []
        for i, text in enumerate(english_inputs):
            print(f"  [{i+1}/{len(english_inputs)}] sending request...")
            result = self.run_rewrite(text, en_author)
            result["input"] = text
            english_results.append(result)
            print(f"  Done — latency: {result['latency']}s | status: {result['status']}")

        print("\nRunning Nepali evaluations...")
        nepali_results = []
        for i, text in enumerate(nepali_inputs):
            print(f"  [{i+1}/{len(nepali_inputs)}] sending request...")
            result = self.run_rewrite(text, ne_author)
            result["input"] = text
            nepali_results.append(result)
            print(f"  Done — latency: {result['latency']}s | status: {result['status']}")

        results = {
            "english": english_results,
            "nepali": nepali_results,
        }

        with open("eval_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("\nRaw results saved to eval_results.json")

        return results

if __name__ == "__main__":
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
    
    runner = EvaluationRunner()
    results = runner.run_all(english_inputs, nepali_inputs, english_author, nepali_author)
    
    try:
        from evaluation.metrics import MetricsCalculator
        calc = MetricsCalculator("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        calc.summarise(results["english"], results["nepali"])
        
        calc.compute_rouge(results["english"])
        calc.compute_bleu(results["english"])
    except ImportError:
        print("Could not load metrics calculator.")
