"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Input, Label, Textarea } from "@/components/ui/input";

interface AnimatedFieldProps {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  highlight?: boolean;
  error?: string;
  type?: string;
  placeholder?: string;
  textarea?: boolean;
  rows?: number;
}

export function AnimatedField({
  label,
  name,
  value,
  onChange,
  highlight,
  error,
  type = "text",
  placeholder,
  textarea,
  rows = 4,
}: AnimatedFieldProps) {
  return (
    <motion.div
      layout
      animate={
        highlight
          ? {
              scale: [1, 1.02, 1],
              boxShadow: [
                "0 0 0 0 rgba(109,40,217,0)",
                "0 0 0 3px rgba(139,92,246,0.35)",
                "0 0 0 0 rgba(109,40,217,0)",
              ],
            }
          : {}
      }
      transition={{ duration: 0.55 }}
      className="space-y-1.5 rounded-xl"
    >
      <Label htmlFor={name}>{label}</Label>
      {textarea ? (
        <Textarea
          id={name}
          name={name}
          value={value}
          rows={rows}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            highlight && "border-violet-400 bg-violet-50/60",
            error && "border-rose-400 ring-1 ring-rose-200"
          )}
        />
      ) : (
        <Input
          id={name}
          name={name}
          type={type}
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            highlight && "border-violet-400 bg-violet-50/60",
            error && "border-rose-400 ring-1 ring-rose-200"
          )}
        />
      )}
      {error && <p className="text-xs text-rose-600">{error}</p>}
    </motion.div>
  );
}
