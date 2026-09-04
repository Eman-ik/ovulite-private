import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  CalendarDays,
  ClipboardList,
  Dna,
  Filter,
  Loader2,
  RefreshCw,
  TrendingUp,
  Users,
} from "lucide-react";

import api from "@/lib/api";
import KpiCard from "@/components/dashboard/KpiCard";
import type {
  AnalyticsBiomarkerBin,
  AnalyticsBiomarkerResult,
  AnalyticsBiomarkersResponse,
  AnalyticsDonorStats,
  AnalyticsDonorStatsResponse,
  AnalyticsFunnelResponse,
  AnalyticsFunnelStage,
  AnalyticsKPIResponse,
  AnalyticsMonthlyTrend,
  AnalyticsProtocolImportance,
  AnalyticsProtocolRate,
  AnalyticsProtocolRatesResponse,
  AnalyticsProtocolRegression,
} from "@/lib/types";

/* ─────────────────────────────────────────────────────────
   Generic data-fetching hook for the analytics endpoints.
   Each panel owns its own loading/error/empty state so one
   failing endpoint never blocks the rest of the page, and we
   never silently substitute fabricated numbers on failure.
   ───────────────────────────────────────────────────────── */

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

function extractErrorMessage(err: unknown): string {
  if (typeof err === "object" && err !== null) {
    const withResponse = err as {
      response?: { status?: number; data?: { detail?: string } };
      message?: string;
    };
    if (withResponse.response?.status === 404) {
      return "Not enough data has been processed yet for this view.";
    }
    if (withResponse.response?.data?.detail) {
      return withResponse.response.data.detail;
    }
    if (withResponse.message) {
      return withResponse.message;
    }
  }
  return "Failed to load analytics data.";
}

function useAnalyticsQuery<T>(path: string, refreshToken: number): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ data: null, loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ data: prev.data, loading: true, error: null }));

    api
      .get<T>(path)
      .then((response) => {
        if (cancelled) return;
        setState({ data: response.data, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        console.error(`Analytics request failed: ${path}`, err);
        setState({ data: null, loading: false, error: extractErrorMessage(err) });
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, refreshToken]);

  return state;
}

/* ───────────────────────────── formatting helpers ───────────────────────────── */

function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function fmtNum(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/* ───────────────────────────── shared UI bits ───────────────────────────── */

function SectionCard({
  title,
  subtitle,
  action,
  children,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          {subtitle ? <p className="text-sm text-gray-500">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

function StatusBlock({ loading, error }: { loading: boolean; error: string | null }): ReactNode {
  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-6 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading analytics data…
      </div>
    );
  }
  if (error) {
    return (
      <div className="flex items-start gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">
        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
        <span>{error}</span>
      </div>
    );
  }
  return null;
}

function EmptyBlock({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-6 text-center text-sm text-gray-500">
      {message}
    </div>
  );
}

/** Pill showing a rate together with its sample size — never a bare percentage. */
function RatePill({ rate, n, pregnant }: { rate: number | null | undefined; n: number; pregnant?: number }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800">
      {fmtPct(rate)}
      <span className="text-emerald-500">
        ({pregnant !== undefined ? `${fmtNum(pregnant)}/` : ""}
        n={n})
      </span>
    </span>
  );
}

const CHART_TOOLTIP_STYLE = {
  borderRadius: 16,
  border: "1px solid #E5E7EB",
  background: "rgba(255,255,255,0.98)",
  fontSize: 13,
};

const CATEGORY_COLORS = ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444", "#ec4899", "#06b6d4", "#f97316"];

/** Minimal, loosely-typed shape for recharts' custom Tooltip `content` render-prop.
 *  Recharts injects `active`/`payload` at render time via cloneElement, so a
 *  standalone `<MyTooltip />` element must accept them as optional. */
interface ChartTooltipProps {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: unknown }>;
}

/* ───────────────────────────── tab plumbing ───────────────────────────── */

type TabKey = "overview" | "protocols" | "donors" | "biomarkers";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "protocols", label: "Protocols" },
  { key: "donors", label: "Donors" },
  { key: "biomarkers", label: "Biomarkers" },
];

