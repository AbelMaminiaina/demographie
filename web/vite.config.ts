import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";

// Les données sont produites par le pipeline Python dans sorties/web/donnees/ :
// on sert ce dossier comme dossier public, en développement comme à la construction.
export default defineConfig({
  base: "./",
  publicDir: fileURLToPath(new URL("../sorties/web", import.meta.url)),
  plugins: [react(), tailwindcss()],
  worker: { format: "es" },   // le worker de MapLibre est un module ES
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 1500 },
});
