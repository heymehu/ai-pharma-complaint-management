"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Complaints", icon: Sparkles },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
];

export function AppNav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 h-14 border-b border-violet-100/70 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex h-full max-w-[1600px] items-center gap-6 px-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-600 text-sm font-bold text-white shadow-sm shadow-violet-300">
            A
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold tracking-tight text-slate-900">
              AIVOA
            </p>
            <p className="text-[10px] uppercase tracking-wider text-violet-600">
              Complaint Management
            </p>
          </div>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-violet-50 text-violet-700"
                    : "text-slate-600 hover:bg-slate-50"
                )}
              >
                <l.icon className="h-3.5 w-3.5" />
                {l.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <span className="hidden text-xs text-slate-400 sm:inline">
            QA · Pharma SaaS
          </span>
        </div>
      </div>
    </header>
  );
}
