import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { Dashboard } from "./pages/Dashboard";
import { Keys } from "./pages/Keys";
import { Login } from "./pages/Login";

function Protected({ children }: { children?: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <main className="loading"><span className="spinner" />Loading gliccOps…</main>;
  }
  return user ? children ?? <Dashboard /> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected />} />
      <Route path="/keys" element={<Protected><Keys /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
