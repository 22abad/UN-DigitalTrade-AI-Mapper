import type { ReactNode } from "react";
import { AuthContext, useAuthProvider } from "../hooks/useAuth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const value = useAuthProvider();
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
