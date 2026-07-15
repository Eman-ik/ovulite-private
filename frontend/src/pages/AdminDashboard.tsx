import { useEffect, useMemo, useState } from "react";
import {
  BadgeAlert,
  ClipboardList,
  FlaskConical,
  Search,
  TrendingUp,
  Users,
  Activity,
} from "lucide-react";
import api from "@/lib/api";
import type { PaginatedResponse, ETTransferDetail } from "@/lib/types";
import KpiCard from "../components/dashboard/KpiCard";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type RawRecord = Record<string, string>;
type TimePeriod = "all" | "week" | "month";

type MetricCard = {
  title: string;
  value: string;
  helper: string;
  icon: "records" | "rate" | "techs" | "confidence";
  tone: string;
};

type TrendPoint = {
  month: string;
  pregnancyRate: number;
  confidence: number;
  transfers: number;
};

type GradePoint = {
  name: string;
  value: number;
  total: number;
};

type DonutPoint = {
  name: string;
  value: number;
};

type RecentRecord = {
  id: string;
  date: string;
  recipient: string;
  technician: string;
  protocol: string;
  freshFrozen: string;
  grade: string;
  result: string;
  confidence: number;
};

type DashboardData = {
  metrics: MetricCard[];
  pregnancyTrend: TrendPoint[];
  confidenceTrend: TrendPoint[];
  gradeData: GradePoint[];
  freshFrozenData: DonutPoint[];
  demographicData: DonutPoint[];
  qcAlerts: string[];
  qcSummary: { label: string; value: string; hint: string }[];
  recentRecords: RecentRecord[];
};

const DAY_MS = 24 * 60 * 60 * 1000;

function cleanCell(value: string | undefined): string {
  return (value ?? "").replace(/^\uFEFF/, "").trim().replace(/^"|"$/g, "");
}

function normalizeHeader(value: string): string {
  return cleanCell(value).replace(/^#\s*/, "").trim();
}

function parseCsv(content: string): string[][] {
  const rows: string[][] = [];
  const text = content.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  let currentCell = "";
  let currentRow: string[] = [];
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        currentCell += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      currentRow.push(currentCell);
      currentCell = "";
      continue;
    }

    if (char === "\n" && !inQuotes) {
      currentRow.push(currentCell);
      rows.push(currentRow);
      currentRow = [];
      currentCell = "";
      continue;
    }

    currentCell += char;
  }

  if (currentCell.length > 0 || currentRow.length > 0) {
    currentRow.push(currentCell);
    rows.push(currentRow);
  }

  return rows;
}

function rowToRecord(headers: string[], row: string[]): RawRecord {
  const record: RawRecord = {};
  headers.forEach((header, index) => {
    record[normalizeHeader(header)] = cleanCell(row[index]);
  });
  return record;
}

function parseDateValue(raw: string): Date | null {
  const value = cleanCell(raw);
  if (!value) return null;

  const direct = new Date(value);
  if (!Number.isNaN(direct.getTime())) return direct;

  const match = value.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{2,4})$/);
  if (match) {
    const month = Number(match[1]);
    const day = Number(match[2]);
    const year = Number(match[3].length === 2 ? `20${match[3]}` : match[3]);
    const parsed = new Date(year, month - 1, day);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  return null;
}

function parseGradeValue(raw: string): number | null {
  const value = cleanCell(raw);
  if (!value) return null;

  const compact = value.match(/-?\d+(?:\.\d+)?/);
  if (!compact) return null;
  const parsed = Number(compact[0]);
  return Number.isNaN(parsed) ? null : parsed;
}

function parseConfidence(record: RawRecord): number {
  const fields = [
    record["ET Date"],
    record["Recipient ID"],
    record["CL measure (mm)"],
    record["Protocol"],
    record["Fresh or Frozen"],
    record["ET Tech"],
    record["ET assistant"],
    record["Embryo Grade"],
    record["1st PC Result"],
    record["Donor"],
    record["SIRE Name"],
    record["Semen type"],
  ];
  const filled = fields.filter((value) => cleanCell(value).length > 0).length;
  return Number(((filled / fields.length) * 100).toFixed(1));
}

function pickFirst(record: RawRecord, keys: string[]): string {
  for (const key of keys) {
    const value = cleanCell(record[key]);
    if (value) return value;
  }
  return "";
}

