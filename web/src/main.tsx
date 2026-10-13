import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { FournisseurLangue } from "./i18n";
import "./styles.css";

createRoot(document.getElementById("racine")!).render(
  <StrictMode>
    <FournisseurLangue>
      <App />
    </FournisseurLangue>
  </StrictMode>,
);
