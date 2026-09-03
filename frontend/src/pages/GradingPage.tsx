import { useState, useCallback, useRef } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Upload, Microscope, Loader2, Images, Sparkles, Flame } from "lucide-react";

/* ─── Types ─────────────────────────────────────────────── */

interface GradeProbability {
  grade: number;
  label: string;
  probability: number;
}

interface GradePredictionResult {
  predicted_grade: number;
  predicted_label: string;
  confidence: number;
  probabilities: GradeProbability[];
  model_type: string;
  model_version: string;
  heatmap_available: boolean;
  caveats: string[];
}

interface GradePredictionWithHeatmapResult extends GradePredictionResult {
  heatmap_image_base64: string;
}

interface SimilarCaseMetadata {
  sequence_number: number | null;
  et_number: string | null;
  donor: string | null;
  donor_breed: string | null;
  et_date: string | null;
  embryo_stage: string | null;
  embryo_grade: string | null;
  fresh_or_frozen: string | null;
  technician_name: string | null;
  pregnancy_outcome: string | null;
}

interface SimilarCase {
  rank: number;
  filename: string;
  similarity: number;
  metadata: SimilarCaseMetadata;
}

interface SimilarCasesResult {
  matches: SimilarCase[];
  n_index_cases: number;
  model_type: string;
}

/* ─── Page Component ────────────────────────────────────── */

