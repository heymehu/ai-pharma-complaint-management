"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { v4 as uuidv4 } from "uuid";
import {
  defaultWorkspace,
  loadWorkspace,
  saveWorkspace,
  type WorkspaceState,
  WELCOME,
} from "@/lib/workspace-store";
import type { ChatMessage, ComplaintFormData } from "@/lib/types";

interface WorkspaceContextValue extends WorkspaceState {
  formRef: React.MutableRefObject<ComplaintFormData>;
  setForm: React.Dispatch<React.SetStateAction<ComplaintFormData>>;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  setSavedId: React.Dispatch<React.SetStateAction<string | undefined>>;
  setDbId: React.Dispatch<React.SetStateAction<number | undefined>>;
  setStatus: React.Dispatch<React.SetStateAction<string>>;
  resetWorkspace: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<WorkspaceState>(defaultWorkspace);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setState(loadWorkspace());
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    saveWorkspace(state);
  }, [state, ready]);

  const setForm = useCallback(
    (updater: React.SetStateAction<ComplaintFormData>) => {
      setState((prev) => ({
        ...prev,
        form: typeof updater === "function" ? updater(prev.form) : updater,
      }));
    },
    []
  );

  const setMessages = useCallback(
    (updater: React.SetStateAction<ChatMessage[]>) => {
      setState((prev) => ({
        ...prev,
        messages: typeof updater === "function" ? updater(prev.messages) : updater,
      }));
    },
    []
  );

  const setSavedId = useCallback(
    (savedId: React.SetStateAction<string | undefined>) => {
      setState((prev) => ({
        ...prev,
        savedId: typeof savedId === "function" ? savedId(prev.savedId) : savedId,
      }));
    },
    []
  );

  const setDbId = useCallback(
    (dbId: React.SetStateAction<number | undefined>) => {
      setState((prev) => ({
        ...prev,
        dbId: typeof dbId === "function" ? dbId(prev.dbId) : dbId,
      }));
    },
    []
  );

  const setStatus = useCallback((status: React.SetStateAction<string>) => {
    setState((prev) => ({
      ...prev,
      status: typeof status === "function" ? status(prev.status) : status,
    }));
  }, []);

  const resetWorkspace = useCallback(() => {
    setState({
      ...defaultWorkspace(),
      sessionId: uuidv4(),
    });
  }, []);

  const formRef = useRef(state.form);
  formRef.current = state.form;

  const value = useMemo(
    () => ({
      ...state,
      formRef,
      setForm,
      setMessages,
      setSavedId,
      setDbId,
      setStatus,
      resetWorkspace,
    }),
    [state, setForm, setMessages, setSavedId, setDbId, setStatus, resetWorkspace]
  );

  return (
    <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspace must be used within WorkspaceProvider");
  }
  return ctx;
}

export { WELCOME };
