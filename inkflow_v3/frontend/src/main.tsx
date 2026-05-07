import React from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "react-hot-toast";
import App from "./App";
import "@/styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App/>
    <Toaster
      position="bottom-center"
      toastOptions={{
        style: {
          background: "rgba(29, 29, 31, 0.8)",
          backdropFilter: "blur(20px)",
          color: "#F5F5F7",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          borderRadius: "100px", // Pill shape for Apple feel
          fontFamily: "Inter, system-ui, sans-serif",
          fontSize: "12px",
          fontWeight: "600",
          padding: "10px 20px",
          boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
        },
        success: {
          iconTheme: {
            primary: "#32D74B",
            secondary: "#000",
          }
        },
        error: {
          iconTheme: {
            primary: "#FF453A",
            secondary: "#000",
          }
        },
      }}
    />
  </React.StrictMode>
);
