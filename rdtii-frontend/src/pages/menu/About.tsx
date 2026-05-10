import Footer from "@/components/Footer/Footer";
import ColorBends from "@/components/ColorBends/ColorBends";

const team = [
  {
    name: "Dong",
    role: "Tech Leader & Architect",
    desc: "Orchestrated the foundational system framework and end-to-end development workflow, providing critical cross-disciplinary guidance bridging legal compliance and technical execution.",
  },
  {
    name: "Katie",
    role: "Legal Leader",
    desc: "A legal scholar with native-level proficiency in both English and Chinese. Serves as the ultimate legal authority, directing regulatory logic, resolving linguistic conflicts, and ensuring PDPA compliance.",
  },
  {
    name: "Chenming",
    role: "Full-Stack & AI Engineer",
    desc: "Spearheaded the stunning frontend UI design, while deeply integrating the RAG pipeline, LLM interactions, and PostgreSQL database workflows.",
  },
  {
    name: "Abel",
    role: "Backend Engineer",
    desc: "Lead developer for the robust backend infrastructure, building the core Python extraction pipelines and anti-bot crawler engine.",
  },
  {
    name: "Rujing",
    role: "Project Coordinator",
    desc: "Manages cross-functional liaison, external communications, and technical documentation, ensuring seamless project execution.",
  },
];

const pillars = [
  { number: "1", title: "Tariffs and trade defence", desc: "Covers tariffs and trade defence measures applied to intraregional imports of ICT goods." },
  { number: "2", title: "Public procurement", desc: "Policies governing participation in public procurement of ICT goods and digital services." },
  { number: "3", title: "Foreign direct investment", desc: "Policies regulating foreign direct investment in sectors related to digital trade." },
  { number: "4", title: "Intellectual property rights", desc: "IPRs frameworks, including provisions for protection and innovation." },
  { number: "5", title: "Telecommunications", desc: "Policies related to telecommunications infrastructure and market competition." },
  { number: "6", title: "Cross-border data policies", desc: "Data localization rules, Standard Contractual Clauses, and adequacy decisions across APAC jurisdictions." },
  { number: "7", title: "Domestic data protection & Privacy", desc: "National privacy frameworks, consent obligations, and breach notification requirements." },
  { number: "8", title: "Internet intermediary liability", desc: "Legal frameworks for internet intermediary liability." },
  { number: "9", title: "Content access", desc: "Regulations on access to online content and measures related to illegal content." },
  { number: "10", title: "Non-technical NTMs", desc: "Non-technical non-tariff measures (NTMs) affecting trade in ICT goods and digital trade." },
  { number: "11", title: "Standards and procedures", desc: "Technical standards and conformity assessment procedures relevant to digital trade." },
  { number: "12", title: "Online sales and transactions", desc: "Regulations related to online sales and transactions, including electronic signatures." },
];

const architecture = [
  {
    step: "01",
    title: "Deterministic Anchoring",
    desc: "Regex & PDFPlumber precisely slice legal PDFs by articles and clauses — no hallucinations at the slicing layer.",
  },
  {
    step: "02",
    title: "Semantic Extraction",
    desc: "NLP/LLM API reads each chunk and extracts specific compliance obligations with indicator-level granularity.",
  },
  {
    step: "03",
    title: "Structured Mapping",
    desc: "Pydantic & JSON Schema force LLM outputs into strict RDTII-compliant data structures.",
  },
  {
    step: "04",
    title: "Transparency Audit View",
    desc: "React frontend links every JSON mapping directly back to highlighted source text in the original document.",
  },
];

