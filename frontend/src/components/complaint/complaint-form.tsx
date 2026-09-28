"use client";

import { useMemo } from "react";
import { AnimatedField } from "./animated-field";
import { InvestigationCards } from "./investigation-cards";
import type { ComplaintFormData } from "@/lib/types";
import { Badge } from "@/components/ui/input";
import { statusColor } from "@/lib/utils";

interface Props {
  form: ComplaintFormData;
  setForm: React.Dispatch<React.SetStateAction<ComplaintFormData>>;
  highlighted: Set<string>;
  status?: string;
  complaintId?: string;
}

export function ComplaintForm({
  form,
  setForm,
  highlighted,
  status = "pending",
  complaintId,
}: Props) {
  const errors = useMemo(() => {
    const e: Record<string, string> = {};
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      e.email = "Invalid email";
    }
    if (form.batch_number && form.batch_number.length < 3) {
      e.batch_number = "Batch number looks incomplete";
    }
    if (form.expiry_date) {
      const exp = Date.parse(form.expiry_date);
      if (!Number.isNaN(exp) && exp < Date.now()) {
        e.expiry_date = "Product appears expired";
      }
    }
    return e;
  }, [form]);

  const set =
    (key: keyof ComplaintFormData) =>
    (value: string) =>
      setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="space-y-8 pb-10">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">
            Complaint Form
          </h2>
          <p className="text-sm text-slate-500">
            Fields auto-fill when the AI Copilot extracts complaint data
          </p>
        </div>
        <div className="flex items-center gap-2">
          {complaintId && (
            <Badge className="border-slate-200 bg-white text-slate-700">
              {complaintId}
            </Badge>
          )}
          <Badge className={statusColor(status)}>
            {status.replace("_", " ")}
          </Badge>
        </div>
      </div>

      <section className="space-y-4">
        <h3 className="text-sm font-semibold text-violet-700">
          1. Complaint Details
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <AnimatedField
            label="Complaint Source"
            name="complaint_source"
            value={form.complaint_source}
            onChange={set("complaint_source")}
            highlight={highlighted.has("complaint_source")}
            placeholder="e.g. Apollo Pharmacy"
          />
          <AnimatedField
            label="Customer Name"
            name="customer_name"
            value={form.customer_name}
            onChange={set("customer_name")}
            highlight={highlighted.has("customer_name")}
          />
          <AnimatedField
            label="Email"
            name="email"
            value={form.email}
            onChange={set("email")}
            highlight={highlighted.has("email")}
            error={errors.email}
            type="email"
          />
          <AnimatedField
            label="Phone"
            name="phone"
            value={form.phone}
            onChange={set("phone")}
            highlight={highlighted.has("phone")}
          />
          <AnimatedField
            label="Complaint Date"
            name="complaint_date"
            value={form.complaint_date}
            onChange={set("complaint_date")}
            highlight={highlighted.has("complaint_date")}
            type="date"
          />
        </div>
      </section>

      <section className="space-y-4">
        <h3 className="text-sm font-semibold text-violet-700">
          2. Product Information
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <AnimatedField
            label="Product Name"
            name="product_name"
            value={form.product_name}
            onChange={set("product_name")}
            highlight={highlighted.has("product_name")}
          />
          <AnimatedField
            label="Strength"
            name="strength"
            value={form.strength}
            onChange={set("strength")}
            highlight={highlighted.has("strength")}
          />
          <AnimatedField
            label="Batch Number"
            name="batch_number"
            value={form.batch_number}
            onChange={set("batch_number")}
            highlight={highlighted.has("batch_number")}
            error={errors.batch_number}
          />
          <AnimatedField
            label="Manufacturing Date"
            name="manufacturing_date"
            value={form.manufacturing_date}
            onChange={set("manufacturing_date")}
            highlight={highlighted.has("manufacturing_date")}
          />
          <AnimatedField
            label="Expiry Date"
            name="expiry_date"
            value={form.expiry_date}
            onChange={set("expiry_date")}
            highlight={highlighted.has("expiry_date")}
            error={errors.expiry_date}
          />
          <AnimatedField
            label="Quantity"
            name="quantity"
            value={form.quantity}
            onChange={set("quantity")}
            highlight={highlighted.has("quantity")}
          />
        </div>
      </section>

      <section className="space-y-4">
        <h3 className="text-sm font-semibold text-violet-700">
          3. Complaint Summary
        </h3>
        <AnimatedField
          label="Summary"
          name="summary"
          value={form.summary}
          onChange={set("summary")}
          highlight={highlighted.has("summary")}
          textarea
          rows={5}
          placeholder="Complaint narrative..."
        />
      </section>

      <section className="space-y-4">
        <h3 className="text-sm font-semibold text-violet-700">
          4. AI Suggested Investigation
        </h3>
        <InvestigationCards form={form} />
      </section>
    </div>
  );
}
