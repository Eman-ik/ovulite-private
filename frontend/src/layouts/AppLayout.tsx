import { NavLink, Outlet } from "react-router-dom";
import { useState } from "react";
import { ROLE_PERMISSIONS } from "@/lib/roleRoutes";
import {
  LayoutDashboard,
  FileInput,
  Brain,
  Microscope,
  Shield,
  BarChart3,
  LogOut,
  Menu,
  X,
  FileText,
  TrendingUp,
  FolderOpen,
  HelpCircle,
  LifeBuoy,
  Sun,
  Moon,
} from "lucide-react";
import ovuliteLogo from "../pages/icon.png";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";

const navItems = [
  { to: "", icon: LayoutDashboard, label: "Dashboard" },
  { to: "data-entry", icon: FileInput, label: "Data Entry" },
  { to: "predictions", icon: Brain, label: "Predictions" },
  { to: "embryo-grading", icon: Microscope, label: "Embryo Grading" },
  { to: "lab-qc", icon: Shield, label: "Lab QC" },
  { to: "analytics", icon: BarChart3, label: "Analytics" },
  { to: "cases", icon: FolderOpen, label: "Case Records" },
  { to: "model-performance", icon: TrendingUp, label: "Model Performance" },
  { to: "reports", icon: FileText, label: "Reports & Export" },
];

