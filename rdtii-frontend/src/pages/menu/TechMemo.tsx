import Footer from "@/components/Footer/Footer";
import ColorBends from "@/components/ColorBends/ColorBends";

const layers = [
  {
    id: "layer-1",
    label: "Layer I",
    title: "Data Acquisition",
    subtitle: "Automated Discovery Engine",
    body: "Unlike traditional scrapers, our engine utilises Playwright with Stealth Injection to bypass sophisticated government anti-bot barriers (e.g., Cloudflare) and handle complex JavaScript rendering. It intelligently discovers and downloads legal sources, including dynamic HTML and hidden PDF links.",
  },
  {
    id: "layer-2",
    label: "Layer II",
    title: "Ingestion & Processing",
    subtitle: "The Three-Stage Rocket",
    body: null,
    stages: [
      { tag: "Stage 1", name: "Pure Text", desc: "PyMuPDF for lightning-fast extraction from digital-native PDFs." },
      { tag: "Stage 2", name: "Standard OCR", desc: "Tesseract OCR with OpenCV preprocessing (grayscale, thresholding, denoising) for scanned documents." },
      { tag: "Stage 3", name: "Vision Fallback", desc: "For low-quality or complex scans, the system triggers OpenAI Vision (GPT-4o) to ensure no text is lost." },
      { tag: "Smart Chunking", name: "Article-level Chunker", desc: "Regex-based slicing by legal headings (\"Article\", \"Section\") preserves legal context and prevents the \"Lost-in-the-Middle\" phenomenon during LLM inference." },
    ],
  },
  {
    id: "layer-3",
    label: "Layer III",
    title: "Reasoning & Mapping",
    subtitle: "Vector-Relational Hybrid",
    body: "We utilise a PostgreSQL + pgvector architecture. Legal clauses are converted into high-dimensional embeddings stored alongside relational metadata, enabling semantic search and multi-pillar mapping via Gemini 1.5 Pro and Claude 3.5 Sonnet across all 11 RDTII pillars simultaneously.",
  },
  {
    id: "layer-4",
    label: "Layer IV",
    title: "Verification & Audit",
    subtitle: "Expert Review Interface",
    body: "Every AI-generated mapping is linked to exact source coordinates. The Workbench UI allows legal experts to review, approve, or reject mappings. Approved decisions are persisted directly into the database, generating a verified audit trail for UN submission.",
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

const team = [
  { name: "Dong", role: "Tech Leader & Architect", desc: "Orchestrated the foundational system framework and end-to-end development workflow, bridging legal compliance and technical execution." },
  { name: "Katie", role: "Legal Leader", desc: "Legal scholar with native-level English and Chinese proficiency. Directs regulatory logic, resolves linguistic conflicts, and ensures PDPA compliance." },
  { name: "Chenming", role: "Full-Stack & AI Engineer", desc: "Spearheaded the frontend UI design while deeply integrating the RAG pipeline, LLM interactions, and PostgreSQL database workflows." },
  { name: "Abel", role: "Backend Engineer", desc: "Lead developer for the robust backend infrastructure, building the core Python extraction pipelines and anti-bot crawler engine." },
  { name: "Rujing", role: "Project Coordinator", desc: "Manages cross-functional liaison, external communications, and technical documentation, ensuring seamless project execution." },
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
          {/* Drop a video file at /public/tech-memo-bg.mp4 to activate */}
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
        <nav className="hidden md:flex flex-col gap-3 sticky top-24 self-start w-44 shrink-0 text-sm -translate-x-8 -ml-20">
          <p className="text-xs font-semibold uppercase tracking-widest opacity-40 mb-2 mt-10">On this page</p>
          {[
            { href: "#summary", label: "Summary" },
            { href: "#pipeline", label: "Four-Layer Pipeline" },
            { href: "#sustainability", label: "Sustainability" },
            { href: "#team", label: "Team Expertise" },
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

          {/* Executive Summary */}
          <section id="summary">
            <h2 className="text-2xl md:text-3xl font-semibold mb-6 mt-10 sticky top-0 py-3 backdrop-blur-md bg-white/80 z-20">
              Summary
            </h2>
            <p className="opacity-70 leading-relaxed text-lg">
              Team <strong>SENTINEL</strong> presents an industrial-grade, end-to-end pipeline that transforms
              fragmented legal documents into structured, evidence-based insights across all 12 RDTII Pillars.
              By combining advanced automation with a <em>Human-in-the-Loop</em> verification mechanism, we
              ensure 100% auditable and hallucination-free regulatory analysis.
            </p>
          </section>

          <div className="h-px w-[calc(100%+3rem)] -ml-6 bg-[#10B981]/40" />

          {/* Four-Layer Pipeline */}
          <section id="pipeline">
            <h2 className="text-2xl md:text-3xl font-semibold mb-10 sticky top-0 py-3 backdrop-blur-md bg-white/80 z-20">
              4 Layer Pipeline
            </h2>
            <div className="space-y-10">
              {layers.map((layer) => (
                <div key={layer.id}>
                  <div className="relative border border-[#10B981]/20 p-8 hover:border-[#10B981]/50 transition-colors">
                    {/* Gradient number tag — top right */}
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

          <p className="text-xs opacity-40 italic pb-8 mb-10">
            This memo is submitted to the UN Global Hackathon Committee on behalf of Team SENTINEL.
            All technical details reflect the prototype built during the hackathon period.
          </p>

        </div>

        {/* Right vertical divider */}
        <div className="hidden md:block w-px self-stretch bg-[#10B981]/40" />

      </div>
      </div>{/* end gradient wrapper */}

      <div className="h-px w-full bg-[#10B981]/40" />

      <Footer />
    </main>
  );
}