/* ═══════════════════════════════ Main Page ═══════════════════════════════ */

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [refreshToken, setRefreshToken] = useState(0);
  const [isRunningPipeline, setIsRunningPipeline] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const kpis = useAnalyticsQuery<AnalyticsKPIResponse>("/analytics/kpis", refreshToken);
  const trends = useAnalyticsQuery<AnalyticsMonthlyTrend[]>("/analytics/trends", refreshToken);
  const funnel = useAnalyticsQuery<AnalyticsFunnelResponse>("/analytics/funnel", refreshToken);
  const protocols = useAnalyticsQuery<AnalyticsProtocolRatesResponse>("/analytics/protocols", refreshToken);
  const protocolRegression = useAnalyticsQuery<AnalyticsProtocolRegression>(
    "/analytics/protocols/regression",
    refreshToken
  );
  const protocolImportance = useAnalyticsQuery<AnalyticsProtocolImportance>(
    "/analytics/protocols/importance",
    refreshToken
  );
  const donors = useAnalyticsQuery<AnalyticsDonorStatsResponse>("/analytics/donors", refreshToken);
  const biomarkers = useAnalyticsQuery<AnalyticsBiomarkersResponse>("/analytics/biomarkers", refreshToken);

  const handleRefresh = async () => {
    setIsRunningPipeline(true);
    setRunError(null);
    try {
      await api.post("/analytics/run");
    } catch (err) {
      console.error("Failed to trigger analytics pipeline run", err);
      setRunError(extractErrorMessage(err));
    } finally {
      setIsRunningPipeline(false);
      setRefreshToken((token) => token + 1);
    }
  };

  return (
    <div className="min-h-screen bg-[#dff4e4] p-8">
      <div className="space-y-8">
        {/* Header */}
        <div className="rounded-3xl bg-white p-8 shadow-sm border border-emerald-50">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div>
              <div className="inline-flex items-center rounded-full border border-emerald-200 px-4 py-2 text-xs font-semibold text-emerald-700 bg-emerald-50">
                OVULITE ANALYTICS
              </div>
              <h1 className="mt-4 text-4xl font-bold text-gray-900">Analytics</h1>
              <p className="mt-2 text-gray-600 max-w-2xl">
                Pregnancy outcomes, protocol efficiency, donor performance, and biomarker sweet spots computed
                directly from the ET analytics pipeline. Every rate shown is reported with its sample size (n) —
                this dataset is small, so denominators matter.
              </p>
            </div>

            <div className="flex flex-col items-end gap-2">
              <button
                onClick={handleRefresh}
                disabled={isRunningPipeline}
                className="inline-flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700 transition-colors hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RefreshCw className={`h-4 w-4 ${isRunningPipeline ? "animate-spin" : ""}`} />
                {isRunningPipeline ? "Recomputing…" : "Recompute analytics"}
              </button>
              {runError ? <p className="max-w-[280px] text-right text-xs text-rose-600">{runError}</p> : null}
            </div>
          </div>
        </div>

        {/* KPI cards */}
        <KpiRow kpis={kpis} />

        {/* Tabs */}
        <div className="flex flex-wrap gap-2 rounded-3xl bg-white p-2 shadow-sm border border-emerald-50 w-fit">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-2xl px-5 py-2.5 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "bg-emerald-700 text-white"
                  : "text-gray-600 hover:bg-emerald-50 hover:text-emerald-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "overview" ? (
          <OverviewTab kpis={kpis} trends={trends} funnel={funnel} />
        ) : null}

        {activeTab === "protocols" ? (
          <ProtocolsTab protocols={protocols} regression={protocolRegression} importance={protocolImportance} />
        ) : null}

        {activeTab === "donors" ? <DonorsTab donors={donors} /> : null}

        {activeTab === "biomarkers" ? <BiomarkersTab biomarkers={biomarkers} /> : null}
      </div>
    </div>
  );
}

/* ───────────────────────────── KPI row ───────────────────────────── */

