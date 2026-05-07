import React from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "react-hot-toast";
import App from "./App";
import "@/styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App/>
    <Toaster
      position="bottom-right"
      toastOptions={{
        style: {
          background: "#1a1a3a",
          color: "#e8e8f0",
          border: "1px solid rgba(201,168,76,0.3)",
          borderRadius: "12px",
          fontFamily: "system-ui, sans-serif",
          fontSize: "13px",
        },
        success: { iconTheme: { primary:"#c9a84c", secondary:"#0f0f20" } },
        error:   { iconTheme: { primary:"#ef4444", secondary:"#0f0f20" } },
      }}
    />
  </React.StrictMode>
);
