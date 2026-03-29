import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";

const API_BASE = "http://127.0.0.1:8000";

export default function HomePage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("rewrite");

  // Shared state
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [out, setOut] = useState("");

  // Rewrite / Continue state
  const [author, setAuthor] = useState("");
  const [authors, setAuthors] = useState([]);
  const [lang, setLang] = useState("");

  // Load authors
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/authors`);
        const data = await res.json();
        setAuthors(data.authors || []);
      } catch (e) {
        console.error("Failed to fetch authors:", e);
        setAuthors([]);
      }
    })();
  }, []);

  // Rewrite
  async function handleRewrite() {
    if (!text.trim() || !author) {
      alert("Enter text and choose an author.");
      return;
    }

    setLoading(true);
    setOut("");
    setLang("");

    try {
      const res = await fetch(`${API_BASE}/rewrite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, author }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Rewrite failed");

      setOut(data.rewritten || "");
      setLang(data.language || "");
    } catch (err) {
      console.error(err);
      setOut(`Rewrite error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  // Continue
  async function handleContinue() {
    if (!text.trim() || !author) {
      alert("Enter text and choose an author.");
      return;
    }

    setLoading(true);
    setOut("");

    try {
      const res = await fetch(`${API_BASE}/continue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, author }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Continuation failed");

      setOut(data.continuation || "");
    } catch (err) {
      console.error(err);
      setOut(`Continuation error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  // Analyze
  async function handleAnalyze() {
    if (!text.trim()) {
      alert("Enter text to analyze.");
      return;
    }

    setLoading(true);
    setOut("");

    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      const data = await res.json();
      console.log("ANALYZE RESPONSE:", data);

      if (!res.ok) {
        throw new Error(data?.detail || "Analysis failed");
      }
      //Handle short / insufficient input
      if (data.analysis_type === "insufficient-input") {
        setOut(
          `Analysis unavailable\n\n` +
          `${data.message}\n\n` +
          `Details:\n` +
          `• Tokens: ${data.details.token_count}\n` +
          `• Sentences: ${data.details.sentence_count}\n` +
          `• Minimum required: ${data.details.minimum_required.tokens} tokens, ` +
          `${data.details.minimum_required.sentences} sentences`
        );
        return;
      }


      let report = `Analysis Report\n\n`;

      // Embedding signals
      if (data.embedding_analysis) {
        const sig = data.embedding_analysis.embedding_signals || {};
        const stats = data.embedding_analysis.sentence_stats || {};

        report += `Writing Style Highlights:\n`;
        report += ` • Emotion Level: ${sig.emotional_intensity}\n`;
        report += ` • Topic Changes: ${sig.semantic_drift}\n`;
        report += ` • Confidence Level: ${sig.assertiveness}\n\n`;

        report += `What This Means:\n`;
        report += ` • Emotion Level: Higher values mean the text uses stronger emotional words.\n`;
        report += ` • Topic Changes: Higher values mean the ideas flow freely from one to another.\n`;
        report += ` • Confidence Level: Higher values mean the statements are direct and sure.\n\n`;

        report += `Sentence Details:\n`;
        report += ` • Total Sentences: ${stats.num_sentences}\n`;
        report += ` • Average Similarity: ${stats.mean_sentence_similarity}\n\n`;
      }

      // Author alignment
      if (data.author_alignment) {
        const a = data.author_alignment;

        report += `Author Alignment:\n`;
        report += ` • Closest author: ${a.closest_author}\n`;
        report += ` • Deviation from author centroid: ${a.deviation_from_author}\n`;

        if (a.similarities) {
          const top = Object.entries(a.similarities)
            .sort(([, x], [, y]) => y - x)
            .slice(0, 3);

          report += ` • Top matches: ${top
            .map(([k, v]) => `${k} (${v})`)
            .join(", ")}\n`;
        }

        report += `\n`;
      }

      // Notes / limitations
      if (data.limitations) {
        report += `Notes & Limitations:\n`;
        data.limitations.forEach((l) => {
          report += ` • ${l}\n`;
        });
      }

      setOut(report);
    } catch (err) {
      console.error(err);
      setOut(`Analysis error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  const renderControls = () => {
    if (activeTab === "analyze") {
      return <h2>Text to Analyze</h2>;
    }

    return (
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>{activeTab === "continue" ? "Start Text" : "Input"}</h2>
        <select
          className="select"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          style={{ width: "auto", minWidth: "220px" }}
        >
          <option value="">Choose target author style</option>
          {authors.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>
    );
  };

  const activeAction = () => {
    if (activeTab === "rewrite") handleRewrite();
    else if (activeTab === "continue") handleContinue();
    else if (activeTab === "analyze") handleAnalyze();
  };

  const getButtonText = () => {
    if (loading) return "Processing...";
    if (activeTab === "rewrite") return "Rewrite";
    if (activeTab === "continue") return "Continue";
    return "🔍 Analyze";
  };

  // Render
  return (
    <div className="container" style={{ marginTop: 40, maxWidth: "1200px" }}>
      <header style={{ marginBottom: 40, textAlign: "center" }}>
        <h1>
          Welcome back, <span className="gradient-text">{user?.name || "Writer"}</span>!
        </h1>
        <p className="small">AI-powered writing assistant: Rewrite, Continue, and Analyze.</p>
      </header>

      {/* Tabs */}
      <div className="tab-group" style={{ maxWidth: "600px", margin: "0 auto 24px auto" }}>
        {["rewrite", "continue", "analyze"].map((tab) => (
          <button
            key={tab}
            className={`tab-btn ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="grid grid-2">
        <div className="panel" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {renderControls()}

          <textarea
            className="textarea"
            placeholder={
              activeTab === "continue"
                ? "Start your story here..."
                : "Paste your text here (English or Nepali)…"
            }
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{
              flex: 1,
              minHeight: 350,
              fontFamily: "monospace",
              resize: "none",
            }}
          />

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              className="btn primary"
              onClick={activeAction}
              disabled={
                loading ||
                !text.trim() ||
                ((activeTab === "rewrite" || activeTab === "continue") && !author)
              }
            >
              {getButtonText()}
            </button>
          </div>
        </div>

        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <h2>{activeTab === "analyze" ? "Analysis Results" : "Output"}</h2>

          <div
            style={{
              flex: 1,
              background: "var(--input-bg)",
              borderRadius: 10,
              border: "1px solid var(--input-border)",
              padding: "1rem",
              whiteSpace: "pre-wrap",
              overflowY: "auto",
            }}
          >
            {out || (
              <span style={{ color: "var(--text-secondary)", fontStyle: "italic" }}>
                {activeTab === "analyze"
                  ? "Analysis results will appear here..."
                  : "The result will appear here..."}
              </span>
            )}
          </div>

          {out && (
            <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
              <button className="btn ghost" onClick={() => navigator.clipboard.writeText(out)}>
                📋 Copy
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