export function AboutPage() {
  return (
    <main className="relative min-h-screen font-geist">

      {/* Full-page ColorBends background — desktop only */}
      <div className="fixed inset-0 -z-10 hidden md:block">
        <ColorBends colors={["#44ad8a", "#07864d"]} speed={0.2} intensity={1.5} noise={0.15} frequency={1} />
      </div>
      <div className="fixed inset-0 -z-10 hidden md:block bg-white/30" />
      {/* Mobile solid fallback */}
      <div className="fixed inset-0 -z-10 md:hidden bg-white" />

      {/* Hero */}
      <section className="relative text-center overflow-hidden bg-white">

        <p className="relative z-10 text-[#10B981] text-sm font-semibold uppercase tracking-widest mb-4 py-20">
          UN Global Hackathon 2025 · Maynooth University
        </p>
        <h1 className="relative z-10 text-4xl md:text-6xl font-bold mb-6">
          TEAM{" "}
          <span className="text-[#10B981]">SENTINEL</span>
        </h1>
        <p className="relative z-10 text-lg md:text-xl opacity-70 max-w-2xl mx-auto leading-relaxed pb-20">
          Automated Workflow for ESCAP Researchers to grade RDTII Indicators.
          <br />
          <span className="italic">"Where Code Meets Law."</span>
        </p>

        {/* line */}
        <div className="relative z-10 mt-0 h-px w-full bg-[#10B981]/40" />
      </section>

      {/* Body: quick nav + content */}
      {/* White covers left-to-right-divider; right margin stays transparent (ColorBends shows) */}
      <div style={{ background: "linear-gradient(to right, white calc(50% + 576px), transparent calc(50% + 576px))" }}>
      <div className="flex gap-6 max-w-6xl mx-auto items-stretch px-4 md:px-0">

        {/* Quick nav — sticky left sidebar */}
        <nav className="hidden md:flex flex-col gap-3 sticky top-24 w-44 shrink-0 text-sm">
          <p className="text-xs font-semibold uppercase tracking-widest opacity-40 mb-2 mt-10">On this page</p>
          {[
            { href: "#mission", label: "Mission" },
            { href: "#focus", label: "Core Focus" },
            { href: "#architecture", label: "Architecture" },
            { href: "#team", label: "The Squad" },
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

        {/* Vertical divider */}
        <div className="hidden md:block w-px self-stretch bg-[#10B981]/40 -ml-20" />

        {/* Main content — left justified */}
        <div className="flex-1 min-w-0 space-y-16 pb-10">

          {/* Mission */}
          <section id="mission">
            <h2 className="text-2xl md:text-3xl font-semibold mb-6 mt-10 sticky top-0 py-3 backdrop-blur-md bg-background/80 z-20">The Mission</h2>
          <p className="opacity-70 leading-relaxed text-lg">
              Sentinel is an automated workflow engine designed for UN ESCAP researchers to map legal evidence 
              against all 12 RDTII pillars. It automates the discovery, extraction, and mapping of complex 
              digital trade regulations, transforming raw legislation into structured, evidence-based policy insights.
            </p>
          </section>

          <div className="h-px w-[calc(100%+3rem)] -ml-6 bg-[#10B981]/40" />

          {/* Core Focus */}
          <section id="focus">
            <h2 className="text-2xl md:text-3xl font-semibold mb-10 sticky top-0 py-3 backdrop-blur-md bg-background/80 z-20">Core Focus</h2>
            <div className="grid md:grid-cols-2 gap-6">
              {pillars.map((p) => (
                <div
                  key={p.number}
                  className="rounded-none border border-[#10B981]/20 p-8 hover:border-[#10B981]/50 transition-colors"
                >
                  <span className="text-[#10B981] text-4xl font-black opacity-30">P{p.number}</span>
                  <h3 className="text-lg font-semibold mt-2 mb-3">{p.title}</h3>
                  <p className="opacity-60 text-sm leading-relaxed">{p.desc}</p>
                </div>
              ))}
            </div>
          </section>

          <div className="h-px w-[calc(100%+3rem)] -ml-6 bg-[#10B981]/40" />

          {/* Architecture */}
          <section id="architecture">
            <h2 className="text-2xl md:text-3xl font-semibold mb-10 sticky top-0 py-3 backdrop-blur-md bg-background/80 z-20">Hybrid Architecture</h2>
            <div className="grid md:grid-cols-2 gap-6">
              {architecture.map((a) => (
                <div key={a.step} className="flex gap-5">
                  <span className="text-[#10B981] text-2xl font-black opacity-30 shrink-0 w-8">{a.step}</span>
                  <div>
                    <h3 className="font-semibold mb-1">{a.title}</h3>
                    <p className="opacity-60 text-sm leading-relaxed">{a.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="h-px w-[calc(100%+3rem)] -ml-6 bg-[#10B981]/40" />

          {/* Team */}
          <section id="team">
            <h2 className="text-2xl md:text-3xl font-semibold mb-10 sticky top-0 py-3 backdrop-blur-md bg-background/80 z-20">The Squad</h2>
            <div className="grid sm:grid-cols-2 gap-6">
              {team.map((m) => (
                <div
                  key={m.name}
                  className="rounded-none border border-[#10B981]/20 p-8 hover:border-[#10B981]/50 transition-colors"
                >
                  <h3 className="font-semibold text-lg mb-1">{m.name}</h3>
                  <p className="text-[#10B981] text-xs font-medium uppercase tracking-wide mb-3">{m.role}</p>
                  <p className="opacity-60 text-sm leading-relaxed">{m.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Disclaimer */}
          <p className="text-xs opacity-40 italic mb-5">
            Disclaimer: The outputs of this tool are for conceptual demonstration and research
            purposes only, not formal legal advice.
          </p>

        </div>

        {/* Vertical divider — right */}
        <div className="hidden md:block w-px self-stretch bg-[#10B981]/40" />

      </div>
      </div>

      <div className="h-px w-full bg-[#10B981]/40" />

      <Footer />
    </main>
  );
}
