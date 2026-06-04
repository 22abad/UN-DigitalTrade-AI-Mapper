import Footer from "@/components/Footer/Footer";
import ColorBends from "@/components/ColorBends/ColorBends";

const layers = [
  {
    id: "layer-1",
    label: "Layer I",
    title: "Data Acquisition",
    subtitle: "Three-Tier Adaptive Crawler",
    body: null,
    stages: [
      { tag: "Tier A", name: "Fast HTTP Path", desc: "httpx-based direct fetch completes in under 2 seconds for static HTML sources. Link extraction strips iframe, SVG, and script nodes before parsing, eliminating rendering artefacts entirely." },
      { tag: "Tier B", name: "Playwright Stealth", desc: "For JavaScript-rendered pages and Cloudflare-protected government portals, a headless browser with stealth injection simulates real user behaviour, defeating fingerprinting and dynamic content barriers." },
      { tag: "Tier C", name: "Session & Auth Walls", desc: "Handles login-gated and session-cookie sites via configurable credential injection, enabling access to authenticated regulatory databases that block anonymous crawlers." },
      { tag: "Quality Guard", name: "Crawl Heuristics", desc: "Post-fetch analysis detects cookie consent walls (signal counting), navigation-only pages (low word-count + nav-density heuristic), and empty results — surfacing a proactive warning to the researcher before LLM inference is ever triggered." },
      { tag: "Text Pipeline", name: "Normalisation", desc: "A dedicated _clean_text() pass strips residual HTML tags, inline JavaScript artefacts, and collapses whitespace — ensuring only clean prose reaches the chunker." },
    ],
  },
  {
    id: "layer-2",
    label: "Layer II",
    title: "Ingestion & Processing",
    subtitle: "Four-Stage PDF Intelligence",
    body: null,
    stages: [
      { tag: "Stage 1", name: "Pure Text", desc: "PyMuPDF extracts text natively from digital-born PDFs in milliseconds with full Unicode support and layout preservation." },
      { tag: "Stage 2", name: "Watermark Suppression", desc: "Before OCR, an adaptive filter detects and removes repeating low-opacity watermark layers (common in official government PDFs) that corrupt OCR output if left untreated." },
      { tag: "Stage 3", name: "Standard OCR", desc: "Tesseract OCR with OpenCV preprocessing — adaptive thresholding, grayscale normalisation, and denoising — handles scanned and photocopied legislative documents." },
      { tag: "Stage 4", name: "Vision Fallback", desc: "Confidence scoring from Tesseract triggers automatic escalation to OpenAI Vision (GPT-4o) for degraded, rotated, or handwritten-annotation pages, ensuring zero text loss." },
      { tag: "Smart Chunking", name: "Article-level Chunker", desc: "Regex-based slicing by legal headings (\"Article\", \"Section\", \"Chapter\") preserves legal context across chunk boundaries and prevents the \"Lost-in-the-Middle\" phenomenon during LLM inference." },
    ],
  },
  {
    id: "layer-3",
    label: "Layer III",
    title: "Reasoning & Mapping",
    subtitle: "Vector-Relational Hybrid",
    body: "We utilise a PostgreSQL + pgvector architecture. Legal clauses are converted into high-dimensional embeddings stored alongside relational metadata, enabling semantic search and multi-pillar mapping via Gemini 1.5 Pro and Claude 3.5 Sonnet across all 12 RDTII pillars simultaneously.",
  },
  {
    id: "layer-4",
    label: "Layer IV",
    title: "Verification & Audit",
    subtitle: "Human-in-the-Loop Architecture",
    body: "To be trusted by the UN, a system cannot just extract random sentences. It must empower human legal experts. When a researcher reviews AI output, our Workbench instantly highlights the exact source text coordinates. By clicking 'Approve', decisions are persisted into our PostgreSQL database, creating a 100% verified, hallucination-free audit trail.",
  },
];

const sustainability = [
  {
    title: "Inference Optimisation",
    desc: "Tiered model strategy — lighter models for data cleaning, high-tier models only for final legal reasoning — keeps operational costs extremely low.",
  },
  {
    title: "Modular Sovereignty",
    desc: "Fully compatible with open-weight models like Llama 3 (8B). Supports model quantisation (GGUF), enabling UN member states to self-host the entire infrastructure on consumer-grade hardware with absolute data sovereignty.",
  },
];

