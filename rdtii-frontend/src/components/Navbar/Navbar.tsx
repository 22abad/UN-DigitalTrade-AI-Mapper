import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

const navLinks = [
  { label: "About", href: "/about" },
  { label: "Workbench", href: "/workbench" },
  { label: "About the Logic", href: "/tech_memo" },
];

export function Navbar() {
  const location = useLocation();
  const [pastHero, setPastHero] = useState(false);

  useEffect(() => {
    const onScroll = () => setPastHero(window.scrollY > window.innerHeight * 0.9);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (location.pathname === "/login" || location.pathname === "/register" || location.pathname === "/workbench") return null;

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 bg-transparent">

        {/* Logo */}
        <div
          className="relative flex items-center cursor-pointer group"
          onClick={() => window.location.href = "/"}
        >
          <img
            src="/svg.svg"
            alt="Sentinel"
            aria-hidden="true"
            className={`h-7 w-auto transition-all duration-500 group-hover:drop-shadow-lg ${pastHero ? "" : "brightness-0 invert"}`}
          />
        </div>

        {/* Nav links */}
        <nav className="flex items-center space-x-1">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className={`text-xs font-light px-3 py-2 rounded-full transition-all duration-500 ${pastHero ? "text-[#10B981]/80 hover:text-[#10B981] hover:bg-[#10B981]/10" : "text-white/80 hover:text-white hover:bg-white/10"}`}
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Login button */}
        <button
          className={`group flex items-center justify-center rounded-full text-xs h-8 px-5 cursor-pointer transition-all duration-500 ${pastHero ? "bg-[#10B981] text-white" : "bg-white text-black"}`}
          onClick={() => window.location.href = "/login"}
        >
          <span>Login</span>
          <span className="overflow-hidden w-0 group-hover:w-4 transition-all duration-300 flex items-center justify-center">
            <svg className="w-3 h-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 17L17 7M17 7H7M17 7V17" />
            </svg>
          </span>
        </button>

      </header>
    </>
  );
}
