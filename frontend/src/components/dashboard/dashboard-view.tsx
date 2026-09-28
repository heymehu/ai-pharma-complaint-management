"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  AlertOctagon,
  CheckCircle2,
  Clock3,
  Download,
  FolderOpen,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/utils";
import { downloadComplaintPdf } from "@/lib/complaint-pdf";
import type { DashboardStats, Complaint } from "@/lib/types";
import { Badge } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { statusColor, riskColor } from "@/lib/utils";

const COLORS = ["#8B5CF6", "#A78BFA", "#C4B5FD", "#DDD6FE", "#F5F3FF"];

type ComplaintDetail = Complaint & {
  complaint_source?: string;
  email?: string;
  phone?: string;
  strength?: string;
  manufacturing_date?: string;
  expiry_date?: string;
  quantity?: string;
  possible_root_cause?: string;
  affected_batches?: string;
  regulatory_concern?: string;
  impact?: string;
  confidence_score?: number;
  potential_issue?: string;
  suggested_test?: string;
  recommended_action?: string;
  ai_reasoning?: string;
};

export function DashboardView() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [deletingSelected, setDeletingSelected] = useState(false);

  useEffect(() => {
    Promise.all([
      api<DashboardStats>("/dashboard/stats"),
      api<Complaint[]>("/complaints?limit=8"),
    ])
      .then(([s, c]) => {
        setStats(s);
        setRecent(c);
      })
      .catch(() => {
        setStats({
          total_complaints: 0,
          open_complaints: 0,
          critical_complaints: 0,
          resolved: 0,
          avg_resolution_days: 0,
          by_status: {},
          by_month: [],
          by_risk: {},
        });
      })
      .finally(() => setLoading(false));
  }, []);

  const handleComplaintClick = async (complaint: Complaint) => {
    setDownloadingId(complaint.id);
    try {
      const detail = await api<ComplaintDetail>(`/complaints/${complaint.id}`);
      await downloadComplaintPdf(
        {
          ...detail,
          complaint_id: detail.complaint_id,
          status: detail.status,
        },
        `${detail.complaint_id}.pdf`
      );
      toast.success(`Downloaded ${detail.complaint_id} PDF`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "PDF download failed");
    } finally {
      setDownloadingId(null);
    }
  };

  const allRecentSelected =
    recent.length > 0 && recent.every((complaint) => selectedIds.has(complaint.id));

  const toggleComplaintSelection = (id: number) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAllRecent = () => {
    setSelectedIds(
      allRecentSelected ? new Set() : new Set(recent.map((complaint) => complaint.id))
    );
  };

  const deleteSelected = async () => {
    const ids = recent
      .filter((complaint) => selectedIds.has(complaint.id))
      .map((complaint) => complaint.id);
    if (!ids.length || deletingSelected) return;
    if (
      !window.confirm(
        `Permanently delete ${ids.length} selected complaint${ids.length === 1 ? "" : "s"}? This cannot be undone.`
      )
    ) {
      return;
    }

    setDeletingSelected(true);
    try {
      const result = await api<{ deleted_count: number }>(
        "/complaints/bulk-delete",
        { method: "POST", body: JSON.stringify({ ids }) }
      );
      const deletedIds = new Set(ids);
      setRecent((current) => current.filter((complaint) => !deletedIds.has(complaint.id)));
      setSelectedIds(new Set());
      toast.success(`Deleted ${result.deleted_count} complaint${result.deleted_count === 1 ? "" : "s"}`);

      const refreshedStats = await api<DashboardStats>("/dashboard/stats");
      setStats(refreshedStats);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Complaint deletion failed");
    } finally {
      setDeletingSelected(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto grid max-w-6xl gap-4 p-6 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-28 animate-pulse rounded-2xl bg-violet-100/60"
          />
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: "Total Complaints",
      value: stats?.total_complaints ?? 0,
      icon: FolderOpen,
      color: "text-violet-600 bg-violet-50",
    },
    {
      label: "Open",
      value: stats?.open_complaints ?? 0,
      icon: Clock3,
      color: "text-sky-600 bg-sky-50",
    },
    {
      label: "Critical",
      value: stats?.critical_complaints ?? 0,
      icon: AlertOctagon,
      color: "text-rose-600 bg-rose-50",
    },
    {
      label: "Resolved",
      value: stats?.resolved ?? 0,
      icon: CheckCircle2,
      color: "text-emerald-600 bg-emerald-50",
    },
  ];

  const statusData = Object.entries(stats?.by_status || {}).map(([name, value]) => ({
    name: name.replace("_", " "),
    value,
  }));
  const riskData = Object.entries(stats?.by_risk || {}).map(([name, value]) => ({
    name,
    value,
  }));

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Quality Dashboard
        </h1>
        <p className="text-sm text-slate-500">
          Complaint trends, risk heat, and resolution performance
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <div
            key={c.label}
            className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-slate-500">{c.label}</p>
              <span className={`rounded-xl p-2 ${c.color}`}>
                <c.icon className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-3 text-3xl font-semibold tracking-tight">
              {c.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold">Monthly Complaints</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats?.by_month?.length ? stats.by_month : [{ month: "—", count: 0 }]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E9D5FF" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#7C3AED" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold">Risk Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskData.length ? riskData : [{ name: "none", value: 1 }]}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={3}
                >
                  {(riskData.length ? riskData : [{ name: "none", value: 1 }]).map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {statusData.map((s) => (
              <Badge key={s.name} className={statusColor(s.name.replace(" ", "_"))}>
                {s.name}: {s.value}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold">Recent Complaints</h3>
            <p className="text-xs text-slate-500">
              Select complaints to delete, or click a row to download its PDF
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {selectedIds.size > 0 && (
              <Button
                type="button"
                variant="danger"
                size="sm"
                disabled={deletingSelected}
                onClick={deleteSelected}
              >
                <Trash2 aria-hidden="true" className="h-3.5 w-3.5" />
                {deletingSelected ? "Deleting..." : `Delete selected (${selectedIds.size})`}
              </Button>
            )}
            <p className="text-xs text-slate-500">
              Avg resolution: {stats?.avg_resolution_days ?? 0} days
            </p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-slate-500">
              <tr className="border-b border-slate-100">
                <th className="py-2 pr-3 font-medium">
                  <input
                    type="checkbox"
                    aria-label="Select all recent complaints"
                    checked={allRecentSelected}
                    disabled={recent.length === 0 || deletingSelected}
                    onChange={toggleAllRecent}
                    className="h-4 w-4 accent-violet-600"
                  />
                </th>
                <th className="py-2 pr-3 font-medium">ID</th>
                <th className="py-2 pr-3 font-medium">Customer</th>
                <th className="py-2 pr-3 font-medium">Product</th>
                <th className="py-2 pr-3 font-medium">Batch</th>
                <th className="py-2 pr-3 font-medium">Risk</th>
                <th className="py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {recent.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No complaints yet — paste one in the AI Copilot to begin.
                  </td>
                </tr>
              )}
              {recent.map((c) => (
                <tr
                  key={c.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => handleComplaintClick(c)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      handleComplaintClick(c);
                    }
                  }}
                  className={`cursor-pointer border-b border-slate-50 transition-colors hover:bg-violet-50/60 ${selectedIds.has(c.id) ? "bg-violet-50/70" : ""}`}
                >
                  <td className="py-2.5 pr-3" onClick={(event) => event.stopPropagation()}>
                    <input
                      type="checkbox"
                      aria-label={`Select ${c.complaint_id}`}
                      checked={selectedIds.has(c.id)}
                      disabled={deletingSelected}
                      onChange={() => toggleComplaintSelection(c.id)}
                      onKeyDown={(event) => event.stopPropagation()}
                      className="h-4 w-4 accent-violet-600"
                    />
                  </td>
                  <td className="py-2.5 pr-3 font-medium text-violet-700">
                    <span className="inline-flex items-center gap-1.5">
                      {downloadingId === c.id ? (
                        <Download className="h-3.5 w-3.5 animate-pulse" />
                      ) : null}
                      {c.complaint_id}
                    </span>
                  </td>
                  <td className="py-2.5 pr-3">{c.customer_name || "—"}</td>
                  <td className="py-2.5 pr-3">{c.product_name || "—"}</td>
                  <td className="py-2.5 pr-3">{c.batch_number || "—"}</td>
                  <td className="py-2.5 pr-3">
                    <Badge className={riskColor(c.risk_level)}>
                      {c.risk_level}
                    </Badge>
                  </td>
                  <td className="py-2.5">
                    <Badge className={statusColor(c.status)}>
                      {c.status.replace("_", " ")}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
