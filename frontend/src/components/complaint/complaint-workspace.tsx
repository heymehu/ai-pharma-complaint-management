"use client";

import { useCallback, useMemo, useState } from "react";
import { v4 as uuidv4 } from "uuid";
const uuid = () => uuidv4();
import { toast } from "sonner";
import {
  Download,
  PlusCircle,
  Save,
  Shield,
  Wand2,
} from "lucide-react";
import { ComplaintForm } from "./complaint-form";
import { AICopilot } from "./ai-copilot";
import { useWorkspace } from "./workspace-provider";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/utils";
import { downloadComplaintPdf } from "@/lib/complaint-pdf";
import type { ComplaintFormData } from "@/lib/types";

type ExtractPayload = {
  fields?: Partial<ComplaintFormData>;
  investigation?: Partial<ComplaintFormData> & {
    required_tests?: string[];
    missing_information?: string[];
    regulatory_implications?: string[];
    confidence_score?: number;
  };
  message?: string;
  reply?: string;
  action?: string;
  duplicates?: { complaint_id: string; summary?: string }[];
};

function looksLikeFullComplaint(text: string) {
  return (
    text.length > 100 &&
    /batch|complaint|reported|capsule|tablet|expiry|pharmacy|hospital/i.test(
      text
    ) &&
    /(product|email|name|quantity|strength|manufactur|expir|contamin|discolou?r|capsule|tablet)/i.test(
      text
    )
  );
}

function looksLikeCorrection(text: string) {
  return /correct|update|change|fix|actually|instead|wrong|should be|batch|quantity|qty|product name|strength|expiry|email|phone|customer/i.test(
    text
  );
}

