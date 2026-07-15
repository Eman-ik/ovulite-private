import { useEffect, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  motion,
  useScroll,
  useTransform,
  useSpring,
  useReducedMotion,
  useMotionValueEvent,
  AnimatePresence,
} from "framer-motion";
import {
  ArrowRight,
  ArrowUpRight,
  Brain,
  ChevronRight,
  CircleDot,
  Database,
  FlaskConical,
  Gauge,
  GitMerge,
  LineChart,
  Menu,
  Microscope,
  Play,
  Quote,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Target,
  Workflow,
  X,
} from "lucide-react";

/* ============================================================
   Ovulite — Premium cinematic landing page
   Single file, Tailwind + Framer Motion + lucide-react.
   Scoped styling so global app theme is untouched.
   ============================================================ */

// Warm cream / amber / gold palette — matches the brand reference image.
// Legacy key names (forest, cream, bio…) are kept so existing references
// resolve; the values are what define the new look.
const PALETTE = {
  forest: "#E8D5B7",         // page bg — warm cream
  forestDeep: "#DEC59E",     // recessed surfaces — deeper cream
  emerald: "#A87432",        // mid accent — bronze
  emeraldGlow: "#C9963F",    // bright accent — amber
  terracotta: "#8B5A2B",     // warm secondary — bronze
  terracottaSoft: "#B8794A", // softer secondary
  cream: "#4A3220",          // primary text — dark warm brown
  stone: "#704A24",          // secondary text — medium brown
  bio: "#A87432",            // glow / highlight — readable bronze (was soft gold #E8B86F, too low contrast on cream)
  ink: "#3D2817",            // deepest contrast — espresso brown
};

const NAV = [
  { label: "Platform", id: "platform" },
  { label: "Pillars", id: "pillars" },
  { label: "How it Works", id: "how" },
  { label: "Features", id: "features" },
  { label: "Testimonials", id: "testimonials" },
];

export default function OvuliteLandingPage() {
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [navHidden, setNavHidden] = useState(false);
  const reduceMotion = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);
  const lastScrollY = useRef(0);
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { scrollY } = useScroll();
  useMotionValueEvent(scrollY, "change", (v) => {
    setScrolled(v > 24);

    // Direction-aware nav: hide on scroll-down past hero, show on scroll-up.
    const prev = lastScrollY.current;
    const delta = v - prev;
    if (v < 80) {
      setNavHidden(false);
    } else if (delta > 6) {
      setNavHidden(true);
    } else if (delta < -6) {
      setNavHidden(false);
    }
    lastScrollY.current = v;

    // Auto-hide after scroll stops (1.6s of inactivity), unless near top.
    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => {
      if (scrollY.get() > 240) setNavHidden(true);
    }, 1600);
  });

  // We will let the global CSS handle the background color now.

  return (
    <div
      ref={containerRef}
      className="ov-root relative min-h-screen w-full overflow-x-hidden"
      style={{
        fontFamily: "'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif",
      }}
    >
      <ScopedStyles />
      <GrainOverlay />
      <NoiseGradient />

      <Header
        navigate={navigate}
        scrolled={scrolled}
        hidden={navHidden}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
      />

      <Hero navigate={navigate} reduceMotion={!!reduceMotion} />

      <ProblemSection />

      <PillarsSection />

      <HowItWorksSection />

      <FeaturesSection />

      <DashboardPreviewSection />

      <TrustSection />

      <TestimonialsSection />

      <Footer />
    </div>
  );
}

/* -----------------------------------------------------------
   Scoped styles + fonts (no global CSS edits)
   ----------------------------------------------------------- */
function ScopedStyles() {
  return (
    <style>{`
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600;9..144,700;9..144,800&family=Inter:wght@300;400;500;600;700;800&display=swap');

      .ov-root, .ov-root * { font-feature-settings: "ss01","cv11"; }
      .ov-root .ov-serif {
        font-family: 'Fraunces', 'Times New Roman', serif;
        font-optical-sizing: auto;
        letter-spacing: -0.022em;
      }
      .ov-root .ov-mono {
        font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
        letter-spacing: 0.02em;
      }
      .ov-root .ov-eyebrow {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.28em;
        font-weight: 600;
      }

      .ov-glass-card {
        background: linear-gradient(180deg, rgba(74, 50, 32, 0.045), rgba(74, 50, 32, 0.018));
        backdrop-filter: blur(18px) saturate(140%);
        -webkit-backdrop-filter: blur(18px) saturate(140%);
        border: 1px solid rgba(74, 50, 32, 0.08);
        box-shadow:
          inset 0 1px 0 rgba(74, 50, 32, 0.06),
          inset 0 0 30px rgba(201, 150, 63, 0.04),
          0 30px 80px -30px rgba(60, 35, 15, 0.55);
        border-radius: 22px;
      }

      .ov-glass-card.ov-glow:hover {
        border-color: rgba(232, 184, 111, 0.22);
        box-shadow:
          inset 0 1px 0 rgba(74, 50, 32, 0.08),
          inset 0 0 60px rgba(201, 150, 63, 0.10),
          0 40px 100px -25px rgba(60, 35, 15, 0.6);
      }

      .ov-text-grad {
        background: linear-gradient(120deg, #4A3220 0%, #704A24 35%, #C9963F 75%, #A87432 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: transparent;
      }

      .ov-text-warm {
        background: linear-gradient(100deg, #4A3220 0%, #8B5A2B 55%, #C9963F 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: transparent;
      }

      .ov-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(74, 50, 32, 0.18), transparent);
      }

      .ov-grain {
        position: fixed; inset: 0; pointer-events: none; z-index: 1;
        opacity: 0.06; mix-blend-mode: overlay;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.5 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
      }

      .ov-vignette {
        position: fixed; inset: 0; pointer-events: none; z-index: 0;
        background:
          radial-gradient(ellipse at 18% 0%, rgba(201, 150, 63, 0.16), transparent 55%),
          radial-gradient(ellipse at 92% 8%, rgba(139, 90, 43, 0.12), transparent 50%),
          radial-gradient(ellipse at 50% 100%, rgba(232, 213, 183, 0.6), transparent 60%);
      }

      @keyframes ovFloat {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
      }
      .ov-float { animation: ovFloat 5.5s ease-in-out infinite; }
      .ov-float-slow { animation: ovFloat 8s ease-in-out infinite; }

      @keyframes ovPulseRing {
        0% { box-shadow: 0 0 0 0 rgba(232, 184, 111, 0.45); }
        80%, 100% { box-shadow: 0 0 0 22px rgba(232, 184, 111, 0); }
      }
      .ov-pulse { animation: ovPulseRing 2.6s cubic-bezier(0.4,0,0.2,1) infinite; }

      @keyframes ovDash {
        to { stroke-dashoffset: -200; }
      }
      .ov-dash { stroke-dasharray: 4 6; animation: ovDash 6s linear infinite; }

      @keyframes ovOrbit {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      .ov-link {
        position: relative; transition: color 220ms ease;
      }
      .ov-link::after {
        content: ''; position: absolute; left: 0; bottom: -4px;
        width: 100%; height: 1px;
        background: linear-gradient(90deg, #E8B86F, #B8794A);
        transform: scaleX(0); transform-origin: left;
        transition: transform 320ms cubic-bezier(0.22, 1, 0.36, 1);
      }
      .ov-link:hover::after { transform: scaleX(1); }

      .ov-btn-primary {
        position: relative; isolation: isolate;
        background: linear-gradient(135deg, #A87432 0%, #E8D5B7 100%);
        color: #4A3220;
        border: 1px solid rgba(232, 184, 111, 0.28);
        box-shadow:
          inset 0 1px 0 rgba(74, 50, 32, 0.14),
          0 14px 40px -16px rgba(201, 150, 63, 0.6),
          0 0 0 0 rgba(232, 184, 111, 0);
        transition: transform 240ms cubic-bezier(0.22,1,0.36,1), box-shadow 240ms ease;
      }
      .ov-btn-primary:hover {
        transform: translateY(-2px);
        box-shadow:
          inset 0 1px 0 rgba(74, 50, 32, 0.2),
          0 22px 50px -18px rgba(201, 150, 63, 0.8),
          0 0 0 4px rgba(232, 184, 111, 0.08);
      }
      .ov-btn-primary::before {
        content: ''; position: absolute; inset: 0; border-radius: inherit; z-index: -1;
        background: linear-gradient(135deg, rgba(232, 184, 111, 0.2), transparent 60%);
        opacity: 0; transition: opacity 240ms ease;
      }
      .ov-btn-primary:hover::before { opacity: 1; }

      .ov-btn-ghost {
        background: rgba(74, 50, 32, 0.04);
        color: #4A3220;
        border: 1px solid rgba(74, 50, 32, 0.18);
        transition: all 240ms ease;
      }
      .ov-btn-ghost:hover {
        background: rgba(74, 50, 32, 0.09);
        border-color: rgba(232, 184, 111, 0.4);
        transform: translateY(-2px);
      }

      .ov-tick { color: #E8B86F; }

      /* Marquee for trust badges */
      @keyframes ovScroll {
        from { transform: translateX(0); }
        to { transform: translateX(-50%); }
      }
      .ov-marquee-track { animation: ovScroll 28s linear infinite; }

      @media (prefers-reduced-motion: reduce) {
        .ov-float, .ov-float-slow, .ov-pulse, .ov-dash, .ov-marquee-track {
          animation: none !important;
        }
      }
    `}</style>
  );
}

