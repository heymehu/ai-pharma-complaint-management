"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  Beaker,
  CheckCircle2,
  FileWarning,
  Flame,
  ShieldAlert,
} from "lucide-react";
import { Badge } from "@/components/ui/input";
import { riskColor } from "@/lib/utils";
import type { ComplaintFormData } from "@/lib/types";

export function InvestigationCards({ form }: { form: ComplaintFormData }) {
  if (!form.potential_issue && !form.suggested_test) return null;

  const cards = [
    {
      title: "Potential Issue",
      value: form.potential_issue,
      icon: AlertTriangle,
      accent: "from-violet-500/10 to-fuchsia-500/5 border-violet-100",
    },
    {
      title: "Suggested Test",
      value: form.suggested_test,
      icon: Beaker,
      accent: "from-sky-500/10 to-cyan-500/5 border-sky-100",
    },
    {
      title: "Priority",
      value: form.priority ? form.priority.toUpperCase() : "",
      icon: Flame,
      accent: "from-orange-500/10 to-amber-500/5 border-orange-100",
    },
    {
      title: "Recommended Action",
      value: form.recommended_action,
      icon: CheckCircle2,
      accent: "from-emerald-500/10 to-teal-500/5 border-emerald-100",
    },
  ];

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            AI Suggested Investigation
          </h3>
          <p className="text-xs text-slate-500">
            Explainable recommendations with confidence scoring
          </p>
        </div>
        {form.confidence_score > 0 && (
          <Badge className="border-violet-200 bg-violet-50 text-violet-700">
            Confidence {(form.confidence_score * 100).toFixed(0)}%
          </Badge>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {cards.map((card, i) =>
          card.value ? (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 * i, duration: 0.35 }}
              className={`rounded-2xl border bg-gradient-to-br p-4 ${card.accent}`}
            >
              <div className="mb-2 flex items-center gap-2 text-slate-600">
                <card.icon className="h-4 w-4 text-violet-600" />
                <span className="text-xs font-semibold uppercase tracking-wide">
                  {card.title}
                </span>
              </div>
              <p className="text-sm font-medium text-slate-800">
                {card.value}
              </p>
            </motion.div>
          ) : null
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {form.risk_level && (
          <div className="rounded-2xl border border-slate-100 bg-white p-3">
            <p className="mb-1 text-xs text-slate-500">Risk Level</p>
            <Badge className={riskColor(form.risk_level)}>
              {form.risk_level}
            </Badge>
          </div>
        )}
        {form.affected_batches && (
          <div className="rounded-2xl border border-slate-100 bg-white p-3">
            <p className="mb-1 text-xs text-slate-500">Affected Batches</p>
            <p className="text-sm font-medium">{form.affected_batches}</p>
          </div>
        )}
        {form.escalation_level && (
          <div className="rounded-2xl border border-slate-100 bg-white p-3">
            <p className="mb-1 text-xs text-slate-500">Escalation</p>
            <p className="text-sm font-medium">{form.escalation_level}</p>
          </div>
        )}
      </div>

      {form.regulatory_concern && (
        <div className="flex gap-3 rounded-2xl border border-violet-100 bg-violet-50/50 p-4">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-violet-600" />
          <div>
            <p className="text-xs font-semibold text-violet-800">
              Regulatory Concern
            </p>
            <p className="text-sm text-slate-700">
              {form.regulatory_concern}
            </p>
          </div>
        </div>
      )}

      {form.ai_reasoning && (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/80 p-4">
          <p className="mb-1 text-xs font-semibold text-slate-500">
            Explainable AI — Reasoning
          </p>
          <p className="text-sm text-slate-700">
            {form.ai_reasoning}
          </p>
        </div>
      )}

      {form.required_tests?.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold text-slate-500">
            Required Laboratory Tests
          </p>
          <div className="flex flex-wrap gap-2">
            {form.required_tests.map((t) => (
              <Badge
                key={t}
                className="border-sky-100 bg-sky-50 text-sky-800"
              >
                <Beaker className="mr-1 h-3 w-3" />
                {t}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {form.missing_information?.length > 0 && (
        <div className="rounded-2xl border border-amber-100 bg-amber-50/60 p-4">
          <div className="mb-2 flex items-center gap-2 text-amber-800">
            <FileWarning className="h-4 w-4" />
            <p className="text-xs font-semibold">Missing Information</p>
          </div>
          <ul className="list-inside list-disc text-sm text-amber-900/80">
            {form.missing_information.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
