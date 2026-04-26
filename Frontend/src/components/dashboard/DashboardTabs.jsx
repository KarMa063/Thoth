import { TAB_META } from "../../constants/dashboard";

const DASHBOARD_TABS = ["rewrite", "continue", "analyze"];

export default function DashboardTabs({ activeTab, onChange }) {
  return (
    <div className="dashboard-tabs" role="tablist" aria-label="Workspace mode">
      {DASHBOARD_TABS.map((tab) => (
        <button
          key={tab}
          type="button"
          className={`dashboard-tab ${activeTab === tab ? "active" : ""}`}
          onClick={() => onChange(tab)}
          role="tab"
          aria-selected={activeTab === tab}
        >
          <span className="dashboard-tab-icon" aria-hidden="true">
            {TAB_META[tab].icon}
          </span>
          {TAB_META[tab].label}
        </button>
      ))}
    </div>
  );
}
