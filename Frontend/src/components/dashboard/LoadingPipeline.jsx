import { MICROCOPY, PIPELINE_STEPS } from "../../constants/dashboard";

const SKELETON_LINES = ["wide", "medium", "large", "short"];

export default function LoadingPipeline({ activeTab, currentStep, microcopyIndex }) {
  const steps = PIPELINE_STEPS[activeTab];

  return (
    <div className="loading-pipeline">
      <div className="pipeline-steps">
        {steps.map((step, index) => {
          const state = index < currentStep ? "completed" : index === currentStep ? "active" : "pending";
          return (
            <div key={step.label} className={`pipeline-step ${state}`}>
              {state === "completed" ? (
                <div className="step-check-circle">✓</div>
              ) : state === "active" ? (
                <div className="step-ring" />
              ) : (
                <div className="step-dot-circle" />
              )}
              <span>{step.label}</span>
            </div>
          );
        })}
      </div>

      <div className="skeleton-stack" aria-hidden="true">
        {SKELETON_LINES.map((size) => (
          <div key={size} className={`skeleton-line ${size}`} />
        ))}
      </div>

      <div className="microcopy-row">
        <span aria-hidden="true">›</span>
        <span className="microcopy-text" key={microcopyIndex}>
          {MICROCOPY[activeTab][microcopyIndex]}
        </span>
      </div>

      <div className="quality-note">
        Thoth is comparing candidate outputs before showing the best result.
      </div>
    </div>
  );
}
