import { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getUser } from "@/lib/auth";

export function RequireAuth({ children }: { children: ReactNode }) {
  const user = getUser();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
