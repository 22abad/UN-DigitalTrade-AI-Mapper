const bricks = [
  {
    tag: "01",
    title: "Ingest Any Source",
    body: "Paste raw legal text or drop a URL — Sentinel crawls official government portals, handles JavaScript rendering, and extracts clean text from PDFs automatically.",
  },
  {
    tag: "02",
    title: "AI-Powered Mapping",
    body: "Gemini and Claude reason over every clause, mapping provisions to all 12 RDTII pillars simultaneously with verbatim evidence and confidence scores.",
  },
  {
    tag: "03",
    title: "Human-in-the-Loop Audit",
    body: "Legal experts review, approve, or reject each mapping in the Workbench. Every decision is persisted to the database, creating a fully auditable trail for UN submission.",
  },
];

export function Description() {
  return (
    <section className="bg-white py-24 px-6">
      <div className="max-w-5xl mx-auto">

        {/* Header */}
        <div className="mb-16">
          <p className="text-[#10B981] text-xs font-bold uppercase tracking-widest mb-3">How it works</p>
          <h2 className="text-3xl md:text-4xl font-bold text-[#1f2933] max-w-xl leading-tight">
            From raw legislation to structured evidence — in minutes.
          </h2>
        </div>

        {/* Bricks */}
        <div className="grid md:grid-cols-3 gap-px bg-[#e4eaee]">
          {bricks.map((b) => (
            <div key={b.tag} className="bg-white p-8 flex flex-col gap-4">
              <span className="text-3xl font-black text-[#10B981]/20 leading-none">{b.tag}</span>
              <h3 className="text-lg font-semibold text-[#1f2933]">{b.title}</h3>
              <p className="text-sm text-[#667085] leading-relaxed">{b.body}</p>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}
