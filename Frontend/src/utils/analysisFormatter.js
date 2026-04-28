export function formatAnalysisReport(data) {
  if (data.analysis_type === "insufficient-input") {
    return (
      `Analysis unavailable\n\n${data.message}\n\nDetails:\n` +
      `- Tokens: ${data.details.token_count}\n` +
      `- Sentences: ${data.details.sentence_count}\n` +
      `- Minimum required: ${data.details.minimum_required.tokens} tokens, ` +
      `${data.details.minimum_required.sentences} sentences`
    );
  }

  let report = "Analysis Report\n\n";

  if (data.embedding_analysis) {
    const sig = data.embedding_analysis.embedding_signals || {};
    const stats = data.embedding_analysis.sentence_stats || {};
    report += "Writing Style Highlights:\n";
    report += `- Emotion Level: ${sig.emotional_intensity}\n`;
    report += `- Topic Changes: ${sig.semantic_drift}\n`;
    report += `- Confidence Level: ${sig.assertiveness}\n\n`;
    report += "What This Means:\n";
    report += "- Emotion Level: Higher values mean the text uses stronger emotional words.\n";
    report += "- Topic Changes: Higher values mean the ideas flow freely from one to another.\n";
    report += "- Confidence Level: Higher values mean the statements are direct and sure.\n\n";
    report += "Sentence Details:\n";
    report += `- Total Sentences: ${stats.num_sentences}\n`;
    report += `- Average Similarity: ${stats.mean_sentence_similarity}\n\n`;
  }

  if (data.author_alignment) {
    const alignment = data.author_alignment;
    report += "Author Alignment:\n";
    report += `- Closest author: ${alignment.closest_author}\n`;
    report += `- Deviation from author centroid: ${alignment.deviation_from_author}\n`;

    if (alignment.similarities) {
      const topMatches = Object.entries(alignment.similarities)
        .sort(([, left], [, right]) => right - left)
        .slice(0, 3);
      report += `- Top matches: ${topMatches.map(([name, score]) => `${name} (${score})`).join(", ")}\n`;
    }
    report += "\n";
  }

  if (data.limitations?.length) {
    report += "Notes & Limitations:\n";
    data.limitations.forEach((limitation) => {
      report += `- ${limitation}\n`;
    });
  }

  return report;
}