const differentiators = [
  {
    label: "01",
    title: "Production-Grade, Not a Demo",
    desc: "SENTINEL ships with JWT-secured multi-user authentication, persistent PostgreSQL audit storage, and a Rust-based extract sidecar — architecture decisions made for real UN deployment, not just a hackathon presentation.",
  },
  {
    label: "02",
    title: "Real-Time Streaming Extraction",
    desc: "Results appear indicator by indicator via Server-Sent Events as the LLM reasons — researchers see output in seconds, not after a 60-second wait. Progressive rendering transforms a slow batch process into an interactive workflow.",
  },
  {
    label: "03",
    title: "Provider-Agnostic AI Core",
    desc: "A unified provider interface supports Gemini, Claude, GPT-4o, DeepSeek, Mistral, and locally self-hosted Llama 3 interchangeably. No vendor lock-in means member states choose sovereignty over convenience without losing capability.",
  },
  {
    label: "04",
    title: "Hallucination-Resistant by Design",
    desc: "Every extracted mapping includes a verbatim quote and character-level source coordinates. The human reviewer sees the exact sentence highlighted in the original document — not a paraphrase. Approval writes an immutable audit row to PostgreSQL.",
  },
  {
    label: "05",
    title: "Adversarial Web Coverage",
    desc: "The three-tier crawler defeats Cloudflare bot protection, JavaScript-rendered government portals, and cookie consent walls that block every off-the-shelf scraper. Combined with quality heuristics, researchers are warned before wasting inference budget on empty pages.",
  },
  {
    label: "06",
    title: "Zero-Infrastructure Deployment",
    desc: "A single `docker compose up` spins the entire stack — PostgreSQL, Redis, AI service, Rust sidecar, and Nginx-served frontend. Designed to run on a UN analyst's laptop or scale to a cloud cluster without code changes.",
  },
];

