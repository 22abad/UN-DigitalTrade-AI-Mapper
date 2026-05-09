import React from "react";
import { Mail, MapPin, Globe } from "lucide-react";
import { FooterBackgroundGradient } from "@/components/Footer/Hoverfooter";
import { TextHoverEffect } from "@/components/Footer/Hoverfooter";
import { Links } from "react-router-dom";

function HoverFooter() {
  const footerLinks = [
    {
      title: "About",
      links: [
        { label: "Our Solution", href: "/workbench" },
        { label: "About Us", href: "/about" },
        { label: "Classification Logic", href: "#" },
        { label: "API Docs", href: "#" },
      ],
    },
    {
      title: "Account",
      links: [
        { label: "Sign In", href: "/login" },
        { label: "Register", href: "/register" },
        { label: "Live Status", href: "#", pulse: true },
      ],
    },
  ];

  const contactInfo = [
    {
      icon: <Mail size={18} className="text-[#10B981]" />,
      text: "sentinel@hackathon.un.org",
      href: "mailto:sentinel@hackathon.un.org",
    },
    {
      icon: <Globe size={18} className="text-[#10B981]" />,
      text: "UN Global Hackathon 2025",
      href: "#",
    },
    {
      icon: <MapPin size={18} className="text-[#10B981]" />,
      text: "Maynooth University, Ireland",
    },
  ];

  return (
    <footer className="relative h-fit rounded-3xl overflow-hidden w-full">
      
      {/* separator */}
      <div className="mt-12 h-px w-full bg-[#10B981]/40" />

      <div className="max-w-7xl mx-auto p-14 z-40 relative">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12 md:gap-8 lg:gap-16 pb-12">

          {/* Brand section */}
          <div className="flex flex-col space-y-4">
            <span className="text-[#10B981] text-3xl font-bold tracking-tight">SENTINEL</span>
            <p className="text-sm leading-relaxed">
              <span className="italic">"Where Code Meets Law."</span>
              <br />
              Secure Evidence-based Network for Trade &amp; International Law — built for the UN ESCAP RDTII 2.1 framework.
            </p>
            <p className="text-xs opacity-50 leading-relaxed">
              Open-source prototype · Maynooth University
            </p>
          </div>

          {/* Footer link sections */}
          {footerLinks.map((section) => (
            <div key={section.title}>
              <h4 className="text-ink text-lg font-semibold mb-6">
                {section.title}
              </h4>
              <ul className="space-y-3">
                {section.links.map((link) => (
                  <li key={link.label} className="relative">
                    <a href={link.href} className="hover:text-ink transition-colors">
                      {link.label}
                    </a>
                    {link.pulse && (
                      <span className="absolute top-0 right-[-10px] w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {/* Contact section */}
          <div>
            <h4 className="text-ink text-lg font-semibold mb-6">Contact</h4>
            <ul className="space-y-4">
              {contactInfo.map((item, i) => (
                <li key={i} className="flex items-center space-x-3">
                  {item.icon}
                  {item.href ? (
                    <a href={item.href} className="hover:text-[#10B981] transition-colors text-sm">
                      {item.text}
                    </a>
                  ) : (
                    <span className="text-sm">{item.text}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>


        {/* Footer bottom */}
        <div className="flex flex-col md:flex-row justify-between items-center text-xs opacity-60 space-y-2 md:space-y-0">
          <p>
            &copy; {new Date().getFullYear()} Sentinel · Maynooth University ·{" "}
            <span className="italic">
              Outputs are for conceptual demonstration only.
            </span>
          </p>
          <a
            href="https://www.unescap.org"
            target="_blank"
            rel="noreferrer"
            className="hover:text-[#10B981] transition-colors"
          >
            UN ESCAP RDTII 2.1 ↗
          </a>
        </div>
      </div>

      {/* Text hover effect — full width, pushed down so only top edge is visible */}
      <div className="lg:flex hidden h-[25rem] -mt-82 -mb-28">
        <TextHoverEffect text="SENTINEL" className="z-50 w-full" />
      </div>

      <FooterBackgroundGradient />
    </footer>
  );
}

export default HoverFooter;
