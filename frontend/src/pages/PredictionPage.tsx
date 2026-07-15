import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Baby,
  Brain,
  Building2,
  CalendarDays,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  Dna,
  Download,
  Droplets,
  Eye,
  FlaskConical,
  Info,
  Leaf,
  Pencil,
  RotateCcw,
  Save,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  TrendingUp,
  UserRound,
} from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import type { PaginatedResponse, Protocol, Technician } from "@/lib/types";
import PredictionAssistantChatbox from "@/components/PredictionAssistantChatbox";

interface ShapContribution {
  feature: string;
  value: number;
}

interface PredictionResult {
  probability: number;
  probability_percent?: number;
  confidence_lower: number;
  confidence_upper: number;
  risk_band: string;
  uncertainty_level?: string;
  is_ood?: boolean;
  ood_reasons?: string[];
  similar_cases?: Array<{ transfer_reference: string; et_date: string; outcome: number; distance: number }>;
  plain_language_summary?: string;
  feature_schema_version?: string;
  request_id?: string;
  created_at?: string;
  model_name: string;
  model_version: string;
  shap_explanation: {
    base_value: number;
    contributions: ShapContribution[];
  };
  prediction_id: number | null;
}

interface ModelInfo {
  model_name: string;
  model_version: string;
  n_features: number;
  best_model_key: string;
  training_split: Record<string, unknown>;
  top_features: [string, number][];
}

type FormState = {
  caseId: string;
  transferDate: string;
  status: string;
  recipientId: string;
  species: string;
  breed: string;
  age: string;
  bcs: string;
  history: string;
  syncProtocol: string;
  daysPostEstrus: string;
  clSide: string;
  clPresent: string;
  clSize: string;
  clQuality: string;
  uterineTone: string;
  embryoId: string;
  embryoType: string;
  embryoStage: string;
  embryoGrade: string;
  embryoDay: string;
  donorId: string;
  donorBreed: string;
  donorBwEpd: string;
  sireId: string;
  sireBwEpd: string;
  semenType: string;
  technicianName: string;
  transferSide: string;
  transferDifficulty: string;
  environment: string;
  customerId: string;
};

const today = new Date().toISOString().slice(0, 10);

const initialForm: FormState = {
  caseId: "ET-2026-00124",
  transferDate: today,
  status: "Draft",
  recipientId: "",
  species: "Cattle",
  breed: "",
  age: "",
  bcs: "",
  history: "",
  syncProtocol: "",
  daysPostEstrus: "",
  clSide: "",
  clPresent: "",
  clSize: "",
  clQuality: "",
  uterineTone: "",
  embryoId: "",
  embryoType: "Fresh",
  embryoStage: "",
  embryoGrade: "",
  embryoDay: "",
  donorId: "",
  donorBreed: "",
  donorBwEpd: "",
  sireId: "",
  sireBwEpd: "",
  semenType: "",
  technicianName: "",
  transferSide: "",
  transferDifficulty: "",
  environment: "",
  customerId: "DZF",
};

type RecentRow = {
  caseId: string;
  recipient: string;
  embryo: string;
  date: string;
  probability: number;
  confidence: "High" | "Medium" | "Low";
  outcome: "Pending" | "Pregnant" | "Not Pregnant";
};

const recentData: RecentRow[] = [
  { caseId: "ET-2026-00124", recipient: "REC-0345", embryo: "EMB-0456", date: "05 Jul 2026", probability: 72, confidence: "Medium", outcome: "Pending" },
  { caseId: "ET-2026-00123", recipient: "REC-0338", embryo: "EMB-0449", date: "04 Jul 2026", probability: 61, confidence: "High", outcome: "Pregnant" },
  { caseId: "ET-2026-00122", recipient: "REC-0321", embryo: "EMB-0432", date: "03 Jul 2026", probability: 38, confidence: "Medium", outcome: "Not Pregnant" },
  { caseId: "ET-2026-00121", recipient: "REC-0318", embryo: "EMB-0425", date: "02 Jul 2026", probability: 81, confidence: "High", outcome: "Pregnant" },
];

function SectionShell({
  icon: Icon,
  title,
  helper,
  children,
  index,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  helper: string;
  children: ReactNode;
  index: number;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.45, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
      className="pp-glass-card rounded-2xl p-6 md:p-7"
    >
      <div className="mb-5 flex items-start gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[var(--pp-foam)] text-[var(--pp-primary)] shadow-inner">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h3 className="font-display text-2xl leading-tight text-[var(--pp-foreground)]">{title}</h3>
          <p className="mt-1 text-sm text-[var(--pp-muted)]">{helper}</p>
        </div>
      </div>
      <div className="mb-5 h-px bg-[var(--pp-border)]" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{children}</div>
    </motion.section>
  );
}

function Field({
  label,
  helper,
  children,
  full,
}: {
  label: string;
  helper?: string;
  children: ReactNode;
  full?: boolean;
}) {
  return (
    <div className={full ? "md:col-span-2" : undefined}>
      <label className="mb-1.5 block text-sm font-medium text-[var(--pp-foreground)]">{label}</label>
      {children}
      {helper && <p className="mt-1.5 text-xs text-[var(--pp-muted)]">{helper}</p>}
    </div>
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
  type = "text",
  min,
  max,
  step,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  min?: string;
  max?: string;
  step?: string;
}) {
  return (
    <input
      type={type}
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      className="pp-input"
    />
  );
}