function GrainOverlay() {
  return <div className="ov-grain" />;
}
function NoiseGradient() {
  return <div className="ov-vignette" />;
}

/* -----------------------------------------------------------
   Header
   ----------------------------------------------------------- */
function Header({
  navigate,
  scrolled,
  hidden,
  mobileOpen,
  setMobileOpen,
}: {
  navigate: (p: string) => void;
  scrolled: boolean;
  hidden: boolean;
  mobileOpen: boolean;
  setMobileOpen: (v: boolean) => void;
}) {
  return (
    <motion.header
      initial={{ y: -40, opacity: 0 }}
      animate={{
        y: hidden && !mobileOpen ? -120 : 0,
        opacity: hidden && !mobileOpen ? 0 : 1,
      }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className="fixed inset-x-0 top-0 z-50 px-4 pt-4 sm:px-6"
    >
      <div
        className="mx-auto flex max-w-[1600px] items-center justify-between rounded-full px-5 py-3 transition-all duration-500"
        style={{
          background: scrolled ? "rgba(222, 197, 158, 0.78)" : "rgba(222, 197, 158, 0.42)",
          backdropFilter: "blur(16px) saturate(150%)",
          WebkitBackdropFilter: "blur(16px) saturate(150%)",
          border: `1px solid ${scrolled ? "rgba(74, 50, 32, 0.10)" : "rgba(74, 50, 32, 0.06)"}`,
          boxShadow: scrolled ? "0 16px 40px -20px rgba(60, 35, 15, 0.5)" : "none",
        }}
      >
        <a href="#top" className="flex items-center gap-3">
          <Logo />
          <div className="leading-none">
            <div className="ov-serif text-[15px] font-semibold tracking-tight" style={{ color: PALETTE.cream }}>
              Ovulite
            </div>
            <div
              className="ov-eyebrow mt-0.5"
              style={{ color: "#8B5A2B", fontSize: 9, fontWeight: 700 }}
            >
              Reproductive&nbsp;Intelligence
            </div>
          </div>
        </a>

        <nav className="hidden items-center gap-8 lg:flex">
          {NAV.map((n) => (
            <a
              key={n.id}
              href={`#${n.id}`}
              className="ov-link text-[13px] font-medium"
              style={{ color: "rgba(74, 50, 32, 0.85)" }}
            >
              {n.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 sm:flex">
          <button
            onClick={() => navigate("/login")}
            className="rounded-full px-4 py-2 text-[13px] font-medium ov-link"
            style={{ color: "rgba(74, 50, 32, 0.85)" }}
          >
            Sign in
          </button>
          <button
            onClick={() => navigate("/login")}
            className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-[13px] font-semibold transition-all duration-200 hover:-translate-y-0.5"
            style={{
              background: "linear-gradient(135deg, #3D2817 0%, #4A3220 100%)",
              color: "#FAF1DD",
              border: "1px solid rgba(74, 50, 32, 0.6)",
              boxShadow:
                "0 10px 24px -10px rgba(60, 35, 15, 0.6), inset 0 1px 0 rgba(250, 241, 221, 0.12)",
            }}
          >
            Request Demo
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <button
          className="rounded-full p-2 sm:hidden"
          aria-label="Open menu"
          onClick={() => setMobileOpen(!mobileOpen)}
          style={{ color: PALETTE.cream }}
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mx-auto mt-2 max-w-[1600px] overflow-hidden rounded-3xl px-5 py-3 sm:hidden"
            style={{ background: "rgba(222, 197, 158, 0.92)", border: "1px solid rgba(74, 50, 32, 0.08)" }}
          >
            {NAV.map((n) => (
              <a
                key={n.id}
                href={`#${n.id}`}
                className="block py-2.5 text-sm"
                style={{ color: "rgba(74, 50, 32, 0.85)" }}
                onClick={() => setMobileOpen(false)}
              >
                {n.label}
              </a>
            ))}
            <div className="mt-2 flex gap-2">
              <button
                onClick={() => navigate("/login")}
                className="ov-btn-ghost flex-1 rounded-full py-2.5 text-sm font-semibold"
              >
                Sign in
              </button>
              <button
                onClick={() => navigate("/login")}
                className="ov-btn-primary flex-1 rounded-full py-2.5 text-sm font-semibold"
              >
                Demo
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}

function Logo() {
  return (
    <div className="relative flex h-9 w-9 items-center justify-center">
      <svg viewBox="0 0 40 40" className="absolute inset-0">
        <defs>
          <radialGradient id="lg1" cx="50%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#E8B86F" stopOpacity="0.95" />
            <stop offset="60%" stopColor="#A87432" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#E8D5B7" stopOpacity="1" />
          </radialGradient>
          <linearGradient id="lg2" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#B8794A" />
            <stop offset="100%" stopColor="#8B5A2B" />
          </linearGradient>
        </defs>
        <circle cx="20" cy="20" r="17" fill="url(#lg1)" />
        <circle cx="20" cy="20" r="17" fill="none" stroke="rgba(232, 184, 111, 0.4)" strokeWidth="0.6" />
        <circle cx="20" cy="20" r="6.5" fill="none" stroke="rgba(74, 50, 32, 0.5)" strokeWidth="0.8" />
        <circle cx="14.5" cy="18" r="2.4" fill="url(#lg2)" />
        <circle cx="22.5" cy="16" r="1.8" fill="rgba(232, 184, 111, 0.85)" />
        <circle cx="24" cy="22" r="2" fill="rgba(74, 50, 32, 0.85)" />
        <circle cx="17" cy="24" r="1.6" fill="rgba(232, 184, 111, 0.7)" />
      </svg>
    </div>
  );
}

/* -----------------------------------------------------------
   HERO — animated SVG biology scene + parallax
   ----------------------------------------------------------- */
function Hero({ navigate, reduceMotion: _reduceMotion }: { navigate: (p: string) => void; reduceMotion: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const y1 = useTransform(scrollYProgress, [0, 1], [0, -80]);
  const y2 = useTransform(scrollYProgress, [0, 1], [0, -160]);
  const y3 = useTransform(scrollYProgress, [0, 1], [0, -240]);
  const opacity = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  return (
    <section
      id="top"
      ref={ref}
      className="relative px-4 pt-24 sm:px-6"
    >
      {/* Hero panel — bronze gradient container that frames the entire hero */}
      <div
        className="relative mx-auto w-full max-w-[1600px] overflow-hidden rounded-[36px]"
        style={{
          background:
            "radial-gradient(120% 110% at 25% 40%, #DEC59E 0%, #C9963F 45%, #A87432 100%)",
          border: "1px solid rgba(74, 50, 32, 0.28)",
          boxShadow:
            "inset 0 1px 0 rgba(250, 241, 221, 0.35), inset 0 0 60px rgba(232, 184, 111, 0.08), 0 40px 90px -30px rgba(60, 35, 15, 0.45), 0 12px 28px -10px rgba(168, 116, 50, 0.35)",
        }}
      >
        {/* Soft inner glow accents (parallax) — kept inside the panel */}
        <motion.div
          style={{ y: y3 }}
          className="pointer-events-none absolute inset-0"
          aria-hidden
        >
          <BackdropGlow />
        </motion.div>
        <motion.div
          style={{ y: y2, opacity }}
          className="pointer-events-none absolute inset-0 flex items-center justify-end"
          aria-hidden
        >
          <div className="hidden h-[640px] w-[640px] translate-x-1/4 lg:block opacity-50">
            <BackdropGlow />
          </div>
        </motion.div>

        {/* Subtle top-edge highlight */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-px"
          style={{
            background:
              "linear-gradient(90deg, transparent, rgba(250, 241, 221, 0.55), transparent)",
          }}
        />

        <motion.div
          style={{ y: y1 }}
          className="relative z-10 grid w-full grid-cols-1 items-center gap-12 px-6 py-16 sm:px-10 sm:py-20 lg:grid-cols-[1.05fr_0.95fr] lg:px-14 lg:py-24"
        >
        <div className="space-y-7">
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-[11px] font-semibold"
            style={{
              background: "rgba(250, 241, 221, 0.85)",
              border: "1px solid rgba(139, 90, 43, 0.35)",
              color: "#8B5A2B",
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              boxShadow: "0 4px 14px -6px rgba(168, 116, 50, 0.35)",
            }}
          >
            <CircleDot className="h-3 w-3" style={{ color: "#C9963F" }} />
            <span>Reproductive Intelligence Platform</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="ov-serif text-[clamp(2.8rem,5.6vw,5.2rem)] font-light leading-[0.98] tracking-tight"
            style={{ color: PALETTE.cream }}
          >
            Precision <span className="ov-text-warm italic">Reproduction.</span>
            <br />
            Powered by <span className="ov-text-grad">Intelligence.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="max-w-xl text-[17px] leading-relaxed"
            style={{ color: "rgba(74, 50, 32, 0.82)" }}
          >
            AI-driven embryo grading, pregnancy prediction, and lab QC — engineered for
            bovine embryo transfer programs that demand objective, traceable, and
            explainable decisions at every stage of the IVF–ET cycle.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.45 }}
            className="flex flex-wrap items-center gap-3 pt-2"
          >
            <button
              onClick={() => navigate("/login")}
              className="ov-btn-primary group inline-flex items-center gap-2 rounded-full px-7 py-3.5 text-sm font-semibold"
            >
              Explore the Platform
              <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </button>
            <button className="ov-btn-ghost inline-flex items-center gap-2 rounded-full px-6 py-3.5 text-sm font-semibold">
              <span
                className="grid h-6 w-6 place-items-center rounded-full"
                style={{ background: "rgba(232, 184, 111, 0.18)" }}
              >
                <Play className="h-3 w-3" fill="#E8B86F" stroke="#E8B86F" />
              </span>
              Watch 2-min Demo
            </button>
          </motion.div>

          {/* Category pills — quick-scan capability badges */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-wrap items-center gap-2.5 pt-3"
          >
            {[
              { label: "Embryo Grading", active: true },
              { label: "Pregnancy Prediction", active: false },
              { label: "Lab QC", active: false },
              { label: "Analytics", active: false },
              { label: "Reports", active: false },
            ].map((c) => (
              <span
                key={c.label}
                className="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-[14px] font-semibold tracking-tight transition-all duration-200 hover:-translate-y-0.5"
                style={
                  c.active
                    ? {
                        background:
                          "linear-gradient(135deg, #C9963F 0%, #A87432 100%)",
                        color: "#FAF1DD",
                        border: "1px solid rgba(232, 184, 111, 0.5)",
                        boxShadow:
                          "0 10px 22px -8px rgba(168, 116, 50, 0.6), inset 0 1px 0 rgba(250, 241, 221, 0.35)",
                      }
                    : {
                        background: "rgba(250, 241, 221, 0.78)",
                        color: "#4A3220",
                        border: "1px solid rgba(139, 90, 43, 0.3)",
                      }
                }
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{
                    background: c.active ? "#FAF1DD" : "#C9963F",
                    boxShadow: c.active ? "0 0 6px #FAF1DD" : "none",
                  }}
                />
                {c.label}
              </span>
            ))}
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.7 }}
            className="grid max-w-xl grid-cols-3 gap-6 pt-8"
          >
            {[
              { k: "4,400", l: "Clinical Records" },
              { k: "39", l: "Variables Modeled" },
              { k: "9", l: "Intelligence Modules" },
            ].map((s) => (
              <div key={s.l}>
                <div
                  className="ov-serif text-3xl font-medium"
                  style={{ color: PALETTE.cream }}
                >
                  {s.k}
                </div>
                <div className="ov-eyebrow mt-1" style={{ color: "rgba(74, 50, 32, 0.72)" }}>
                  {s.l}
                </div>
              </div>
            ))}
          </motion.div>
        </div>

        {/* Right column — floating product chips */}
        <div className="relative">
          <FloatingHeroChips />
        </div>
        </motion.div>

        <ScrollIndicator />
      </div>
    </section>
  );
}

/* ------ Hero cow portrait — premium framed image with amber glow ------ */
function BackdropGlow() {
  return (
    <>
      <div
        className="absolute -left-32 top-10 h-[520px] w-[520px] rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(201, 150, 63, 0.30), transparent 65%)",
          filter: "blur(44px)",
        }}
      />
      <div
        className="absolute right-[-10%] top-[40%] h-[520px] w-[520px] rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(139, 90, 43, 0.20), transparent 65%)",
          filter: "blur(48px)",
        }}
      />
      <div
        className="absolute left-[40%] bottom-0 h-[420px] w-[420px] rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(232, 184, 111, 0.16), transparent 65%)",
          filter: "blur(50px)",
        }}
      />
    </>
  );
}

function ScrollIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 1.4, duration: 1 }}
      className="pointer-events-none absolute inset-x-0 bottom-8 z-20 flex flex-col items-center gap-2"
    >
      <span className="ov-eyebrow text-[10px]" style={{ color: "rgba(74, 50, 32, 0.7)" }}>
        Scroll to explore
      </span>
      <div className="relative h-9 w-[18px] rounded-full" style={{ border: "1px solid rgba(74, 50, 32, 0.25)" }}>
        <motion.div
          className="absolute left-1/2 top-1.5 h-1.5 w-1.5 -translate-x-1/2 rounded-full"
          style={{ background: PALETTE.bio }}
          animate={{ y: [0, 14, 0], opacity: [1, 0, 1] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
    </motion.div>
  );
}

/* ------ Animated SVG biology scene: blastocyst → neural network → calf silhouette ------ */
function BiologyScene({ reduceMotion }: { reduceMotion: boolean }) {
  // Phase cycles 0 → 1 → 2 → 0 (embryo → neural → calf)
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    if (reduceMotion) return;
    const id = window.setInterval(() => setPhase((p) => (p + 1) % 3), 5200);
    return () => window.clearInterval(id);
  }, [reduceMotion]);

  return (
    <div className="relative h-full w-full">
      {/* Outer halo ring */}
      <div className="absolute inset-0 grid place-items-center">
        <div
          className="ov-pulse h-[78%] w-[78%] rounded-full"
          style={{
            background:
              "radial-gradient(circle, rgba(232, 184, 111, 0.10) 0%, rgba(201, 150, 63, 0.05) 40%, transparent 70%)",
            border: "1px solid rgba(232, 184, 111, 0.18)",
          }}
        />
      </div>

      {/* Orbiting particles */}
      <div className="absolute inset-0" style={{ animation: reduceMotion ? "none" : "ovOrbit 22s linear infinite" }}>
        {[0, 60, 120, 180, 240, 300].map((deg) => (
          <div
            key={deg}
            className="absolute left-1/2 top-1/2 h-1.5 w-1.5 rounded-full"
            style={{
              background: PALETTE.bio,
              boxShadow: "0 0 12px rgba(232, 184, 111, 0.7)",
              transform: `rotate(${deg}deg) translate(180px) rotate(-${deg}deg)`,
            }}
          />
        ))}
      </div>

      <svg viewBox="0 0 600 600" className="absolute inset-0 h-full w-full">
        <defs>
          <radialGradient id="cellGrad" cx="50%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#F0D9A8" stopOpacity="0.95" />
            <stop offset="60%" stopColor="#C9963F" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#E8D5B7" stopOpacity="1" />
          </radialGradient>
          <radialGradient id="warmCell" cx="50%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#D4A878" stopOpacity="0.92" />
            <stop offset="100%" stopColor="#8B5A2B" stopOpacity="0.95" />
          </radialGradient>
          <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#E8B86F" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#B8794A" stopOpacity="0.7" />
          </linearGradient>
          <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* PHASE 0: Blastocyst */}
        <g transform="translate(300 300)">
          {[
            { x: -90, y: -10, r: 38, g: "url(#cellGrad)" },
            { x: -30, y: -78, r: 32, g: "url(#cellGrad)" },
            { x: 50, y: -64, r: 36, g: "url(#cellGrad)" },
            { x: 88, y: 10, r: 30, g: "url(#warmCell)" },
            { x: 60, y: 74, r: 34, g: "url(#cellGrad)" },
            { x: -20, y: 86, r: 32, g: "url(#cellGrad)" },
            { x: -78, y: 54, r: 28, g: "url(#cellGrad)" },
            { x: 0, y: 0, r: 22, g: "url(#warmCell)" },
          ].map((c, i) => (
            <motion.circle
              key={i}
              cx={c.x}
              cy={c.y}
              r={c.r}
              fill={c.g}
              filter="url(#softGlow)"
              animate={
                reduceMotion
                  ? {}
                  : {
                      opacity: phase === 0 ? [0.95, 1, 0.95] : 0.08,
                      scale: phase === 0 ? [1, 1.04, 1] : 0.85,
                    }
              }
              transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.18, ease: "easeInOut" }}
              style={{ transformOrigin: `${c.x}px ${c.y}px` }}
            />
          ))}
          {/* Outer membrane */}
          <motion.circle
            cx={0}
            cy={0}
            r={150}
            fill="none"
            stroke="rgba(232, 184, 111, 0.35)"
            strokeWidth="1"
            animate={reduceMotion ? {} : { opacity: phase === 0 ? 0.7 : 0.1 }}
            transition={{ duration: 1.4 }}
          />
        </g>

        {/* PHASE 1: Neural network */}
        <g>
          {(() => {
            const nodes = [
              [120, 220], [120, 320], [120, 420],
              [300, 160], [300, 280], [300, 380], [300, 460],
              [480, 220], [480, 340], [480, 440],
            ];
            const edges: [number, number][] = [];
            for (let i = 0; i < 3; i++) for (let j = 3; j < 7; j++) edges.push([i, j]);
            for (let i = 3; i < 7; i++) for (let j = 7; j < 10; j++) edges.push([i, j]);
            return (
              <>
                {edges.map(([a, b], i) => (
                  <motion.line
                    key={i}
                    x1={nodes[a][0]}
                    y1={nodes[a][1]}
                    x2={nodes[b][0]}
                    y2={nodes[b][1]}
                    stroke="url(#lineGrad)"
                    strokeWidth="0.8"
                    initial={false}
                    animate={
                      reduceMotion ? {} : { opacity: phase === 1 ? 0.55 : 0, pathLength: phase === 1 ? 1 : 0 }
                    }
                    transition={{ duration: 0.9, delay: i * 0.012 }}
                  />
                ))}
                {nodes.map(([x, y], i) => (
                  <motion.circle
                    key={i}
                    cx={x}
                    cy={y}
                    r={8}
                    fill={i % 4 === 0 ? "url(#warmCell)" : "url(#cellGrad)"}
                    filter="url(#softGlow)"
                    initial={false}
                    animate={
                      reduceMotion
                        ? {}
                        : {
                            opacity: phase === 1 ? [0.85, 1, 0.85] : 0.05,
                            scale: phase === 1 ? [1, 1.18, 1] : 0.6,
                          }
                    }
                    transition={{ duration: 2, repeat: Infinity, delay: i * 0.1, ease: "easeInOut" }}
                    style={{ transformOrigin: `${x}px ${y}px` }}
                  />
                ))}
              </>
            );
          })()}
        </g>

        {/* PHASE 2: Calf silhouette */}
        <g transform="translate(300 320)">
          <motion.path
            d="M -130 30 C -130 -10, -100 -50, -60 -52 C -40 -85, 10 -90, 40 -70 C 80 -78, 120 -55, 130 -10 C 140 30, 130 60, 100 70 L 90 110 L 70 110 L 70 80 L 30 80 L 30 110 L 10 110 L 10 80 C -20 80, -60 85, -90 80 L -90 110 L -110 110 L -110 80 C -125 70, -135 55, -130 30 Z"
            fill="url(#cellGrad)"
            stroke="rgba(232, 184, 111, 0.45)"
            strokeWidth="1.2"
            filter="url(#softGlow)"
            initial={false}
            animate={
              reduceMotion
                ? {}
                : {
                    opacity: phase === 2 ? 0.95 : 0,
                    scale: phase === 2 ? 1 : 0.8,
                  }
            }
            transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
            style={{ transformOrigin: "0 0" }}
          />
          <motion.circle
            cx={-50}
            cy={-60}
            r={4}
            fill="#4A3220"
            initial={false}
            animate={reduceMotion ? {} : { opacity: phase === 2 ? 1 : 0 }}
            transition={{ duration: 1.2 }}
          />
          {/* Heart pulse line under calf */}
          <motion.path
            d="M -100 130 L -60 130 L -50 110 L -30 150 L -10 100 L 10 160 L 30 130 L 100 130"
            fill="none"
            stroke="#B8794A"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={false}
            animate={reduceMotion ? {} : { opacity: phase === 2 ? 0.9 : 0 }}
            transition={{ duration: 1, delay: 0.6 }}
          />
        </g>

        {/* Phase indicator label */}
        <g transform="translate(300 540)">
          <motion.text
            textAnchor="middle"
            fontFamily="Fraunces, serif"
            fontStyle="italic"
            fontSize="14"
            fill="rgba(74, 50, 32, 0.6)"
            initial={false}
            animate={{ opacity: 1 }}
          >
            {phase === 0 ? "Blastocyst" : phase === 1 ? "Inference" : "Outcome"}
          </motion.text>
        </g>
      </svg>

      {/* Phase dots */}
      <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-1 rounded-full transition-all duration-500"
            style={{
              width: phase === i ? 22 : 8,
              background: phase === i ? PALETTE.bio : "rgba(74, 50, 32, 0.25)",
            }}
          />
        ))}
      </div>
    </div>
  );
}

