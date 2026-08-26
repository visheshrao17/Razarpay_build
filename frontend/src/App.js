import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Runs from "./pages/Runs";
import RunSummary from "./pages/RunSummary";
import Matches from "./pages/Matches";
import MatchDetail from "./pages/MatchDetail";
import Exceptions from "./pages/Exceptions";
import Audit from "./pages/Audit";
import Report from "./pages/Report";

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null)
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-slate-500">
        Checking session…
      </div>
    );
  if (user === false) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" richColors />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Protected><Runs /></Protected>} />
          <Route path="/runs/:runId" element={<Protected><RunSummary /></Protected>} />
          <Route path="/runs/:runId/matches" element={<Protected><Matches /></Protected>} />
          <Route path="/runs/:runId/matches/:matchId" element={<Protected><MatchDetail /></Protected>} />
          <Route path="/runs/:runId/exceptions" element={<Protected><Exceptions /></Protected>} />
          <Route path="/runs/:runId/audit" element={<Protected><Audit /></Protected>} />
          <Route path="/runs/:runId/report" element={<Protected><Report /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
