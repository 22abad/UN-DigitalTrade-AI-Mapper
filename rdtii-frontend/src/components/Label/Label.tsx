import { TextHoverEffect } from "@/components/Footer/Hoverfooter";

export function Label() {
  return (
    <section className="label-section relative z-20 mt-12">

      {/* Text hover effect */}
      <div className="lg:flex hidden h-[30rem]">
        <TextHoverEffect text="RDTII 2.1" className="z-50" />
      </div>

      <div className="mt-12 h-px w-full bg-[#10B981]/40" />

      {/* Main label content */}
      <div className="relative z-20 px-6 mt-12">
        <h2 className="text-2xl md:text-4xl font-semibold text-gray-800 mb-4">
          Mapping the Digital Trade Landscape
        </h2>
        <p className="text-gray-600 max-w-xl mx-auto">
          The UN ESCAP Digital Trade Evidence Workbench empowers policymakers
          with AI-driven insights, enabling informed decision-making in the
          rapidly evolving digital trade ecosystem.
        </p>
      </div>

      {/* Bottom separator */}
      <div className="mt-12 h-px w-full bg-[#10B981]/40" />

    </section>
  );
}
