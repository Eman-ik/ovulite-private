import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import confetti from "canvas-confetti";
import { 
  Download, FileText, Zap, Sparkles, Database, Info, 
  BarChart3, TrendingUp, CheckCircle2
} from "lucide-react";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ReportsTab = "generate" | "templates" | "exports";

export default function ReportsExportPage() {
  const [activeTab, setActiveTab] = useState<ReportsTab>("generate");
  
  const [reportType, setReportType] = useState("summary");
  const [exportFormat, setExportFormat] = useState("pdf");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [includeAnalytics, setIncludeAnalytics] = useState(true);
  const [includePredictions, setIncludePredictions] = useState(true);
  const [includeQC, setIncludeQC] = useState(true);
  const [includeAuditTrail, setIncludeAuditTrail] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [showInfoModal, setShowInfoModal] = useState(false);

  // Mint & Glass Theme Colors
  const mintBg = "#F0F4F4";
  const deepGreen = "#004D40";
  const emeraldMint = "#66BB6A";

  const handleGenerateReport = async () => {
    setLoading(true);
    setError(null);

    // Simulate API call
    setTimeout(() => {
      setLoading(false);
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
        colors: [emeraldMint, deepGreen, "#ffffff"]
      });
      setShowSuccessModal(true);
    }, 1200);
  };

  const reportTypes = [
    { id: "summary", name: "Summary Report", icon: BarChart3, color: "from-emerald-500 to-teal-600" },
    { id: "detailed", name: "Detailed Report", icon: FileText, color: "from-teal-600 to-cyan-600" },
    { id: "analytics", name: "Analytics Report", icon: TrendingUp, color: "from-cyan-500 to-emerald-500" },
  ];

  const exportFormats = [
    { id: "pdf", name: "PDF", icon: FileText, color: "text-rose-600" },
    { id: "excel", name: "Excel", icon: Download, color: "text-emerald-600" },
    { id: "csv", name: "CSV", icon: Database, color: "text-amber-600" },
  ];

  return (
    <div className="min-h-screen" style={{ background: `linear-gradient(to bottom right, ${mintBg}, #E0F2F1)` }}>
      <div className="max-w-[1600px] mx-auto p-6 lg:p-10 space-y-8">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-between items-start"
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-xl shadow-emerald-500/20">
              <FileText className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-[#1A202C]">Reports & Export</h1>
              <p className="text-[#475569] mt-1">Professional reports with glassmorphism aesthetics</p>
            </div>
          </div>

          <Button 
            onClick={() => setShowInfoModal(true)}
            variant="outline"
            className="border-emerald-200 hover:bg-emerald-50"
          >
            <Info className="w-4 h-4 mr-2" /> Help
          </Button>
        </motion.div>

        {/* Tabs */}
        <div className="inline-flex bg-white/70 backdrop-blur-xl border border-white rounded-3xl p-1.5 shadow-xl">
          {[
            { id: "generate", label: "Generate Report", icon: Zap },
            { id: "templates", label: "Templates", icon: FileText },
            { id: "exports", label: "Bulk Exports", icon: Database },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as ReportsTab)}
              className={`px-8 py-3 rounded-2xl font-medium flex items-center gap-2 transition-all ${
                activeTab === tab.id 
                  ? "bg-gradient-to-r from-[#004D40] to-emerald-700 text-white shadow-lg" 
                  : "text-[#475569] hover:bg-white/50"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <AnimatePresence mode="wait">
          {/* GENERATE TAB */}
          {activeTab === "generate" && (
            <motion.div
              key="generate"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="grid grid-cols-1 lg:grid-cols-5 gap-8"
            >
              <div className="lg:col-span-3">
                <Card className="bg-white/80 backdrop-blur-2xl border border-white/60 shadow-2xl">
                  <CardHeader>
                    <CardTitle className="text-2xl text-[#1A202C]">Create Custom Report</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-8">
                    {/* Report Type */}
                    <div>
                      <label className="text-sm font-semibold text-[#334155] mb-4 block">Report Type</label>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {reportTypes.map((type) => (
                          <motion.button
                            key={type.id}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => setReportType(type.id)}
                            className={`p-6 rounded-3xl border transition-all ${
                              reportType === type.id 
                                ? "border-emerald-600 bg-emerald-50 shadow-md" 
                                : "border-white/60 hover:border-emerald-200"
                            }`}
                          >
                            <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${type.color} flex items-center justify-center mb-4`}>
                              <type.icon className="w-6 h-6 text-white" />
                            </div>
                            <p className="font-semibold text-[#1A202C]">{type.name}</p>
                          </motion.button>
                        ))}
                      </div>
                    </div>

                    {/* Format */}
                    <div>
                      <label className="text-sm font-semibold text-[#334155] mb-4 block">Export Format</label>
                      <div className="grid grid-cols-3 gap-4">
                        {exportFormats.map((fmt) => (
                          <motion.button
                            key={fmt.id}
                            whileHover={{ scale: 1.03 }}
                            onClick={() => setExportFormat(fmt.id)}
                            className={`p-5 rounded-3xl border text-center transition-all ${
                              exportFormat === fmt.id 
                                ? "border-emerald-600 bg-white shadow" 
                                : "border-white/60 hover:border-emerald-200"
                            }`}
                          >
                            <fmt.icon className={`mx-auto mb-2 w-8 h-8 ${fmt.color}`} />
                            <p className="font-medium">{fmt.name}</p>
                          </motion.button>
                        ))}
                      </div>
                    </div>

                    {/* Date Range + Content Options */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                      <div>
                        <label className="text-sm font-semibold text-[#334155] mb-3 block">Date Range</label>
                        <div className="space-y-4">
                          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="bg-white" />
                          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="bg-white" />
                        </div>
                      </div>

                      <div>
                        <label className="text-sm font-semibold text-[#334155] mb-3 block">Include</label>
                        <div className="space-y-3">
                          {[
                            { label: "Analytics & KPIs", checked: includeAnalytics, setter: setIncludeAnalytics },
                            { label: "Predictions", checked: includePredictions, setter: setIncludePredictions },
                            { label: "QC Analysis", checked: includeQC, setter: setIncludeQC },
                            { label: "Audit Trail", checked: includeAuditTrail, setter: setIncludeAuditTrail },
                          ].map((item, i) => (
                            <label key={i} className="flex items-center gap-3 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={item.checked}
                                onChange={(e) => item.setter(e.target.checked)}
                                className="w-5 h-5 accent-emerald-600"
                              />
                              <span className="text-[#475569]">{item.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>

                    <Button
                      onClick={handleGenerateReport}
                      disabled={loading}
                      size="lg"
                      className="w-full h-14 text-lg bg-gradient-to-r from-[#004D40] to-emerald-700 hover:brightness-110"
                    >
                      {loading ? "Generating Report..." : "Generate & Download Report"}
                    </Button>
                  </CardContent>
                </Card>
              </div>

              {/* Right Sidebar Info */}
              <div className="lg:col-span-2">
                <Card className="bg-white/70 backdrop-blur-2xl border border-white/60 h-full">
                  <CardContent className="pt-8">
                    <h3 className="font-semibold text-xl mb-6 flex items-center gap-3">
                      <Sparkles className="text-emerald-600" /> Quick Tips
                    </h3>
                    <div className="space-y-6 text-sm">
                      <p className="text-[#475569]">PDF is best for sharing and printing.</p>
                      <p className="text-[#475569]">Excel/CSV are ideal for further analysis.</p>
                      <p className="text-[#475569]">Include Audit Trail only when you need full traceability.</p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </motion.div>
          )}

          {/* Other tabs (Templates & Exports) can be expanded similarly with glass cards */}
          {activeTab === "templates" && (
            <div className="text-center py-20 text-[#475569]">
              Templates tab coming soon with glass cards...
            </div>
          )}
          {activeTab === "exports" && (
            <div className="text-center py-20 text-[#475569]">
              Bulk exports tab with glassmorphism cards...
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* Success Modal */}
      <AnimatePresence>
        {showSuccessModal && (
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center">
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="bg-white rounded-3xl p-10 max-w-md text-center shadow-2xl"
            >
              <CheckCircle2 className="w-20 h-20 text-emerald-600 mx-auto mb-6" />
              <h3 className="text-3xl font-bold text-[#1A202C] mb-2">Report Generated!</h3>
              <p className="text-[#475569] mb-8">Your report has been downloaded successfully.</p>
              <Button onClick={() => setShowSuccessModal(false)} className="w-full bg-emerald-700">
                Done
              </Button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Help Modal */}
      <AnimatePresence>
        {showInfoModal && (
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-3xl p-8 max-w-lg shadow-2xl"
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-emerald-100 flex items-center justify-center">
                  <Info className="w-6 h-6 text-emerald-700" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-[#1A202C]">Reports help</h3>
                  <p className="mt-3 text-[#475569]">
                    Choose a report type, export format, date range, and the sections to include. PDF is best for sharing; CSV and Excel are best for downstream analysis.
                  </p>
                </div>
              </div>
              <Button onClick={() => setShowInfoModal(false)} className="mt-8 w-full bg-emerald-700">
                Got it
              </Button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