function SelectField({
  value,
  onValueChange,
  placeholder,
  options,
}: {
  value: string;
  onValueChange: (value: string) => void;
  placeholder: string;
  options: string[];
}) {
  return (
    <select value={value} onChange={(event) => onValueChange(event.target.value)} className="pp-input">
      <option value="">{placeholder}</option>
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

function KpiCard({
  icon: Icon,
  label,
  value,
  caption,
  delay,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  caption: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: [0, -5, 0] }}
      transition={{
        opacity: { duration: 0.45, delay },
        y: { duration: 4, repeat: Infinity, ease: "easeInOut", delay },
      }}
      whileHover={{ scale: 1.02 }}
      className="pp-glass-card group relative overflow-hidden rounded-2xl p-5"
    >
      <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-[var(--pp-leaf)]/25 blur-2xl" />
      <div className="flex items-center justify-between">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-[var(--pp-foam)] text-[var(--pp-primary)]">
          <Icon className="h-5 w-5" />
        </div>
        <TrendingUp className="h-4 w-4 text-[var(--pp-sage)]" />
      </div>
      <div className="mt-4">
        <div className="text-sm text-[var(--pp-muted)]">{label}</div>
        <div className="mt-1 font-display text-4xl leading-none text-[var(--pp-foreground)]">{value}</div>
        <div className="mt-2 text-xs text-[var(--pp-muted)]">{caption}</div>
      </div>
    </motion.div>
  );
}

