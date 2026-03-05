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

// ── sessionStorage helpers ──────────────────────────────────────
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

export default function ChatShell() {
  // ── Conversation state ────────────────────────────────────────
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId]   = useState<string | null>(null);
  const [convTitle, setConvTitle]         = useState("New Conversation");

  // ── Message state ─────────────────────────────────────────────
  const [messages, setMessages]           = useState<Message[]>([]);
  const [inputValue, setInputValue]       = useState("");
  const [prefillValue, setPrefillValue]   = useState<string | undefined>();

  // ── Streaming state ───────────────────────────────────────────
  const [isStreaming, setIsStreaming]      = useState(false);
  const [isThinking, setIsThinking]       = useState(false);
  const [checkpointId, setCheckpointId]   = useState<string | null>(null);

  // ── Load from sessionStorage on mount ────────────────────────
  useEffect(() => {
    const saved = loadConversations();
    setConversations(saved);
  }, []);

  // ── Persist conversations ─────────────────────────────────────
  useEffect(() => {
    if (conversations.length > 0) saveConversations(conversations);
  }, [conversations]);

  // ── Persist messages ──────────────────────────────────────────
  useEffect(() => {
    if (activeConvId && messages.length > 0) {
      saveMessages(activeConvId, messages);
    }
  }, [messages, activeConvId]);

  // ── Message helpers ───────────────────────────────────────────
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

  // Write search query into the message so it persists after streaming
  function setMsgSearchQuery(id: string, query: string): void {
    setMessages((prev) =>
      prev.map((m) => m.id === id ? { ...m, searchQuery: query, searchUrls: [] } : m)
    );
  }

  // Write search URLs into the message so they persist after streaming
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

  // ── New chat ──────────────────────────────────────────────────
  function handleNewChat(): void {
    setMessages([]);
    setCheckpointId(null);
    setActiveConvId(null);
    setConvTitle("New Conversation");
    setIsStreaming(false);
    setIsThinking(false);
    setInputValue("");
  }

  // ── Select conversation ───────────────────────────────────────
  function handleSelectConv(id: string): void {
    setActiveConvId(id);
    const conv = conversations.find((c) => c.id === id);
    if (conv) setConvTitle(conv.title);
    setMessages(loadMessages(id));
    setCheckpointId(null);
  }

  // ── Prefill ───────────────────────────────────────────────────
  const handlePrefill = useCallback((text: string) => {
    setInputValue(text);
    setPrefillValue(text);
  }, []);

  // ── Send message ──────────────────────────────────────────────
  async function handleSend(): Promise<void> {
    const text = inputValue.trim();
    if (!text || isStreaming) return;

    setInputValue("");
    setIsStreaming(true);
    addUserMessage(text);

    // Create conversation entry on first message
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
              // Create the agent bubble early so the card has a home
              if (agentMsgId === null) {
                setIsThinking(false);
                agentMsgId = startAgentMessage();
              }
              // Store query inside the message itself
              setMsgSearchQuery(agentMsgId, payload.query);
              break;

            case "search_results":
              // Store URLs inside the message itself
              if (agentMsgId !== null) {
                setMsgSearchUrls(agentMsgId, payload.urls ?? []);
              }
              break;

            case "search_error":
              if (agentMsgId !== null) {
                setMsgSearchUrls(agentMsgId, []);
              }
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

  // ── Render ────────────────────────────────────────────────────
  return (
    <div
      style={{
        position: "relative",
        zIndex: 2,
        display: "flex",
        width: "100%",
        height: "100vh",
        overflow: "hidden",
      }}
    >
      <Sidebar
        conversations={conversations}
        activeId={activeConvId}
        onNewChat={handleNewChat}
        onSelectConv={handleSelectConv}
      />

      <main
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          height: "100%",
          minWidth: 0,
          position: "relative",
        }}
      >
        <TopBar title={convTitle} />

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