import json
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import nltk
nltk.download('punkt')

with open("eval_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

english = [r for r in data["english"] 
           if r["status"] == "success" and r["output"]]

# ROUGE
scorer = rouge_scorer.RougeScorer(
    ['rouge1', 'rouge2', 'rougeL'], use_stemmer=True
)

rouge1_scores, rouge2_scores, rougeL_scores = [], [], []

print("=== ROUGE SCORES (per sample) ===")
for r in english:
    scores = scorer.score(r["input"], r["output"])
    rouge1_scores.append(scores['rouge1'].fmeasure)
    rouge2_scores.append(scores['rouge2'].fmeasure)
    rougeL_scores.append(scores['rougeL'].fmeasure)
    print(f"Input : {r['input'][:60]}...")
    print(f"Output: {r['output'][:60]}...")
    print(f"R1={scores['rouge1'].fmeasure:.4f} "
          f"R2={scores['rouge2'].fmeasure:.4f} "
          f"RL={scores['rougeL'].fmeasure:.4f}\n")

print("=== ROUGE AVERAGES ===")
print(f"ROUGE-1 : {sum(rouge1_scores)/len(rouge1_scores):.4f}")
print(f"ROUGE-2 : {sum(rouge2_scores)/len(rouge2_scores):.4f}")
print(f"ROUGE-L : {sum(rougeL_scores)/len(rougeL_scores):.4f}")

# BLEU
print("\n=== BLEU SCORES (per sample) ===")
bleu_scores = []
smoothie = SmoothingFunction().method1

for r in english:
    ref = [r["input"].split()]
    hyp = r["output"].split()
    bleu = sentence_bleu(ref, hyp, smoothing_function=smoothie)
    bleu_scores.append(bleu)
    print(f"BLEU={bleu:.4f} | {r['output'][:60]}...")

print(f"\nBLEU Average: {sum(bleu_scores)/len(bleu_scores):.4f}")