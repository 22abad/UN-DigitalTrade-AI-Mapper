import { TextHoverEffect } from "@/components/Footer/Hoverfooter";

export function Label() {
  return (
    <section className="relative z-20 mt-12">

      {/* Text hover effect */}
      <div className="flex h-[16rem] lg:h-[30rem]">
        <TextHoverEffect text="RDTII 2.1" className="z-50" />
      </div>

      <div className="h-px w-full bg-[#10B981]/40" />

      {/* Label content */}
      <div className="flex gap-6 max-w-6xl mx-auto items-start py-16 px-6">

        {/* Left label */}
        <div className="hidden md:block w-44 shrink-0">
          <p className="text-xs font-semibold uppercase tracking-widest opacity-40 ">What is Sentinel?</p>
        </div>

        {/* Vertical divider */}
        <div className="hidden md:block w-px self-stretch bg-[#10B981]/40" />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl md:text-4xl font-semibold mb-6">
            Automated RDTII Grading Engine
          </h2>
          <p className="opacity-70 leading-relaxed text-lg max-w-2xl">
            Sentinel is an automated workflow engine designed for UN ESCAP researchers to map legal evidence 
            against all 12 Pillars of RDTII 2.1, transforming raw legislation into structured evidence in minutes.
          </p>
        </div>

        {/* Vertical divider */}
        <div className="hidden md:block w-px self-stretch bg-[#10B981]/40" />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl md:text-4xl font-semibold mb-6">
            How It Works
          </h2>
          <p className="opacity-70 leading-relaxed text-lg max-w-2xl">
            From raw legislation to structured evidence — in minutes. 
            Our hybrid extraction engine automates the discovery, extraction, 
            and mapping of regulations to provide evidence-based policy insights.
          </p>
        </div>

      </div>

      <div className="h-px w-full bg-[#10B981]/40" />

    </section>
  );
}
