"use client";

import { useEffect, useState } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Badge } from "@/components/ui/input";
import { api } from "@/lib/utils";
import { toast } from "sonner";

type KBItem = {
  id: number;
  title: string;
  doc_type: string;
  filename?: string;
  chunk_count: number;
};

export function KnowledgeView() {
  const [items, setItems] = useState<KBItem[]>([]);
  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState("SOP");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const load = () =>
    api<KBItem[]>("/knowledge").then(setItems).catch(() => setItems([]));

  useEffect(() => {
    load();
  }, []);

  const upload = async (file: File) => {
    if (!title.trim()) {
      toast.error("Enter a document title");
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    fd.append("title", title);
    fd.append("doc_type", docType);
    await api("/knowledge/upload", { method: "POST", body: fd });
    toast.success("Document indexed in RAG knowledge base");
    setTitle("");
    load();
  };

  const ask = async () => {
    const res = await api<{ answer: string }>("/ai/rag/ask", {
      method: "POST",
      body: JSON.stringify({ query: question }),
    });
    setAnswer(res.answer);
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          RAG Knowledge Base
        </h1>
        <p className="text-sm text-slate-500">
          Upload SOPs, FDA guidelines, WHO GMP, manuals, and CAPA templates
        </p>
      </div>

      <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
        <div className="grid gap-3 sm:grid-cols-3">
          <Input
            placeholder="Document title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <Input
            placeholder="Doc type (SOP, FDA, WHO_GMP...)"
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
          />
          <label className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 text-sm font-medium text-white hover:bg-violet-700">
            <Upload className="h-4 w-4" />
            Upload
            <input
              type="file"
              className="hidden"
              accept=".pdf,.docx,.txt,.doc"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) upload(f);
              }}
            />
          </label>
        </div>
      </div>

      <div className="space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white px-4 py-3"
          >
            <div>
              <p className="text-sm font-medium">{item.title}</p>
              <p className="text-xs text-slate-500">{item.filename}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge className="border-violet-100 bg-violet-50 text-violet-700">
                {item.doc_type}
              </Badge>
              <span className="text-xs text-slate-400">
                {item.chunk_count} chunks
              </span>
            </div>
          </div>
        ))}
      </div>

          <div className="rounded-2xl border border-violet-100 bg-violet-50/40 p-4">
        <h2 className="mb-3 text-sm font-semibold">Ask the knowledge base</h2>
        <div className="flex gap-2">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="How should capsule discoloration complaints be investigated?"
          />
          <Button onClick={ask}>Ask</Button>
        </div>
        {answer && (
          <p className="mt-4 whitespace-pre-wrap text-sm text-slate-700">
            {answer}
          </p>
        )}
      </div>
    </div>
  );
}