function FloatingHeroChips() {
  // Solid-cream glass card style — high contrast for readable text on top of
  // the cow image. Reused inline so we don't disturb the page-wide .ov-glass-card.
  const chipBg: React.CSSProperties = {
    background: "rgba(250, 241, 221, 0.94)",
    backdropFilter: "blur(14px) saturate(150%)",
    WebkitBackdropFilter: "blur(14px) saturate(150%)",
    border: "1px solid rgba(139, 90, 43, 0.22)",
    boxShadow:
      "inset 0 1px 0 rgba(250, 241, 221, 0.8), 0 24px 60px -22px rgba(60, 35, 15, 0.45), 0 6px 18px -6px rgba(168, 116, 50, 0.25)",
    borderRadius: 18,
  };
  const eyebrow: React.CSSProperties = {
    color: "#8B5A2B",
    fontSize: 9,
    letterSpacing: "0.16em",
    textTransform: "uppercase",
    fontWeight: 700,
  };

  return (
    <>
      {/* SHAP Explanation — top-right */}
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.92 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ delay: 0.9, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="ov-float pointer-events-none absolute -top-6 -right-6 hidden w-56 p-4 lg:block"
        style={chipBg}
      >
        <div className="mb-2" style={eyebrow}>
          SHAP Explanation
        </div>
        <div className="space-y-1.5">
          {[
            { k: "CL Size", v: 0.84, c: "#C9963F" },
            { k: "Progesterone", v: 0.67, c: "#C9963F" },
            { k: "Day 7 Stage", v: 0.51, c: "#8B5A2B" },
            { k: "Blood Flow", v: 0.38, c: "#A87432" },
          ].map((b) => (
            <div key={b.k} className="flex items-center gap-2">
              <span
                className="w-20 text-[10.5px] font-medium"
                style={{ color: "#4A3220" }}
              >
                {b.k}
              </span>
              <div
                className="relative h-1.5 flex-1 overflow-hidden rounded-full"
                style={{ background: "rgba(74, 50, 32, 0.12)" }}
              >
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${b.v * 100}%` }}
                  transition={{ delay: 1.1, duration: 1.2, ease: "easeOut" }}
                  className="absolute inset-y-0 left-0 rounded-full"
                  style={{ background: b.c, boxShadow: `0 0 6px ${b.c}` }}
                />
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Pregnancy Probability — bottom-right of the cow */}
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.92 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ delay: 1.05, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="ov-float-slow pointer-events-none absolute -bottom-4 -right-4 hidden w-56 p-4 lg:block"
        style={chipBg}
      >
        <div className="flex items-center justify-between">
          <div>
            <div style={eyebrow}>Pregnancy Probability</div>
            <div
              className="ov-serif mt-1 text-3xl font-semibold leading-none"
              style={{ color: "#4A3220" }}
            >
              74<span className="text-base font-medium">%</span>
            </div>
          </div>
          <RagGauge value={74} />
        </div>
        <div
          className="mt-2 flex items-center gap-1.5 text-[10.5px] font-semibold"
          style={{ color: "#8B5A2B" }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: "#C9963F", boxShadow: "0 0 6px #E8B86F" }}
          />
          Confidence: High · RAG · Green
        </div>
      </motion.div>

      {/* Grad-CAM — bottom-left of the cow */}
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.92 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ delay: 1.2, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="ov-float pointer-events-none absolute bottom-10 -left-8 hidden w-44 p-3 lg:block"
        style={chipBg}
      >
        <div className="mb-1.5" style={eyebrow}>
          Grad-CAM
        </div>
        <div
          className="h-14 w-full rounded-lg"
          style={{
            background:
              "radial-gradient(circle at 30% 40%, rgba(139, 90, 43, 0.9), transparent 45%), radial-gradient(circle at 70% 60%, rgba(232, 184, 111, 0.85), transparent 50%), linear-gradient(135deg, #DEC59E, #C9963F)",
          }}
        />
        <div
          className="mt-2 text-[10.5px] font-medium"
          style={{ color: "#4A3220" }}
        >
          E-211 · Grade A · 92% conf
        </div>
      </motion.div>
    </>
  );
}

function RagGauge({ value }: { value: number }) {
  const r = 18;
  const c = 2 * Math.PI * r;
  const dash = (value / 100) * c;
  return (
    <svg viewBox="0 0 50 50" width={50} height={50} className="-rotate-90">
      <circle cx="25" cy="25" r={r} fill="none" stroke="rgba(74, 50, 32, 0.1)" strokeWidth="3" />
      <motion.circle
        cx="25"
        cy="25"
        r={r}
        fill="none"
        stroke="#E8B86F"
        strokeWidth="3"
        strokeLinecap="round"
        initial={{ strokeDasharray: `0 ${c}` }}
        animate={{ strokeDasharray: `${dash} ${c}` }}
        transition={{ duration: 1.4, delay: 1.2, ease: "easeOut" }}
        style={{ filter: "drop-shadow(0 0 4px rgba(232, 184, 111, 0.7))" }}
      />
    </svg>
  );
}

/* -----------------------------------------------------------
   PROBLEM SECTION — scrollytelling
   ----------------------------------------------------------- */
function ProblemSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ["start end", "end start"] });
  const blur = useTransform(scrollYProgress, [0.05, 0.45], [12, 0]);
  const blurFilter = useTransform(blur, (v) => `blur(${v}px)`);
  const aiLabelOpacity = useTransform(scrollYProgress, [0.35, 0.55], [0, 1]);
  const heatOpacity = useTransform(scrollYProgress, [0.4, 0.6], [0, 1]);

  return (
    <section ref={sectionRef} id="platform" className="relative px-4 py-16 sm:px-6 lg:py-24">
      <div className="mx-auto max-w-[1600px]">
        <SectionEyebrow text="The Problem" />
        <SectionTitle>
          Subjective grading. <em className="ov-text-warm not-italic">Inconsistent outcomes.</em>
        </SectionTitle>
        <SectionLead>
          For decades, bovine embryo transfer has relied on the human eye, manual records, and
          intuition. The result: an industry shaped by variability — where the same embryo can
          earn different grades from different technicians on different days.
        </SectionLead>

        <div className="mt-20 grid gap-12 lg:grid-cols-2 lg:gap-20">
          {/* Left: counters */}
          <div className="space-y-6">
            {[
              { v: 35, suffix: "%", label: "Grading Variance Between Technicians", color: PALETTE.terracottaSoft },
              { v: 42, suffix: "%", label: "Average ET Pregnancy Success Rate", color: PALETTE.bio },
              { v: 58, suffix: "%", label: "Embryo Wastage From Suboptimal Selection", color: PALETTE.terracotta },
            ].map((s) => (
              <CounterCard key={s.label} {...s} />
            ))}
          </div>

          {/* Right: subjective → objective transformation */}
          <div className="ov-glass-card relative overflow-hidden p-6 sm:p-8">
            <div className="ov-eyebrow mb-3" style={{ color: "rgba(139, 90, 43, 0.95)" }}>
              From Subjective → Objective
            </div>
            <div className="ov-serif text-2xl font-medium leading-snug" style={{ color: PALETTE.cream }}>
              Same embryo. Different lens.
            </div>

            <div className="mt-8 grid grid-cols-2 gap-4">
              <div>
                <div className="ov-eyebrow mb-2 text-[9px]" style={{ color: "rgba(74, 50, 32, 0.68)" }}>
                  Manual Eye
                </div>
                <motion.div
                  style={{ filter: blurFilter }}
                  className="aspect-square w-full rounded-xl"
                >
                  <EmbryoMicroscope />
                </motion.div>
                <div className="mt-2 text-xs" style={{ color: "rgba(74, 50, 32, 0.72)" }}>
                  Grade?  <span style={{ color: PALETTE.terracottaSoft }}>Subjective</span>
                </div>
              </div>

              <div>
                <div className="ov-eyebrow mb-2 text-[9px]" style={{ color: PALETTE.bio }}>
                  Ovulite AI
                </div>
                <div className="relative aspect-square w-full overflow-hidden rounded-xl">
                  <EmbryoMicroscope />
                  <motion.div style={{ opacity: heatOpacity }} className="pointer-events-none absolute inset-0">
                    <GradCamOverlay />
                  </motion.div>
                  <motion.div
                    style={{ opacity: aiLabelOpacity }}
                    className="absolute bottom-2 left-2 rounded-full px-2.5 py-1 text-[10px] font-semibold"
                    initial={false}
                  >
                    <span
                      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1"
                      style={{
                        background: "rgba(232, 213, 183, 0.85)",
                        color: PALETTE.bio,
                        border: "1px solid rgba(232, 184, 111, 0.4)",
                      }}
                    >
                      <span className="h-1.5 w-1.5 rounded-full" style={{ background: PALETTE.bio }} />
                      Grade 1 · 94%
                    </span>
                  </motion.div>
                </div>
                <div className="mt-2 text-xs" style={{ color: "rgba(74, 50, 32, 0.72)" }}>
                  Grade <span style={{ color: PALETTE.bio }}>Objective · Reproducible</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function CounterCard({ v, suffix, label, color }: { v: number; suffix: string; label: string; color: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 80%", "center center"] });
  const motionVal = useTransform(scrollYProgress, [0, 1], [0, v]);
  const smooth = useSpring(motionVal, { stiffness: 80, damping: 20 });
  const [n, setN] = useState(0);
  useMotionValueEvent(smooth, "change", (val) => setN(Math.round(val)));

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -4 }}
      className="ov-glass-card ov-glow flex items-center gap-6 p-7"
    >
      <div className="ov-serif text-6xl font-light" style={{ color }}>
        {n}
        <span className="text-3xl">{suffix}</span>
      </div>
      <div className="flex-1 text-sm leading-relaxed" style={{ color: "rgba(74, 50, 32, 0.85)" }}>
        {label}
      </div>
    </motion.div>
  );
}

function EmbryoMicroscope() {
  return (
    <svg viewBox="0 0 200 200" className="h-full w-full">
      <defs>
        <radialGradient id="emField" cx="50%" cy="50%" r="55%">
          <stop offset="0%" stopColor="#D4A878" />
          <stop offset="100%" stopColor="#3D2817" />
        </radialGradient>
        <radialGradient id="emCell" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor="#F0D9A8" stopOpacity="0.95" />
          <stop offset="100%" stopColor="#A87432" stopOpacity="1" />
        </radialGradient>
      </defs>
      <rect width="200" height="200" fill="url(#emField)" />
      <circle cx="100" cy="100" r="70" fill="none" stroke="rgba(232, 184, 111, 0.18)" strokeWidth="0.5" />
      <circle cx="100" cy="100" r="55" fill="none" stroke="rgba(232, 184, 111, 0.12)" strokeWidth="0.5" />
      {[
        [85, 88, 14], [108, 82, 12], [115, 105, 13], [95, 115, 14], [80, 102, 11], [105, 95, 9],
      ].map(([cx, cy, r], i) => (
        <circle key={i} cx={cx} cy={cy} r={r} fill="url(#emCell)" opacity="0.85" />
      ))}
      <circle cx="100" cy="100" r="42" fill="none" stroke="rgba(74, 50, 32, 0.18)" strokeWidth="0.6" />
    </svg>
  );
}

function GradCamOverlay() {
  return (
    <div
      className="absolute inset-0"
      style={{
        background:
          "radial-gradient(circle at 45% 48%, rgba(184, 121, 74, 0.55) 0%, transparent 30%), radial-gradient(circle at 60% 55%, rgba(212, 168, 120, 0.45) 0%, transparent 28%), radial-gradient(circle at 35% 60%, rgba(232, 184, 111, 0.4) 0%, transparent 35%)",
        mixBlendMode: "screen",
      }}
    />
  );
}

/* -----------------------------------------------------------
   PILLARS
   ----------------------------------------------------------- */
function PillarsSection() {
  const pillars = [
    {
      tag: "Module 01",
      title: "Pregnancy Predictor",
      sub: "TabPFN · XGBoost",
      body: "Forecast transfer-level pregnancy probability using CL size, progesterone, blood flow, embryo metadata, and protocol history. Every prediction is paired with a RAG confidence band and SHAP-based explanations.",
      icon: Brain,
      points: ["RAG confidence scoring", "SHAP feature attribution", "Calibrated reliability bands"],
      accent: PALETTE.bio,
    },
    {
      tag: "Module 02",
      title: "AI Embryo Grader",
      sub: "ResNet18 · Grad-CAM",
      body: "Image-metadata fusion combines deep visual features with day, stage, and media type to produce objective Grade 1/2/3 outputs — with Grad-CAM heatmaps that show exactly what the model saw.",
      icon: ScanLine,
      points: ["Image + metadata fusion", "Grad-CAM heatmaps", "Day 6–8 viability scoring"],
      accent: PALETTE.terracottaSoft,
    },
    {
      tag: "Module 03",
      title: "Lab QC Indicator",
      sub: "Isolation Forest",
      body: "Unsupervised anomaly detection continuously monitors media batches, technician performance, and model drift — flagging deviations before they cascade into wasted embryos or failed cycles.",
      icon: ShieldCheck,
      points: ["Media batch anomalies", "Operator drift detection", "Auto QC reports"],
      accent: PALETTE.emeraldGlow,
    },
  ];

  return (
    <section id="pillars" className="relative px-4 py-16 sm:px-6 lg:py-24">
      <div className="mx-auto max-w-[1600px]">
        <SectionEyebrow text="The Three Pillars" />
        <SectionTitle>
          One platform. <em className="ov-text-grad not-italic">Three intelligences.</em>
        </SectionTitle>
        <SectionLead>
          Ovulite unifies prediction, perception, and process control into a single
          decision-support layer engineered for IVF–ET programs.
        </SectionLead>

        <div className="mt-20 grid gap-6 md:grid-cols-3">
          {pillars.map((p, i) => (
            <PillarCard key={p.title} {...p} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}

function PillarCard({
  tag,
  title,
  sub,
  body,
  icon: Icon,
  points,
  accent,
  index,
}: {
  tag: string;
  title: string;
  sub: string;
  body: string;
  icon: any;
  points: string[];
  accent: string;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 48, scale: 0.95 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.85, delay: index * 0.14, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -10, scale: 1.04 }}
      className="ov-glass-card ov-glow group relative overflow-hidden p-7"
    >
      <div
        className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full opacity-30 blur-3xl transition-opacity duration-500 group-hover:opacity-60"
        style={{ background: accent }}
      />

      <div className="flex items-center justify-between">
        <span className="ov-eyebrow" style={{ color: "rgba(74, 50, 32, 0.7)" }}>
          {tag}
        </span>
        <div
          className="grid h-10 w-10 place-items-center rounded-xl"
          style={{ background: "rgba(232, 184, 111, 0.08)", border: "1px solid rgba(232, 184, 111, 0.2)" }}
        >
          <Icon className="h-4 w-4" style={{ color: accent }} />
        </div>
      </div>

      <h3 className="ov-serif mt-6 text-3xl font-medium leading-tight" style={{ color: PALETTE.cream }}>
        {title}
      </h3>
      <div className="ov-mono mt-1 text-[11px]" style={{ color: accent }}>
        {sub}
      </div>

      <p className="mt-5 text-sm leading-relaxed" style={{ color: "rgba(74, 50, 32, 0.82)" }}>
        {body}
      </p>

      <ul className="mt-6 space-y-2">
        {points.map((p) => (
          <li key={p} className="flex items-center gap-2 text-[13px]" style={{ color: "rgba(74, 50, 32, 0.85)" }}>
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ background: accent, boxShadow: `0 0 6px ${accent}` }}
            />
            {p}
          </li>
        ))}
      </ul>

      <div className="mt-7 flex items-center gap-2 text-[12px] font-medium" style={{ color: accent }}>
        Learn more <ChevronRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
      </div>
    </motion.div>
  );
}

/* -----------------------------------------------------------
   HOW IT WORKS — sticky timeline w/ rail fill
   ----------------------------------------------------------- */
function HowItWorksSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ["start 80%", "end 30%"] });
  const railH = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  const steps = [
    {
      n: "01",
      title: "Data Intake",
      body: "Standardize 39 clinical variables — donor, embryo, recipient, technician, hormones — through structured forms, CSV import, and validation gates.",
      icon: Database,
    },
    {
      n: "02",
      title: "AI Inference",
      body: "Multi-model orchestration runs CNN-based grading, TabPFN/XGBoost prediction, and Isolation Forest anomaly scoring against a calibrated baseline.",
      icon: Brain,
    },
    {
      n: "03",
      title: "Explainable Insight",
      body: "Every output ships with SHAP attributions, Grad-CAM heatmaps, and RAG-coded confidence bands — never a black box, always a biological argument.",
      icon: Sparkles,
    },
    {
      n: "04",
      title: "Better Outcomes",
      body: "Outcomes are recorded, the continuous learning loop ingests them, and the models retrain — closing the feedback loop from OPU to confirmed pregnancy.",
      icon: Target,
    },
  ];

  return (
    <section id="how" ref={sectionRef} className="relative px-4 py-16 sm:px-6 lg:py-24">
      <div className="mx-auto max-w-5xl">
        <SectionEyebrow text="The Workflow" />
        <SectionTitle>
          From clinical record to <em className="ov-text-warm not-italic">confirmed pregnancy.</em>
        </SectionTitle>

        <div className="relative mt-24 pl-6 sm:pl-12">
          {/* Rail */}
          <div className="absolute left-1.5 top-2 bottom-2 w-px sm:left-3.5" style={{ background: "rgba(74, 50, 32, 0.1)" }}>
            <motion.div
              style={{ height: railH }}
              className="absolute left-0 top-0 w-px"
            >
              <div
                className="h-full w-px"
                style={{
                  background: `linear-gradient(180deg, ${PALETTE.bio}, ${PALETTE.terracottaSoft})`,
                  boxShadow: `0 0 12px ${PALETTE.bio}`,
                }}
              />
            </motion.div>
          </div>

          {steps.map((s, i) => (
            <TimelineStep key={s.n} {...s} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}

function TimelineStep({
  n,
  title,
  body,
  icon: Icon,
  index,
}: {
  n: string;
  title: string;
  body: string;
  icon: any;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 30 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: "-120px" }}
      transition={{ duration: 0.7, delay: index * 0.1, ease: [0.22, 1, 0.36, 1] }}
      className="relative mb-16 last:mb-0"
    >
      <div
        className="absolute -left-[26px] top-1.5 grid h-7 w-7 place-items-center rounded-full sm:-left-[42px]"
        style={{
          background: PALETTE.forestDeep,
          border: `1px solid ${PALETTE.bio}`,
          boxShadow: `0 0 0 4px rgba(232, 184, 111, 0.08)`,
        }}
      >
        <Icon className="h-3.5 w-3.5" style={{ color: PALETTE.bio }} />
      </div>
      <div className="ov-eyebrow mb-2" style={{ color: "rgba(139, 90, 43, 0.6)" }}>
        Step {n}
      </div>
      <h3 className="ov-serif text-3xl font-medium tracking-tight sm:text-4xl" style={{ color: PALETTE.cream }}>
        {title}
      </h3>
      <p className="mt-3 max-w-2xl text-[15px] leading-relaxed" style={{ color: "rgba(74, 50, 32, 0.82)" }}>
        {body}
      </p>
    </motion.div>
  );
}

/* -----------------------------------------------------------
   FEATURES GRID
   ----------------------------------------------------------- */
function FeaturesSection() {
  const features = [
    {
      icon: Sparkles,
      title: "SHAP Explanations",
      body: "Per-prediction feature attribution that surfaces which clinical variables drove the score — and by how much.",
    },
    {
      icon: Gauge,
      title: "RAG Confidence",
      body: "Red-Amber-Green bands convert raw probabilities into clinically interpretable trust signals.",
    },
    {
      icon: Microscope,
      title: "Grad-CAM Heatmaps",
      body: "Visual overlays on embryo images expose the regions that influenced the AI's grading decision.",
    },
    {
      icon: Workflow,
      title: "IVF Funnel Analytics",
      body: "Track loss at every stage — OPU → Embryo → ET → Pregnancy — with stage-level conversion KPIs.",
    },
    {
      icon: LineChart,
      title: "Sweet-Spot Charts",
      body: "Optimal CL size and progesterone windows surfaced from outcome data — your biological success bands.",
    },
    {
      icon: GitMerge,
      title: "Recipient Matching",
      body: "Prioritize biologically aligned donor–recipient pairings backed by historical outcome correlations.",
    },
    {
      icon: ShieldCheck,
      title: "Role-Based Access",
      body: "Granular permissions across Vet, Embryologist, Farm Manager, and Admin — protected with JWT.",
    },
    {
      icon: FlaskConical,
      title: "Continuous Learning",
      body: "Outcome data feeds a monitored retraining loop — drift surfaces fast, accuracy keeps improving.",
    },
  ];

  return (
    <section id="features" className="relative px-4 py-16 sm:px-6 lg:py-24">
      <div className="mx-auto max-w-[1600px]">
        <SectionEyebrow text="Capabilities" />
        <SectionTitle>
          Built for teams that need <em className="ov-text-grad not-italic">more than a spreadsheet.</em>
        </SectionTitle>
        <SectionLead>
          Eight capabilities. One coherent intelligence layer. No black boxes.
        </SectionLead>

        <div className="mt-16 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 32, scale: 0.96 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.7, delay: (i % 4) * 0.1, ease: [0.22, 1, 0.36, 1] }}
              whileHover={{ y: -10, scale: 1.06 }}
              className="ov-glass-card ov-glow group p-6"
            >
              <div
                className="grid h-9 w-9 place-items-center rounded-lg transition-all duration-300 group-hover:scale-110"
                style={{
                  background: "rgba(232, 184, 111, 0.08)",
                  border: "1px solid rgba(232, 184, 111, 0.18)",
                }}
              >
                <f.icon className="h-4 w-4" style={{ color: PALETTE.bio }} />
              </div>
              <h4 className="ov-serif mt-4 text-lg font-medium leading-snug" style={{ color: PALETTE.cream }}>
                {f.title}
              </h4>
              <p className="mt-2 text-[13px] leading-relaxed" style={{ color: "rgba(74, 50, 32, 0.8)" }}>
                {f.body}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* -----------------------------------------------------------
   DASHBOARD PREVIEW
   ----------------------------------------------------------- */
function DashboardPreviewSection() {
  return (
    <section className="relative px-4 py-16 sm:px-6 lg:py-24">
      <div className="mx-auto max-w-[1600px]">
        <SectionEyebrow text="The Command Center" />
        <SectionTitle>
          A single pane of glass for <em className="ov-text-warm not-italic">reproductive performance.</em>
        </SectionTitle>

        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.97 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
          className="ov-glass-card relative mt-16 overflow-hidden p-4 sm:p-7"
          style={{ borderRadius: 28 }}
        >
          {/* Window chrome */}
          <div className="mb-5 flex items-center justify-between border-b pb-4" style={{ borderColor: "rgba(74, 50, 32, 0.06)" }}>
            <div className="flex items-center gap-2">
              <div className="h-2.5 w-2.5 rounded-full" style={{ background: "#B8794A" }} />
              <div className="h-2.5 w-2.5 rounded-full" style={{ background: "rgba(74, 50, 32, 0.25)" }} />
              <div className="h-2.5 w-2.5 rounded-full" style={{ background: "rgba(74, 50, 32, 0.25)" }} />
              <div className="ov-mono ml-3 text-[10px]" style={{ color: "rgba(74, 50, 32, 0.68)" }}>
                ovulite.app / dashboard
              </div>
            </div>
            <div className="ov-eyebrow text-[9px]" style={{ color: PALETTE.bio }}>
              Live · Synced
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
            <div className="space-y-4">
              {/* KPI tiles */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  { k: "Active Cases", v: "128", d: "+12 this week", c: PALETTE.bio },
                  { k: "Pregnancy Rate", v: "61%", d: "+8% vs Q3", c: PALETTE.bio },
                  { k: "Avg Confidence", v: "82.4%", d: "RAG: Green", c: PALETTE.bio },
                  { k: "QC Anomalies", v: "3", d: "Media batch B-7", c: PALETTE.terracottaSoft },
                ].map((kpi) => (
                  <motion.div
                    key={kpi.k}
                    whileHover={{ y: -3 }}
                    className="rounded-xl p-3.5"
                    style={{ background: "rgba(74, 50, 32, 0.025)", border: "1px solid rgba(74, 50, 32, 0.05)" }}
                  >
                    <div className="ov-eyebrow text-[9px]" style={{ color: "rgba(74, 50, 32, 0.7)" }}>
                      {kpi.k}
                    </div>
                    <div className="ov-serif mt-1 text-2xl font-medium" style={{ color: kpi.c }}>
                      {kpi.v}
                    </div>
                    <div className="mt-1 text-[10px]" style={{ color: "rgba(74, 50, 32, 0.75)" }}>
                      {kpi.d}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* IVF Funnel */}
              <div
                className="rounded-2xl p-5"
                style={{ background: "rgba(74, 50, 32, 0.025)", border: "1px solid rgba(74, 50, 32, 0.05)" }}
              >
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <div className="ov-eyebrow text-[9px]" style={{ color: "rgba(74, 50, 32, 0.7)" }}>
                      IVF Funnel
                    </div>
                    <div className="ov-serif mt-1 text-base font-medium" style={{ color: PALETTE.cream }}>
                      OPU → Embryo → ET → Pregnancy
                    </div>
                  </div>
                  <div className="ov-mono text-[10px]" style={{ color: PALETTE.bio }}>
                    Last 90 days
                  </div>
                </div>
                <FunnelChart />
              </div>
            </div>

            {/* Right: grading queue */}
            <div className="space-y-3">
              <div
                className="rounded-2xl p-4"
                style={{ background: "rgba(74, 50, 32, 0.025)", border: "1px solid rgba(74, 50, 32, 0.05)" }}
              >
                <div className="mb-3 flex items-center justify-between">
                  <div className="ov-eyebrow text-[9px]" style={{ color: "rgba(74, 50, 32, 0.7)" }}>
                    Grading Queue · Today
                  </div>
                  <Microscope className="h-3.5 w-3.5" style={{ color: PALETTE.bio }} />
                </div>
                <div className="space-y-2">
                  {[
                    { id: "E-211", grade: "1", conf: 94, day: 7 },
                    { id: "E-209", grade: "1", conf: 89, day: 7 },
                    { id: "E-204", grade: "2", conf: 76, day: 8 },
                    { id: "E-198", grade: "3", conf: 81, day: 6 },
                  ].map((e, i) => (
                    <motion.div
                      key={e.id}
                      initial={{ opacity: 0, x: 20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: i * 0.06 }}
                      whileHover={{ x: 3 }}
                      className="flex items-center gap-3 rounded-xl p-2.5"
                      style={{ background: "rgba(232, 184, 111, 0.04)", border: "1px solid rgba(232, 184, 111, 0.1)" }}
                    >
                      <div
                        className="h-9 w-9 rounded-lg"
                        style={{
                          background:
                            "radial-gradient(circle at 35% 45%, rgba(184, 121, 74, 0.6), transparent 50%), radial-gradient(circle at 65% 55%, rgba(232, 184, 111, 0.5), transparent 50%), #E8D5B7",
                        }}
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="ov-mono text-xs font-semibold" style={{ color: PALETTE.cream }}>
                            {e.id}
                          </span>
                          <span
                            className="rounded-full px-2 py-0.5 text-[9px] font-bold"
                            style={{
                              background: e.grade === "1" ? "rgba(232, 184, 111, 0.15)" : e.grade === "2" ? "rgba(212, 168, 120, 0.15)" : "rgba(139, 90, 43, 0.15)",
                              color: e.grade === "1" ? PALETTE.bio : e.grade === "2" ? PALETTE.terracottaSoft : PALETTE.terracotta,
                              border: `1px solid ${e.grade === "1" ? "rgba(232, 184, 111, 0.3)" : e.grade === "2" ? "rgba(212, 168, 120, 0.3)" : "rgba(139, 90, 43, 0.3)"}`,
                            }}
                          >
                            Grade {e.grade}
                          </span>
                        </div>
                        <div className="mt-0.5 text-[10px]" style={{ color: "rgba(74, 50, 32, 0.75)" }}>
                          Day {e.day} · {e.conf}% conf
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

              <div
                className="rounded-2xl p-4"
                style={{ background: "rgba(74, 50, 32, 0.025)", border: "1px solid rgba(74, 50, 32, 0.05)" }}
              >
                <div className="ov-eyebrow text-[9px]" style={{ color: "rgba(74, 50, 32, 0.7)" }}>
                  Sweet Spot · CL Size
                </div>
                <SweetSpotChart />
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function FunnelChart() {
  const stages = [
    { label: "OPU", value: 100, count: "412" },
    { label: "Embryo", value: 78, count: "321" },
    { label: "ET", value: 62, count: "256" },
    { label: "Pregnancy", value: 38, count: "156" },
  ];
  return (
    <div className="space-y-2">
      {stages.map((s, i) => (
        <div key={s.label} className="flex items-center gap-3">
          <div className="ov-mono w-20 text-[10px]" style={{ color: "rgba(74, 50, 32, 0.8)" }}>
            {s.label}
          </div>
          <div className="relative h-8 flex-1 overflow-hidden rounded-lg" style={{ background: "rgba(74, 50, 32, 0.04)" }}>
            <motion.div
              initial={{ width: 0 }}
              whileInView={{ width: `${s.value}%` }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15, duration: 1, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-y-0 left-0 rounded-lg"
              style={{
                background: `linear-gradient(90deg, ${PALETTE.emerald}, ${PALETTE.bio} ${i === 3 ? "60%" : "100%"}${i === 3 ? `, ${PALETTE.terracottaSoft}` : ""})`,
                boxShadow: "inset 0 1px 0 rgba(74, 50, 32, 0.1)",
              }}
            />
            <div className="ov-mono absolute inset-y-0 right-3 flex items-center text-[10px]" style={{ color: PALETTE.cream }}>
              {s.count} · {s.value}%
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function SweetSpotChart() {
  const points = [
    { x: 8, y: 62 }, { x: 15, y: 52 }, { x: 22, y: 38 }, { x: 30, y: 28 },
    { x: 38, y: 18 }, { x: 46, y: 14 }, { x: 54, y: 18 }, { x: 62, y: 26 },
    { x: 70, y: 36 }, { x: 78, y: 48 }, { x: 86, y: 58 },
  ];
  const path = points
    .map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`))
    .join(" ");
  return (
    <div className="relative mt-2 aspect-[2/1] w-full">
      <svg viewBox="0 0 100 70" className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
        <defs>
          <linearGradient id="sweetFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#E8B86F" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#E8B86F" stopOpacity="0" />
          </linearGradient>
        </defs>
        <motion.path
          d={`${path} L 86 70 L 8 70 Z`}
          fill="url(#sweetFill)"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4, duration: 1 }}
        />
        <motion.path
          d={path}
          fill="none"
          stroke="#E8B86F"
          strokeWidth="1"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.4, ease: "easeInOut" }}
        />
        {/* Sweet spot band */}
        <rect x="38" y="0" width="16" height="70" fill="rgba(232, 184, 111, 0.08)" />
        <line x1="46" y1="0" x2="46" y2="70" stroke="rgba(232, 184, 111, 0.4)" strokeWidth="0.4" strokeDasharray="2 2" />
        <circle cx="46" cy="14" r="1.6" fill="#B8794A" style={{ filter: "drop-shadow(0 0 3px #B8794A)" }} />
      </svg>
      <div className="absolute bottom-1 right-2 ov-mono text-[9px]" style={{ color: PALETTE.terracottaSoft }}>
        Optimum: 18–22 mm
      </div>
    </div>
  );
}

