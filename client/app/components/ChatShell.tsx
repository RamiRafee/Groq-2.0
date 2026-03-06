"use client";

import { useState, useCallback, useEffect } from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import { Message, Conversation, SSEEvent } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const SS_CONVS_KEY   = "agentui:conversations";
const SS_MSGS_PREFIX = "agentui:messages:";

function loadConversations(): Conversation[] {
  try {
    const raw = sessionStorage.getItem(SS_CONVS_KEY);
    return raw ? (JSON.parse(raw) as Conversation[]) : [];
  } catch { return []; }
}

function saveConversations(convs: Conversation[]): void {
  try { sessionStorage.setItem(SS_CONVS_KEY, JSON.stringify(convs)); }
  catch { /* quota exceeded */ }
}

function loadMessages(convId: string): Message[] {
  try {
    const raw = sessionStorage.getItem(SS_MSGS_PREFIX + convId);
    return raw ? (JSON.parse(raw) as Message[]) : [];
  } catch { return []; }
}

function saveMessages(convId: string, msgs: Message[]): void {
  try {
    const finished = msgs.map((m) => ({ ...m, isStreaming: false }));
    sessionStorage.setItem(SS_MSGS_PREFIX + convId, JSON.stringify(finished));
  } catch { /* quota exceeded */ }
}

function genId(): string {
  return Math.random().toString(36).slice(2);
}

// Hook to detect desktop vs mobile
function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    setIsDesktop(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return isDesktop;
}

