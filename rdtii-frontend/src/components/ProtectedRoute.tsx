import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getStoredToken } from "../hooks/useAuth";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  if (!getStoredToken()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
