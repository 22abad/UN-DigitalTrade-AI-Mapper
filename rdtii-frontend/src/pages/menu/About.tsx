import Footer from "@/components/Footer/Footer";

const team = [
  {
    name: "Dong Li",
    role: "Project Manager & Legal Architect",
    desc: "20+ years of legal practice. Bridges legal logic and coding algorithms.",
    icon: "⚖️",
  },
  {
    name: "Rujing Xu",
    role: "Policy Analyst & Narrative Lead",
    desc: "Economics & Trade expert. Defines business value and policy mapping.",
    icon: "📊",
  },
  {
    name: "Jie Xu",
    role: "Tech Lead & Backend Engine",
    desc: "Python developer. Architect of the text-to-data extraction MVP (FastAPI).",
    icon: "⚙️",
  },
  {
    name: "Chenming Tao",
    role: "UX/UI & AI Video Lead",
    desc: "Design expert. Crafts the Audit View UI and cinematic concept presentation.",
    icon: "🎨",
  },
];

const pillars = [
  {
    number: "6",
    title: "Cross-border Data Policies",
    desc: "Data localisation rules, Standard Contractual Clauses, and adequacy decisions across APAC jurisdictions.",
  },
  {
    number: "7",
    title: "Domestic Data Protection & Privacy",
    desc: "National privacy frameworks, consent obligations, and breach notification requirements.",
  },
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
    <main className="min-h-screen">

      {/* Hero */}
      <section className="relative px-6 py-32 text-center">
        <p className="text-[#10B981] text-sm font-semibold uppercase tracking-widest mb-4">
          UN Global Hackathon 2025 · Maynooth University
        </p>
        <h1 className="text-4xl md:text-6xl font-bold mb-6">
          About{" "}
          <span className="text-[#10B981]">Sentinel</span>
        </h1>
        <p className="text-lg md:text-xl opacity-70 max-w-2xl mx-auto leading-relaxed">
          Secure Evidence-based Network for Trade &amp; International Law.
          <br />
          <span className="italic">"Where Code Meets Law."</span>
        </p>

        {/* Gradient line */}
        <div className="mt-16 h-px w-full bg-gradient-to-r from-transparent via-[#10B981]/40 to-transparent" />
      </section>

      {/* Mission */}
      <section className="px-6 py-16 max-w-4xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-semibold mb-6">The Mission</h2>
        <p className="opacity-70 leading-relaxed text-lg">
          Global digital trade is hindered by fragmented data localisation and privacy laws.
          Traditional manual legal review is no longer scalable. <strong>Sentinel</strong> is a
          hybrid extraction engine designed to automatically discover, extract, and map complex
          digital trade regulations against the{" "}
          <a
            href="https://www.unescap.org"
            target="_blank"
            rel="noreferrer"
            className="text-[#10B981] hover:underline"
          >
            UNESCAP Regional Digital Trade Integration Index (RDTII 2.1)
          </a>
          .
        </p>
      </section>

      {/* Gradient line */}
      <div className="h-px w-full bg-gradient-to-r from-transparent via-[#10B981]/40 to-transparent" />

      {/* Core Focus */}
      <section className="px-6 py-16 max-w-4xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-semibold mb-10">Core Focus</h2>
        <div className="grid md:grid-cols-2 gap-6">
          {pillars.map((p) => (
            <div
              key={p.number}
              className="rounded-2xl border border-[#10B981]/20 p-8 hover:border-[#10B981]/50 transition-colors"
            >
              <span className="text-[#10B981] text-4xl font-black opacity-30">P{p.number}</span>
              <h3 className="text-lg font-semibold mt-2 mb-3">{p.title}</h3>
              <p className="opacity-60 text-sm leading-relaxed">{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Gradient line */}
      <div className="h-px w-full bg-gradient-to-r from-transparent via-[#10B981]/40 to-transparent" />

      {/* Architecture */}
      <section className="px-6 py-16 max-w-4xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-semibold mb-10">Hybrid Architecture</h2>
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

      {/* Gradient line */}
      <div className="h-px w-full bg-gradient-to-r from-transparent via-[#10B981]/40 to-transparent" />

      {/* Team */}
      <section className="px-6 py-16 max-w-4xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-semibold mb-10">The Squad</h2>
        <div className="grid sm:grid-cols-2 gap-6">
          {team.map((m) => (
            <div
              key={m.name}
              className="rounded-2xl border border-[#10B981]/20 p-8 hover:border-[#10B981]/50 transition-colors"
            >
              <span className="text-3xl">{m.icon}</span>
              <h3 className="font-semibold text-lg mt-3 mb-1">{m.name}</h3>
              <p className="text-[#10B981] text-xs font-medium uppercase tracking-wide mb-3">{m.role}</p>
              <p className="opacity-60 text-sm leading-relaxed">{m.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Gradient line */}
      <div className="h-px w-full bg-gradient-to-r from-transparent via-[#10B981]/40 to-transparent" />

      {/* Disclaimer */}
      <section className="px-6 py-10 text-center">
        <p className="text-xs opacity-40 italic max-w-xl mx-auto">
          Disclaimer: The outputs of this tool are for conceptual demonstration and research
          purposes only, not formal legal advice.
        </p>
      </section>

      <Footer />
    </main>
  );
}
