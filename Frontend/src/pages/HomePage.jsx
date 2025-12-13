import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function HomePage() {
  const { user } = useAuth();
  const [text, setText] = useState("");
  const [author, setAuthor] = useState("");
  const [loading, setLoading] = useState(false);
  const [out, setOut] = useState("");

  async function handleRewrite() {
    if (!text.trim() || !author)
      return alert("Enter text and choose an author.");

    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/rewrite", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: text,
          author: author
        })
      });

      if (!res.ok) throw new Error();

      const data = await res.json();
      setOut(data.rewritten || "No rewritten text returned.");

    } catch (err) {
      console.error(err);
      setOut("Error contacting backend. Make sure FastAPI is running.");
    }

    setLoading(false);
  }

  return (
    <div className="container" style={{ marginTop: 40, maxWidth: "1200px" }}>
      <h1>Welcome back, {user?.name || "Writer"}! ✍️</h1>

      <div className="grid grid-2" style={{ gap: 24 }}>
        <div className="panel">
          <h2>Input</h2>

          <textarea
            className="textarea"
            placeholder="Paste your paragraph…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{ minHeight: 280 }}
          />

          <select
            className="select"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
          >
            <option value="">Choose target author style</option>
            <option value="Kafka">Kafka</option>
          </select>

          <button
            className="btn primary"
            onClick={handleRewrite}
            disabled={loading}
          >
            {loading ? "Rewriting…" : "Rewrite"}
          </button>
        </div>

        <div className="panel">
          <h2>Output</h2>

          {out ? (
            <pre style={{ whiteSpace: "pre-wrap" }}>{out}</pre>
          ) : (
            <p style={{ color: "var(--muted)" }}>
              Output will appear here…
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
