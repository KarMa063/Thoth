import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <>
      <section className="hero center" style={{ background: "radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.1) 0%, transparent 50%)" }}>
        <div className="container center" style={{ flexDirection: "column", textAlign: "center", gap: 32, maxWidth: "900px", zIndex: 1 }}>
          <h1 className="fade-in">
            Thoth — <span className="gradient-text">Bilingual Psycho-Literary Assistant</span>
          </h1>
          <p className="lead fade-in" style={{ fontSize: "1.25rem", color: "var(--text-secondary)", animationDelay: "0.1s" }}>
            Analyze writing, detect biases, and rewrite in the voice of renowned authors.
            Start with English; Nepali support coming next. Clean UI with explainable insights.
          </p>
          <div className="fade-in" style={{ display: "flex", gap: 16, marginTop: 16, flexWrap: "wrap", justifyContent: "center", animationDelay: "0.2s" }}>
            <Link to="/login" className="btn primary" style={{ padding: "16px 32px", fontSize: "1.1rem" }}>
              Get Started
            </Link>
            <a href="#features" className="btn ghost" style={{ padding: "16px 32px", fontSize: "1.1rem" }}>
              Learn More
            </a>
          </div>
        </div>
      </section>

      <section id="features" className="container" style={{ paddingBottom: "5rem" }}>
        <div style={{ textAlign: "center", marginBottom: 64 }}>
          <h2 style={{ marginBottom: 16 }}>Key Features</h2>
          <p className="small" style={{ fontSize: "1.1rem", maxWidth: "600px", margin: "0 auto" }}>
            Powerful tools to enhance your writing and understand your style
          </p>
        </div>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "2rem" }}>
          {[
            {
              title: "Author Tone",
              desc: "Rewriting guided by exemplar-based style sheets. Transform your writing to match the voice of renowned authors.",
              icon: "✍️"
            },
            {
              title: "Bias & Strengths",
              desc: "Surface hedging, clarity, rhythm, and vocabulary richness. Get insights into your writing patterns.",
              icon: "🔍"
            },
            {
              title: "Explainability",
              desc: "Show 'why': tone tags, anchors, and style stats. Understand the reasoning behind every suggestion.",
              icon: "💡"
            },
          ].map((f, i) => (
            <div key={i} className="panel feature fade-in" style={{ animationDelay: `${0.3 + (i * 0.1)}s`, display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ fontSize: "48px", marginBottom: "8px" }}>{f.icon}</div>
              <h3>{f.title}</h3>
              <p className="small" style={{ margin: 0, fontSize: "1rem", lineHeight: "1.6" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer style={{ background: "var(--footer-bg)", color: "var(--footer-text)", padding: "2rem 0", textAlign: "center", borderTop: "1px solid var(--card-border)" }}>
        <div className="container">
          <p style={{ margin: 0 }}>© {new Date().getFullYear()} Thoth. All rights reserved.</p>
        </div>
      </footer>
    </>
  );
}