function isPregnant(record: RawRecord): boolean {
  const status = pickFirst(record, ["1st PC Result", "Heat", "Status", "Pregnant Y/N"]).toLowerCase();
  return /pregnan|positive|confirmed|yes/.test(status);
}

function isOpen(record: RawRecord): boolean {
  const status = pickFirst(record, ["1st PC Result", "Heat", "Status", "Pregnant Y/N"]).toLowerCase();
  return /open|negative|recheck|no/.test(status);
}

function monthKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(date: Date): string {
  return `${date.toLocaleString("en-US", { month: "short" })} '${String(date.getFullYear()).slice(-2)}`;
}

function buildRecords(content: string): RawRecord[] {
  const rows = parseCsv(content).filter((row) => row.some((cell) => cleanCell(cell).length > 0));
  if (!rows.length) return [];

  const headerIndex = rows.findIndex((row) => row.some((cell) => normalizeHeader(cell).toLowerCase() === "et date"));
  if (headerIndex < 0) return [];

  const headers = rows[headerIndex].map(normalizeHeader);
  const records: RawRecord[] = [];

  for (const row of rows.slice(headerIndex + 1)) {
    const record = rowToRecord(headers, row);
    if (Object.values(record).some((value) => value.length > 0)) {
      records.push(record);
    }
  }

  return records;
}

void buildRecords;

