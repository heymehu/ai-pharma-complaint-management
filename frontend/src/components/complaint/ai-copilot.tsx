"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bot,
  FileUp,
  Loader2,
  Mic,
  MicOff,
  Paperclip,
  Send,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import type { ChatMessage, ComplaintFormData } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  messages: ChatMessage[];
  isTyping: boolean;
  onSend: (text: string) => void;
  onUpload: (file: File) => void;
  quickActions: { label: string; prompt: string }[];
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-1">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-violet-500"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
          transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </div>
  );
}

function renderMarkdownish(content: string) {
  const parts = content.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-slate-900">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export function AICopilot({
  messages,
  isTyping,
  onSend,
  onUpload,
  quickActions,
}: Props) {
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const submit = () => {
    const text = input.trim();
    if (!text || isTyping) return;
    setInput("");
    onSend(text);
  };

  const toggleVoice = () => {
    const SR =
      typeof window !== "undefined"
        ? window.SpeechRecognition || window.webkitSpeechRecognition
        : undefined;
    if (!SR) {
      onSend("Voice recognition is not supported in this browser. Please paste or type the complaint.");
      return;
    }
    if (listening && recognitionRef.current) {
      recognitionRef.current.stop();
      setListening(false);
      return;
    }
    const recognition = new SR();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;
      setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      setListening(false);
    };
    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  return (
    <div className="flex h-full flex-col bg-gradient-to-b from-violet-50/80 via-white to-white">
      <div className="flex items-center gap-3 border-b border-violet-100/80 px-4 py-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600 text-white shadow-sm shadow-violet-300">
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">
            AIVOA AI Copilot
          </p>
          <p className="truncate text-xs text-slate-500">
            Extract · Investigate · CAPA · Reports
          </p>
        </div>
        <Bot className="h-4 w-4 text-violet-500" />
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        <AnimatePresence initial={false}>
          {messages.map((m) => (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                "flex",
                m.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap",
                  m.role === "user"
                    ? "bg-violet-600 text-white shadow-sm shadow-violet-200"
                    : "border border-slate-100 bg-white text-slate-700 shadow-sm"
                )}
              >
                {m.role === "assistant" ? renderMarkdownish(m.content) : m.content}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        {isTyping && (
          <div className="flex justify-start">
            <div className="rounded-2xl border border-slate-100 bg-white px-3 py-2 shadow-sm">
              <TypingDots />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-violet-100/80 px-3 py-2">
        <div className="mb-2 flex gap-1.5 overflow-x-auto pb-1">
          {quickActions.map((a) => (
            <button
              key={a.label}
              type="button"
              onClick={() => onSend(a.prompt)}
              className="shrink-0 rounded-full border border-violet-100 bg-white px-2.5 py-1 text-[11px] font-medium text-violet-700 hover:bg-violet-50"
            >
              {a.label}
            </button>
          ))}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste complaint email, ask a question, or dictate..."
            rows={3}
            className="min-h-[72px] border-0 shadow-none focus-visible:ring-0"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
          />
          <div className="flex items-center justify-between gap-2 px-1 pb-1">
            <div className="flex items-center gap-1">
              <input
                ref={fileRef}
                type="file"
                className="hidden"
                accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.webp"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) onUpload(f);
                  e.target.value = "";
                }}
              />
              <Button
                type="button"
                size="icon"
                variant="ghost"
                onClick={() => fileRef.current?.click()}
                title="Upload document / image"
              >
                <Paperclip className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                onClick={() => fileRef.current?.click()}
                title="OCR / PDF"
              >
                <FileUp className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                size="icon"
                variant={listening ? "secondary" : "ghost"}
                onClick={toggleVoice}
                title="Dictate complaint"
              >
                {listening ? (
                  <MicOff className="h-4 w-4 text-rose-500" />
                ) : (
                  <Mic className="h-4 w-4" />
                )}
              </Button>
            </div>
            <Button type="button" size="sm" onClick={submit} disabled={isTyping || !input.trim()}>
              {isTyping ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Send
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export type { ComplaintFormData };
