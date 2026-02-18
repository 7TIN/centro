const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonObject = { [key: string]: JsonValue };

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  const payload = await parseResponseBody(response);

  if (!response.ok) {
    if (typeof payload === "object" && payload !== null) {
      const errorBody = payload as { message?: string; details?: unknown };
      throw new ApiError(
        errorBody.message ?? `Request failed with status ${response.status}`,
        response.status,
        errorBody.details,
      );
    }
    throw new ApiError(String(payload), response.status);
  }

  return payload as T;
}

export type HealthResponse = {
  status: string;
  environment: string;
  version: string;
  database: boolean;
  timestamp: string;
};

export type PersonResponse = {
  id: string;
  name: string;
  role: string | null;
  department: string | null;
  base_system_prompt: string | null;
  communication_style: JsonObject | null;
  is_active: boolean;
  metadata: JsonObject | null;
  created_at: string;
  updated_at: string;
};

export type PersonCreatePayload = {
  name: string;
  role?: string;
  department?: string;
  base_system_prompt?: string;
  communication_style?: JsonObject;
  metadata?: JsonObject;
};

export type PersonUpdatePayload = {
  name?: string;
  role?: string;
  department?: string;
  base_system_prompt?: string;
  communication_style?: JsonObject;
  is_active?: boolean;
  metadata?: JsonObject;
};

export type KnowledgeEntryResponse = {
  id: string;
  person_id: string;
  content: string;
  title: string | null;
  summary: string | null;
  source_type: string;
  source_reference: string | null;
  tags: string[] | null;
  priority: number;
  metadata: JsonObject | null;
  created_at: string;
  updated_at: string;
};

export type KnowledgeEntryCreatePayload = {
  content: string;
  title?: string;
  summary?: string;
  source_type: string;
  source_reference?: string;
  tags?: string[];
  priority?: number;
  metadata?: JsonObject;
};

export type ChatRequestPayload = {
  person_id: string;
  message: string;
  conversation_id?: string;
  system_prompt?: string;
  person_identity?: string;
  knowledge_text?: string;
  knowledge_files?: string[];
  use_retrieval?: boolean;
  retrieval_top_k?: number;
};

export type ChatResponse = {
  response: string;
  conversation_id: string;
  message_id: string;
  metadata: JsonObject;
};

export type RetrievalIndexPayload = {
  person_id: string;
  source?: string;
  knowledge_text?: string;
  knowledge_files?: string[];
};

export type RetrievalIndexResponse = {
  person_id: string;
  indexed_chunks: number;
  source: string;
};

export type RetrievalSearchPayload = {
  person_id: string;
  query: string;
  top_k?: number;
  min_score?: number;
};

export type RetrievedDocument = {
  id: string;
  score: number;
  source: string | null;
  content: string;
  retrieval_mode: string | null;
  metadata: JsonObject;
};

export type RetrievalSearchResponse = {
  person_id: string;
  query: string;
  results: RetrievedDocument[];
};

export type RetrievalSourceDeletePayload = {
  person_id: string;
  source: string;
};

export type RetrievalSourceReplacePayload = {
  person_id: string;
  source: string;
  knowledge_text?: string;
  knowledge_files?: string[];
};

export type RetrievalSourceActionResponse = {
  person_id: string;
  source: string;
  deleted_chunks: number;
  indexed_chunks: number;
};

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health", { method: "GET" });
}

export function listPersons(): Promise<PersonResponse[]> {
  return request<PersonResponse[]>("/v1/persons", { method: "GET" });
}

export function getPerson(personId: string): Promise<PersonResponse> {
  return request<PersonResponse>(`/v1/persons/${personId}`, { method: "GET" });
}

export function createPerson(
  payload: PersonCreatePayload,
): Promise<PersonResponse> {
  return request<PersonResponse>("/v1/persons", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updatePerson(
  personId: string,
  payload: PersonUpdatePayload,
): Promise<PersonResponse> {
  return request<PersonResponse>(`/v1/persons/${personId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function addKnowledgeEntry(
  personId: string,
  payload: KnowledgeEntryCreatePayload,
): Promise<KnowledgeEntryResponse> {
  return request<KnowledgeEntryResponse>(`/v1/persons/${personId}/knowledge`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listKnowledgeEntries(
  personId: string,
): Promise<KnowledgeEntryResponse[]> {
  return request<KnowledgeEntryResponse[]>(`/v1/persons/${personId}/knowledge`, {
    method: "GET",
  });
}

export function chat(payload: ChatRequestPayload): Promise<ChatResponse> {
  return request<ChatResponse>("/v1/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function retrievalIndex(
  payload: RetrievalIndexPayload,
): Promise<RetrievalIndexResponse> {
  return request<RetrievalIndexResponse>("/v1/retrieval/index", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function retrievalSearch(
  payload: RetrievalSearchPayload,
): Promise<RetrievalSearchResponse> {
  return request<RetrievalSearchResponse>("/v1/retrieval/search", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function retrievalDeleteSource(
  payload: RetrievalSourceDeletePayload,
): Promise<RetrievalSourceActionResponse> {
  return request<RetrievalSourceActionResponse>("/v1/retrieval/source/delete", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function retrievalReplaceSource(
  payload: RetrievalSourceReplacePayload,
): Promise<RetrievalSourceActionResponse> {
  return request<RetrievalSourceActionResponse>("/v1/retrieval/source/replace", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
