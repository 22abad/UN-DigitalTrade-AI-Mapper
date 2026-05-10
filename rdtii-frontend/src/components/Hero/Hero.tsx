import ColorBends from "@/components/ColorBends/ColorBends";

export function Hero() {
  return (
    <section className="relative h-screen w-full overflow-hidden">
      {/* Background canvas */}
      <div className="absolute inset-0">
        <ColorBends
          colors={["#44ad8a", "#07864d"]}
          speed={0.2}
          intensity={1.5}
          noise={0.15}
          frequency={1}
        />
      </div>

      {/* Shader overlay */}
      <div className="absolute inset-0 z-10 bg-black/10" />

      {/* Overlay content */}
      <div className="relative z-20 flex flex-col items-center justify-center h-full text-center px-6">
        <h1 className="text-5xl md:text-7xl font-bold text-white drop-shadow-lg">
          SENTINEL
        </h1>
        <p className="mt-6 text-lg md:text-xl text-white max-w-2xl drop-shadow">
          Empowering policymakers with AI-driven insights for informed
          decision-making in digital trade.
        </p>
        <a
          href="/workbench"
          className="mt-10 px-8 py-3 rounded-full bg-black/10 border border-grey/10 text-white font-medium backdrop-blur-sm hover:bg-black/25 transition"
        >
          Open Workbench →
        </a>
      </div>
    </section>
  );
}
