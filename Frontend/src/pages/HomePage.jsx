import { useEffect, useState, useRef, useCallback } from "react";
import { useAuth } from "../context/AuthContext";

const API_BASE = "http://127.0.0.1:8000";

const PIPELINE_STEPS = {
  rewrite: [
    { label: "Reading input" },
    { label: "Fetching author style" },
    { label: "Generating candidates" },
    { label: "Ranking best version" },
    { label: "Finalizing output" },
  ],
  continue: [
    { label: "Analyzing your text" },
    { label: "Loading author voice" },
    { label: "Building continuation" },
    { label: "Refining flow" },
    { label: "Polishing result" },
  ],
  analyze: [
    { label: "Tokenizing input" },
    { label: "Computing embeddings" },
    { label: "Detecting style signals" },
    { label: "Matching author profiles" },
    { label: "Building report" },
  ],
};

// --- Rotating microcopy messages ---
const MICROCOPY = {
  rewrite: [
    "Matching author voice…",
    "Preserving your meaning…",
    "Avoiding repetition…",
    "Polishing final wording…",
    "Comparing candidate versions…",
    "Selecting the best rewrite…",
  ],
  continue: [
    "Extending the narrative…",
    "Maintaining story flow…",
    "Channeling the author's rhythm…",
    "Building on your ideas…",
    "Crafting the continuation…",
  ],
  analyze: [
    "Mapping semantic space…",
    "Detecting emotion layers…",
    "Comparing to known authors…",
    "Measuring confidence signals…",
    "Scanning writing patterns…",
  ],
};

const AUTHOR_TRAITS = {
  "William Shakespeare": [
    '"Brevity is the soul of wit."',
    "Known for: iambic pentameter, rich metaphors",
    "Style: poetic, dramatic, layered meaning",
  ],
  "Jane Austen": [
    '"It is a truth universally acknowledged…"',
    "Known for: irony, social commentary",
    "Style: elegant, witty, observational",
  ],
  "Charles Dickens": [
    '"It was the best of times, it was the worst of times."',
    "Known for: vivid characters, social critique",
    "Style: descriptive, emotional, sweeping",
  ],
  "Mark Twain": [
    '"The secret of getting ahead is getting started."',
    "Known for: colloquial language, humor, satire",
    "Style: conversational, sharp, direct",
  ],
  "Ernest Hemingway": [
    '"Write hard and clear about what hurts."',
    "Known for: iceberg theory, sparse prose",
    "Style: minimalist, direct, understated",
  ],
  "Virginia Woolf": [
    '"You cannot find peace by avoiding life."',
    "Known for: stream of consciousness",
    "Style: lyrical, introspective, flowing",
  ],
};

