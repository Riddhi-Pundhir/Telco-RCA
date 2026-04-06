/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        espresso: "#452829",
        slate: "#57595B",
        sand: "#E8D1C5",
        cream: "#F3E8DF",
        healthy: "#5DD39E",
        suspect: "#F2B950",
        failure: "#F56A6A",
        signal: "#D7B79B",
      },
      boxShadow: {
        panel: "0 24px 80px rgba(17, 7, 5, 0.35)",
        glow: "0 0 0 1px rgba(243, 232, 223, 0.08), 0 18px 60px rgba(17, 7, 5, 0.28)",
        alarm: "0 0 0 1px rgba(245, 106, 106, 0.25), 0 0 30px rgba(245, 106, 106, 0.18)",
      },
      borderRadius: {
        "4xl": "2rem",
      },
      backgroundImage: {
        mesh:
          "radial-gradient(circle at top left, rgba(232, 209, 197, 0.24), transparent 32%), radial-gradient(circle at 80% 0%, rgba(215, 183, 155, 0.22), transparent 28%), radial-gradient(circle at 50% 100%, rgba(87, 89, 91, 0.35), transparent 40%)",
      },
      animation: {
        float: "float 8s ease-in-out infinite",
        pulseSoft: "pulseSoft 2.8s ease-in-out infinite",
        panelIn: "panelIn 0.65s ease-out",
        sweep: "sweep 2s linear infinite",
        flash: "flash 1.35s ease-in-out infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-12px)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "0.45", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.08)" },
        },
        panelIn: {
          "0%": { opacity: "0", transform: "translateY(18px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        sweep: {
          "0%": { backgroundPosition: "0% 50%" },
          "100%": { backgroundPosition: "200% 50%" },
        },
        flash: {
          "0%, 100%": { boxShadow: "0 0 0 rgba(245, 106, 106, 0)" },
          "50%": { boxShadow: "0 0 24px rgba(245, 106, 106, 0.35)" },
        },
      },
    },
  },
  plugins: [],
};