export default function AppLayout() {
  const { logout, user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const role = user?.role?.toLowerCase() || "viewer";
const permissions = ROLE_PERMISSIONS[role as keyof typeof ROLE_PERMISSIONS];

  const NavItems = ({ onNavigate }: { onNavigate?: () => void }) => (
    <nav className="space-y-1.5">
      {navItems
  .filter((item) => {
    if (item.to === "analytics") return permissions?.canViewAnalytics;
    if (item.to === "data-entry") return permissions?.canEnterETData;
    if (item.to === "predictions") return permissions?.canEnterETData;
    if (item.to === "embryo-grading") return permissions?.canGradeEmbryos;
    if (item.to === "lab-qc") return permissions?.canEnterLabData;
    if (item.to === "reports") return permissions?.canExportReports;
    return true;
  })
  .map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === ""}
          onClick={onNavigate}
          className={({ isActive }) =>
            `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
              isActive
                ? "bg-white !text-black shadow-[0_0_20px_rgba(255,255,255,0.1)]"
                : "!text-white/70 hover:bg-white/10 hover:!text-white"
            }`
          }
        >
          <item.icon className="h-4 w-4 shrink-0" strokeWidth={1.5} />
          {item.label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-[var(--background)] text-black transition-colors duration-300 lg:flex lg:items-start lg:gap-4 lg:p-[4px]">
      {/* Desktop sidebar */}
     <aside className="sidebar-glow hidden w-64 lg:sticky lg:top-10 lg:z-30 lg:flex lg:h-[calc(100vh-8px)] lg:w-72 flex-col rounded-2xl lg:rounded-3xl border border-white/20 bg-[var(--sidebar-bg)] shadow-2xl overflow-visible">
       
        <div className="flex h-16 lg:h-20 items-center gap-2 lg:gap-3 border-b border-white/10 px-4 lg:px-6">
          <div
            className="ov-pulse-ring flex h-8 lg:h-10 w-8 lg:w-10 items-center justify-center rounded-lg lg:rounded-xl text-sm font-bold text-black glow-shadow-amber overflow-hidden"
            style={{ background: "linear-gradient(135deg, #FFC107, #FADBB3)" }}
          >
            <img src={ovuliteLogo} alt="O" className="h-full w-full object-cover" />
          </div>
          <div>
            <p className="font-semibold tracking-tight !text-white text-sm lg:text-base">Ovulite</p>
            <p className="text-[10px] lg:text-xs uppercase tracking-[0.18em] !text-white" style={{ filter: "drop-shadow(0 0 4px rgba(255,193,7,0.3))" }}>
              Dashboard
            </p>
          </div>
        </div>

        <div className="flex-1 p-2 lg:p-4 overflow-y-auto custom-scrollbar">
          <NavItems />
        </div>

        <div className="space-y-3 lg:space-y-4 border-t border-white/10 p-3 lg:p-4">
          <div className="space-y-1">
            <p className="px-3 text-[10px] font-semibold uppercase tracking-wider !text-white/40">Help & Support</p>
            <button className="flex w-full items-center gap-3 rounded-lg lg:rounded-xl px-3 py-2 text-xs lg:text-sm font-medium !text-white/70 hover:bg-white/10 hover:!text-white transition-all">
              <HelpCircle className="h-4 w-4 shrink-0" strokeWidth={1.5} />
              <span className="hidden xl:inline">Help</span>
            </button>
            <button className="flex w-full items-center gap-3 rounded-lg lg:rounded-xl px-3 py-2 text-xs lg:text-sm font-medium !text-white/70 hover:bg-white/10 hover:!text-white transition-all">
              <LifeBuoy className="h-4 w-4 shrink-0" strokeWidth={1.5} />
              <span className="hidden xl:inline">Center</span>
            </button>
          </div>

          <button
            className="flex w-full items-center gap-3 rounded-lg lg:rounded-xl px-3 py-2 lg:py-2.5 text-xs lg:text-sm font-medium !text-white hover:bg-red-500/10 transition-all mt-2"
            onClick={logout}
          >
            <LogOut className="h-4 w-4 shrink-0" strokeWidth={1.5} />
            <span className="hidden xl:inline">Logout</span>
          </button>
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)}>
          <aside className="h-full w-80 max-w-[88vw] rounded-r-2xl lg:rounded-r-3xl border-r border-white/10 p-3 sm:p-4 bg-[var(--sidebar-bg)] shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg text-sm font-bold text-black glow-shadow-amber overflow-hidden" style={{ background: "linear-gradient(135deg, #FFC107, #FADBB3)" }}>
                  <img src={ovuliteLogo} alt="O" className="h-full w-full object-cover" />
                </div>
                <p className="text-sm lg:text-base font-semibold !text-white">Ovulite</p>
              </div>
              <button type="button" className="rounded-lg p-2 !text-white/70 hover:bg-white/10 hover:!text-white" onClick={() => setMobileOpen(false)} aria-label="Close menu">
                <X className="h-5 w-5" strokeWidth={1.5} />
              </button>
            </div>
            <NavItems onNavigate={() => setMobileOpen(false)} />
            <div className="mt-5 space-y-3 lg:space-y-4 border-t border-white/10 pt-4">
              <div className="space-y-1">
                <p className="px-3 text-[10px] font-semibold uppercase tracking-wider !text-white/40">Help & Support</p>
                <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium !text-white/70 hover:bg-white/10 hover:!text-white transition-all">
                  <HelpCircle className="h-4 w-4" strokeWidth={1.5} />
                  Help
                </button>
                <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium !text-white/70 hover:bg-white/10 hover:!text-white transition-all">
                  <LifeBuoy className="h-4 w-4" strokeWidth={1.5} />
                  Center
                </button>
              </div>

              <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium !text-white hover:bg-red-500/10 transition-all" onClick={logout}>
                <LogOut className="h-4 w-4" strokeWidth={1.5} />
                Logout
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 min-w-0 lg:mt-2.5">
        {/* Mobile trigger */}
        <header className="sticky top-0 z-20 flex h-14 sm:h-16 items-center justify-between border-b border-white/10 bg-[var(--background)]/80 backdrop-blur-md px-3 sm:px-4 lg:hidden">
          <button type="button" className="rounded-lg p-2 -ml-2 !text-white hover:bg-white/10 transition-colors" onClick={() => setMobileOpen(true)}>
            <Menu className="h-5 w-5 sm:h-6 sm:w-6" strokeWidth={1.5} />
          </button>
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 sm:h-8 sm:w-8 overflow-hidden rounded-lg">
              <img src={ovuliteLogo} alt="O" className="h-full w-full object-cover" />
            </div>
            <span className="text-sm sm:text-base font-bold tracking-tight !text-white">Ovulite</span>
          </div>
          <div className="w-10" />
        </header>

        <main className="px-3 sm:px-4 lg:px-6 py-4 sm:py-5 lg:py-0">
          <div className="mb-4 sm:mb-6 mt-4 flex justify-end">
            <div className="flex items-center gap-2 sm:gap-4 shrink-0">
              <button onClick={toggleTheme} className="flex h-10 w-10 sm:h-12 sm:w-12 items-center justify-center rounded-lg lg:rounded-2xl bg-[var(--card)] shadow-sm border border-white/10 text-[var(--foreground)] transition-all hover:scale-105 flex-shrink-0" title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
                {theme === "light" ? <Moon size={18} className="sm:w-5 sm:h-5" /> : <Sun size={18} className="sm:w-5 sm:h-5" />}
              </button>
              <div className="flex h-10 w-10 sm:h-12 sm:w-12 items-center justify-center rounded-lg lg:rounded-2xl bg-[var(--card)] shadow-sm border border-white/10 overflow-hidden flex-shrink-0">
                <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user?.username || 'guest'}`} alt="Profile" className="h-full w-full" />
              </div>
            </div>
          </div>
          <section className="glass-panel min-h-[calc(100vh-10rem)] rounded-2xl lg:rounded-3xl p-3 sm:p-4 lg:p-6 shadow-sm">
            <Outlet />
          </section>
        </main>
      </div>
    </div>
  );
}