/* -----------------------------------------------------------
   TRUST + TECH
   ----------------------------------------------------------- */
function TrustSection() {
  const principles = [
    { title: "Explainable by Design", body: "SHAP + Grad-CAM ship with every prediction.", icon: Sparkles },
    { title: "Biology-First", body: "Models calibrated against clinical sweet-spot data.", icon: FlaskConical },
    { title: "Human-in-the-Loop", body: "AI augments, never replaces, expert judgment.", icon: ShieldCheck },
    { title: "Traceable", body: "Unique Case IDs from OPU through confirmed pregnancy.", icon: Workflow },
  ];

  const stack = ["React 19", "FastAPI", "PyTorch", "PostgreSQL", "XGBoost", "TabPFN", "SHAP", "Docker", "Tailwind", "ResNet18"];

  return (
    <section className="relative px-4 py-16 sm:px-6 lg:py-24">
      <div className="mx-auto max-w-[1600px]">
        <SectionEyebrow text="Foundations" />
        <SectionTitle>
          Engineered around <em className="ov-text-grad not-italic">trust.</em>
        </SectionTitle>

        <div className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {principles.map((p, i) => (
            <motion.div
              key={p.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.7, delay: i * 0.08 }}
              whileHover={{ y: -6 }}
              className="ov-glass-card ov-glow p-6"
            >
              <p.icon className="h-4 w-4" style={{ color: PALETTE.bio }} />
              <h4 className="ov-serif mt-4 text-xl font-medium" style={{ color: PALETTE.cream }}>
                {p.title}
              </h4>
              <p className="mt-2 text-[13px] leading-relaxed" style={{ color: "rgba(74, 50, 32, 0.8)" }}>
                {p.body}
              </p>
            </motion.div>
          ))}
        </div>

        <div className="mt-16">
          <div className="ov-eyebrow mb-5 text-center" style={{ color: "rgba(74, 50, 32, 0.68)" }}>
            Built With
          </div>
          <div className="relative overflow-hidden">
            <div className="ov-marquee-track flex gap-12 whitespace-nowrap">
              {[...stack, ...stack].map((s, i) => (
                <span
                  key={i}
                  className="ov-serif italic"
                  style={{ color: "rgba(74, 50, 32, 0.72)", fontSize: 22 }}
                >
                  {s}
                </span>
              ))}
            </div>
            <div className="pointer-events-none absolute inset-y-0 left-0 w-32" style={{ background: `linear-gradient(90deg, ${PALETTE.forestDeep}, transparent)` }} />
            <div className="pointer-events-none absolute inset-y-0 right-0 w-32" style={{ background: `linear-gradient(270deg, ${PALETTE.forestDeep}, transparent)` }} />
          </div>
        </div>
      </div>
    </section>
  );
}

