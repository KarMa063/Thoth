import { Link } from "react-router-dom";

const features = [
  {
    icon: "R",
    title: "Author Style Rewriting",
    desc: "Rewrite English or Nepali prose against retrieved author examples instead of relying on a generic prompt alone.",
  },
  {
    icon: "C",
    title: "Style-Aware Continuation",
    desc: "Continue a passage while preserving the selected author's rhythm, vocabulary, and narrative flow.",
  },
  {
    icon: "A",
    title: "Explainable Style Analysis",
    desc: "Report measurable style signals such as semantic drift, emotional intensity, and author alignment.",
  },
];

const stats = [
  { value: "12", label: "Literary Authors" },
  { value: "21K+", label: "Corpus Chunks" },
  { value: "2", label: "Languages" },
  { value: "4", label: "Core Modules" },
];

const pipeline = [
  {
    step: "01",
    title: "Submit text",
    desc: "Paste writing in English or Nepali and choose the task: rewrite, continue, or analyze.",
  },
  {
    step: "02",
    title: "Retrieve author evidence",
    desc: "The RAG layer searches author corpus chunks for relevant style examples.",
  },
  {
    step: "03",
    title: "Generate grounded output",
    desc: "The model uses the retrieved examples to produce text aligned with the selected author.",
  },
  {
    step: "04",
    title: "Inspect the result",
    desc: "The interface returns output with language detection and style-analysis signals where available.",
  },
];

export default function LandingPage() {
  return (
    <>
      <section className="hero">
        <div className="hero-inner">
          <div className="fade-in">
            <span className="hero-eyebrow">Bilingual / Explainable / Corpus-Grounded</span>
          </div>

          <h1 className="fade-in">
            Thoth, a bilingual psycho-literary assistant
          </h1>

          <p className="lead fade-in">
            Analyze writing, rewrite it in selected author styles, and continue
            passages using retrieval from real literary corpora.
          </p>

          <div className="hero-actions fade-in">
            <Link to="/login" className="btn primary btn-large">
              Open Workspace
            </Link>
            <a href="#features" className="btn ghost btn-large">
              View Modules
            </a>
          </div>
        </div>
      </section>

      <section className="landing-stat-strip">
        <div className="container">
          <div className="landing-stat-grid">
            {stats.map((stat) => (
              <div key={stat.label} className="fade-in">
                <div className="landing-stat-value">{stat.value}</div>
                <div className="landing-stat-label">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="container feature-section">
        <div className="section-header">
          <span className="section-label">System Modules</span>
          <h2>Focused tools for literary style work</h2>
          <p className="text-muted">
            Built around retrieval-augmented generation, author corpora, and
            measurable style signals.
          </p>
        </div>

        <div className="feature-grid">
          {features.map((feature) => (
            <article key={feature.title} className="panel feature fade-in">
              <div className="feature-icon">{feature.icon}</div>
              <h3>{feature.title}</h3>
              <p>{feature.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-pipeline">
        <div className="container">
          <div className="section-header">
            <span className="section-label">Pipeline</span>
            <h2>How Thoth produces a result</h2>
          </div>

          <div className="pipeline-list">
            {pipeline.map((item) => (
              <article key={item.step} className="pipeline-item fade-in">
                <div className="pipeline-number">{item.step}</div>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.desc}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-cta">
        <div className="landing-cta-inner">
          <h2>Move from text to evidence-backed style output</h2>
          <p className="text-muted">
            Sign in to test rewriting, continuation, and analysis from the
            workspace.
          </p>
          <Link to="/login" className="btn primary btn-large">
            Start Testing
          </Link>
        </div>
      </section>

      <footer>
        <div className="container">
          <p>Thoth - Bilingual Psycho-Literary Assistant. Built at Herald College Kathmandu.</p>
        </div>
      </footer>
    </>
  );
}
