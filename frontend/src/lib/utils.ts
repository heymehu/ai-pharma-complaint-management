import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("aivoa_token") : null;
  const headers: HeadersInit = {
    ...(options.body instanceof FormData
      ? {}
      : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/pdf")) {
    return (await res.blob()) as T;
  }
  return res.json();
}

export function statusColor(status: string) {
  const map: Record<string, string> = {
    pending: "bg-amber-100 text-amber-800 border-amber-200",
    under_review: "bg-sky-100 text-sky-800 border-sky-200",
    investigation: "bg-violet-100 text-violet-800 border-violet-200",
    capa: "bg-orange-100 text-orange-800 border-orange-200",
    closed: "bg-emerald-100 text-emerald-800 border-emerald-200",
  };
  return map[status] || "bg-slate-100 text-slate-700";
}

export function riskColor(risk: string) {
  const map: Record<string, string> = {
    low: "bg-emerald-50 text-emerald-700 border-emerald-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    high: "bg-orange-50 text-orange-700 border-orange-200",
    critical: "bg-rose-50 text-rose-700 border-rose-200",
  };
  return map[risk] || "bg-slate-50 text-slate-700";
}
