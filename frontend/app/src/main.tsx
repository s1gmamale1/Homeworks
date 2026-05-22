import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles/global.css";

// The v2 runtime is a LIGHT-only design (Apple glass). Force data-theme="light"
// on <html> so the prefers-color-scheme:dark token flip in _tokens.css never
// applies — otherwise --v2-text flips near-white on a dark OS while the shell
// forces a light background, making all titles invisible. Robust regardless of
// how the /h/{id} server shell wraps the document.
document.documentElement.setAttribute("data-theme", "light");

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