export default function GradingPage() {
  // Image state
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Embryologist's own manual assessment — recorded for the record, kept
  // separately attributable from the AI similarity tool below (FR-M4-08).
  // The "Manual Grade" here is entered by the embryologist; the AI never
  // assigns a grade of its own.
  const [embryoStage, setEmbryoStage] = useState("");
  const [manualGrade, setManualGrade] = useState("");
  const [donorBreed, setDonorBreed] = useState("");
  const [freshOrFrozen, setFreshOrFrozen] = useState("");
  const [technicianName, setTechnicianName] = useState("");

  // Result state — similarity search
  const [result, setResult] = useState<SimilarCasesResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  // Result state — AI grade prediction
  const [gradeResult, setGradeResult] = useState<GradePredictionResult | null>(null);
  const [gradeLoading, setGradeLoading] = useState(false);
  const [gradeError, setGradeError] = useState<string | null>(null);
  const [gradeUnavailable, setGradeUnavailable] = useState(false);
  const [heatmapBase64, setHeatmapBase64] = useState<string | null>(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);

  const [activeTab, setActiveTab] = useState<"grade" | "similar">("grade");

  /* ─── File handling ───────────────────────────────── */

  const handleFile = useCallback((file: File) => {
    setImageFile(file);
    setError(null);
    setUnavailable(false);
    setResult(null);
    setGradeResult(null);
    setGradeError(null);
    setGradeUnavailable(false);
    setHeatmapBase64(null);

    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target?.result as string);
    reader.readAsDataURL(file);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  /* ─── Submit ──────────────────────────────────────── */

  const handleFindSimilar = async () => {
    if (!imageFile) {
      setError("Please upload an image first");
      return;
    }

    setLoading(true);
    setError(null);
    setUnavailable(false);
    setActiveTab("similar");

    const formData = new FormData();
    formData.append("image", imageFile);
    formData.append("k", "5");

    try {
      const { data } = await api.post<SimilarCasesResult>(
        "/grade/similar-cases",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setResult(data);
    } catch (err: any) {
      if (err.response?.status === 503) {
        setUnavailable(true);
      } else {
        setError(err.response?.data?.detail || "Similarity search failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handlePredictGrade = async () => {
    if (!imageFile) {
      setGradeError("Please upload an image first");
      return;
    }

    setGradeLoading(true);
    setGradeError(null);
    setGradeUnavailable(false);
    setHeatmapBase64(null);
    setActiveTab("grade");

    const formData = new FormData();
    formData.append("image", imageFile);

    try {
      const { data } = await api.post<GradePredictionResult>(
        "/grade/embryo",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setGradeResult(data);
    } catch (err: any) {
      if (err.response?.status === 503) {
        setGradeUnavailable(true);
      } else {
        setGradeError(err.response?.data?.detail || "Grade prediction failed. Please try again.");
      }
    } finally {
      setGradeLoading(false);
    }
  };

  const handleShowHeatmap = async () => {
    if (!imageFile) return;

    setHeatmapLoading(true);
    setGradeError(null);

    const formData = new FormData();
    formData.append("image", imageFile);

    try {
      const { data } = await api.post<GradePredictionWithHeatmapResult>(
        "/grade/embryo-with-heatmap",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setGradeResult(data);
      setHeatmapBase64(data.heatmap_image_base64);
    } catch (err: any) {
      setGradeError(err.response?.data?.detail || "Heatmap generation failed. Please try again.");
    } finally {
      setHeatmapLoading(false);
    }
  };

  /* ─── Reset ───────────────────────────────────────── */

  const handleReset = () => {
    setImageFile(null);
    setImagePreview(null);
    setResult(null);
    setError(null);
    setUnavailable(false);
    setGradeResult(null);
    setGradeError(null);
    setGradeUnavailable(false);
    setHeatmapBase64(null);
    setEmbryoStage("");
    setManualGrade("");
    setDonorBreed("");
    setFreshOrFrozen("");
    setTechnicianName("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  /* ─── Render ──────────────────────────────────────── */

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary/15 p-2">
          <Microscope className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Embryo Grading & Similarity Assist</h1>
          <p className="text-muted-foreground">
            Upload a blastocyst image for an AI grade prediction, or find visually similar known cases
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ─── Left: Upload & Metadata ─── */}
        <div className="space-y-4">
          {/* Drop zone */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Upload Image</CardTitle>
              <CardDescription>
                Drag & drop or click to upload any image format
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors duration-200
                  ${isDragging ? "border-primary bg-primary/10" : "border-white/25 hover:border-primary/60"}
                  ${imagePreview ? "border-primary bg-primary/10" : ""}
                `}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="*"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFile(f);
                  }}
                />

                {imagePreview ? (
                  <div className="space-y-3">
                    <img
                      src={imagePreview}
                      alt="Embryo"
                      className="max-h-64 mx-auto rounded-lg shadow-md"
                    />
                    <p className="text-sm text-muted-foreground">
                      {imageFile?.name} ({((imageFile?.size ?? 0) / 1024).toFixed(1)} KB)
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
                    <p className="font-medium">Drop image here or click to browse</p>
                    <p className="text-sm text-muted-foreground">
                      Any image format, max 10MB
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Manual assessment form — the embryologist's own record, not sent to or produced by AI */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Your Assessment</CardTitle>
              <CardDescription>
                Recorded manually by the embryologist. This is your own grade, kept
                separate from the AI's prediction on the right (FR-M4-08) — the AI
                grade is decision support from a model trained on a published external
                dataset, not a replacement for your judgment.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="stage">Embryo Stage</Label>
                  <Select
                    id="stage"
                    value={embryoStage}
                    onChange={(e) => setEmbryoStage(e.target.value)}
                  >
                    <option value="">Select...</option>
                    {[4, 5, 6, 7, 8].map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="grade">Manual Grade</Label>
                  <Select
                    id="grade"
                    value={manualGrade}
                    onChange={(e) => setManualGrade(e.target.value)}
                  >
                    <option value="">Select...</option>
                    {[1, 2, 3, 4].map((g) => (
                      <option key={g} value={g}>{g}</option>
                    ))}
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="breed">Donor Breed</Label>
                <Input
                  id="breed"
                  placeholder="e.g. Holstein, Sahiwal"
                  value={donorBreed}
                  onChange={(e) => setDonorBreed(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="ff">Fresh or Frozen</Label>
                  <Select
                    id="ff"
                    value={freshOrFrozen}
                    onChange={(e) => setFreshOrFrozen(e.target.value)}
                  >
                    <option value="">Select...</option>
                    <option value="Fresh">Fresh</option>
                    <option value="Frozen">Frozen</option>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tech">Technician</Label>
                  <Input
                    id="tech"
                    placeholder="Name"
                    value={technicianName}
                    onChange={(e) => setTechnicianName(e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              className="flex-1"
              onClick={handlePredictGrade}
              disabled={!imageFile || gradeLoading}
            >
              {gradeLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Predicting...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Predict Grade
                </>
              )}
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              onClick={handleFindSimilar}
              disabled={!imageFile || loading}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Images className="w-4 h-4 mr-2" />
                  Find Similar Cases
                </>
              )}
            </Button>
            <Button variant="outline" onClick={handleReset}>
              Reset
            </Button>
          </div>

          {(error || gradeError) && (
            <div className="rounded-md border border-red-300/40 bg-red-500/10 p-3 text-sm text-red-100">
              {gradeError || error}
            </div>
          )}

          {unavailable && (
            <div className="rounded-md border border-amber-300/40 bg-amber-500/10 p-3 text-sm text-amber-100">
              The similarity model isn't built in this environment yet. An administrator
              needs to run SimCLR pretraining and build the embedding index before this
              tool can return results.
            </div>
          )}

          {gradeUnavailable && (
            <div className="rounded-md border border-amber-300/40 bg-amber-500/10 p-3 text-sm text-amber-100">
              The grade classifier isn't trained in this environment yet. An administrator
              needs to run `python -m ml.grading.train_real_grading` before this tool can
              return predictions.
            </div>
          )}
        </div>

        {/* ─── Right: Results ─── */}
        <div className="space-y-4">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "grade" | "similar")}>
            <TabsList>
              <TabsTrigger value="grade">AI Grade Prediction</TabsTrigger>
              <TabsTrigger value="similar">Similar Cases</TabsTrigger>
            </TabsList>

            <TabsContent value="grade">
              {gradeResult ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">AI Grade Prediction</CardTitle>
                    <CardDescription>
                      Decision support only — trained on a published external dataset
                      (Rocha et al. 2017), not on this organization's own embryo images.
                      Review alongside your own assessment before drawing conclusions.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div className="flex items-center justify-between rounded-lg border border-white/10 p-4">
                      <div>
                        <p className="text-sm text-muted-foreground">Predicted Grade</p>
                        <p className="text-2xl font-bold">{gradeResult.predicted_label}</p>
                      </div>
                      <Badge className="bg-primary text-white text-base px-3 py-1">
                        {(gradeResult.confidence * 100).toFixed(1)}% confidence
                      </Badge>
                    </div>

                    <div className="space-y-2">
                      {gradeResult.probabilities
                        .slice()
                        .sort((a, b) => a.grade - b.grade)
                        .map((p) => (
                          <div key={p.grade} className="space-y-1">
                            <div className="flex justify-between text-sm">
                              <span className="text-muted-foreground">{p.label}</span>
                              <span className="font-mono font-semibold">
                                {(p.probability * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="h-2 overflow-hidden rounded-full bg-white/15">
                              <div
                                className={`h-full rounded-full transition-all duration-700 ${
                                  p.grade === gradeResult.predicted_grade ? "bg-primary" : "bg-white/30"
                                }`}
                                style={{ width: `${Math.max(0, Math.min(1, p.probability)) * 100}%` }}
                              />
                            </div>
                          </div>
                        ))}
                    </div>

                    {gradeResult.heatmap_available && (
                      <div className="space-y-3">
                        {heatmapBase64 ? (
                          <div className="space-y-2">
                            <p className="text-sm font-medium flex items-center gap-1.5">
                              <Flame className="w-4 h-4 text-primary" />
                              Grad-CAM explanation
                            </p>
                            <img
                              src={`data:image/jpeg;base64,${heatmapBase64}`}
                              alt="Grad-CAM heatmap overlay"
                              className="max-h-64 mx-auto rounded-lg shadow-md"
                            />
                            <p className="text-xs text-muted-foreground text-center">
                              Warmer colors show the regions that most influenced the prediction.
                            </p>
                          </div>
                        ) : (
                          <Button
                            variant="outline"
                            className="w-full"
                            onClick={handleShowHeatmap}
                            disabled={heatmapLoading}
                          >
                            {heatmapLoading ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Generating heatmap...
                              </>
                            ) : (
                              <>
                                <Flame className="w-4 h-4 mr-2" />
                                Show Grad-CAM Explanation
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    )}

                    <div className="space-y-1 border-t border-white/10 pt-3">
                      {gradeResult.caveats.map((c, i) => (
                        <p key={i} className="text-xs text-muted-foreground italic">
                          {c}
                        </p>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card className="h-full flex items-center justify-center min-h-[300px]">
                  <CardContent className="text-center text-muted-foreground py-16">
                    <Sparkles className="w-16 h-16 mx-auto mb-4 opacity-20" />
                    <p className="text-lg font-medium">No prediction yet</p>
                    <p className="text-sm mt-1">
                      Upload an embryo image and click "Predict Grade" for an AI grade estimate
                    </p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="similar">
          {result ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Similar Known Cases</CardTitle>
                  <CardDescription>
                    Nearest visual matches among {result.n_index_cases} known cases, ranked by
                    embedding similarity. This is a reference tool, not a grade or outcome
                    prediction — review each match's context yourself before drawing conclusions.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {result.matches.length === 0 && (
                    <p className="text-sm text-muted-foreground">No similar cases found.</p>
                  )}
                  {result.matches.map((match) => (
                    <div
                      key={match.filename}
                      className="rounded-lg border border-white/10 p-4 space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">#{match.rank}</Badge>
                          <span className="font-mono text-sm text-muted-foreground">
                            {match.filename}
                          </span>
                        </div>
                        {match.metadata.pregnancy_outcome && (
                          <Badge
                            className={
                              match.metadata.pregnancy_outcome === "Pregnant"
                                ? "bg-primary text-white"
                                : "bg-white/15"
                            }
                          >
                            {match.metadata.pregnancy_outcome}
                          </Badge>
                        )}
                      </div>

                      <div className="space-y-1">
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Similarity</span>
                          <span className="font-mono font-semibold">
                            {(match.similarity * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-white/15">
                          <div
                            className="h-full rounded-full bg-primary transition-all duration-700"
                            style={{ width: `${Math.max(0, Math.min(1, match.similarity)) * 100}%` }}
                          />
                        </div>
                      </div>

                      {(match.metadata.donor ||
                        match.metadata.donor_breed ||
                        match.metadata.et_date ||
                        match.metadata.embryo_stage ||
                        match.metadata.technician_name) && (
                        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
                          {match.metadata.donor && (
                            <>
                              <dt>Donor</dt>
                              <dd className="text-right text-foreground">{match.metadata.donor}</dd>
                            </>
                          )}
                          {match.metadata.donor_breed && (
                            <>
                              <dt>Breed</dt>
                              <dd className="text-right text-foreground">{match.metadata.donor_breed}</dd>
                            </>
                          )}
                          {match.metadata.et_date && (
                            <>
                              <dt>ET Date</dt>
                              <dd className="text-right text-foreground">{match.metadata.et_date}</dd>
                            </>
                          )}
                          {match.metadata.embryo_stage && (
                            <>
                              <dt>Stage</dt>
                              <dd className="text-right text-foreground">{match.metadata.embryo_stage}</dd>
                            </>
                          )}
                          {match.metadata.technician_name && (
                            <>
                              <dt>Technician</dt>
                              <dd className="text-right text-foreground">{match.metadata.technician_name}</dd>
                            </>
                          )}
                        </dl>
                      )}

                      {!match.metadata.donor &&
                        !match.metadata.donor_breed &&
                        !match.metadata.et_date &&
                        !match.metadata.pregnancy_outcome && (
                          <p className="text-xs text-muted-foreground italic">
                            No historical record could be linked to this match.
                          </p>
                        )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </>
          ) : (
            <Card className="h-full flex items-center justify-center min-h-[300px]">
              <CardContent className="text-center text-muted-foreground py-16">
                <Images className="w-16 h-16 mx-auto mb-4 opacity-20" />
                <p className="text-lg font-medium">No results yet</p>
                <p className="text-sm mt-1">
                  Upload an embryo image and click "Find Similar Cases" to see visually
                  similar reference cases
                </p>
              </CardContent>
            </Card>
          )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
