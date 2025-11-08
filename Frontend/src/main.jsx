import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";
import "./style.css";
import { initializeTheme } from "./utils/themeManager";

// Initialize theme immediately before rendering
initializeTheme();

ReactDOM.createRoot(document.getElementById("app")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
