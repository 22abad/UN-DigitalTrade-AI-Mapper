import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

const EASE = [0.65, 0.01, 0.05, 0.99] as const;

const navLinks = [
  { label: "Home", href: "/", index: "01" },
  { label: "About", href: "/about", index: "02" },
  { label: "Workbench", href: "/workbench", index: "03" },
  { label: "Tech Memo", href: "/tech_memo", index: "04" },
];

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const { user, logout } = useAuth();

  // Close on escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Lock body scroll when open
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  if (
    location.pathname === "/login" ||
    location.pathname === "/register" ||
    location.pathname === "/workbench"
  )
    return null;

  return (
    <>
      {/* Toggle button — only visible when closed */}
      <AnimatePresence>
        {!open && (
          <motion.button
            onClick={() => setOpen(true)}
            aria-label="Open menu"
            className="fixed top-5 right-5 z-[60] text-xs font-light text-[#FFFFF] tracking-widest uppercase bg-transparent border-0 p-0 min-h-0"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            Menu
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop */}
            <motion.div
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35, ease: EASE }}
              onClick={() => setOpen(false)}
            />

            {/* Drawer — slides from right */}
            <motion.aside
              className="fixed top-0 right-0 bottom-0 z-50 w-[80vw] max-w-sm flex flex-col bg-[#0a0a0a] border-l border-white/[0.06] overflow-hidden"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ duration: 0.55, ease: EASE }}
            >
              {/* Staggered background strips */}
              {[0, 1].map((i) => (
                <motion.div
                  key={i}
                  className="absolute inset-0 bg-[#111] origin-right"
                  initial={{ scaleX: 1 }}
                  animate={{ scaleX: 0 }}
                  exit={{ scaleX: 1 }}
                  transition={{ duration: 0.55, delay: i * 0.08, ease: EASE }}
                />
              ))}

              {/* Header */}
              <motion.div
                className="flex items-center justify-between px-7 pt-6 pb-4"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ delay: 0.3, duration: 0.3 }}
              >
                <img src="/svg.svg" alt="Sentinel" className="h-5 w-auto brightness-0 invert opacity-30" />
                <button
                  onClick={() => setOpen(false)}
                  className="text-white/30 hover:text-white/70 transition-colors text-xl leading-none bg-transparent border-0 p-0 min-h-0"
                >
                  ✕
                </button>
              </motion.div>

              {/* Nav links */}
              <nav className="flex flex-col px-7 mt-6 flex-1">
                {navLinks.map((link, i) => (
                  <NavItem
                    key={link.href}
                    link={link}
                    index={i}
                    active={location.pathname === link.href}
                    onNavigate={() => setOpen(false)}
                  />
                ))}
              </nav>

              {/* Footer */}
              <motion.div
                className="px-7 pb-10 pt-6 border-t border-white/[0.06] flex items-center justify-between"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ delay: 0.45, duration: 0.35 }}
              >
                <span className="text-[10px] text-white/20 tracking-widest uppercase">
                  UN Digital Trade
                </span>
                {user ? (
                  <button
                    className="text-xs text-white/40 hover:text-white transition-colors bg-transparent border-0 p-0 min-h-0"
                    onClick={() => { logout(); setOpen(false); window.location.href = "/"; }}
                  >
                    Sign out →
                  </button>
                ) : (
                  <button
                    className="text-xs text-white/40 hover:text-white transition-colors bg-transparent border-0 p-0 min-h-0"
                    onClick={() => { setOpen(false); window.location.href = "/login"; }}
                  >
                    Login →
                  </button>
                )}
              </motion.div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

function NavItem({
  link,
  index,
  active,
  onNavigate,
}: {
  link: { label: string; href: string; index: string };
  index: number;
  active: boolean;
  onNavigate: () => void;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <motion.a
      href={link.href}
      onClick={onNavigate}
      initial={{ opacity: 0, x: 40, rotateX: -15 }}
      animate={{ opacity: 1, x: 0, rotateX: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ delay: 0.25 + index * 0.07, duration: 0.45, ease: EASE }}
      className="relative flex items-center justify-between py-5 border-b border-white/[0.06] group overflow-hidden"
      onHoverStart={() => setHovered(true)}
      onHoverEnd={() => setHovered(false)}
    >
      {/* Hover fill */}
      <motion.span
        className="absolute inset-0 bg-white/[0.04] rounded-lg"
        initial={false}
        animate={{ opacity: hovered ? 1 : 0, x: hovered ? 0 : -8 }}
        transition={{ duration: 0.2 }}
      />

      <div className="flex items-baseline gap-3 relative">
        <span className="text-[10px] text-white/20 font-mono">{link.index}</span>
        <motion.span
          className="text-2xl font-light tracking-tight"
          animate={{
            x: hovered ? 4 : 0,
            color: active ? "#10B981" : hovered ? "#ffffff" : "rgba(255,255,255,0.6)",
          }}
          transition={{ duration: 0.25, ease: EASE }}
        >
          {link.label}
        </motion.span>
      </div>

      <motion.span
        className="relative text-white/30 text-sm"
        animate={{ opacity: hovered ? 1 : 0, x: hovered ? 0 : -6 }}
        transition={{ duration: 0.2 }}
      >
        →
      </motion.span>
    </motion.a>
  );
}
