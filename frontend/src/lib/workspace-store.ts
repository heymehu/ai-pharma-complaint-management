import { v4 as uuidv4 } from "uuid";
import {
  emptyForm,
  type ChatMessage,
  type ComplaintFormData,
} from "@/lib/types";

const STORAGE_KEY = "aivoa-workspace-draft";

export const WELCOME =
  "Ready to process new complaints. You can paste the complaint here, upload a document, or dictate the complaint. I'll extract the data and fill the form automatically.";

export interface WorkspaceState {
  form: ComplaintFormData;
  messages: ChatMessage[];
  sessionId: string;
  savedId?: string;
  dbId?: number;
  status: string;
}

export function defaultWorkspace(): WorkspaceState {
  return {
    form: emptyForm(),
    messages: [
      {
        id: uuidv4(),
        role: "assistant",
        content: WELCOME,
        timestamp: new Date(),
      },
    ],
    sessionId: uuidv4(),
    savedId: undefined,
    dbId: undefined,
    status: "pending",
  };
}

export function loadWorkspace(): WorkspaceState {
  if (typeof window === "undefined") return defaultWorkspace();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultWorkspace();
    const parsed = JSON.parse(raw) as WorkspaceState;
    return {
      ...defaultWorkspace(),
      ...parsed,
      form: { ...emptyForm(), ...parsed.form },
      messages: (parsed.messages || []).map((m) => ({
        ...m,
        timestamp: new Date(m.timestamp),
      })),
    };
  } catch {
    return defaultWorkspace();
  }
}

export function saveWorkspace(state: WorkspaceState) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function clearWorkspaceStorage() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}