export function ComplaintWorkspace() {
  const {
    form,
    formRef,
    messages,
    sessionId,
    savedId,
    dbId,
    status,
    setForm,
    setMessages,
    setSavedId,
    setDbId,
    setStatus,
    resetWorkspace,
  } = useWorkspace();

  const [highlighted, setHighlighted] = useState<Set<string>>(new Set());
  const [isTyping, setIsTyping] = useState(false);

  const applyExtraction = useCallback(
    (payload: ExtractPayload) => {
      const fields = payload.fields || {};
      const inv = payload.investigation || {};
      const nextKeys: string[] = [];

      setForm((prev) => {
        const next = { ...prev };
        const merge = { ...fields, ...inv } as Record<string, unknown>;
        for (const [k, v] of Object.entries(merge)) {
          if (v === null || v === undefined || v === "") continue;
          if (k in next) {
            (next as Record<string, unknown>)[k] = v;
            nextKeys.push(k);
          }
        }
        if (typeof inv.confidence_score === "number") {
          next.confidence_score = inv.confidence_score;
          nextKeys.push("confidence_score");
        }
        if (inv.required_tests) next.required_tests = inv.required_tests;
        if (inv.missing_information)
          next.missing_information = inv.missing_information;
        if (inv.regulatory_implications)
          next.regulatory_implications = inv.regulatory_implications;
        return next;
      });

      setHighlighted(new Set(nextKeys));
      setTimeout(() => setHighlighted(new Set()), 1800);

      if (payload.duplicates?.length) {
        toast.warning(
          `Possible duplicate: ${payload.duplicates.map((d) => d.complaint_id).join(", ")}`
        );
      }
    },
    [setForm]
  );

  const pushAssistant = (content: string) => {
    setMessages((m) => [
      ...m,
      { id: uuid(), role: "assistant", content, timestamp: new Date() },
    ]);
  };

  const handleSend = async (text: string) => {
    setMessages((m) => [
      ...m,
      { id: uuid(), role: "user", content: text, timestamp: new Date() },
    ]);
    setIsTyping(true);
    try {
      const currentForm = formRef.current;
      const hasFormData = Boolean(
        currentForm.batch_number ||
          currentForm.product_name ||
          currentForm.customer_name ||
          currentForm.summary ||
          currentForm.quantity
      );

      const useUpdatePath =
        hasFormData && looksLikeCorrection(text) && !looksLikeFullComplaint(text);

      if (looksLikeFullComplaint(text) && !useUpdatePath) {
        const res = await api<ExtractPayload>("/ai/extract", {
          method: "POST",
          body: JSON.stringify({ text, session_id: sessionId }),
        });
        applyExtraction(res);
        pushAssistant(res.message || "Form updated from complaint text.");
      } else {
        const res = await api<ExtractPayload>("/ai/chat", {
          method: "POST",
          body: JSON.stringify({
            message: text,
            session_id: sessionId,
            complaint_id: dbId,
            form_data: currentForm,
          }),
        });
        if (res.fields || res.investigation) {
          applyExtraction(res);
        } else if (useUpdatePath) {
          toast.message("No field changes detected — try: batch number is ABC123");
        }
        pushAssistant(res.reply || "Done.");
      }
    } catch (err) {
      pushAssistant(
        `I couldn't reach the AI service (${err instanceof Error ? err.message : "error"}). Is the backend running on port 8000?`
      );
    } finally {
      setIsTyping(false);
    }
  };

  const handleUpload = async (file: File) => {
    setMessages((m) => [
      ...m,
      {
        id: uuid(),
        role: "user",
        content: `Uploaded: ${file.name}`,
        timestamp: new Date(),
      },
    ]);
    setIsTyping(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("session_id", sessionId);
      const res = await api<{
        extracted_text?: string;
        extraction?: ExtractPayload;
      }>("/ai/upload", { method: "POST", body: fd });
      if (res.extraction) {
        applyExtraction(res.extraction);
        pushAssistant(
          res.extraction.message ||
            `Extracted text from ${file.name} and filled the form.`
        );
      } else {
        pushAssistant(
          res.extracted_text
            ? `Extracted text:\n\n${res.extracted_text.slice(0, 600)}`
            : "Upload received, but no text could be extracted."
        );
      }
    } catch (err) {
      pushAssistant(
        `Upload failed: ${err instanceof Error ? err.message : "error"}`
      );
    } finally {
      setIsTyping(false);
    }
  };

  const saveComplaint = async () => {
    try {
      const body = {
        ...form,
        raw_text: form.summary,
        risk_level: form.risk_level || undefined,
        priority: form.priority || undefined,
        ai_suggestions: {
          required_tests: form.required_tests,
          missing_information: form.missing_information,
          regulatory_implications: form.regulatory_implications,
        },
      };
      const res = await api<{ id: number; complaint_id: string; status: string }>(
        "/complaints",
        { method: "POST", body: JSON.stringify(body) }
      );
      setSavedId(res.complaint_id);
      setDbId(res.id);
      setStatus(res.status);
      toast.success(`Saved ${res.complaint_id}`);
      pushAssistant(`Complaint saved as **${res.complaint_id}**.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    }
  };

  const downloadPdf = async () => {
    try {
      await downloadComplaintPdf(
        { ...form, complaint_id: savedId, status },
        savedId ? `${savedId}.pdf` : undefined
      );
      toast.success("Complaint Report downloaded");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "PDF failed");
    }
  };

  const advance = async () => {
    if (!dbId) {
      toast.message("Save the complaint first");
      return;
    }
    const res = await api<{ status: string }>(`/complaints/${dbId}/advance`, {
      method: "POST",
    });
    setStatus(res.status);
    toast.success(`Status → ${res.status.replace("_", " ")}`);
  };

  const startNextComplaint = () => {
    resetWorkspace();
    setHighlighted(new Set());
    toast.success("Ready for the next complaint");
  };

  const quickActions = useMemo(
    () => [
      { label: "Summarize", prompt: "Summarize this complaint" },
      { label: "Investigate", prompt: "Generate investigation" },
      { label: "CAPA", prompt: "Write CAPA" },
      { label: "FDA Report", prompt: "Generate FDA report" },
      { label: "Root Cause", prompt: "Suggest root cause with 5 Whys" },
      { label: "Customer Reply", prompt: "Generate customer reply" },
      { label: "Classify", prompt: "Classify severity and risk" },
    ],
    []
  );

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col lg:flex-row">
      <div className="flex w-full flex-col border-r border-slate-200 lg:w-[65%]">
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 bg-white/80 px-4 py-2.5 backdrop-blur">
          <Button size="sm" onClick={saveComplaint}>
            <Save className="h-3.5 w-3.5" />
            Save Complaint
          </Button>
          <Button size="sm" variant="secondary" onClick={startNextComplaint}>
            <PlusCircle className="h-3.5 w-3.5" />
            Next Complaint
          </Button>
          <Button size="sm" variant="secondary" onClick={advance}>
            <Wand2 className="h-3.5 w-3.5" />
            Advance Status
          </Button>
          <Button size="sm" variant="outline" onClick={downloadPdf}>
            <Download className="h-3.5 w-3.5" />
            PDF
          </Button>
          <div className="ml-auto flex items-center gap-1.5 text-xs text-slate-500">
            <Shield className="h-3.5 w-3.5 text-violet-500" />
            Audit-ready
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5">
          <ComplaintForm
            form={form}
            setForm={setForm}
            highlighted={highlighted}
            status={status}
            complaintId={savedId}
          />
        </div>
      </div>

      <div className="h-[45vh] w-full lg:h-full lg:w-[35%]">
        <AICopilot
          messages={messages}
          isTyping={isTyping}
          onSend={handleSend}
          onUpload={handleUpload}
          quickActions={quickActions}
        />
      </div>
    </div>
  );
}
