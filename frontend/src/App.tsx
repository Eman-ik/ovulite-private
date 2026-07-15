import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/layouts/AppLayout";
import OvuliteLandingPage from "@/pages/OvuliteLandingPage";
import LoginPage from "@/pages/LoginPage";
import SignupPage from "@/pages/SignupPage";
import LoginDebugPage from "@/pages/LoginDebugPage";
import DashboardPage from "@/pages/DashboardPage";
import DataEntryPage from "@/pages/DataEntryPage";
import TransferFormPage from "@/pages/TransferFormPage";
import PredictionPage from "@/pages/PredictionPage";
import DecisionSupportPage from "@/pages/DecisionSupportPage";
import GradingPage from "@/pages/GradingPage";
import QCDashboardPage from "@/pages/QCDashboardPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import CaseRecordsPage from "@/pages/CaseRecordsPage";
import CaseDetailPage from "@/pages/CaseDetailPage";
import ModelPerformancePage from "@/pages/ModelPerformancePage";
import ReportsExportPage from "@/pages/ReportsExportPage";

import { ThemeProvider } from "@/contexts/ThemeContext";

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<OvuliteLandingPage />} />
            <Route path="/landing" element={<OvuliteLandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/login/debug" element={<LoginDebugPage />} />
            <Route path="/signup" element={<SignupPage />} />
            
            
            <Route element={<ProtectedRoute />}>
              <Route path="/app" element={<AppLayout />}>
                <Route index element={<DashboardPage />} />

<Route
  path="data-entry"
  element={
    <ProtectedRoute allowedRoles={["admin", "et team"]}>
      <DataEntryPage />
    </ProtectedRoute>
  }
/>

<Route
  path="data-entry/new"
  element={
    <ProtectedRoute allowedRoles={["admin", "et team"]}>
      <TransferFormPage />
    </ProtectedRoute>
  }
/>

<Route
  path="data-entry/:id"
  element={
    <ProtectedRoute allowedRoles={["admin", "et team"]}>
      <TransferFormPage />
    </ProtectedRoute>
  }
/>

<Route
  path="predictions"
  element={
    <ProtectedRoute allowedRoles={["admin", "et team"]}>
      <PredictionPage />
    </ProtectedRoute>
  }
/>

<Route
  path="predictions/:id/decision-support"
  element={
    <ProtectedRoute allowedRoles={["admin", "et team"]}>
      <DecisionSupportPage />
    </ProtectedRoute>
  }
/>

<Route
  path="embryo-grading"
  element={
    <ProtectedRoute allowedRoles={["admin", "embryologist"]}>
      <GradingPage />
    </ProtectedRoute>
  }
/>

<Route
  path="lab-qc"
  element={
    <ProtectedRoute allowedRoles={["admin", "embryologist"]}>
      <QCDashboardPage />
    </ProtectedRoute>
  }
/>

<Route
  path="analytics"
  element={
    <ProtectedRoute allowedRoles={["admin"]}>
      <AnalyticsPage />
    </ProtectedRoute>
  }
/>

<Route
  path="cases" element={<CaseRecordsPage />} />
<Route path="cases/:id" element={<CaseDetailPage />} />

<Route
  path="model-performance"
  element={
    <ProtectedRoute allowedRoles={["admin"]}>
      <ModelPerformancePage />
    </ProtectedRoute>
  }
/>

<Route
  path="reports"
  element={
    <ProtectedRoute allowedRoles={["admin", "embryologist", "et team"]}>
      <ReportsExportPage />
    </ProtectedRoute>
  }
/>
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