export function TechMemoPage() {
  return (
    <main className="min-h-screen font-geist">

      {/* Full-page ColorBends background — desktop only */}
      <div className="fixed inset-0 -z-10 hidden md:block">
        <ColorBends colors={["#44ad8a", "#07864d"]} speed={0.2} intensity={1.5} noise={0.15} frequency={1} />
      </div>
      <div className="fixed inset-0 -z-10 hidden md:block bg-white/30" />
      {/* Mobile solid fallback */}
      <div className="fixed inset-0 -z-10 md:hidden bg-white" />

      {/* Hero with video background */}
      <section className="relative h-[70vh] w-full overflow-hidden flex items-center justify-center bg-white">
        <video
          className="absolute inset-0 w-full h-full object-cover"
          autoPlay
          loop
          muted
          playsInline
        >
          <source src="/vid.mp4" type="video/mp4" />
        </video>

        {/* Dark overlay */}
        <div className="absolute inset-0 bg-black/60" />

        {/* Hero content */}
        <div className="relative z-10 text-center px-6 text-white">
          <p className="text-[#10B981] text-sm font-semibold uppercase tracking-widest mb-4">
            Technical Memorandum · May 15, 2026
          </p>
          <h1 className="text-4xl md:text-6xl font-bold mb-6">
            SYSTEM{" "}
            <span className="text-[#10B981]">ARCHITECTURE</span>
          </h1>
          <p className="text-lg md:text-xl opacity-80 max-w-2xl mx-auto leading-relaxed">
            Automated Discovery and Multi-Pillar Mapping of Digital Trade Regulations
          </p>
          <p className="mt-4 text-sm opacity-50">
            TO: UN Global Hackathon Committee &nbsp;·&nbsp; FROM: Team SENTINEL
          </p>
        </div>

        {/* Bottom fade */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-b from-background to-transparent" />
      </section>

      {/* Body */}
      <div style={{ background: "linear-gradient(to right, white calc(50% + 576px), transparent calc(50% + 576px))" }}>
      <div className="flex gap-6 max-w-6xl mx-auto items-stretch px-4 md:px-0">

        {/* Quick nav */}
        <nav className="hidden md:flex flex-col gap-3 sticky top-24 w-44 shrink-0 self-start text-sm">
          <p className="text-xs font-semibold uppercase tracking-widest opacity-40 mb-2 mt-10">On this page</p>
          {[
            { href: "#summary", label: "Summary" },
            { href: "#pipeline", label: "The AI Pipeline" },
            { href: "#sustainability", label: "Sustainability" },
            { href: "#team", label: "Why SENTINEL" },
          ].map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="opacity-50 hover:opacity-100 hover:text-[#10B981] transition-colors"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Left vertical divider */}
        <div className="hidden md:block w-px self-stretch bg-[#10B981]/40 -ml-20" />

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-16">

          {/* The Bottleneck */}
          <section id="summary">
            <h2 className="text-2xl md:text-3xl font-semibold mb-6 mt-10 sticky top-0 py-3 backdrop-blur-md bg-white/80 z-20">
              The Bottleneck: Why Manual Mapping Fails
            </h2>
            <div className="p-8 rounded-lg">
              <h3 className="text-xl font-bold text-[#1f2933] mb-4">The Complexity Surge</h3>
              <p className="opacity-80 leading-relaxed text-lg mb-4 text-[#1f2933]">
                As digital economy growth accelerates, emerging regulations have increased in volume and complexity. Traditional manual mapping is a labor-intensive bottleneck that hinders policy responsiveness and creates high operational costs.
              </p>
              <p className="opacity-80 leading-relaxed text-lg text-[#1f2933]">
                <strong>The Problem:</strong> Mapping domestic laws to international standards is manual and error-prone. 
                <br />
                <strong>The Need:</strong> An automated AI framework for inclusive digital trade that bridges the gap between fragmented law and actionable evidence.
              </p>
            </div>
          </section>

          <div className="h-px w-[calc(100%+3rem)] -ml-6 bg-[#10B981]/40" />

          {/* The AI Pipeline */}
          <section id="pipeline">
            <h2 className="text-2xl md:text-3xl font-semibold mb-10 sticky top-0 py-3 backdrop-blur-md bg-white/80 z-20">
              The AI Pipeline: Technical Architecture
            </h2>
            <div className="space-y-10">
              {layers.map((layer) => (
                <div key={layer.id}>
                  <div className="relative border border-[#10B981]/20 p-8 hover:border-[#10B981]/50 transition-colors">
                    <span className="absolute top-6 right-6 text-2xl font-black bg-gradient-to-br from-[#10B981] to-[#059669] bg-clip-text text-transparent select-none">
                      {layer.label.replace("Layer ", "")}
                    </span>
                    <h3 className="font-semibold text-lg mb-1">{layer.title}</h3>
                    <p className="text-[#10B981] text-xs font-medium uppercase tracking-wide mb-4 opacity-80">{layer.subtitle}</p>
                    {layer.body && (
                      <p className="opacity-60 text-sm leading-relaxed">{layer.body}</p>
                    )}
                    {layer.stages && (
                      <div className="space-y-4">
                        {layer.stages.map((s) => (
                          <div key={s.tag} className="flex gap-4">
                            <span className="shrink-0 text-[#10B981] text-xs font-black uppercase tracking-wide opacity-50 w-24 pt-0.5">{s.tag}</span>
                            <div>
                              <span className="font-semibold text-sm">{s.name}: </span>
                              <span className="opacity-60 text-sm leading-relaxed">{s.desc}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="h-px w-[calc(100%+3rem)] -ml-6 bg-[#10B981]/40" />

          {/* Sustainability */}
          <section id="sustainability">
            <h2 className="text-2xl md:text-3xl font-semibold mb-10 sticky top-0 py-3 backdrop-blur-md bg-white/80 z-20">
              Sustainability
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              {sustainability.map((s) => (
                <div key={s.title} className="border border-[#10B981]/20 p-8 hover:border-[#10B981]/50 transition-colors">
                  <h3 className="font-semibold text-lg mb-3">{s.title}</h3>
                  <p className="opacity-60 text-sm leading-relaxed">{s.desc}</p>
                </div>
              ))}
            </div>
          </section>

          <div className="h-px w-[calc(100%+3rem)] -ml-6 bg-[#10B981]/40" />

          {/* Why SENTINEL */}
          <section id="team">
            <h2 className="text-2xl md:text-3xl font-semibold mb-10 sticky top-0 py-3 backdrop-blur-md bg-white/80 z-20">
              Why SENTINEL
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              {differentiators.map((d) => (
                <div key={d.label} className="border border-[#10B981]/20 p-8 hover:border-[#10B981]/50 transition-colors">
                  <span className="text-3xl font-black bg-gradient-to-br from-[#10B981] to-[#059669] bg-clip-text text-transparent select-none">{d.label}</span>
                  <h3 className="font-semibold text-lg mt-3 mb-3">{d.title}</h3>
                  <p className="opacity-60 text-sm leading-relaxed">{d.desc}</p>
                </div>
              ))}
            </div>
          </section>

          <div className="h-px w-[calc(100%+3rem)] -ml-6 bg-[#10B981]/40" />

          <p className="text-xs opacity-40 italic pb-8 mb-10">
            This memo is submitted to the UN Global Hackathon Committee on behalf of Team SENTINEL.
            All technical details reflect the prototype built during the hackathon period.
          </p>

        </div>

        {/* Right vertical divider */}
        <div className="hidden md:block w-px self-stretch bg-[#10B981]/40" />

      </div>
      </div>

      <div className="h-px w-full bg-[#10B981]/40" />

      <Footer />
    </main>
  );
}
