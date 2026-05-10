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
          <p className="text-xs font-semibold uppercase tracking-widest opacity-40 ">What's Sentinel ?</p>
        </div>

        {/* Vertical divider */}
        <div className="hidden md:block w-px self-stretch bg-[#10B981]/40" />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl md:text-4xl font-semibold mb-6">
            Mapping the Digital Trade Landscape
          </h2>
          <p className="opacity-70 leading-relaxed text-lg max-w-2xl">
            Sentinel empowers policymakers
            with AI-driven insights, enabling informed decision-making in the
            rapidly evolving digital trade ecosystem.
          </p>
        </div>

      </div>

      <div className="h-px w-full bg-[#10B981]/40" />

    </section>
  );
}