/* -----------------------------------------------------------
   TESTIMONIALS
   ----------------------------------------------------------- */
function TestimonialsSection() {
  const t = [
    {
      quote:
        "We stopped arguing about grades. The Grad-CAM overlays gave the team a shared visual language — and our transfer success rate climbed within the first quarter.",
      name: "Dr. M. Hayat",
      role: "Senior Veterinarian",
      org: "Reproductive Program Lead",
    },
    {
      quote:
        "The QC indicator caught a media batch issue three days before we would have noticed it manually. That's six embryos saved on a single anomaly alert.",
      name: "S. Aslam",
      role: "Lead Embryologist",
      org: "IVF Lab",
    },
    {
      quote:
        "I finally have a single dashboard that tells me where my pregnancies are leaking — OPU, embryo, transfer, or recipient. Decisions stopped being guesses.",
      name: "R. Tariq",
      role: "Farm Manager",
      org: "Bovine Reproduction",
    },
  ];

  return (
    <section id="testimonials" className="relative px-4 py-16 sm:px-6 lg:py-24">
      <div className="mx-auto max-w-[1600px]">
        <SectionEyebrow text="Voices From The Field" />
        <SectionTitle>
          Trusted by teams who can't afford to <em className="ov-text-warm not-italic">guess.</em>
        </SectionTitle>

        <div className="mt-16 grid gap-5 lg:grid-cols-3">
          {t.map((q, i) => (
            <motion.figure
              key={q.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.7, delay: i * 0.1 }}
              whileHover={{ y: -6 }}
              className="ov-glass-card ov-glow relative p-7"
            >
              <Quote className="absolute right-6 top-6 h-7 w-7 opacity-20" style={{ color: PALETTE.bio }} />
              <blockquote className="ov-serif text-[18px] font-light leading-relaxed" style={{ color: PALETTE.cream }}>
                "{q.quote}"
              </blockquote>
              <figcaption className="mt-6 flex items-center gap-3 border-t pt-5" style={{ borderColor: "rgba(74, 50, 32, 0.08)" }}>
                <div
                  className="grid h-10 w-10 place-items-center rounded-full"
                  style={{
                    background: `linear-gradient(135deg, ${PALETTE.emerald}, ${PALETTE.terracotta})`,
                    color: PALETTE.cream,
                    fontFamily: "Fraunces, serif",
                    fontWeight: 600,
                  }}
                >
                  {q.name.split(" ")[1]?.[0] || q.name[0]}
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: PALETTE.cream }}>
                    {q.name}
                  </div>
                  <div className="text-[11px]" style={{ color: "rgba(74, 50, 32, 0.75)" }}>
                    {q.role} · {q.org}
                  </div>
                </div>
              </figcaption>
            </motion.figure>
          ))}
        </div>
      </div>
    </section>
  );
}

