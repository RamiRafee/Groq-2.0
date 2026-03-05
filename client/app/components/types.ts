export type MessageRole = "user" | "agent";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  isStreaming?: boolean;
  searchQuery?: string;
  searchUrls?: string[];
}

export interface Conversation {
  id: string;
  title: string;
  time: string;
}

export interface SSESession       { type: "session";        checkpoint_id: string; }
export interface SSEThinking      { type: "thinking";       stage: string; }
export interface SSEContent       { type: "content";        content: string; index: number; }
export interface SSESearchStart   { type: "search_start";   query: string; tool_call_id: string; }
export interface SSESearchResults { type: "search_results"; urls: string[]; snippets: string[]; titles: string[]; result_count: number; tool_call_id: string; }
export interface SSESearchError   { type: "search_error";   error: string; tool_call_id: string; }
export interface SSEToolStart     { type: "tool_start";     tool_name: string; tool_call_id: string; args: Record<string, unknown>; }
export interface SSEToolEnd       { type: "tool_end";       tool_name: string; tool_call_id: string; }
export interface SSEError         { type: "error";          error: string; code: string; }
export interface SSEEnd           { type: "end"; }

export type SSEEvent =
  | SSESession
  | SSEThinking
  | SSEContent
  | SSESearchStart
  | SSESearchResults
  | SSESearchError
  | SSEToolStart
  | SSEToolEnd
  | SSEError
  | SSEEnd;