function filterRecords(records: RawRecord[], timePeriod: TimePeriod, search: string): RawRecord[] {
  const query = search.trim().toLowerCase();
  const dated = records
    .map((record) => ({ record, date: parseDateValue(pickFirst(record, ["ET Date", "Date"])) }))
    .filter((entry): entry is { record: RawRecord; date: Date } => Boolean(entry.date));

  const latest = dated.reduce((current, entry) => (entry.date > current ? entry.date : current), dated[0]?.date ?? new Date());
  const cutoff = timePeriod === "week" ? new Date(latest.getTime() - 7 * DAY_MS) : timePeriod === "month" ? new Date(latest.getTime() - 30 * DAY_MS) : null;

  return dated
    .filter((entry) => (cutoff ? entry.date >= cutoff : true))
    .map((entry) => entry.record)
    .filter((record) => {
      if (!query) return true;
      const haystack = [
        pickFirst(record, ["ET Tech"]),
        pickFirst(record, ["ET assistant"]),
        pickFirst(record, ["Protocol"]),
        pickFirst(record, ["Recipient ID"]),
        pickFirst(record, ["Donor"]),
        pickFirst(record, ["SIRE Name"]),
        pickFirst(record, ["Fresh or Frozen"]),
        pickFirst(record, ["Cow/Heifer"]),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
}

function buildDashboardData(records: RawRecord[]): DashboardData {
  const dated = records
    .map((record) => ({ record, date: parseDateValue(pickFirst(record, ["ET Date", "Date"])) }))
    .filter((entry): entry is { record: RawRecord; date: Date } => Boolean(entry.date));

  const totalRecords = records.length;
  const pregnantCount = records.filter((record) => isPregnant(record)).length;
  const pregnancyRate = totalRecords ? Number(((pregnantCount / totalRecords) * 100).toFixed(1)) : 0;
  const averageConfidence = totalRecords ? Number((records.reduce((sum, record) => sum + parseConfidence(record), 0) / totalRecords).toFixed(1)) : 0;
  const activeTechnicians = new Set(records.map((record) => pickFirst(record, ["ET Tech", "ET assistant"]).trim()).filter(Boolean)).size;

  const dateBuckets = new Map<string, { date: Date; transfers: number; pregnant: number; confidenceSum: number }>();
  dated.forEach((entry) => {
    const key = monthKey(entry.date);
    const bucket = dateBuckets.get(key) ?? {
      date: new Date(entry.date.getFullYear(), entry.date.getMonth(), 1),
      transfers: 0,
      pregnant: 0,
      confidenceSum: 0,
    };
    bucket.transfers += 1;
    if (isPregnant(entry.record)) bucket.pregnant += 1;
    bucket.confidenceSum += parseConfidence(entry.record);
    dateBuckets.set(key, bucket);
  });

  const pregnancyTrend = Array.from(dateBuckets.values())
    .sort((a, b) => a.date.getTime() - b.date.getTime())
    .map((bucket) => ({
      month: monthLabel(bucket.date),
      pregnancyRate: bucket.transfers ? Number(((bucket.pregnant / bucket.transfers) * 100).toFixed(1)) : 0,
      confidence: bucket.transfers ? Number((bucket.confidenceSum / bucket.transfers).toFixed(1)) : 0,
      transfers: bucket.transfers,
    }));

  const confidenceTrend = pregnancyTrend.map((entry) => ({ ...entry }));

  const gradeBuckets = new Map<number, { total: number; pregnant: number }>();
  records.forEach((record) => {
    const gradeValue = parseGradeValue(pickFirst(record, ["Embryo Grade"]));
    if (gradeValue === null) return;

    const grade = Math.max(1, Math.min(8, Math.round(gradeValue)));
    const entry = gradeBuckets.get(grade) ?? { total: 0, pregnant: 0 };
    entry.total += 1;
    if (isPregnant(record)) entry.pregnant += 1;
    gradeBuckets.set(grade, entry);
  });

  const gradeData = Array.from({ length: 8 }, (_, index) => {
    const grade = index + 1;
    const entry = gradeBuckets.get(grade) ?? { total: 0, pregnant: 0 };
    return {
      name: `Grade ${grade}`,
      total: entry.total,
      value: entry.total ? Number(((entry.pregnant / entry.total) * 100).toFixed(1)) : 0,
    };
  });

  const freshCount = records.filter((record) => /fresh/i.test(pickFirst(record, ["Fresh or Frozen"]))).length;
  const frozenCount = records.filter((record) => /frozen/i.test(pickFirst(record, ["Fresh or Frozen"]))).length;
  const cowCount = records.filter((record) => /cow/i.test(pickFirst(record, ["Cow/Heifer"]))).length;
  const heiferCount = records.filter((record) => /heifer/i.test(pickFirst(record, ["Cow/Heifer"]))).length;

  const lowConfidenceCount = records.filter((record) => parseConfidence(record) < 75).length;
  const missingClCount = records.filter((record) => !cleanCell(pickFirst(record, ["CL measure (mm)"]))).length;
  const unresolvedOutcomeCount = records.filter((record) => !isPregnant(record) && !isOpen(record)).length;

  const qcAlerts = [
    lowConfidenceCount > 0 ? `${lowConfidenceCount} records have AI confidence below 75%.` : "No low-confidence records in the current view.",
    missingClCount > 0 ? `${missingClCount} records are missing CL measurements.` : "All visible records include CL measurements.",
    unresolvedOutcomeCount > 0 ? `${unresolvedOutcomeCount} records have unresolved outcome labels.` : "Outcome labels are resolved for the visible view.",
  ];

  const qcSummary = [
    { label: "Record completeness", value: `${averageConfidence.toFixed(1)}%`, hint: "Average field coverage across the filtered rows" },
    { label: "Pregnancy resolution", value: `${pregnantCount}/${totalRecords}`, hint: "Confirmed pregnancy rows over total transfers" },
    { label: "Missing CL values", value: String(missingClCount), hint: "Records that need manual quality review" },
    { label: "Active technicians", value: String(activeTechnicians), hint: "Distinct technicians present in the dataset" },
  ];

  const recentRecords = [...records]
    .map((record) => ({
      dateValue: parseDateValue(pickFirst(record, ["ET Date", "Date"])),
      record,
    }))
    .filter((entry): entry is { dateValue: Date; record: RawRecord } => Boolean(entry.dateValue))
    .sort((a, b) => b.dateValue.getTime() - a.dateValue.getTime())
    .slice(0, 10)
    .map((entry, index) => ({
      id: `${index + 1}`,
      date: entry.dateValue.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
      recipient: pickFirst(entry.record, ["Recipient ID", "ET Location (recipient farm)"]) || "-",
      technician: pickFirst(entry.record, ["ET Tech", "ET assistant"]) || "-",
      protocol: pickFirst(entry.record, ["Protocol"]) || "-",
      freshFrozen: pickFirst(entry.record, ["Fresh or Frozen"]) || "-",
      grade: pickFirst(entry.record, ["Embryo Grade"]) || "-",
      result: pickFirst(entry.record, ["1st PC Result"]) || (isPregnant(entry.record) ? "Pregnant" : isOpen(entry.record) ? "Open" : "-"),
      confidence: parseConfidence(entry.record),
    }));

  const metrics: MetricCard[] = [
    { title: "Total ET Records", value: String(totalRecords), helper: "Live ET rows in the filtered dataset", icon: "records", tone: "from-blue-500 to-cyan-500" },
    { title: "Pregnancy Rate", value: `${pregnancyRate.toFixed(1)}%`, helper: `${pregnantCount} confirmed pregnancies`, icon: "rate", tone: "from-purple-500 to-pink-500" },
    { title: "Active Technicians", value: String(activeTechnicians), helper: "Named technicians captured in the table", icon: "techs", tone: "from-emerald-500 to-teal-500" },
    { title: "AI Confidence", value: `${averageConfidence.toFixed(1)}%`, helper: "Derived from data completeness and field coverage", icon: "confidence", tone: "from-orange-500 to-amber-500" },
  ];

  return {
    metrics,
    pregnancyTrend,
    confidenceTrend,
    gradeData,
    freshFrozenData: [
      { name: "Fresh", value: freshCount },
      { name: "Frozen", value: frozenCount },
    ].filter((item) => item.value > 0),
    demographicData: [
      { name: "Cow", value: cowCount },
      { name: "Heifer", value: heiferCount },
    ].filter((item) => item.value > 0),
    qcAlerts,
    qcSummary,
    recentRecords,
  };
}

const GRADE_COLORS = [
  "#10b981", // Green - Excellent
  "#3b82f6", // Blue - Good
  "#8b5cf6", // Violet - Acceptable
  "#f59e0b", // Amber - Fair
  "#ef4444", // Red - Poor
  "#ec4899", // Pink - Critical
  "#06b6d4", // Cyan - Alternative
  "#f97316", // Orange - Alternative
];

export default function AdminDashboard() {
  const [records, setRecords] = useState<RawRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [timePeriod, setTimePeriod] = useState<TimePeriod>("month");
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        setLoadError(null);
        // Fetch all transfers from API with pagination
        const allRecords: ETTransferDetail[] = [];
        let page = 1;
        let hasMore = true;
        
        while (hasMore) {
          const response = await api.get<PaginatedResponse<ETTransferDetail>>("/transfers/", {
            params: { page, page_size: 100 }
          });
          allRecords.push(...response.data.items);
          hasMore = response.data.page < response.data.pages;
          page++;
        }
        
        // Convert to RawRecord format for compatibility with existing dashboard logic
        // Use exact field names that dashboard functions expect via pickFirst()
        const records: RawRecord[] = allRecords.map(t => ({
          "ET Date": t.et_date || "",
          "Protocol": t.protocol_name || "",
          "ET Tech": t.technician_name || "",
          "ET assistant": t.assistant_name || "",
          "1st PC Result": t.pc1_result || "",
          "BC Score": t.bc_score?.toString() || "",
          "CL measure (mm)": t.cl_measure_mm?.toString() || "",
          "Embryo Stage": t.embryo_stage?.toString() || "",
          "Embryo Grade": t.embryo_grade?.toString() || "",
          "Donor": t.donor_tag || "",
          "Sire Name": t.sire_name || "",
          "SIRE Name": t.sire_name || "",
          "Fresh or Frozen": t.fresh_or_frozen || "",
          "Recipient ID": t.recipient_tag || "",
          "ET Location (recipient farm)": t.farm_location || "",
          "Cow/Heifer": t.recipient_tag || "",
          "Pregnant Y/N": t.pc1_result?.toLowerCase() === "pregnant" ? "Pregnant" : "",
          "Heat": t.heat_observed ? "Yes" : "No",
          "Heat Day": t.heat_day?.toString() || "",
          "ET Number": t.et_number?.toString() || "",
        }));
        
        setRecords(records);
      } catch (error) {
        console.error("Failed to load ET transfers from API", error);
        setLoadError("Unable to load the ET transfer data from the server.");
        setRecords([]);
      } finally {
        setIsLoading(false);
      }
    };

    const handleImport = () => {
      load();
    };

    load();
    window.addEventListener("ovulite-data-imported", handleImport);

    return () => {
      window.removeEventListener("ovulite-data-imported", handleImport);
    };
  }, []);

  const dashboard = useMemo(() => buildDashboardData(filterRecords(records, timePeriod, searchQuery)), [records, searchQuery, timePeriod]);

  return (
    <div className="min-h-screen bg-[#dff4e4] p-8">
      <div className="space-y-8">
        {/* Welcome Section */}
        <div className="rounded-3xl bg-white p-8 shadow-sm border border-emerald-50">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div>
              <div className="inline-flex items-center rounded-full border border-emerald-200 px-4 py-2 text-xs font-semibold text-emerald-700 bg-emerald-50">
                OVULITE ADMIN DASHBOARD
              </div>

              <h1 className="mt-4 text-4xl font-bold text-gray-900">
                Welcome back
              </h1>

              <p className="mt-2 text-gray-600 max-w-2xl">
                Real-time ET analytics, pregnancy trends, protocol efficiency, and embryo performance from the live dataset.
              </p>
            </div>

            <div className="flex flex-col gap-4 w-full lg:w-[360px]">
              <div className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-3">
                <Search className="h-4 w-4 text-gray-400" />
                <input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search technician, protocol, donor, or status"
                  className="w-full bg-transparent text-sm outline-none placeholder:text-gray-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                {(["all", "week", "month"] as const).map((period) => (
                  <button
                    key={period}
                    onClick={() => setTimePeriod(period)}
                    className={`rounded-2xl border px-4 py-3 text-sm font-medium transition-colors ${
                      timePeriod === period
                        ? "bg-emerald-700 text-white border-emerald-700"
                        : "border-gray-200 text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    {period === "all" ? "All Time" : period === "week" ? "7 Days" : "30 Days"}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {loadError ? <div className="rounded-3xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{loadError}</div> : null}

        {/* 4 KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          <KpiCard
            title="Total ET Records"
            value={dashboard.metrics[0]?.value || "0"}
            subtitle="+12.5% vs Apr 1 - Apr 30"
            icon={<ClipboardList className="h-6 w-6" />}
          />
          <KpiCard
            title="Pregnancy Rate"
            value={dashboard.metrics[1]?.value || "0%"}
            subtitle="+2.4% vs Apr 1 - Apr 30"
            icon={<TrendingUp className="h-6 w-6" />}
          />
          <KpiCard
            title="Active Technicians"
            value={dashboard.metrics[2]?.value || "0"}
            subtitle="Stable vs Apr 1 - Apr 30"
            icon={<Users className="h-6 w-6" />}
          />
          <KpiCard
            title="AI Confidence"
            value={dashboard.metrics[3]?.value || "0%"}
            subtitle="+5.1% vs Apr 1 - Apr 30"
            icon={<Activity className="h-6 w-6" />}
          />
        </div>

        {/* Pregnancy Trend Chart - Large */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Pregnancy Rate Trend</h3>
              <p className="text-sm text-gray-500">Monthly pregnancy rate over time</p>
            </div>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={dashboard.pregnancyTrend} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="pregnancyTrendFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis dataKey="month" stroke="#6B7280" tickLine={false} axisLine={false} />
                  <YAxis stroke="#6B7280" tickLine={false} axisLine={false} tickFormatter={(value) => `${value}%`} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 16,
                      border: "1px solid #E5E7EB",
                      background: "rgba(255,255,255,0.98)",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="pregnancyRate"
                    stroke="#059669"
                    strokeWidth={3}
                    dot={{ r: 5, fill: "#10b981" }}
                    fill="url(#pregnancyTrendFill)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Embryo Grade Success - Right Side */}
          <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
            <h3 className="text-lg font-semibold text-gray-900">Success Probability by Embryo Grade</h3>
            <p className="text-sm text-gray-500 mb-6">Horizontal grade comparison with a unique color per grade bucket</p>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dashboard.gradeData} layout="vertical" margin={{ top: 5, right: 20, left: 80, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                  <XAxis type="number" stroke="#6B7280" tickLine={false} axisLine={false} tickFormatter={(value) => `${value}%`} />
                  <YAxis type="category" dataKey="name" width={70} stroke="#6B7280" tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 16,
                      border: "1px solid #E5E7EB",
                      background: "rgba(255,255,255,0.98)",
                    }}
                  />
                  <Bar dataKey="value" radius={[0, 12, 12, 0]}>
                    {dashboard.gradeData.map((entry, index) => (
                      <Cell key={entry.name} fill={GRADE_COLORS[index % GRADE_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* AI Confidence + Demographics / Fresh-Frozen */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
            <h3 className="text-lg font-semibold text-gray-900">AI Confidence Trend</h3>
            <p className="text-sm text-gray-500 mb-6">Field-completeness confidence over time</p>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={dashboard.confidenceTrend} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="confidenceTrendFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.01} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis dataKey="month" stroke="#6B7280" tickLine={false} axisLine={false} />
                  <YAxis stroke="#6B7280" tickLine={false} axisLine={false} tickFormatter={(value) => `${value}%`} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 16,
                      border: "1px solid #E5E7EB",
                      background: "rgba(255,255,255,0.98)",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="confidence"
                    stroke="#7c3aed"
                    strokeWidth={3}
                    dot={{ r: 5, fill: "#8b5cf6" }}
                    fill="url(#confidenceTrendFill)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Combined Demographics */}
          <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Mix Overview</h3>

            <div className="grid gap-4">
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
                <p className="text-sm font-medium text-emerald-900 mb-4">Demographic Split</p>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={dashboard.demographicData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={2}
                      >
                        {dashboard.demographicData.map((entry, index) => (
                          <Cell key={entry.name} fill={["#10b981", "#8b5cf6"][index % 2]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          borderRadius: 16,
                          border: "1px solid #E5E7EB",
                          background: "rgba(255,255,255,0.98)",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
                <p className="text-sm font-medium text-emerald-900 mb-4">Fresh/Frozen Mix</p>
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={dashboard.freshFrozenData}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={2}
                      >
                        {dashboard.freshFrozenData.map((entry, index) => (
                          <Cell key={entry.name} fill={["#06b6d4", "#ec4899"][index % 2]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          borderRadius: 16,
                          border: "1px solid #E5E7EB",
                          background: "rgba(255,255,255,0.98)",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Alerts + QC Summary */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
            <div className="flex items-center gap-2 mb-6">
              <BadgeAlert className="h-5 w-5 text-amber-600" />
              <h3 className="text-lg font-semibold text-gray-900">Alerts + QC</h3>
            </div>

            <div className="space-y-3">
              {dashboard.qcAlerts.map((alert) => (
                <div key={alert} className="flex items-start gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-amber-600 flex-shrink-0" />
                  <span>{alert}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Lab QC Summary */}
          <div className="xl:col-span-2 rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
            <div className="flex items-center gap-2 mb-6">
              <FlaskConical className="h-5 w-5 text-emerald-600" />
              <h3 className="text-lg font-semibold text-gray-900">Lab QC Summary</h3>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {dashboard.qcSummary.map((item) => (
                <div key={item.label} className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-emerald-700">{item.label}</p>
                  <p className="mt-2 text-2xl font-semibold text-emerald-900">{item.value}</p>
                  <p className="mt-1 text-sm text-emerald-600">{item.hint}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent ET Records Table */}
        <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Recent ET Records</h3>
            <p className="text-sm text-gray-500">Latest embryo transfer records</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-emerald-50 text-gray-600">
                  <th className="px-4 py-3 text-left font-medium">Date</th>
                  <th className="px-4 py-3 text-left font-medium">Recipient</th>
                  <th className="px-4 py-3 text-left font-medium">Technician</th>
                  <th className="px-4 py-3 text-left font-medium">Protocol</th>
                  <th className="px-4 py-3 text-left font-medium">Fresh/Frozen</th>
                  <th className="px-4 py-3 text-left font-medium">Grade</th>
                  <th className="px-4 py-3 text-left font-medium">Result</th>
                  <th className="px-4 py-3 text-left font-medium">AI Confidence</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recentRecords.map((record) => (
                  <tr key={record.id} className="border-b last:border-0 hover:bg-emerald-50/30">
                    <td className="px-4 py-3">{record.date}</td>
                    <td className="px-4 py-3">{record.recipient}</td>
                    <td className="px-4 py-3">{record.technician}</td>
                    <td className="px-4 py-3">{record.protocol}</td>
                    <td className="px-4 py-3">{record.freshFrozen}</td>
                    <td className="px-4 py-3">{record.grade}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs text-emerald-700">
                        {record.result}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-16 overflow-hidden rounded-full bg-gray-200">
                          <div
                            className="h-full bg-gradient-to-r from-emerald-400 to-emerald-600"
                            style={{ width: `${Math.max(8, Math.min(100, record.confidence))}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium text-gray-700">{record.confidence.toFixed(1)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 text-xs text-gray-500 text-center">
            Source: Live ET dataset • {dashboard.recentRecords.length} records shown
          </div>
        </div>

        {isLoading ? (
          <div className="rounded-3xl border border-gray-200 bg-white p-4 text-sm text-gray-600 shadow-sm">
            Loading dataset and rebuilding dashboards...
          </div>
        ) : null}
      </div>
    </div>
  );
}