function getAuthorTrait(authorName) {
  const traits = AUTHOR_TRAITS[authorName];
  if (!traits) return `Working in ${authorName}'s style`;
  return traits[Math.floor(Math.random() * traits.length)];
}

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

  // Loading UX state
  const [currentStep, setCurrentStep] = useState(0);
  const [microcopyIndex, setMicrocopyIndex] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const abortControllerRef = useRef(null);
  const stepIntervalRef = useRef(null);
  const microcopyIntervalRef = useRef(null);
  const timerIntervalRef = useRef(null);

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

  // --- Loading animation intervals ---
  useEffect(() => {
    if (loading) {
      const steps = PIPELINE_STEPS[activeTab];
      let step = 0;
      setCurrentStep(0);
      setMicrocopyIndex(0);
      setElapsedTime(0);

      // Progress steps — advance every 2-4s but never past second-to-last until done
      stepIntervalRef.current = setInterval(() => {
        step++;
        if (step < steps.length - 1) {
          setCurrentStep(step);
        }
      }, 2500);

      // Microcopy rotation
      microcopyIntervalRef.current = setInterval(() => {
        setMicrocopyIndex((prev) => {
          const messages = MICROCOPY[activeTab];
          return (prev + 1) % messages.length;
        });
      }, 2800);

      // Elapsed timer
      timerIntervalRef.current = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);
    } else {
      // Show final step briefly when done
      const steps = PIPELINE_STEPS[activeTab];
      setCurrentStep(steps.length - 1);

      clearInterval(stepIntervalRef.current);
      clearInterval(microcopyIntervalRef.current);
      clearInterval(timerIntervalRef.current);
    }

    return () => {
      clearInterval(stepIntervalRef.current);
      clearInterval(microcopyIntervalRef.current);
      clearInterval(timerIntervalRef.current);
    };
  }, [loading, activeTab]);

  // --- Cancel handler ---
  const handleCancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setLoading(false);
    setOut("Generation cancelled. You can try again or switch modes.");
  }, []);

  // --- Rewrite ---
  async function handleRewrite() {
    if (!text.trim() || !author) {
      alert("Enter text and choose an author.");
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setOut("");
    setLang("");

    try {
      const res = await fetch(`${API_BASE}/rewrite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, author }),
        signal: controller.signal,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Rewrite failed");

      setOut(data.rewritten || "");
      setLang(data.language || "");
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error(err);
      setOut(`Rewrite error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  // --- Continue ---
  async function handleContinue() {
    if (!text.trim() || !author) {
      alert("Enter text and choose an author.");
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setOut("");

    try {
      const res = await fetch(`${API_BASE}/continue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, author }),
        signal: controller.signal,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Continuation failed");

      setOut(data.continuation || "");
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error(err);
      setOut(`Continuation error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  // --- Analyze ---
  async function handleAnalyze() {
    if (!text.trim()) {
      alert("Enter text to analyze.");
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setOut("");

    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
        signal: controller.signal,
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
      if (err.name === "AbortError") return;
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
    if (loading) return "Generating…";
    if (activeTab === "rewrite") return "Rewrite";
    if (activeTab === "continue") return "Continue";
    return "🔍 Analyze";
  };

  // --- Word count helper ---
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
  const charCount = text.length;

  // --- Loading output panel content ---
  const renderLoadingContent = () => {
    const steps = PIPELINE_STEPS[activeTab];
    const messages = MICROCOPY[activeTab];

    return (
      <div className="loading-experience">
        {/* Pipeline Progress */}
        <div className="pipeline-progress">
          {steps.map((step, i) => (
            <div
              key={i}
              className={`pipeline-step ${i < currentStep ? "completed" : i === currentStep ? "active" : "pending"
                }`}
            >
              <div className="step-indicator">
                {i < currentStep ? (
                  <span className="step-check">✓</span>
                ) : i === currentStep ? (
                  <span className="step-spinner"></span>
                ) : (
                  <span className="step-dot"></span>
                )}
              </div>
              <span className="step-label">{step.icon} {step.label}</span>
            </div>
          ))}
        </div>

        {/* Skeleton content */}
        <div className="skeleton-content">
          <div className="skeleton-line" style={{ width: "92%" }}></div>
          <div className="skeleton-line" style={{ width: "78%" }}></div>
          <div className="skeleton-line" style={{ width: "85%" }}></div>
          <div className="skeleton-line short" style={{ width: "45%" }}></div>
        </div>

        {/* Rotating microcopy */}
        <div className="microcopy-container">
          <div className="blinking-cursor"></div>
          <span className="microcopy-text" key={microcopyIndex}>
            {messages[microcopyIndex]}
          </span>
        </div>

        {/* Quality message */}
        <div className="quality-note">
          <span className="quality-icon"></span>
          Thoth is comparing multiple candidate outputs before showing the best result.
        </div>
      </div>
    );
  };

  // --- Idle output content ---
  const renderIdleContent = () => (
    <div className="idle-output">
      <div className="idle-icon"></div>
      <span className="idle-text">
        {activeTab === "analyze"
          ? "Analysis results will appear here…"
          : "Your result will appear here…"}
      </span>
      <div className="idle-hint">
        {activeTab !== "analyze"
          ? "Paste text on the left, choose an author, and click the button"
          : "Paste text on the left and click Analyze"}
      </div>
    </div>
  );

  // --- Right-side panel during loading ---
  const renderRightPanelHeader = () => {
    if (loading) {
      return (
        <div className="panel-header-loading">
          <div className="header-row">
            <h2>{activeTab === "analyze" ? "Analyzing" : "Generating"}</h2>
            <span className="elapsed-badge">{elapsedTime}s</span>
          </div>

          {/* Metadata chips */}
          <div className="meta-chips">
            {activeTab !== "analyze" && author && (
              <div className="meta-chip">
                <span className="chip-label">Author</span>
                <span className="chip-value">{author}</span>
              </div>
            )}
            <div className="meta-chip">
              <span className="chip-label">Mode</span>
              <span className="chip-value" style={{ textTransform: "capitalize" }}>{activeTab}</span>
            </div>
            <div className="meta-chip">
              <span className="chip-label">Words</span>
              <span className="chip-value">{wordCount}</span>
            </div>
            <div className="meta-chip">
              <span className="chip-label">Characters</span>
              <span className="chip-value">{charCount}</span>
            </div>
          </div>

          {/* Author trait */}
          {activeTab !== "analyze" && author && (
            <div className="author-trait">
              <span className="trait-label">🎭 Style insight</span>
              <span className="trait-value">{getAuthorTrait(author)}</span>
            </div>
          )}
        </div>
      );
    }

    return <h2>{activeTab === "analyze" ? "Analysis Results" : "Output"}</h2>;
  };

  // --- Render ---
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
        {/* Left panel — input */}
        <div className={`panel ${loading ? "panel-locked" : ""}`} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
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
            disabled={loading}
            style={{
              flex: 1,
              minHeight: 350,
              fontFamily: "monospace",
              resize: "none",
              opacity: loading ? 0.6 : 1,
              transition: "opacity 0.3s ease",
            }}
          />

          {/* Input stats bar */}
          <div className="input-stats">
            <span>{wordCount} words · {charCount} characters</span>
            {lang && <span className="lang-badge">Detected: {lang}</span>}
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            {loading && (
              <button className="btn cancel-btn" onClick={handleCancel}>
                ✕ Cancel
              </button>
            )}
            <button
              className={`btn primary ${loading ? "btn-generating" : ""}`}
              onClick={activeAction}
              disabled={
                loading ||
                !text.trim() ||
                ((activeTab === "rewrite" || activeTab === "continue") && !author)
              }
            >
              {loading && <span className="btn-spinner"></span>}
              {getButtonText()}
            </button>
          </div>
        </div>

        {/* Right panel — output */}
        <div className={`panel ${loading ? "panel-generating" : ""}`} style={{ display: "flex", flexDirection: "column" }}>
          {renderRightPanelHeader()}

          <div
            className={`output-box ${loading ? "output-loading" : ""} ${out ? "output-has-content" : ""}`}
          >
            {loading
              ? renderLoadingContent()
              : out
                ? <div className="output-result fade-in">{out}</div>
                : renderIdleContent()
            }
          </div>

          {out && !loading && (
            <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button className="btn ghost" onClick={() => navigator.clipboard.writeText(out)}>
                📋 Copy
              </button>
              <button className="btn ghost" onClick={() => { setOut(""); }}>
                🔄 Clear
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