export default function PredictionPage() {
  const navigate = useNavigate();
  const { token, user } = useAuth();
  const [form, setForm] = useState<FormState>(initialForm);
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [, setModelInfo] = useState<ModelInfo | null>(null);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [initLoading, setInitLoading] = useState(true);
  const [error, setError] = useState("");
  const [initError, setInitError] = useState("");
  const [outcomeOpen, setOutcomeOpen] = useState(false);
  const [outcomeCase, setOutcomeCase] = useState("");
  const [assistantOpen, setAssistantOpen] = useState(false);

  const setField = <K extends keyof FormState>(key: K) => (value: FormState[K]) => {
    setForm((previous) => ({ ...previous, [key]: value }));
  };

  useEffect(() => {
    let cancelled = false;

    async function loadInitialData() {
      setInitLoading(true);
      setInitError("");
      try {
        const [protocolRes, technicianRes, modelRes] = await Promise.all([
          api.get<PaginatedResponse<Protocol>>("/protocols/", { params: { page_size: 50 } }),
          api.get<PaginatedResponse<Technician>>("/technicians/", { params: { page_size: 50 } }),
          api.get<ModelInfo>("/predict/model-info"),
        ]);

        if (cancelled) return;
        setProtocols(Array.isArray(protocolRes.data.items) ? protocolRes.data.items : []);
        setTechnicians(Array.isArray(technicianRes.data.items) ? technicianRes.data.items : []);
        if (isModelInfo(modelRes.data)) setModelInfo(modelRes.data);
      } catch (loadError) {
        if (cancelled) return;
        setInitError(loadError instanceof Error ? loadError.message : "Failed to load prediction reference data");
      } finally {
        if (!cancelled) setInitLoading(false);
      }
    }

    if (token !== null) void loadInitialData();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const canGenerate = Boolean(form.recipientId && form.embryoId && form.clSize && form.embryoStage);

  const dataQuality = useMemo(() => getDataQuality(form), [form]);
  const confidenceLabel = useMemo(() => getConfidenceLabel(prediction, dataQuality.confidence), [prediction, dataQuality.confidence]);
  const probabilityTone = prediction ? getProbabilityTone(prediction.probability * 100) : null;

  const generatePrediction = async () => {
    setError("");

    if (!canGenerate) {
      setError("Enter at least Recipient ID, Embryo ID, CL size, and Embryo Stage to generate a prediction.");
      return;
    }

    setLoading(true);
    setPrediction(null);

    try {
      const payload = {
        cl_measure_mm: parseFloat(form.clSize),
        cl_side: form.clSide || null,
        embryo_stage: parseInt(form.embryoStage, 10),
        embryo_grade: form.embryoGrade ? parseInt(form.embryoGrade, 10) : null,
        fresh_or_frozen: form.embryoType || null,
        protocol_name: form.syncProtocol || null,
        technician_name: form.technicianName || user?.full_name || user?.username || null,
        donor_breed: form.donorBreed || form.breed || null,
        semen_type: form.semenType || null,
        heat_day: form.daysPostEstrus ? parseInt(form.daysPostEstrus, 10) : null,
        bc_score: form.bcs ? parseFloat(form.bcs) : null,
        days_opu_to_et: form.embryoDay ? parseInt(form.embryoDay, 10) : null,
        donor_bw_epd: form.donorBwEpd ? parseFloat(form.donorBwEpd) : null,
        sire_bw_epd: form.sireBwEpd ? parseFloat(form.sireBwEpd) : null,
        customer_id: form.customerId || null,
      };

      const response = await api.post<PredictionResult>("/predict/pregnancy", payload);
      if (!isPredictionResult(response.data)) throw new Error("Prediction response has an unexpected format.");
      setPrediction(response.data);
    } catch (predictError: unknown) {
      setError(getApiErrorMessage(predictError));
    } finally {
      setLoading(false);
    }
  };

  const clearForm = () => {
    setForm(initialForm);
    setPrediction(null);
    setError("");
  };

  return (
    <>
      <style>{predictionPageStyles}</style>

      <div className="pp-page">
        <main className="mx-auto max-w-7xl px-4 py-8 md:px-8 md:py-12">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
            className="mb-8"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--pp-border)] bg-white/60 px-3 py-1 text-xs text-[var(--pp-muted)] backdrop-blur">
              <Sparkles className="h-3.5 w-3.5 text-[var(--pp-sage)]" />
              AI-assisted ET decision support
            </div>
            <h1 className="mt-3 font-display text-4xl leading-[1.05] text-[var(--pp-foreground)] md:text-6xl">
              Pregnancy <span className="italic text-[var(--pp-ocean)]">Prediction</span>
            </h1>
            <p className="mt-3 max-w-2xl text-base text-[var(--pp-muted)] md:text-lg">
              AI-assisted pregnancy success estimation based on recipient condition, embryo quality,
              donor information, and embryo transfer parameters.
            </p>
            <p className="mt-3 max-w-2xl text-xs text-[var(--pp-muted)]/90">
              <Info className="mr-1 inline h-3 w-3" />
              Decision support only. Final reproductive decisions should remain with qualified veterinary and embryology professionals.
            </p>
          </motion.div>

          <div className="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard icon={Activity} label="Total Predictions" value="248" caption="Predictions generated this month" delay={0.05} />
            <KpiCard icon={TrendingUp} label="Average Predicted Success" value="54%" caption="Based on recent ET records" delay={0.12} />
            <KpiCard icon={CheckCircle2} label="Confirmed Pregnancy Rate" value="47%" caption="From updated diagnosis outcomes" delay={0.19} />
            <KpiCard icon={ShieldCheck} label="High Confidence Cases" value="132" caption="Predictions with strong data quality" delay={0.26} />
          </div>

          {initLoading && (
            <div className="mb-6 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-medium text-sky-700">
              Loading protocols, technicians, and model metadata...
            </div>
          )}

          {initError && (
            <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800">
              {initError}. You can still fill the form; live protocol/technician lists need the backend running.
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
            <div className="space-y-6 lg:col-span-3">
              <SectionShell icon={ClipboardCheck} title="Case Information" helper="Basic embryo transfer case details. This record can be saved under your organization." index={0}>
                <Field label="Case ID" helper="Unique identifier for this embryo transfer case.">
                  <TextInput value={form.caseId} onChange={setField("caseId")} placeholder="ET-2026-00124" />
                </Field>
                <Field label="Organization" helper="Auto-linked from your logged-in profile.">
                  <div className="flex h-11 items-center justify-between rounded-xl border border-[var(--pp-border)] bg-[var(--pp-foam)]/60 px-3">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Building2 className="h-4 w-4 text-[var(--pp-primary)]" />
                      DayZee Farms
                    </div>
                    <span className="rounded-full bg-[var(--pp-sage)]/30 px-2.5 py-1 text-xs">Assigned</span>
                  </div>
                </Field>
                <Field label="Embryo Transfer Date">
                  <div className="relative">
                    <CalendarDays className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--pp-muted)]" />
                    <input type="date" className="pp-input pl-9" value={form.transferDate} onChange={(event) => setField("transferDate")(event.target.value)} />
                  </div>
                </Field>
                <Field label="ET Specialist">
                  <div className="flex h-11 items-center gap-2 rounded-xl border border-[var(--pp-border)] bg-white/45 px-3 text-sm">
                    <UserRound className="h-4 w-4 text-[var(--pp-primary)]" />
                    {user?.full_name || user?.username || "Logged-in specialist"}
                  </div>
                </Field>
                <Field label="Case Status">
                  <SelectField value={form.status} onValueChange={setField("status")} placeholder="Select status" options={["Draft", "Ready for Prediction", "Prediction Generated", "Outcome Pending", "Outcome Updated", "Archived"]} />
                </Field>
              </SectionShell>

              <SectionShell icon={Stethoscope} title="Recipient Information" helper="Recipient health and reproductive condition are critical for pregnancy success." index={1}>
                <Field label="Recipient ID" helper="Required to generate a case-level prediction.">
                  <TextInput value={form.recipientId} onChange={setField("recipientId")} placeholder="REC-0345" />
                </Field>
                <Field label="Species">
                  <SelectField value={form.species} onValueChange={setField("species")} placeholder="Select species" options={["Cattle", "Buffalo", "Goat", "Sheep", "Other"]} />
                </Field>
                <Field label="Recipient Breed">
                  <SelectField value={form.breed} onValueChange={setField("breed")} placeholder="Select breed" options={["Holstein Friesian", "Sahiwal", "Jersey", "Brahman", "Crossbred", "Nili Ravi", "Kundi", "Other"]} />
                </Field>
                <Field label="Age" helper="Approximate age in years.">
                  <TextInput type="number" min="0" step="0.5" value={form.age} onChange={setField("age")} placeholder="4.5" />
                </Field>
                <Field label="Body Condition Score">
                  <SelectField value={form.bcs} onValueChange={setField("bcs")} placeholder="Select BCS" options={["1.0", "1.5", "2.0", "2.5", "3.0", "3.5", "4.0", "4.5", "5.0"]} />
                </Field>
                <Field label="Reproductive History">
                  <SelectField value={form.history} onValueChange={setField("history")} placeholder="Select history" options={["Previously pregnant", "Recently calved", "Maiden heifer", "Repeated failure", "Abortion history", "Unknown"]} />
                </Field>
              </SectionShell>

              <SectionShell icon={Droplets} title="Synchronization & CL Status" helper="Corpus luteum quality, size, and timing drive much of the biological signal." index={2}>
                <Field label="Synchronization Protocol">
                  <SelectField
                    value={form.syncProtocol}
                    onValueChange={setField("syncProtocol")}
                    placeholder="Select protocol"
                    options={protocols.length ? protocols.map((protocol) => protocol.name) : ["CIDR", "Ovsynch", "Natural Heat", "PGF", "Unknown"]}
                  />
                </Field>
                <Field label="Days Post Estrus">
                  <TextInput type="number" min="0" value={form.daysPostEstrus} onChange={setField("daysPostEstrus")} placeholder="7" />
                </Field>
                <Field label="CL Present">
                  <SelectField value={form.clPresent} onValueChange={setField("clPresent")} placeholder="Select CL status" options={["Yes", "No", "Unclear"]} />
                </Field>
                <Field label="CL Side">
                  <SelectField value={form.clSide} onValueChange={setField("clSide")} placeholder="Select side" options={["Left", "Right"]} />
                </Field>
                <Field label="CL Size (mm)" helper="Required by the prediction API.">
                  <TextInput type="number" min="0" max="50" step="0.1" value={form.clSize} onChange={setField("clSize")} placeholder="18.5" />
                </Field>
                <Field label="CL Quality">
                  <SelectField value={form.clQuality} onValueChange={setField("clQuality")} placeholder="Select quality" options={["Excellent", "Good", "Fair", "Poor", "Unknown"]} />
                </Field>
                <Field label="Uterine Tone">
                  <SelectField value={form.uterineTone} onValueChange={setField("uterineTone")} placeholder="Select tone" options={["Excellent", "Good", "Fair", "Poor", "Unknown"]} />
                </Field>
              </SectionShell>

              <SectionShell icon={FlaskConical} title="Embryo Information" helper="Embryo stage, grade, preservation, and age are mapped to the live prediction payload." index={3}>
                <Field label="Embryo ID" helper="Required to generate case-level decision support.">
                  <TextInput value={form.embryoId} onChange={setField("embryoId")} placeholder="EMB-0456" />
                </Field>
                <Field label="Fresh / Frozen">
                  <SelectField value={form.embryoType} onValueChange={setField("embryoType")} placeholder="Select type" options={["Fresh", "Frozen"]} />
                </Field>
                <Field label="Embryo Stage" helper="Required by the prediction API.">
                  <SelectField value={form.embryoStage} onValueChange={setField("embryoStage")} placeholder="Select stage" options={["4", "5", "6", "7", "8"]} />
                </Field>
                <Field label="Embryo Grade">
                  <SelectField value={form.embryoGrade} onValueChange={setField("embryoGrade")} placeholder="Select grade" options={["1", "2", "3", "4"]} />
                </Field>
                <Field label="Embryo Day / Days OPU to ET">
                  <TextInput type="number" min="0" value={form.embryoDay} onChange={setField("embryoDay")} placeholder="7" />
                </Field>
              </SectionShell>

              <SectionShell icon={Dna} title="Donor & Sire Information" helper="Genetic and semen features can refine the prediction when available." index={4}>
                <Field label="Donor ID">
                  <TextInput value={form.donorId} onChange={setField("donorId")} placeholder="DON-0081" />
                </Field>
                <Field label="Donor Breed">
                  <TextInput value={form.donorBreed} onChange={setField("donorBreed")} placeholder="Angus / Holstein / Crossbred" />
                </Field>
                <Field label="Donor BW EPD">
                  <TextInput type="number" step="0.01" value={form.donorBwEpd} onChange={setField("donorBwEpd")} placeholder="1.25" />
                </Field>
                <Field label="Sire ID / Name">
                  <TextInput value={form.sireId} onChange={setField("sireId")} placeholder="SIRE-112" />
                </Field>
                <Field label="Sire BW EPD">
                  <TextInput type="number" step="0.01" value={form.sireBwEpd} onChange={setField("sireBwEpd")} placeholder="2.10" />
                </Field>
                <Field label="Semen Type">
                  <SelectField value={form.semenType} onValueChange={setField("semenType")} placeholder="Select semen type" options={["Conventional", "Sexed", "Sexed Female", "Unknown"]} />
                </Field>
              </SectionShell>

              <SectionShell icon={Leaf} title="Transfer Procedure" helper="Procedure quality and transfer difficulty can affect embryo survival and implantation." index={5}>
                <Field label="Technician">
                  <SelectField
                    value={form.technicianName}
                    onValueChange={setField("technicianName")}
                    placeholder="Select technician"
                    options={technicians.length ? technicians.map((technician) => technician.name) : ["ET Team A", "ET Team B", "ET Team C", user?.full_name || user?.username || "Unknown"]}
                  />
                </Field>
                <Field label="Transfer Side">
                  <SelectField value={form.transferSide} onValueChange={setField("transferSide")} placeholder="Select side" options={["Ipsilateral to CL", "Contralateral to CL", "Not recorded"]} />
                </Field>
                <Field label="Transfer Difficulty">
                  <SelectField value={form.transferDifficulty} onValueChange={setField("transferDifficulty")} placeholder="Select difficulty" options={["Easy", "Moderate", "Difficult", "Very difficult", "Not recorded"]} />
                </Field>
                <Field label="Environmental Condition">
                  <SelectField value={form.environment} onValueChange={setField("environment")} placeholder="Select condition" options={["Normal", "Heat stress", "Cold stress", "Transport stress", "High humidity", "Unknown"]} />
                </Field>
                <Field label="Customer ID" full>
                  <TextInput value={form.customerId} onChange={setField("customerId")} placeholder="DZF / client identifier" />
                </Field>
              </SectionShell>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4 }}
                className="pp-glass-card sticky bottom-4 z-30 flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4"
              >
                <div className="text-xs text-[var(--pp-muted)]">
                  {canGenerate ? "Ready to generate prediction." : "Enter Recipient ID, Embryo ID, CL size, and Embryo Stage."}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" className="pp-button pp-button-ghost" onClick={clearForm}>
                    <RotateCcw className="h-4 w-4" /> Clear
                  </button>
                  <button type="button" className="pp-button pp-button-outline">
                    <Save className="h-4 w-4" /> Save Draft
                  </button>
                  <button type="button" onClick={generatePrediction} disabled={loading} className="pp-button pp-button-primary">
                    <Sparkles className="h-4 w-4" />
                    {loading ? "Analyzing..." : "Generate Prediction"}
                  </button>
                </div>
              </motion.div>

              {error && (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                  <AlertCircle className="mr-2 inline h-4 w-4" />
                  {error}
                </div>
              )}
            </div>

            <div className="lg:col-span-2">
              <div className="lg:sticky lg:top-24">
                <ResultPanel
                  loading={loading}
                  prediction={prediction}
                  confidenceLabel={confidenceLabel}
                  probabilityTone={probabilityTone}
                  dataQuality={dataQuality}
                  onOpenAssistant={() => setAssistantOpen(true)}
                  onDecisionSupport={() => {
                    if (prediction?.prediction_id) navigate(`/app/predictions/${prediction.prediction_id}/decision-support`);
                  }}
                />
              </div>
            </div>
          </div>

          <RecentPredictions
            onUpdateOutcome={(caseId) => {
              setOutcomeCase(caseId);
              setOutcomeOpen(true);
            }}
          />
        </main>

        <OutcomeModal open={outcomeOpen} caseId={outcomeCase} onOpenChange={setOutcomeOpen} />

        <footer className="border-t border-[var(--pp-border)] py-8 text-center text-xs text-[var(--pp-muted)]">
          Ovulite · Multi-tenant embryo transfer decision support · Data isolated to DayZee Farms
        </footer>
      </div>

      <button type="button" className="pp-assistant-trigger" onClick={() => setAssistantOpen((open) => !open)}>
        {assistantOpen ? <Sparkles className="h-6 w-6" /> : <Brain className="h-6 w-6" />}
      </button>

      {assistantOpen && (
        <div className="pp-assistant-popover">
          <PredictionAssistantChatbox prediction={prediction} loading={loading} />
        </div>
      )}
    </>
  );
}

