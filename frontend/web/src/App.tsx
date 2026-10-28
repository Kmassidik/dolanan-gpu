import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";

function Protected() {
  const { user, loading } = useAuth();
  if (loading) {
    return <main className="loading"><span className="spinner" />Loading gliccOps…</main>;
  }
  return user ? <Dashboard /> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
