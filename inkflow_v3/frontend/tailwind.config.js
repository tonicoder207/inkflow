export default {
  content: ["./index.html","./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink:    { 900:"#080815",800:"#0f0f25",700:"#1a1a3a",600:"#2a2a5a",500:"#3a3a7a",400:"#6060a8",300:"#9090c8",200:"#c0c0e0",100:"#e0e0f0" },
        paper:  { warm:"#fdf6e3",white:"#fafaf9",aged:"#f5ead0" },
        accent: { gold:"#c9a84c",rust:"#c05a3a",sage:"#5a8a6a" },
      },
      fontFamily: {
        display: ["Georgia","serif"],
        body:    ["system-ui","sans-serif"],
        mono:    ["monospace"],
      },
      animation: {
        "fade-in":  "fadeIn 0.3s ease-out both",
        "slide-up": "slideUp 0.4s cubic-bezier(0.16,1,0.3,1) both",
        "pulse-soft":"pulseSoft 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn:    { from:{opacity:"0"},      to:{opacity:"1"} },
        slideUp:   { from:{opacity:"0",transform:"translateY(16px)"}, to:{opacity:"1",transform:"translateY(0)"} },
        pulseSoft: { "0%,100%":{opacity:"1"}, "50%":{opacity:"0.5"} },
      },
    },
  },
  plugins: [],
};