/* -----------------------------------------------------------
   FOOTER
   ----------------------------------------------------------- */
function Footer() {
  return (
    <footer className="relative border-t px-5 py-12 sm:px-8" style={{ borderColor: "rgba(74, 50, 32, 0.06)" }}>
      <div className="mx-auto flex max-w-[1600px] flex-col gap-8 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-md">
          <div className="flex items-center gap-3">
            <Logo />
            <div className="ov-serif text-base font-semibold" style={{ color: PALETTE.cream }}>
              Ovulite
            </div>
          </div>
          <p className="mt-4 text-[13px] leading-relaxed" style={{ color: "rgba(74, 50, 32, 0.75)" }}>
            Reproductive intelligence for bovine embryo transfer. Objective. Explainable. Continuous.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-x-12 gap-y-6 sm:grid-cols-3">
          {[
            { h: "Product", l: ["Pregnancy Predictor", "Embryo Grader", "Lab QC", "Dashboard"] },
            { h: "Platform", l: ["Pricing", "Integrations", "Security", "Roadmap"] },
            { h: "Company", l: ["About", "Contact", "Careers", "Press"] },
          ].map((g) => (
            <div key={g.h}>
              <div className="ov-eyebrow mb-4" style={{ color: "rgba(74, 50, 32, 0.68)" }}>
                {g.h}
              </div>
              <ul className="space-y-2.5">
                {g.l.map((x) => (
                  <li key={x}>
                    <a href="#" className="ov-link text-[13px]" style={{ color: "rgba(74, 50, 32, 0.85)" }}>
                      {x}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div
        className="mx-auto mt-12 flex max-w-[1600px] flex-col items-start justify-between gap-3 border-t pt-6 text-[12px] sm:flex-row sm:items-center"
        style={{ borderColor: "rgba(74, 50, 32, 0.06)", color: "rgba(74, 50, 32, 0.7)" }}
      >
        <div>© {new Date().getFullYear()} Ovulite. All rights reserved.</div>
        <div className="flex gap-6">
          <a href="#" className="ov-link">Privacy</a>
          <a href="#" className="ov-link">Terms</a>
          <a href="mailto:hello@ovulite.ai" className="ov-link">hello@ovulite.ai</a>
        </div>
      </div>
    </footer>
  );
}

/* -----------------------------------------------------------
   Reusable section atoms
   ----------------------------------------------------------- */
function SectionEyebrow({ text }: { text: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6 }}
      className="ov-eyebrow flex items-center gap-3"
      style={{ color: PALETTE.bio }}
    >
      <span className="h-px w-8" style={{ background: PALETTE.bio }} />
      {text}
    </motion.div>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <motion.h2
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
      className="ov-serif mt-5 max-w-4xl text-[clamp(2.2rem,4.4vw,4rem)] font-light leading-[1.02] tracking-tight"
      style={{ color: PALETTE.cream }}
    >
      {children}
    </motion.h2>
  );
}

function SectionLead({ children }: { children: ReactNode }) {
  return (
    <motion.p
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, delay: 0.15 }}
      className="mt-6 max-w-2xl text-[16px] leading-relaxed"
      style={{ color: "rgba(74, 50, 32, 0.82)" }}
    >
      {children}
    </motion.p>
  );
}

void BiologyScene;
