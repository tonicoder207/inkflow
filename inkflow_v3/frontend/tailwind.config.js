/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        apple: {
          blue: "#007AFF",
          gray: {
            50:  "#F5F5F7",
            100: "#E8E8ED",
            200: "#D2D2D7",
            300: "#86868B",
            400: "#424245",
            500: "#1D1D1F",
          },
          system: {
            blue: "#0A84FF",
            red:  "#FF453A",
            green: "#32D74B",
          }
        },
        glass: {
          light: "rgba(255, 255, 255, 0.7)",
          dark:  "rgba(29, 29, 31, 0.7)",
          border: "rgba(255, 255, 255, 0.15)",
        }
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
      },
      borderRadius: {
        "apple": "18px",
        "apple-sm": "12px",
        "apple-lg": "24px",
      },
      boxShadow: {
        "apple-soft": "0 8px 32px 0 rgba(0, 0, 0, 0.08)",
        "apple-glass": "0 4px 16px 0 rgba(0, 0, 0, 0.04)",
      },
      animation: {
        "vibrate": "vibrate 0.3s linear infinite",
        "fade-in": "fadeIn 0.5s cubic-bezier(0.4, 0, 0.2, 1) both",
        "scale-in": "scaleIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both",
      },
      keyframes: {
        vibrate: {
          "0%, 100%": { transform: "translateX(0)" },
          "25%": { transform: "translateX(-2px)" },
          "75%": { transform: "translateX(2px)" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        scaleIn: {
          from: { opacity: "0", transform: "scale(0.95)" },
          to: { opacity: "1", transform: "scale(1)" },
        }
      },
      backdropBlur: {
        "apple": "20px",
      }
    },
  },
  plugins: [],
};
