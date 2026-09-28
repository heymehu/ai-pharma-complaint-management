"use client";

import { Toaster } from "sonner";
import { AppNav } from "@/components/layout/app-nav";
import { WorkspaceProvider } from "@/components/complaint/workspace-provider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceProvider>
      <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-violet-50 via-white to-slate-50">
        <AppNav />
        <main>{children}</main>
      </div>
      <Toaster richColors position="top-right" />
    </WorkspaceProvider>
  );
}
