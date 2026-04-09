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

export type KnowledgeEntryUpdatePayload = {
  content?: string;
  title?: string;
  summary?: string;
  source_type?: string;
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

export type WikiPageSummary = {
  path: string;
  title: string;
  updated_at: string;
};

export type PersonWikiOverviewResponse = {
  person_id: string;
  root_path: string;
  index_content: string;
  log_content: string;
  pages: WikiPageSummary[];
};

export type TeamWikiOverviewResponse = {
  team_id: string;
  team_name: string;
  root_path: string;
  index_content: string;
  log_content: string;
  pages: WikiPageSummary[];
};

export type WikiPageResponse = {
  path: string;
  title: string;
  updated_at: string;
  content: string;
  person_id?: string;
  team_id?: string;
};

export type TeamKnowledgeUpsertPayload = {
  title: string;
  content: string;
  page_slug?: string;
  source_reference?: string;
  tags?: string[];
  updated_by?: string;
};

export type TeamKnowledgeUpsertResponse = {
  team_id: string;
  page_path: string;
  updated_at: string;
  synced_person_wikis: number;
};

export type DemoPersonSummary = {
  id: string;
  name: string;
  role: string | null;
  department: string | null;
  first_question: string | null;
  suggested_questions: string[];
};

export type DemoBootstrapResponse = {
  team_id: string;
  team_name: string;
  team_pages: number;
  synced_person_wikis: number;
  persons: DemoPersonSummary[];
  default_person_id: string | null;
};

export type GitHubIngestPayload = {
  owner: string;
  repo: string;
  person_id?: string;
  max_items?: number;
  include_open_prs?: boolean;
  include_open_issues?: boolean;
  include_recent_merged_prs?: boolean;
  attach_to_person?: boolean;
  team_page_slug?: string;
  updated_by?: string;
};

export type GitHubIngestResponse = {
  repository: string;
  source_url: string;
  fetched_at: string;
  counts: {
    open_prs: number;
    open_issues: number;
    merged_prs: number;
  };
  team_page_path: string;
  synced_person_wikis: number;
  person_id: string | null;
  person_knowledge_id: string | null;
};

export type SlackIngestPayload = {
  channel_id: string;
  person_id?: string;
  max_messages?: number;
  include_thread_replies?: boolean;
  attach_to_person?: boolean;
  team_page_slug?: string;
  updated_by?: string;
};

export type SlackIngestResponse = {
  workspace: string;
  channel_id: string;
  channel_name: string;
  fetched_at: string;
  counts: {
    messages: number;
    threads: number;
    thread_replies: number;
  };
  team_page_path: string;
  synced_person_wikis: number;
  person_id: string | null;
  person_knowledge_id: string | null;
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

export function updateKnowledgeEntry(
  personId: string,
  knowledgeId: string,
  payload: KnowledgeEntryUpdatePayload,
): Promise<KnowledgeEntryResponse> {
  return request<KnowledgeEntryResponse>(
    `/v1/persons/${personId}/knowledge/${knowledgeId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
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

export function demoBootstrap(): Promise<DemoBootstrapResponse> {
  return request<DemoBootstrapResponse>("/v1/demo/bootstrap", {
    method: "POST",
  });
}

export function getPersonWiki(personId: string): Promise<PersonWikiOverviewResponse> {
  return request<PersonWikiOverviewResponse>(`/v1/persons/${personId}/wiki`, {
    method: "GET",
  });
}

export function getPersonWikiPage(
  personId: string,
  pagePath: string,
): Promise<WikiPageResponse> {
  return request<WikiPageResponse>(
    `/v1/persons/${personId}/wiki/pages/${pagePath}`,
    { method: "GET" },
  );
}

export function getTeamWiki(): Promise<TeamWikiOverviewResponse> {
  return request<TeamWikiOverviewResponse>("/v1/team/wiki", { method: "GET" });
}

export function getTeamWikiPage(pagePath: string): Promise<WikiPageResponse> {
  return request<WikiPageResponse>(`/v1/team/wiki/pages/${pagePath}`, {
    method: "GET",
  });
}

export function upsertTeamKnowledge(
  payload: TeamKnowledgeUpsertPayload,
): Promise<TeamKnowledgeUpsertResponse> {
  return request<TeamKnowledgeUpsertResponse>("/v1/team/wiki/knowledge", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function ingestGitHub(
  payload: GitHubIngestPayload,
): Promise<GitHubIngestResponse> {
  return request<GitHubIngestResponse>("/v1/ingest/github", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function ingestSlack(
  payload: SlackIngestPayload,
): Promise<SlackIngestResponse> {
  return request<SlackIngestResponse>("/v1/ingest/slack", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