export default function ChatShell() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId]   = useState<string | null>(null);
  const [convTitle, setConvTitle]         = useState("New Conversation");
  const [messages, setMessages]           = useState<Message[]>([]);
  const [inputValue, setInputValue]       = useState("");
  const [prefillValue, setPrefillValue]   = useState<string | undefined>();
  const [isStreaming, setIsStreaming]      = useState(false);
  const [isThinking, setIsThinking]       = useState(false);
  const [checkpointId, setCheckpointId]   = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen]     = useState(false);
  const isDesktop                         = useIsDesktop();

  useEffect(() => {
    const saved = loadConversations();
    setConversations(saved);
  }, []);

  useEffect(() => {
    if (conversations.length > 0) saveConversations(conversations);
  }, [conversations]);

  useEffect(() => {
    if (activeConvId && messages.length > 0) {
      saveMessages(activeConvId, messages);
    }
  }, [messages, activeConvId]);

  function addUserMessage(text: string): void {
    setMessages((prev) => [
      ...prev,
      { id: genId(), role: "user", content: text },
    ]);
  }

  function startAgentMessage(): string {
    const id = genId();
    setMessages((prev) => [
      ...prev,
      { id, role: "agent", content: "", isStreaming: true },
    ]);
    return id;
  }

  function appendAgentToken(id: string, token: string): void {
    setMessages((prev) =>
      prev.map((m) => m.id === id ? { ...m, content: m.content + token } : m)
    );
  }

  function setMsgSearchQuery(id: string, query: string): void {
    setMessages((prev) =>
      prev.map((m) => m.id === id ? { ...m, searchQuery: query, searchUrls: [] } : m)
    );
  }

  function setMsgSearchUrls(id: string, urls: string[]): void {
    setMessages((prev) =>
      prev.map((m) => m.id === id ? { ...m, searchUrls: urls } : m)
    );
  }

  function finaliseAgentMessage(id: string): void {
    setMessages((prev) =>
      prev.map((m) => m.id === id ? { ...m, isStreaming: false } : m)
    );
  }

  function handleNewChat(): void {
    setMessages([]);
    setCheckpointId(null);
    setActiveConvId(null);
    setConvTitle("New Conversation");
    setIsStreaming(false);
    setIsThinking(false);
    setInputValue("");
    setSidebarOpen(false);
  }

  function handleSelectConv(id: string): void {
    setActiveConvId(id);
    const conv = conversations.find((c) => c.id === id);
    if (conv) setConvTitle(conv.title);
    setMessages(loadMessages(id));
    setCheckpointId(null);
    setSidebarOpen(false);
  }

  const handlePrefill = useCallback((text: string) => {
    setInputValue(text);
    setPrefillValue(text);
  }, []);

  async function handleSend(): Promise<void> {
    const text = inputValue.trim();
    if (!text || isStreaming) return;

    setInputValue("");
    setIsStreaming(true);
    addUserMessage(text);

    let currentConvId = activeConvId;
    if (!currentConvId) {
      const title = text.slice(0, 40) + (text.length > 40 ? "…" : "");
      const newConv: Conversation = { id: genId(), title, time: "Just now" };
      setConversations((prev) => [newConv, ...prev]);
      setActiveConvId(newConv.id);
      setConvTitle(title);
      currentConvId = newConv.id;
    }

    setIsThinking(true);
    let agentMsgId: string | null = null;

    try {
      const url =
        `${API_BASE}/chat_stream/${encodeURIComponent(text)}` +
        (checkpointId ? `?checkpoint_id=${checkpointId}` : "");

      const resp = await fetch(url);
      if (!resp.body) throw new Error("No response body");

      const reader  = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer    = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let payload: SSEEvent;
          try { payload = JSON.parse(line.slice(6)); }
          catch { continue; }

          switch (payload.type) {
            case "session":
              setCheckpointId(payload.checkpoint_id);
              break;
            case "thinking":
              setIsThinking(true);
              break;
            case "content":
              if (agentMsgId === null) {
                setIsThinking(false);
                agentMsgId = startAgentMessage();
              }
              appendAgentToken(agentMsgId, payload.content);
              break;
            case "search_start":
              if (agentMsgId === null) {
                setIsThinking(false);
                agentMsgId = startAgentMessage();
              }
              setMsgSearchQuery(agentMsgId, payload.query);
              break;
            case "search_results":
              if (agentMsgId !== null) {
                setMsgSearchUrls(agentMsgId, payload.urls ?? []);
              }
              break;
            case "search_error":
              if (agentMsgId !== null) setMsgSearchUrls(agentMsgId, []);
              break;
            case "error":
              if (agentMsgId === null) {
                setIsThinking(false);
                agentMsgId = startAgentMessage();
              }
              appendAgentToken(agentMsgId, `\n\n⚠ ${payload.error}`);
              break;
            case "end":
              break;
          }
        }
      }
    } catch (err) {
      if (agentMsgId === null) {
        setIsThinking(false);
        agentMsgId = startAgentMessage();
      }
      const msg = err instanceof Error ? err.message : "Unknown error";
      appendAgentToken(agentMsgId, `⚠ Connection error: ${msg}`);
    } finally {
      if (agentMsgId) finaliseAgentMessage(agentMsgId);
      setIsThinking(false);
      setIsStreaming(false);
    }
  }

  return (
    <div
      style={{
        position: "relative",
        zIndex: 2,
        display: "flex",
        width: "100%",
        height: "100dvh",
        overflow: "hidden",
      }}
    >
      {/* ── Mobile backdrop ──────────────────────────────────── */}
      {!isDesktop && sidebarOpen && (
        <div
          id="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 10,
          }}
        />
      )}

      {/* ── Sidebar ──────────────────────────────────────────── */}
      <div
        id="sidebar-drawer"
        style={{
          position: isDesktop ? "relative" : "fixed",
          top: 0,
          left: 0,
          height: "100dvh",
          zIndex: isDesktop ? 2 : 20,
          transform: isDesktop || sidebarOpen
            ? "translateX(0)"
            : "translateX(-100%)",
          transition: "transform 0.3s cubic-bezier(0.22, 1, 0.36, 1)",
          flexShrink: 0,
        }}
      >
        <Sidebar
          conversations={conversations}
          activeId={activeConvId}
          onNewChat={handleNewChat}
          onSelectConv={handleSelectConv}
        />
      </div>

      {/* ── Main ─────────────────────────────────────────────── */}
      <main
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          height: "100dvh",
          minWidth: 0,
          position: "relative",
          // On mobile the sidebar is fixed so main takes full width
          width: "100%",
        }}
      >
        <TopBar
          title={convTitle}
          onMenuClick={() => setSidebarOpen((o) => !o)}
        />

        <MessageList
          messages={messages}
          isThinking={isThinking}
          onPrefill={handlePrefill}
        />

        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSend}
          isStreaming={isStreaming}
          prefillValue={prefillValue}
        />
      </main>
    </div>
  );
}