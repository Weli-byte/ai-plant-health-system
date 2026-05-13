import { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getUser } from "@/lib/auth";

export function RequireProfile({ children }: { children: ReactNode }) {
  const user = getUser();
  if (!user?.profileComplete) return <Navigate to="/profile-setup" replace />;
  return <>{children}</>;
}