function KpiRow({ kpis }: { kpis: FetchState<AnalyticsKPIResponse> }) {
  if (kpis.loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-[176px] animate-pulse rounded-3xl bg-white border border-emerald-50 shadow-sm"
          />
        ))}
      </div>
    );
  }

  if (kpis.error || !kpis.data) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
        {kpis.error ?? "KPI data is not available."}
      </div>
    );
  }

  const d = kpis.data;
  const dateRangeValue =
    d.date_range.first && d.date_range.last ? `${d.date_range.span_months} mo` : "N/A";
  const dateRangeSubtitle =
    d.date_range.first && d.date_range.last
      ? `${fmtDate(d.date_range.first)} – ${fmtDate(d.date_range.last)}`
      : "No dated records yet";

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        <KpiCard
          title="Total Transfers"
          value={fmtNum(d.total_transfers)}
          subtitle={`${fmtNum(d.with_outcome)} with a recorded outcome`}
          icon={<ClipboardList className="h-6 w-6" />}
        />
        <KpiCard
          title="Pregnancy Rate"
          value={fmtPct(d.pregnancy_rate)}
          subtitle={
            d.pregnancy_rate !== null
              ? `${fmtNum(d.pregnant)} pregnant / n=${fmtNum(d.with_outcome)}`
              : "No outcomes recorded yet"
          }
          icon={<TrendingUp className="h-6 w-6" />}
        />
        <KpiCard
          title="Embryo Utilization"
          value={fmtPct(d.embryo_utilization)}
          subtitle={
            d.unique_embryos !== null && d.unique_embryos !== undefined
              ? `${fmtNum(d.unique_embryos)} unique embryos tracked`
              : "Not available in current dataset"
          }
          icon={<Dna className="h-6 w-6" />}
        />
        <KpiCard
          title="Date Range"
          value={dateRangeValue}
          subtitle={dateRangeSubtitle}
          icon={<CalendarDays className="h-6 w-6" />}
        />
      </div>

      <div className="rounded-3xl bg-white p-5 shadow-sm border border-emerald-50">
        <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <EntityCount label="Donors" value={d.entity_counts.donors} icon={<Users className="h-3.5 w-3.5" />} />
          <EntityCount label="Recipients" value={d.entity_counts.recipients} icon={<Users className="h-3.5 w-3.5" />} />
          <EntityCount
            label="Technicians"
            value={d.entity_counts.technicians}
            icon={<Users className="h-3.5 w-3.5" />}
          />
          <EntityCount
            label="Protocols"
            value={d.entity_counts.protocols}
            icon={<Filter className="h-3.5 w-3.5" />}
          />
          <EntityCount label="Sires" value={d.entity_counts.sires} icon={<Dna className="h-3.5 w-3.5" />} />
        </div>
      </div>
    </div>
  );
}

function EntityCount({ label, value, icon }: { label: string; value: number; icon: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 text-gray-600">
      <span className="text-emerald-500">{icon}</span>
      <span className="font-semibold text-gray-900">{fmtNum(value)}</span>
      {label}
    </span>
  );
}

/* ═══════════════════════════════ Overview Tab ═══════════════════════════════ */

interface TrendTooltipPayload {
  month: string;
  pregnancy_rate_pct: number;
  n_transfers: number;
  n_pregnant: number;
  avg_cl: number | null;
}

function TrendTooltip({ active, payload }: ChartTooltipProps) {
  if (!active || !payload || !payload.length) return null;
  const row = payload[0]?.payload as TrendTooltipPayload | undefined;
  if (!row) return null;
  return (
    <div style={CHART_TOOLTIP_STYLE} className="px-3 py-2">
      <p className="font-semibold text-gray-900">{row.month}</p>
      <p className="text-emerald-700">
        {row.pregnancy_rate_pct.toFixed(1)}% pregnancy rate (n={row.n_transfers}, {row.n_pregnant} pregnant)
      </p>
      {row.avg_cl !== null ? <p className="text-gray-500">Avg CL: {row.avg_cl.toFixed(1)} mm</p> : null}
    </div>
  );
}

