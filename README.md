# 🏛️ UN-DigitalTrade-AI-Mapper (DTAM)

> **"Where Code Meets Law."** > Transforming 100 pages of unstructured trade regulations into 1 page of actionable, mapped JSON data.

An open-source AI concept prototype built for the **UN Global Hackathon: AI for Digital Trade Regulatory Analysis**.

## 🎯 The Mission
Global digital trade is hindered by fragmented data localization and privacy laws. Traditional manual legal review is no longer scalable. **DTAM** is a hybrid extraction engine designed to automatically discover, extract, and map complex digital trade regulations against the **UNESCAP Regional Digital Trade Integration Index (RDTII 2.1)**.

### Core Focus (MVP)
- **Pillar 6:** Cross-border Data Policies (Data Localization, SCCs, adequacy decisions).
- **Pillar 7:** Domestic Data Protection & Privacy.

## ⚙️ Hybrid Architecture (The Engine)
To eliminate LLM "hallucinations" in legal contexts, we employ a deterministic + probabilistic hybrid approach:
1. **Deterministic Anchoring:** Regex & Python (PDFPlumber) to precisely slice legal PDFs by articles/clauses.
2. **Semantic Extraction:** NLP/LLM API to extract specific compliance obligations.
3. **Structured Mapping:** Pydantic & JSON Schema to force LLM outputs into strict RDTII-compliant data structures.
4. **Transparency UI (Audit View):** React frontend linking JSON outputs directly to highlighted source text in the original PDF.

## 👥 The Squad
We are a cross-disciplinary strike team from Maynooth University:
- **Dong Li** (Project Manager & Legal Architect): 20+ years of legal practice. Bridges legal logic and coding algorithms.
- **Rujing Xu** (Policy Analyst & Narrative Lead): Economics & Trade expert. Defines business value and policy mapping.
- **Jie Xu** (Tech Lead & Backend Engine): Java/Python developer. Architect of the text-to-data extraction MVP.
- **Chenming Tao** (UX/UI & AI Video Lead): Design expert. Crafts the Audit View UI and cinematic concept presentation.

## 📅 15-Day Agile Sprint
- **Phase 1 (Days 1-4):** Logic Mapping & Wireframing
- **Phase 2 (Days 5-11):** MVP Extraction Engine & Video Production
- **Phase 3 (Days 12-15):** Integration, QA, and Submission

---
*Disclaimer: The outputs of this tool are for conceptual demonstration and research purposes only, not formal legal advice.*