function ResultPanel({
  loading,
  prediction,
  confidenceLabel,
  probabilityTone,
  dataQuality,
  onOpenAssistant,
  onDecisionSupport,
}: {
  loading: boolean;
  prediction: PredictionResult | null;
  confidenceLabel: string;
  probabilityTone: { label: string; tone: "success" | "sage" | "warning" | "destructive" } | null;
  dataQuality: DataQuality;
  onOpenAssistant: () => void;
  onDecisionSupport: () => void;
}) {
  const probabilityPct = prediction ? Math.round(prediction.probability * 100) : 0;

  return (
    <div className="pp-glass-card overflow-hidden rounded-2xl">
      <div className="border-b border-[var(--pp-border)] bg-gradient-to-br from-[var(--pp-foam)] to-transparent px-6 py-5">
        <div className="flex items-center gap-2">
          <Baby className="h-5 w-5 text-[var(--pp-primary)]" />
          <h3 className="font-display text-2xl text-[var(--pp-foreground)]">Prediction Result</h3>
        </div>
      </div>

      <div className="p-6">
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center py-16 text-center">
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }} className="grid h-16 w-16 place-items-center rounded-full bg-[var(--pp-foam)]">
                <Sparkles className="h-7 w-7 text-[var(--pp-primary)]" />
              </motion.div>
              <p className="mt-5 text-sm text-[var(--pp-muted)]">Analyzing recipient, embryo, donor, and transfer parameters...</p>
            </motion.div>
          ) : !prediction ? (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center py-14 text-center">
              <div className="grid h-16 w-16 place-items-center rounded-full bg-[var(--pp-foam)]">
                <Baby className="h-7 w-7 text-[var(--pp-primary)]/70" />
              </div>
              <p className="mt-5 text-sm font-medium text-[var(--pp-foreground)]">No prediction generated yet</p>
              <p className="mt-2 max-w-xs text-xs text-[var(--pp-muted)]">
                Complete the embryo transfer form to view pregnancy probability, confidence interval, and key influencing factors.
              </p>
            </motion.div>
          ) : (
            <motion.div key="result" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="space-y-6">
              {prediction.is_ood && (
                <div className="rounded-xl border border-[var(--pp-warning)] bg-[var(--pp-warning)]/10 p-4">
                  <div className="flex items-center gap-2 font-medium text-[var(--pp-foreground)]">
                    <AlertTriangle className="h-4 w-4 text-[var(--pp-warning)]" /> Lower-reliability prediction
                  </div>
                  <ul className="mt-2 list-disc pl-5 text-sm text-[var(--pp-muted)]">
                    {(prediction.ood_reasons ?? []).map((reason) => <li key={reason}>{reason}</li>)}
                  </ul>
                </div>
              )}
              <div>
                <div className="text-xs uppercase tracking-widest text-[var(--pp-muted)]">Pregnancy Success Probability</div>
                <div className="mt-2 flex items-end gap-3">
                  <motion.div initial={{ scale: 0.85, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="font-display text-6xl leading-none text-[var(--pp-foreground)]">
                    {probabilityPct}%
                  </motion.div>
                  {probabilityTone && <span className={`pp-badge pp-badge-${probabilityTone.tone}`}>{probabilityTone.label}</span>}
                </div>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-[var(--pp-muted-bg)]">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${probabilityPct}%` }} transition={{ duration: 0.9 }} className="h-full pp-gradient-primary" />
                </div>
                <p className="mt-3 text-sm text-[var(--pp-muted)]">
                  95% confidence interval: {(prediction.confidence_lower * 100).toFixed(0)}% - {(prediction.confidence_upper * 100).toFixed(0)}%.
                </p>
              </div>

              <div className="rounded-xl border border-[var(--pp-border)] bg-white/45 p-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium text-[var(--pp-foreground)]">Prediction Confidence</div>
                  <span className="rounded-full bg-[var(--pp-ocean)]/15 px-2.5 py-1 text-xs text-[var(--pp-ocean)]">{confidenceLabel}</span>
                </div>
                <div className="mt-2 font-display text-3xl text-[var(--pp-ocean)]">{dataQuality.confidence}%</div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--pp-muted-bg)]">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${dataQuality.confidence}%` }} transition={{ duration: 0.8, delay: 0.2 }} className="h-full bg-[var(--pp-ocean)]" />
                </div>
              </div>

              <FactorsBlock title="Positive Factors" items={derivePositiveFactors(prediction)} tone="pos" />
              <FactorsBlock title="Risk Factors" items={deriveRiskFactors(prediction)} tone="neg" />

              {prediction.plain_language_summary && (
                <div className="rounded-xl border border-[var(--pp-border)] bg-white/45 p-4 text-sm text-[var(--pp-foreground)]/90">
                  {prediction.plain_language_summary}
                </div>
              )}

              {(prediction.similar_cases?.length ?? 0) > 0 && (
                <div className="rounded-xl border border-[var(--pp-border)] bg-white/45 p-4">
                  <div className="mb-2 text-sm font-medium text-[var(--pp-foreground)]">Similar historical cases</div>
                  <ul className="space-y-1 text-sm text-[var(--pp-muted)]">
                    {prediction.similar_cases!.map((item) => (
                      <li key={`${item.transfer_reference}-${item.et_date}`}>Transfer {item.transfer_reference}: {item.outcome ? "Pregnant" : "Open"}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="rounded-xl border border-[var(--pp-sage)]/40 bg-[var(--pp-sage)]/10 p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-[var(--pp-foreground)]">
                  <Sparkles className="h-4 w-4 text-[var(--pp-primary)]" />
                  AI-Assisted Recommendation
                </div>
                <p className="mt-2 text-sm text-[var(--pp-foreground)]/90">{recommendationFor(probabilityPct)}</p>
              </div>

              <div className="rounded-xl border border-[var(--pp-border)] bg-white/45 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <div className="text-sm font-medium text-[var(--pp-foreground)]">Data Quality Check</div>
                  <span className="rounded-full bg-[var(--pp-foam)] px-2.5 py-1 text-xs text-[var(--pp-primary)]">{dataQuality.label}</span>
                </div>
                <ul className="space-y-1.5">
                  {dataQuality.items.map((item) => (
                    <li key={item.name} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2 text-[var(--pp-foreground)]/90">
                        {item.complete ? <CheckCircle2 className="h-4 w-4 text-[var(--pp-success)]" /> : <AlertTriangle className="h-4 w-4 text-[var(--pp-warning)]" />}
                        {item.name}
                      </span>
                      <span className={`text-xs ${item.complete ? "text-[var(--pp-success)]" : "text-[var(--pp-warning)]"}`}>{item.complete ? "Complete" : "Partial"}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="flex flex-wrap gap-2">
                <button type="button" className="pp-button pp-button-primary">
                  <Save className="h-4 w-4" /> Save Prediction
                </button>
                <button type="button" className="pp-button pp-button-outline">
                  <Download className="h-4 w-4" /> Download Report
                </button>
                <button type="button" className="pp-button pp-button-ghost" onClick={onOpenAssistant}>
                  Ask Assistant
                </button>
                {prediction.prediction_id && (
                  <button type="button" className="pp-button pp-button-ghost" onClick={onDecisionSupport}>
                    Decision Support
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function FactorsBlock({ title, items, tone }: { title: string; items: string[]; tone: "pos" | "neg" }) {
  const positive = tone === "pos";
  return (
    <div className="rounded-xl border border-[var(--pp-border)] bg-white/45 p-4">
      <div className="mb-2 text-sm font-medium text-[var(--pp-foreground)]">{title}</div>
      {items.length === 0 ? (
        <div className="text-xs text-[var(--pp-muted)]">None detected.</div>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {items.map((factor) => (
            <motion.span
              key={factor}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs ${positive ? "border-green-200 bg-green-50 text-green-700" : "border-red-200 bg-red-50 text-red-700"}`}
            >
              {positive ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}
              {factor}
            </motion.span>
          ))}
        </div>
      )}
    </div>
  );
}

function RecentPredictions({ onUpdateOutcome }: { onUpdateOutcome: (caseId: string) => void }) {
  const outcomeStyle: Record<RecentRow["outcome"], string> = {
    Pending: "border-amber-200 bg-amber-50 text-amber-800",
    Pregnant: "border-green-200 bg-green-50 text-green-700",
    "Not Pregnant": "border-red-200 bg-red-50 text-red-700",
  };

  return (
    <motion.section initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.1 }} transition={{ duration: 0.5 }} className="mt-12">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h2 className="font-display text-3xl text-[var(--pp-foreground)]">Recent Pregnancy Predictions</h2>
          <p className="mt-1 text-sm text-[var(--pp-muted)]">Latest ET case predictions from your organization.</p>
        </div>
      </div>

      <div className="pp-glass-card overflow-hidden rounded-2xl">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="bg-[var(--pp-foam)]/40 text-left">
                {["Case ID", "Recipient", "Embryo", "Date", "Probability", "Confidence", "Outcome", "Actions"].map((heading) => (
                  <th key={heading} className="px-4 py-3 font-semibold text-[var(--pp-foreground)]">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {recentData.map((row) => (
                <tr key={row.caseId} className="border-t border-[var(--pp-border)] hover:bg-[var(--pp-foam)]/25">
                  <td className="px-4 py-3 font-medium text-[var(--pp-foreground)]">{row.caseId}</td>
                  <td className="px-4 py-3">{row.recipient}</td>
                  <td className="px-4 py-3">{row.embryo}</td>
                  <td className="px-4 py-3 text-[var(--pp-muted)]">{row.date}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-[var(--pp-muted-bg)]">
                        <div className="h-full pp-gradient-primary" style={{ width: `${row.probability}%` }} />
                      </div>
                      <span className="font-medium">{row.probability}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3"><span className="rounded-full bg-[var(--pp-ocean)]/10 px-2.5 py-1 text-xs text-[var(--pp-ocean)]">{row.confidence}</span></td>
                  <td className="px-4 py-3"><span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs ${outcomeStyle[row.outcome]}`}><Circle className="h-2 w-2 fill-current" />{row.outcome}</span></td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <button type="button" className="pp-icon-button" title="View"><Eye className="h-4 w-4" /></button>
                      <button type="button" className="pp-icon-button" title="Edit"><Pencil className="h-4 w-4" /></button>
                      <button type="button" className="pp-table-button" onClick={() => onUpdateOutcome(row.caseId)}>Update Outcome</button>
                      <button type="button" className="pp-icon-button" title="Download"><Download className="h-4 w-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </motion.section>
  );
}

function OutcomeModal({
  open,
  onOpenChange,
  caseId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  caseId: string;
}) {
  const [date, setDate] = useState("");
  const [outcome, setOutcome] = useState("");
  const [method, setMethod] = useState("");
  const [notes, setNotes] = useState("");

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4 backdrop-blur-sm">
      <div className="pp-glass-card w-full max-w-lg rounded-3xl p-6">
        <h3 className="font-display text-2xl text-[var(--pp-foreground)]">Update Pregnancy Outcome</h3>
        <p className="mt-1 text-sm text-[var(--pp-muted)]">Case {caseId || "-"} · record the diagnosis outcome for this ET.</p>
        <div className="mt-6 grid grid-cols-1 gap-4">
          <Field label="Pregnancy Diagnosis Date">
            <TextInput type="date" value={date} onChange={setDate} />
          </Field>
          <Field label="Outcome">
            <SelectField value={outcome} onValueChange={setOutcome} placeholder="Select outcome" options={["Pregnant", "Not Pregnant", "Pregnancy Loss", "Recheck Required", "Unknown"]} />
          </Field>
          <Field label="Diagnosis Method">
            <SelectField value={method} onValueChange={setMethod} placeholder="Select method" options={["Ultrasound", "Rectal palpation", "Blood test", "Farm record", "Other"]} />
          </Field>
          <Field label="Notes">
            <textarea className="pp-input min-h-24 py-3" value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Add diagnosis notes..." />
          </Field>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" className="pp-button pp-button-ghost" onClick={() => onOpenChange(false)}>Cancel</button>
          <button
            type="button"
            className="pp-button pp-button-primary"
            onClick={() => {
              onOpenChange(false);
              setDate("");
              setOutcome("");
              setMethod("");
              setNotes("");
            }}
          >
            Save Outcome
          </button>
        </div>
      </div>
    </div>
  );
}

type DataQuality = {
  label: string;
  confidence: number;
  items: Array<{ name: string; complete: boolean }>;
};

function getDataQuality(form: FormState): DataQuality {
  const groups = [
    { name: "Recipient information", fields: [form.recipientId, form.species, form.breed, form.age, form.bcs, form.history] },
    { name: "Embryo information", fields: [form.embryoId, form.embryoType, form.embryoStage, form.embryoGrade, form.embryoDay] },
    { name: "CL and uterine status", fields: [form.clPresent, form.clSize, form.clQuality, form.uterineTone] },
    { name: "Donor/sire information", fields: [form.donorId, form.sireId] },
    { name: "Transfer procedure", fields: [form.transferSide, form.transferDifficulty, form.technicianName] },
    { name: "Environmental condition", fields: [form.environment] },
  ];

  const items = groups.map((group) => ({
    name: group.name,
    complete: group.fields.every((value) => value && value.trim().length > 0),
  }));

  const completeCount = items.filter((item) => item.complete).length;
  const label = completeCount === items.length
    ? "Excellent Data Quality"
    : completeCount >= 4
      ? "Good Data Quality"
      : completeCount >= 2
        ? "Incomplete Data"
        : "Low Reliability";

  return {
    label,
    confidence: Math.round(40 + (completeCount / items.length) * 55),
    items,
  };
}

function getConfidenceLabel(prediction: PredictionResult | null, fallbackConfidence: number) {
  if (!prediction) return "";
  if (fallbackConfidence >= 80) return "High Confidence";
  if (fallbackConfidence >= 60) return "Medium Confidence";
  return "Low Confidence";
}

function getProbabilityTone(probability: number) {
  if (probability >= 75) return { label: "High Probability", tone: "success" as const };
  if (probability >= 50) return { label: "Moderate Probability", tone: "sage" as const };
  if (probability >= 30) return { label: "Low to Moderate Probability", tone: "warning" as const };
  return { label: "Low Probability", tone: "destructive" as const };
}

function recommendationFor(probability: number) {
  if (probability >= 75) {
    return "This case shows favorable conditions for embryo transfer. Proceed with standard post-transfer monitoring and schedule pregnancy diagnosis according to farm protocol.";
  }
  if (probability >= 50) {
    return "This case has acceptable pregnancy potential, but some factors may reduce success. Review recipient condition, embryo handling, and environmental stress before final decision.";
  }
  return "This case shows multiple risk factors. Consider reviewing recipient eligibility or selecting an alternative recipient before proceeding.";
}

function derivePositiveFactors(prediction: PredictionResult) {
  const positive = prediction.shap_explanation.contributions
    .filter((contribution) => contribution.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 4)
    .map((contribution) => formatFeatureName(contribution.feature));

  return positive.length ? positive : prediction.probability >= 0.5 ? ["Overall predicted probability is favorable"] : [];
}

function deriveRiskFactors(prediction: PredictionResult) {
  const negative = prediction.shap_explanation.contributions
    .filter((contribution) => contribution.value < 0)
    .sort((a, b) => a.value - b.value)
    .slice(0, 4)
    .map((contribution) => formatFeatureName(contribution.feature));

  return negative.length ? negative : prediction.probability < 0.5 ? ["Overall predicted probability is below target"] : [];
}

function isModelInfo(value: unknown): value is ModelInfo {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return typeof candidate.model_name === "string" && typeof candidate.model_version === "string" && typeof candidate.n_features === "number";
}

function isPredictionResult(value: unknown): value is PredictionResult {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  const shap = candidate.shap_explanation as Record<string, unknown> | undefined;
  return (
    typeof candidate.probability === "number" &&
    typeof candidate.confidence_lower === "number" &&
    typeof candidate.confidence_upper === "number" &&
    typeof candidate.risk_band === "string" &&
    !!shap &&
    Array.isArray(shap.contributions)
  );
}

function getApiErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    if (typeof response?.data?.detail === "string") return response.data.detail;
  }
  return "Prediction failed";
}

function formatFeatureName(name: string): string {
  if (name.includes("__")) {
    const [base, value] = name.split("__");
    const label = base.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
    return `${label}: ${value}`;
  }
  return name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .replace("Cl ", "CL ")
    .replace("Bc ", "BC ")
    .replace("Bw ", "BW ")
    .replace("Opu", "OPU");
}

const predictionPageStyles = `
  .pp-page {
    --pp-background: #f4fbf8;
    --pp-foreground: #17332f;
    --pp-card: rgba(255,255,255,0.84);
    --pp-muted: #647a75;
    --pp-muted-bg: #e7f1ee;
    --pp-border: rgba(119, 154, 146, 0.28);
    --pp-primary: #17816f;
    --pp-sage: #9ab89e;
    --pp-ocean: #2e7f91;
    --pp-leaf: #9ae08f;
    --pp-foam: #e5f7ee;
    --pp-success: #1b9b67;
    --pp-warning: #d69e2e;
    --pp-destructive: #d94d4d;
    min-height: 100vh;
    color: var(--pp-foreground);
    background:
      radial-gradient(ellipse at top left, rgba(181, 233, 210, 0.55), transparent 45%),
      radial-gradient(ellipse at bottom right, rgba(159, 215, 224, 0.45), transparent 45%),
      var(--pp-background);
    border-radius: 28px;
    overflow: hidden;
  }

  .pp-glass-card {
    background: var(--pp-card);
    border: 1px solid var(--pp-border);
    box-shadow: 0 18px 48px -26px rgba(23, 72, 64, 0.45), inset 0 1px 0 rgba(255,255,255,0.68);
    backdrop-filter: blur(16px) saturate(1.15);
    -webkit-backdrop-filter: blur(16px) saturate(1.15);
  }

  .pp-gradient-primary {
    background: linear-gradient(135deg, #21a585, #2e7f91);
  }

  .pp-input {
    width: 100%;
    min-height: 44px;
    border-radius: 12px;
    border: 1px solid var(--pp-border);
    background: rgba(255,255,255,0.7);
    padding: 0 12px;
    color: var(--pp-foreground);
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
  }

  .pp-input:focus {
    border-color: rgba(33, 165, 133, 0.7);
    box-shadow: 0 0 0 5px rgba(33, 165, 133, 0.12);
    background: white;
  }

  textarea.pp-input {
    padding-top: 12px;
    padding-bottom: 12px;
  }

  .pp-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border-radius: 12px;
    padding: 10px 14px;
    font-size: 14px;
    font-weight: 700;
    transition: transform 0.2s, opacity 0.2s, background 0.2s;
  }

  .pp-button:hover:not(:disabled) {
    transform: translateY(-1px);
  }

  .pp-button:disabled {
    cursor: not-allowed;
    opacity: 0.65;
  }

  .pp-button-primary {
    border: 1px solid transparent;
    background: linear-gradient(135deg, #21a585, #2e7f91);
    color: white;
    box-shadow: 0 10px 30px -14px rgba(33, 165, 133, 0.8);
  }

  .pp-button-outline {
    border: 1px solid var(--pp-border);
    background: rgba(255,255,255,0.56);
    color: var(--pp-foreground);
  }

  .pp-button-ghost {
    border: 1px solid transparent;
    background: transparent;
    color: var(--pp-foreground);
  }

  .pp-icon-button,
  .pp-table-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    padding: 8px;
    color: var(--pp-foreground);
    transition: background 0.2s;
  }

  .pp-table-button {
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 700;
  }

  .pp-icon-button:hover,
  .pp-table-button:hover {
    background: rgba(23, 129, 111, 0.1);
  }

  .pp-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    border: 1px solid;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 700;
  }

  .pp-badge-success { border-color: rgba(27,155,103,0.3); background: rgba(27,155,103,0.12); color: var(--pp-success); }
  .pp-badge-sage { border-color: rgba(154,184,158,0.45); background: rgba(154,184,158,0.2); color: var(--pp-foreground); }
  .pp-badge-warning { border-color: rgba(214,158,46,0.38); background: rgba(214,158,46,0.15); color: #8a5a00; }
  .pp-badge-destructive { border-color: rgba(217,77,77,0.3); background: rgba(217,77,77,0.12); color: var(--pp-destructive); }

  .pp-assistant-trigger {
    position: fixed;
    bottom: 32px;
    right: 32px;
    z-index: 50;
    display: grid;
    height: 56px;
    width: 56px;
    place-items: center;
    border-radius: 999px;
    background: #17332f;
    color: white;
    box-shadow: 0 12px 28px rgba(0,0,0,0.22);
    transition: transform 0.2s;
  }

  .pp-assistant-trigger:hover {
    transform: scale(1.08);
  }

  .pp-assistant-popover {
    position: fixed;
    bottom: 100px;
    right: 32px;
    z-index: 49;
    width: min(380px, calc(100vw - 32px));
    max-height: 620px;
  }

  @media (max-width: 640px) {
    .pp-assistant-trigger {
      bottom: 18px;
      right: 18px;
    }
    .pp-assistant-popover {
      right: 16px;
      bottom: 84px;
    }
  }
`;