function OverviewTab({
  kpis,
  trends,
  funnel,
}: {
  kpis: FetchState<AnalyticsKPIResponse>;
  trends: FetchState<AnalyticsMonthlyTrend[]>;
  funnel: FetchState<AnalyticsFunnelResponse>;
}) {
  const trendData = useMemo(
    () =>
      (trends.data ?? []).map((t) => ({
        month: t.month,
        pregnancy_rate_pct: t.pregnancy_rate * 100,
        n_transfers: t.n_transfers,
        n_pregnant: t.n_pregnant,
        avg_cl: t.avg_cl,
      })),
    [trends.data]
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <SectionCard
            title="Monthly Pregnancy Rate Trend"
            subtitle="Each point shows the transfer count (n) and confirmed pregnancies for that month"
          >
            {trends.loading || trends.error ? (
              <StatusBlock loading={trends.loading} error={trends.error} />
            ) : trendData.length === 0 ? (
              <EmptyBlock message="No monthly trend data available yet." />
            ) : (
              <>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trendData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="analyticsTrendFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0.01} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                      <XAxis dataKey="month" stroke="#6B7280" tickLine={false} axisLine={false} />
                      <YAxis
                        stroke="#6B7280"
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value: number) => `${value}%`}
                      />
                      <Tooltip content={<TrendTooltip />} />
                      <Area
                        type="monotone"
                        dataKey="pregnancy_rate_pct"
                        stroke="#059669"
                        strokeWidth={3}
                        dot={{ r: 5, fill: "#10b981" }}
                        fill="url(#analyticsTrendFill)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-gray-500">
                        <th className="px-2 py-1 font-medium">Month</th>
                        <th className="px-2 py-1 font-medium">n Transfers</th>
                        <th className="px-2 py-1 font-medium">n Pregnant</th>
                        <th className="px-2 py-1 font-medium">Rate</th>
                        <th className="px-2 py-1 font-medium">Avg CL (mm)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trendData.map((row) => (
                        <tr key={row.month} className="border-t border-gray-100">
                          <td className="px-2 py-1">{row.month}</td>
                          <td className="px-2 py-1">{row.n_transfers}</td>
                          <td className="px-2 py-1">{row.n_pregnant}</td>
                          <td className="px-2 py-1">{row.pregnancy_rate_pct.toFixed(1)}%</td>
                          <td className="px-2 py-1">{row.avg_cl !== null ? row.avg_cl.toFixed(1) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </SectionCard>
        </div>

        <SectionCard title="Fresh vs Frozen" subtitle="Pregnancy rate by embryo state (n shown per group)">
          <FreshFrozenPanel kpis={kpis} />
        </SectionCard>
      </div>

      <SectionCard
        title="IVF / ET Funnel"
        subtitle="Stage-to-stage conversion from embryos available through confirmed pregnancy"
      >
        <FunnelPanel funnel={funnel} />
      </SectionCard>
    </div>
  );
}

function FreshFrozenPanel({ kpis }: { kpis: FetchState<AnalyticsKPIResponse> }) {
  if (kpis.loading || kpis.error) return <StatusBlock loading={kpis.loading} error={kpis.error} />;
  const entries = Object.entries(kpis.data?.fresh_vs_frozen ?? {});
  if (entries.length === 0) return <EmptyBlock message="No fresh/frozen breakdown available yet." />;

  const chartData = entries.map(([label, stats]) => ({
    label,
    rate_pct: (stats.rate ?? 0) * 100,
    n: stats.n,
    pregnant: stats.pregnant,
  }));

  return (
    <div className="space-y-4">
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis dataKey="label" stroke="#6B7280" tickLine={false} axisLine={false} />
            <YAxis
              stroke="#6B7280"
              tickLine={false}
              axisLine={false}
              tickFormatter={(value: number) => `${value}%`}
            />
            <Tooltip
              contentStyle={CHART_TOOLTIP_STYLE}
              formatter={(value, _name, item) => {
                const raw = typeof value === "number" ? value : Number(value);
                const payload = item?.payload as { n: number; pregnant: number } | undefined;
                return [`${raw.toFixed(1)}% (n=${payload?.n ?? "?"}, ${payload?.pregnant ?? "?"} pregnant)`, "Rate"];
              }}
            />
            <Bar dataKey="rate_pct" radius={[8, 8, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={entry.label} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="space-y-2">
        {entries.map(([label, stats]) => (
          <div
            key={label}
            className="flex items-center justify-between rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-2 text-sm"
          >
            <span className="font-medium text-emerald-900">{label}</span>
            <RatePill rate={stats.rate} n={stats.n} pregnant={stats.pregnant} />
          </div>
        ))}
      </div>
    </div>
  );
}

function FunnelPanel({ funnel }: { funnel: FetchState<AnalyticsFunnelResponse> }) {
  if (funnel.loading || funnel.error) return <StatusBlock loading={funnel.loading} error={funnel.error} />;
  const stages = funnel.data?.stages ?? [];
  if (stages.length === 0) return <EmptyBlock message="No funnel data available yet." />;

  const maxCount = Math.max(...stages.map((s: AnalyticsFunnelStage) => s.count), 1);

  return (
    <div className="space-y-3">
      {stages.map((stage, index) => {
        const widthPct = Math.max(6, (stage.count / maxCount) * 100);
        return (
          <div key={stage.stage} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-gray-800">{stage.stage}</span>
              <span className="text-gray-500">
                n={fmtNum(stage.count)}
                {index > 0 && stage.rate_from_previous !== null
                  ? ` · ${fmtPct(stage.rate_from_previous)} of previous stage`
                  : ""}
              </span>
            </div>
            <div className="h-6 w-full overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${widthPct}%`,
                  background: CATEGORY_COLORS[index % CATEGORY_COLORS.length],
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ═══════════════════════════════ Protocols Tab ═══════════════════════════════ */

type ProtocolSortKey = "protocol_name" | "n_transfers" | "pregnancy_rate";

interface ProtocolTooltipRow {
  protocol_name: string;
  rate_pct: number;
  n_transfers: number;
  n_pregnant: number;
  ci_lower_pct: number;
  ci_upper_pct: number;
}

function ProtocolTooltip({ active, payload }: ChartTooltipProps) {
  if (!active || !payload || !payload.length) return null;
  const row = payload[0]?.payload as ProtocolTooltipRow | undefined;
  if (!row) return null;
  return (
    <div style={CHART_TOOLTIP_STYLE} className="px-3 py-2">
      <p className="font-semibold text-gray-900">{row.protocol_name}</p>
      <p className="text-emerald-700">
        {row.rate_pct.toFixed(1)}% (n={row.n_transfers}, {row.n_pregnant} pregnant)
      </p>
      <p className="text-gray-500">
        95% CI: {row.ci_lower_pct.toFixed(1)}% – {row.ci_upper_pct.toFixed(1)}%
      </p>
    </div>
  );
}

function ProtocolsTab({
  protocols,
  regression,
  importance,
}: {
  protocols: FetchState<AnalyticsProtocolRatesResponse>;
  regression: FetchState<AnalyticsProtocolRegression>;
  importance: FetchState<AnalyticsProtocolImportance>;
}) {
  const [sort, setSort] = useState<{ key: ProtocolSortKey; dir: "asc" | "desc" }>({
    key: "n_transfers",
    dir: "desc",
  });

  const rows = protocols.data?.protocols ?? [];

  const sortedRows = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      const cmp = typeof av === "string" ? av.localeCompare(String(bv)) : Number(av) - Number(bv);
      return sort.dir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [rows, sort]);

  const chartData = useMemo(
    () =>
      sortedRows.map((p: AnalyticsProtocolRate) => ({
        protocol_name: p.protocol_name,
        rate_pct: p.pregnancy_rate * 100,
        n_transfers: p.n_transfers,
        n_pregnant: p.n_pregnant,
        ci_lower_pct: p.ci_lower * 100,
        ci_upper_pct: p.ci_upper * 100,
      })),
    [sortedRows]
  );

  const toggleSort = (key: ProtocolSortKey) => {
    setSort((prev) => (prev.key === key ? { key, dir: prev.dir === "asc" ? "desc" : "asc" } : { key, dir: "desc" }));
  };

  return (
    <div className="space-y-6">
      <SectionCard
        title="Pregnancy Rate by Protocol"
        subtitle="Bars show the 95% confidence interval around each rate — narrow n means a wide interval, not a reliable difference"
      >
        {protocols.loading || protocols.error ? (
          <StatusBlock loading={protocols.loading} error={protocols.error} />
        ) : chartData.length === 0 ? (
          <EmptyBlock message="No protocol data available yet." />
        ) : (
          <>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis
                    dataKey="protocol_name"
                    stroke="#6B7280"
                    tickLine={false}
                    axisLine={false}
                    angle={-25}
                    textAnchor="end"
                    interval={0}
                    height={70}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    stroke="#6B7280"
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value: number) => `${value}%`}
                    domain={[0, 100]}
                  />
                  <Tooltip content={<ProtocolTooltip />} />
                  <Bar dataKey="rate_pct" radius={[8, 8, 0, 0]} fill="#10b981">
                    {chartData.map((entry, index) => (
                      <Cell key={entry.protocol_name} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                    ))}
                    <ErrorBar
                      dataKey={(entry: (typeof chartData)[number]) => [
                        Math.max(0, entry.rate_pct - entry.ci_lower_pct),
                        Math.max(0, entry.ci_upper_pct - entry.rate_pct),
                      ]}
                      width={4}
                      strokeWidth={1.5}
                      stroke="#374151"
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-6 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-emerald-50 text-gray-600">
                    <SortHeader label="Protocol" sortKey="protocol_name" sort={sort} onSort={toggleSort} />
                    <SortHeader label="n Transfers" sortKey="n_transfers" sort={sort} onSort={toggleSort} />
                    <th className="px-4 py-3 text-left font-medium">n Pregnant</th>
                    <SortHeader label="Pregnancy Rate" sortKey="pregnancy_rate" sort={sort} onSort={toggleSort} />
                    <th className="px-4 py-3 text-left font-medium">95% CI</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRows.map((p) => (
                    <tr key={p.protocol_name} className="border-b last:border-0 hover:bg-emerald-50/30">
                      <td className="px-4 py-3">{p.protocol_name}</td>
                      <td className="px-4 py-3">{p.n_transfers}</td>
                      <td className="px-4 py-3">{fmtNum(p.n_pregnant)}</td>
                      <td className="px-4 py-3 font-medium">{fmtPct(p.pregnancy_rate)}</td>
                      <td className="px-4 py-3 text-gray-500">
                        {fmtPct(p.ci_lower)} – {fmtPct(p.ci_upper)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </SectionCard>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <SectionCard
          title="Protocol Odds Ratios (logistic regression)"
          subtitle="Exploratory model diagnostic — an odds ratio above 1 favors pregnancy, below 1 disfavors it"
        >
          <RegressionPanel regression={regression} />
        </SectionCard>

        <SectionCard
          title="Feature Importance"
          subtitle="Exploratory model diagnostic — relative contribution of each feature to predicted outcome"
        >
          <ImportancePanel importance={importance} />
        </SectionCard>
      </div>
    </div>
  );
}

function SortHeader<K extends string>({
  label,
  sortKey,
  sort,
  onSort,
}: {
  label: string;
  sortKey: K;
  sort: { key: K; dir: "asc" | "desc" };
  onSort: (key: K) => void;
}) {
  const active = sort.key === sortKey;
  return (
    <th className="px-4 py-3 text-left font-medium">
      <button onClick={() => onSort(sortKey)} className="inline-flex items-center gap-1 hover:text-emerald-700">
        {label}
        {active ? (
          sort.dir === "asc" ? (
            <ArrowUp className="h-3.5 w-3.5" />
          ) : (
            <ArrowDown className="h-3.5 w-3.5" />
          )
        ) : (
          <ArrowUpDown className="h-3.5 w-3.5 text-gray-300" />
        )}
      </button>
    </th>
  );
}

function RegressionPanel({ regression }: { regression: FetchState<AnalyticsProtocolRegression> }) {
  if (regression.loading || regression.error) return <StatusBlock loading={regression.loading} error={regression.error} />;
  const data = regression.data;
  if (!data || data.error || Object.keys(data.odds_ratios).length === 0) {
    return <EmptyBlock message={data?.error ?? "Not enough data yet for a regression model."} />;
  }
  const entries = Object.entries(data.odds_ratios).sort((a, b) => b[1] - a[1]);
  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500">Fit on n={fmtNum(data.n_samples)} records</p>
      {entries.map(([feature, oddsRatio]) => (
        <div key={feature} className="flex items-center justify-between rounded-xl border border-gray-100 px-3 py-2 text-sm">
          <span className="text-gray-700">{feature}</span>
          <span className={`font-semibold ${oddsRatio >= 1 ? "text-emerald-700" : "text-rose-600"}`}>
            {oddsRatio.toFixed(3)}×
          </span>
        </div>
      ))}
    </div>
  );
}

function ImportancePanel({ importance }: { importance: FetchState<AnalyticsProtocolImportance> }) {
  if (importance.loading || importance.error) return <StatusBlock loading={importance.loading} error={importance.error} />;
  const data = importance.data;
  if (!data || data.error || Object.keys(data.feature_importances).length === 0) {
    return <EmptyBlock message={data?.error ?? "Not enough data yet for feature importance."} />;
  }
  const entries = Object.entries(data.feature_importances).sort((a, b) => b[1].mean - a[1].mean);
  const maxMean = Math.max(...entries.map(([, v]) => v.mean), 0.0001);
  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500">Fit on n={fmtNum(data.n_samples)} records</p>
      {entries.map(([feature, v]) => (
        <div key={feature} className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-700">{feature}</span>
            <span className="text-gray-500">
              {v.mean.toFixed(4)} ± {v.std.toFixed(4)}
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-full rounded-full bg-emerald-500"
              style={{ width: `${Math.max(2, (v.mean / maxMean) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════ Donors Tab ═══════════════════════════════ */

type DonorSortKey = "donor_tag" | "n_transfers" | "pregnancy_rate" | "avg_cl";

function DonorsTab({ donors }: { donors: FetchState<AnalyticsDonorStatsResponse> }) {
  const [sort, setSort] = useState<{ key: DonorSortKey; dir: "asc" | "desc" }>({
    key: "n_transfers",
    dir: "desc",
  });

  const rows = donors.data?.donors ?? [];

  const sortedRows = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      const cmp = typeof av === "string" ? av.localeCompare(String(bv)) : Number(av) - Number(bv);
      return sort.dir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [rows, sort]);

  const toggleSort = (key: DonorSortKey) => {
    setSort((prev) => (prev.key === key ? { key, dir: prev.dir === "asc" ? "desc" : "asc" } : { key, dir: "desc" }));
  };

  const topByVolume = useMemo(
    () =>
      [...rows]
        .sort((a, b) => b.n_transfers - a.n_transfers)
        .slice(0, 15)
        .map((d: AnalyticsDonorStats) => ({
          donor_tag: d.donor_tag,
          rate_pct: d.pregnancy_rate * 100,
          n_transfers: d.n_transfers,
          n_pregnant: d.n_pregnant,
        })),
    [rows]
  );

  return (
    <div className="space-y-6">
      <SectionCard
        title="Top Donors by Transfer Volume"
        subtitle="Pregnancy rate for the 15 donors with the most transfers (hover for n)"
      >
        {donors.loading || donors.error ? (
          <StatusBlock loading={donors.loading} error={donors.error} />
        ) : topByVolume.length === 0 ? (
          <EmptyBlock message="No donor data available yet." />
        ) : (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topByVolume} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis
                  dataKey="donor_tag"
                  stroke="#6B7280"
                  tickLine={false}
                  axisLine={false}
                  angle={-40}
                  textAnchor="end"
                  interval={0}
                  height={70}
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  stroke="#6B7280"
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value: number) => `${value}%`}
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={CHART_TOOLTIP_STYLE}
                  formatter={(value, _name, item) => {
                    const raw = typeof value === "number" ? value : Number(value);
                    const payload = item?.payload as { n_transfers: number; n_pregnant: number } | undefined;
                    return [
                      `${raw.toFixed(1)}% (n=${payload?.n_transfers ?? "?"}, ${payload?.n_pregnant ?? "?"} pregnant)`,
                      "Rate",
                    ];
                  }}
                />
                <Bar dataKey="rate_pct" radius={[8, 8, 0, 0]} fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </SectionCard>

      <SectionCard title="All Donors" subtitle="Sortable — click a column header. Every rate is shown with n.">
        {donors.loading || donors.error ? (
          <StatusBlock loading={donors.loading} error={donors.error} />
        ) : sortedRows.length === 0 ? (
          <EmptyBlock message="No donor data available yet." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-emerald-50 text-gray-600">
                  <SortHeader label="Donor" sortKey="donor_tag" sort={sort} onSort={toggleSort} />
                  <th className="px-4 py-3 text-left font-medium">Breed</th>
                  <SortHeader label="n Transfers" sortKey="n_transfers" sort={sort} onSort={toggleSort} />
                  <th className="px-4 py-3 text-left font-medium">n Pregnant</th>
                  <SortHeader label="Pregnancy Rate" sortKey="pregnancy_rate" sort={sort} onSort={toggleSort} />
                  <SortHeader label="Avg CL (mm)" sortKey="avg_cl" sort={sort} onSort={toggleSort} />
                  <th className="px-4 py-3 text-left font-medium">First → Last</th>
                  <th className="px-4 py-3 text-left font-medium">Active Months</th>
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((donor) => (
                  <tr key={donor.donor_tag} className="border-b last:border-0 hover:bg-emerald-50/30">
                    <td className="px-4 py-3 font-medium text-gray-900">{donor.donor_tag}</td>
                    <td className="px-4 py-3">{donor.breed ?? "—"}</td>
                    <td className="px-4 py-3">{donor.n_transfers}</td>
                    <td className="px-4 py-3">{fmtNum(donor.n_pregnant)}</td>
                    <td className="px-4 py-3 font-medium">{fmtPct(donor.pregnancy_rate)}</td>
                    <td className="px-4 py-3">{donor.avg_cl !== null ? donor.avg_cl.toFixed(1) : "—"}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {fmtDate(donor.first_date)} → {fmtDate(donor.last_date)}
                    </td>
                    <td className="px-4 py-3">{donor.active_months}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  );
}

/* ═══════════════════════════════ Biomarkers Tab ═══════════════════════════════ */

const BIOMARKER_LABELS: Record<string, string> = {
  cl_measure: "CL Measure (mm)",
  bc_score: "Body Condition Score",
  heat_day: "Heat Day",
};

function BiomarkersTab({ biomarkers }: { biomarkers: FetchState<AnalyticsBiomarkersResponse> }) {
  if (biomarkers.loading || biomarkers.error) {
    return (
      <SectionCard title="Biomarkers">
        <StatusBlock loading={biomarkers.loading} error={biomarkers.error} />
      </SectionCard>
    );
  }

  const data = biomarkers.data;
  const keys: (keyof AnalyticsBiomarkersResponse)[] = ["cl_measure", "bc_score", "heat_day"];
  const usable = keys.filter((key) => {
    const result = data?.[key];
    return result && !result.error && result.bins.length > 0;
  });

  if (!data || usable.length === 0) {
    return (
      <SectionCard title="Biomarkers">
        <EmptyBlock message="No biomarker sweet-spot data available yet." />
      </SectionCard>
    );
  }

  return (
    <div className="space-y-6">
      {usable.map((key) => (
        <BiomarkerPanel key={key} label={BIOMARKER_LABELS[key] ?? key} result={data[key] as AnalyticsBiomarkerResult} />
      ))}
    </div>
  );
}

interface BiomarkerChartRow {
  range: string;
  rate_pct: number;
  n: number;
  ci_lower_pct: number | null;
  ci_upper_pct: number | null;
  isOptimal: boolean;
}

function BiomarkerTooltip({ active, payload }: ChartTooltipProps) {
  if (!active || !payload || !payload.length) return null;
  const row = payload[0]?.payload as BiomarkerChartRow | undefined;
  if (!row) return null;
  return (
    <div style={CHART_TOOLTIP_STYLE} className="px-3 py-2">
      <p className="font-semibold text-gray-900">
        {row.range} {row.isOptimal ? "★ optimal" : ""}
      </p>
      <p className="text-emerald-700">
        {row.rate_pct.toFixed(1)}% pregnancy rate (n={row.n})
      </p>
      {row.ci_lower_pct !== null && row.ci_upper_pct !== null ? (
        <p className="text-gray-500">
          95% CI: {row.ci_lower_pct.toFixed(1)}% – {row.ci_upper_pct.toFixed(1)}%
        </p>
      ) : null}
    </div>
  );
}

function BiomarkerPanel({ label, result }: { label: string; result: AnalyticsBiomarkerResult }) {
  const optimalRange = result.optimal_bin?.range ?? result.optimal_range?.range ?? null;

  const chartData: BiomarkerChartRow[] = result.bins.map((bin: AnalyticsBiomarkerBin) => ({
    range: bin.range,
    rate_pct: bin.pregnancy_rate * 100,
    n: bin.n,
    ci_lower_pct: bin.ci_lower !== null ? bin.ci_lower * 100 : null,
    ci_upper_pct: bin.ci_upper !== null ? bin.ci_upper * 100 : null,
    isOptimal: bin.range === optimalRange,
  }));

  const hasCI = chartData.some((row) => row.ci_lower_pct !== null && row.ci_upper_pct !== null);

  return (
    <SectionCard
      title={label}
      subtitle={`Overall rate ${fmtPct(result.overall_rate)} across n=${fmtNum(result.total_records)} records${
        optimalRange ? ` · optimal bin: ${optimalRange}` : ""
      }`}
    >
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis dataKey="range" stroke="#6B7280" tickLine={false} axisLine={false} tick={{ fontSize: 11 }} />
            <YAxis
              stroke="#6B7280"
              tickLine={false}
              axisLine={false}
              tickFormatter={(value: number) => `${value}%`}
              domain={[0, 100]}
            />
            <Tooltip content={<BiomarkerTooltip />} />
            <Bar dataKey="rate_pct" radius={[8, 8, 0, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.range} fill={entry.isOptimal ? "#059669" : "#a7f3d0"} />
              ))}
              {hasCI ? (
                <ErrorBar
                  dataKey={(entry: BiomarkerChartRow) => [
                    entry.ci_lower_pct !== null ? Math.max(0, entry.rate_pct - entry.ci_lower_pct) : 0,
                    entry.ci_upper_pct !== null ? Math.max(0, entry.ci_upper_pct - entry.rate_pct) : 0,
                  ]}
                  width={4}
                  strokeWidth={1.5}
                  stroke="#374151"
                />
              ) : null}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="px-2 py-1 font-medium">Range</th>
              <th className="px-2 py-1 font-medium">n</th>
              <th className="px-2 py-1 font-medium">Pregnancy Rate</th>
              <th className="px-2 py-1 font-medium">95% CI</th>
              <th className="px-2 py-1 font-medium">Mean Value</th>
            </tr>
          </thead>
          <tbody>
            {result.bins.map((bin) => (
              <tr
                key={bin.range}
                className={`border-t border-gray-100 ${bin.range === optimalRange ? "bg-emerald-50 font-medium" : ""}`}
              >
                <td className="px-2 py-1">
                  {bin.range}
                  {bin.range === optimalRange ? " ★" : ""}
                </td>
                <td className="px-2 py-1">{bin.n}</td>
                <td className="px-2 py-1">{fmtPct(bin.pregnancy_rate)}</td>
                <td className="px-2 py-1 text-gray-500">
                  {bin.ci_lower !== null && bin.ci_upper !== null ? `${fmtPct(bin.ci_lower)} – ${fmtPct(bin.ci_upper)}` : "—"}
                </td>
                <td className="px-2 py-1">{bin.mean_value !== null ? bin.mean_value.toFixed(2) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}
