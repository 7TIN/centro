"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  addKnowledgeEntry,
  chat,
  createPerson,
  getApiBaseUrl,
  getHealth,
  type HealthResponse,
  listKnowledgeEntries,
  listPersons,
  retrievalDeleteSource,
  retrievalIndex,
  retrievalReplaceSource,
  retrievalSearch,
  type RetrievedDocument,
  type JsonObject,
  type KnowledgeEntryResponse,
  type PersonResponse,
  updatePerson,
} from "@/lib/api";

type ChatTurn = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  metadata?: JsonObject;
};

function asOptional(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function parseJsonObject(
  value: string,
  label: string,
): JsonObject | undefined {
  if (!value.trim()) {
    return undefined;
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error(`${label} must be valid JSON.`);
  }

  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object.`);
  }
  return parsed as JsonObject;
}

function parseCsv(value: string): string[] | undefined {
  const parts = value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return parts.length > 0 ? parts : undefined;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function formatError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed.";
}

function JsonView({ value }: { value: unknown }) {
  return (
    <pre className="overflow-x-auto rounded-md border border-neutral-200 bg-neutral-50 p-3 font-mono text-xs text-neutral-800">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function FrontendWorkbench() {
  const apiBaseUrl = getApiBaseUrl();

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [persons, setPersons] = useState<PersonResponse[]>([]);
  const [activePersonId, setActivePersonId] = useState("");
  const [personLoading, setPersonLoading] = useState(false);
  const [personError, setPersonError] = useState<string | null>(null);
  const [personSuccess, setPersonSuccess] = useState<string | null>(null);

  const [createName, setCreateName] = useState("");
  const [createRole, setCreateRole] = useState("");
  const [createDepartment, setCreateDepartment] = useState("");
  const [createPrompt, setCreatePrompt] = useState("");
  const [createStyleJson, setCreateStyleJson] = useState("");
  const [createMetadataJson, setCreateMetadataJson] = useState("");

  const [updateRole, setUpdateRole] = useState("");
  const [updateDepartment, setUpdateDepartment] = useState("");
  const [updatePrompt, setUpdatePrompt] = useState("");
  const [updateStyleJson, setUpdateStyleJson] = useState("");
  const [updateMetadataJson, setUpdateMetadataJson] = useState("");

  const [knowledge, setKnowledge] = useState<KnowledgeEntryResponse[]>([]);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null);
  const [knowledgeSuccess, setKnowledgeSuccess] = useState<string | null>(null);

  const [knowledgeTitle, setKnowledgeTitle] = useState("");
  const [knowledgeSummary, setKnowledgeSummary] = useState("");
  const [knowledgeSourceType, setKnowledgeSourceType] = useState("manual");
  const [knowledgeSourceRef, setKnowledgeSourceRef] = useState("");
  const [knowledgeTags, setKnowledgeTags] = useState("");
  const [knowledgePriority, setKnowledgePriority] = useState("5");
  const [knowledgeMetadataJson, setKnowledgeMetadataJson] = useState("");
  const [knowledgeContent, setKnowledgeContent] = useState("");

  const [conversationId, setConversationId] = useState("");
  const [chatMessage, setChatMessage] = useState("");
  const [chatSystemPrompt, setChatSystemPrompt] = useState("");
  const [chatPersonIdentity, setChatPersonIdentity] = useState("");
  const [chatKnowledgeText, setChatKnowledgeText] = useState("");
  const [chatKnowledgeFiles, setChatKnowledgeFiles] = useState("");
  const [chatUseRetrieval, setChatUseRetrieval] = useState(false);
  const [chatTopK, setChatTopK] = useState("5");
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([]);
  const [chatMetadata, setChatMetadata] = useState<JsonObject | null>(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const [indexSource, setIndexSource] = useState("manual");
  const [indexKnowledgeText, setIndexKnowledgeText] = useState("");
  const [indexKnowledgeFiles, setIndexKnowledgeFiles] = useState("");
  const [indexLoading, setIndexLoading] = useState(false);
  const [indexStatus, setIndexStatus] = useState<string | null>(null);
  const [indexError, setIndexError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchTopK, setSearchTopK] = useState("5");
  const [searchMinScore, setSearchMinScore] = useState("0");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<RetrievedDocument[]>([]);

  const [sourceActionSource, setSourceActionSource] = useState("");
  const [replaceKnowledgeText, setReplaceKnowledgeText] = useState("");
  const [replaceKnowledgeFiles, setReplaceKnowledgeFiles] = useState("");
  const [sourceActionLoading, setSourceActionLoading] = useState(false);
  const [sourceActionStatus, setSourceActionStatus] = useState<string | null>(null);
  const [sourceActionError, setSourceActionError] = useState<string | null>(null);

  const activePerson = useMemo(
    () => persons.find((person) => person.id === activePersonId) ?? null,
    [activePersonId, persons],
  );

  const refreshHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const response = await getHealth();
      setHealth(response);
    } catch (error: unknown) {
      setHealthError(formatError(error));
    } finally {
      setHealthLoading(false);
    }
  }, []);

  const refreshPersons = useCallback(async () => {
    setPersonLoading(true);
    setPersonError(null);
    try {
      const response = await listPersons();
      setPersons(response);
      setActivePersonId((currentId) => {
        if (!currentId && response.length > 0) {
          return response[0].id;
        }
        if (currentId && !response.some((person) => person.id === currentId)) {
          return response[0]?.id ?? "";
        }
        return currentId;
      });
    } catch (error: unknown) {
      setPersonError(formatError(error));
    } finally {
      setPersonLoading(false);
    }
  }, []);

  const refreshKnowledge = useCallback(async () => {
    if (!activePersonId) {
      setKnowledge([]);
      return;
    }

    setKnowledgeLoading(true);
    setKnowledgeError(null);
    try {
      const response = await listKnowledgeEntries(activePersonId);
      setKnowledge(response);
    } catch (error: unknown) {
      setKnowledgeError(formatError(error));
    } finally {
      setKnowledgeLoading(false);
    }
  }, [activePersonId]);

  useEffect(() => {
    void refreshHealth();
    void refreshPersons();
  }, [refreshHealth, refreshPersons]);

  useEffect(() => {
    if (activePersonId) {
      void refreshKnowledge();
    } else {
      setKnowledge([]);
    }
  }, [activePersonId, refreshKnowledge]);

  async function handleCreatePerson() {
    setPersonError(null);
    setPersonSuccess(null);

    try {
      const payload = {
        name: createName.trim(),
        role: asOptional(createRole),
        department: asOptional(createDepartment),
        base_system_prompt: asOptional(createPrompt),
        communication_style: parseJsonObject(
          createStyleJson,
          "Communication style",
        ),
        metadata: parseJsonObject(createMetadataJson, "Metadata"),
      };

      if (!payload.name) {
        throw new Error("Name is required.");
      }

      const created = await createPerson(payload);
      setPersonSuccess(`Created person ${created.name}.`);
      setCreateName("");
      setCreateRole("");
      setCreateDepartment("");
      setCreatePrompt("");
      setCreateStyleJson("");
      setCreateMetadataJson("");
      await refreshPersons();
      setActivePersonId(created.id);
    } catch (error: unknown) {
      setPersonError(formatError(error));
    }
  }

  async function handleUpdatePerson() {
    if (!activePersonId) {
      setPersonError("Select a person first.");
      return;
    }

    setPersonError(null);
    setPersonSuccess(null);

    try {
      const payload = {
        role: asOptional(updateRole),
        department: asOptional(updateDepartment),
        base_system_prompt: asOptional(updatePrompt),
        communication_style: parseJsonObject(
          updateStyleJson,
          "Update communication style",
        ),
        metadata: parseJsonObject(updateMetadataJson, "Update metadata"),
      };

      const hasPayload = Object.values(payload).some(
        (value) => value !== undefined,
      );
      if (!hasPayload) {
        throw new Error("Provide at least one field to patch.");
      }

      const updated = await updatePerson(activePersonId, payload);
      setPersonSuccess(`Updated person ${updated.name}.`);
      setUpdateRole("");
      setUpdateDepartment("");
      setUpdatePrompt("");
      setUpdateStyleJson("");
      setUpdateMetadataJson("");
      await refreshPersons();
    } catch (error: unknown) {
      setPersonError(formatError(error));
    }
  }

  async function handleAddKnowledge() {
    if (!activePersonId) {
      setKnowledgeError("Select a person first.");
      return;
    }

    setKnowledgeError(null);
    setKnowledgeSuccess(null);

    try {
      const priorityAsNumber = Number(knowledgePriority);
      if (!knowledgeContent.trim()) {
        throw new Error("Knowledge content is required.");
      }
      if (!knowledgeSourceType.trim()) {
        throw new Error("Source type is required.");
      }
      if (
        !Number.isFinite(priorityAsNumber) ||
        priorityAsNumber < 1 ||
        priorityAsNumber > 10
      ) {
        throw new Error("Priority must be a number from 1 to 10.");
      }

      await addKnowledgeEntry(activePersonId, {
        content: knowledgeContent.trim(),
        title: asOptional(knowledgeTitle),
        summary: asOptional(knowledgeSummary),
        source_type: knowledgeSourceType.trim(),
        source_reference: asOptional(knowledgeSourceRef),
        tags: parseCsv(knowledgeTags),
        priority: priorityAsNumber,
        metadata: parseJsonObject(knowledgeMetadataJson, "Knowledge metadata"),
      });

      setKnowledgeSuccess("Knowledge entry added.");
      setKnowledgeTitle("");
      setKnowledgeSummary("");
      setKnowledgeSourceType("manual");
      setKnowledgeSourceRef("");
      setKnowledgeTags("");
      setKnowledgePriority("5");
      setKnowledgeMetadataJson("");
      setKnowledgeContent("");
      await refreshKnowledge();
    } catch (error: unknown) {
      setKnowledgeError(formatError(error));
    }
  }

  async function handleChat() {
    if (!activePersonId) {
      setChatError("Select a person first.");
      return;
    }

    setChatError(null);
    if (!chatMessage.trim()) {
      setChatError("Message is required.");
      return;
    }

    const userTurn: ChatTurn = {
      id: crypto.randomUUID(),
      role: "user",
      content: chatMessage.trim(),
      timestamp: new Date().toISOString(),
    };

    setChatTurns((prev) => [...prev, userTurn]);
    setChatLoading(true);
    try {
      const topK = Number(chatTopK);
      const response = await chat({
        person_id: activePersonId,
        message: chatMessage.trim(),
        conversation_id: asOptional(conversationId),
        system_prompt: asOptional(chatSystemPrompt),
        person_identity: asOptional(chatPersonIdentity),
        knowledge_text: asOptional(chatKnowledgeText),
        knowledge_files: parseCsv(chatKnowledgeFiles),
        use_retrieval: chatUseRetrieval,
        retrieval_top_k:
          Number.isFinite(topK) && topK > 0 ? Math.trunc(topK) : undefined,
      });

      setConversationId(response.conversation_id);
      setChatMetadata(response.metadata);
      setChatTurns((prev) => [
        ...prev,
        {
          id: response.message_id,
          role: "assistant",
          content: response.response,
          timestamp: new Date().toISOString(),
          metadata: response.metadata,
        },
      ]);
      setChatMessage("");
    } catch (error: unknown) {
      setChatError(formatError(error));
    } finally {
      setChatLoading(false);
    }
  }

  async function handleIndexKnowledge() {
    if (!activePersonId) {
      setIndexError("Select a person first.");
      return;
    }

    setIndexError(null);
    setIndexStatus(null);
    setIndexLoading(true);

    try {
      const response = await retrievalIndex({
        person_id: activePersonId,
        source: asOptional(indexSource),
        knowledge_text: asOptional(indexKnowledgeText),
        knowledge_files: parseCsv(indexKnowledgeFiles),
      });
      setIndexStatus(
        `Indexed ${response.indexed_chunks} chunks for source ${response.source}.`,
      );
      setIndexKnowledgeText("");
      setIndexKnowledgeFiles("");
    } catch (error: unknown) {
      setIndexError(formatError(error));
    } finally {
      setIndexLoading(false);
    }
  }

  async function handleSearchKnowledge() {
    if (!activePersonId) {
      setSearchError("Select a person first.");
      return;
    }
    if (!searchQuery.trim()) {
      setSearchError("Search query is required.");
      return;
    }

    setSearchError(null);
    setSearchLoading(true);

    try {
      const topK = Math.trunc(Number(searchTopK));
      const minScore = Number(searchMinScore);
      const response = await retrievalSearch({
        person_id: activePersonId,
        query: searchQuery.trim(),
        top_k: Number.isFinite(topK) && topK > 0 ? topK : 5,
        min_score: Number.isFinite(minScore) ? minScore : 0,
      });
      setSearchResults(response.results);
    } catch (error: unknown) {
      setSearchError(formatError(error));
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }

  async function handleDeleteSource() {
    if (!activePersonId) {
      setSourceActionError("Select a person first.");
      return;
    }
    if (!sourceActionSource.trim()) {
      setSourceActionError("Source is required.");
      return;
    }

    setSourceActionError(null);
    setSourceActionStatus(null);
    setSourceActionLoading(true);
    try {
      const response = await retrievalDeleteSource({
        person_id: activePersonId,
        source: sourceActionSource.trim(),
      });
      setSourceActionStatus(
        `Deleted ${response.deleted_chunks} chunks for source ${response.source}.`,
      );
    } catch (error: unknown) {
      setSourceActionError(formatError(error));
    } finally {
      setSourceActionLoading(false);
    }
  }

  async function handleReplaceSource() {
    if (!activePersonId) {
      setSourceActionError("Select a person first.");
      return;
    }
    if (!sourceActionSource.trim()) {
      setSourceActionError("Source is required.");
      return;
    }

    setSourceActionError(null);
    setSourceActionStatus(null);
    setSourceActionLoading(true);
    try {
      const response = await retrievalReplaceSource({
        person_id: activePersonId,
        source: sourceActionSource.trim(),
        knowledge_text: asOptional(replaceKnowledgeText),
        knowledge_files: parseCsv(replaceKnowledgeFiles),
      });
      setSourceActionStatus(
        `Replaced source ${response.source}: deleted ${response.deleted_chunks}, indexed ${response.indexed_chunks}.`,
      );
      setReplaceKnowledgeText("");
      setReplaceKnowledgeFiles("");
    } catch (error: unknown) {
      setSourceActionError(formatError(error));
    } finally {
      setSourceActionLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
        <header className="rounded-md border border-neutral-200 bg-white p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-[0.16em] text-neutral-500">
                Person X AI Assistant
              </p>
              <h1 className="text-2xl font-semibold tracking-tight">
                Frontend Console
              </h1>
              <p className="max-w-3xl text-sm text-neutral-600">
                Capability console for a personal AI teammate assistant: health,
                person profiles, knowledge, chat, and retrieval.
              </p>
            </div>
            <div className="flex flex-col items-start gap-2 rounded-md border border-neutral-200 p-3 text-xs md:items-end">
              <span className="text-neutral-500">API Base URL</span>
              <code className="font-mono text-neutral-900">{apiBaseUrl}</code>
            </div>
          </div>
        </header>

        <Tabs defaultValue="health" className="w-full">
          <TabsList className="grid h-auto w-full grid-cols-3 rounded-md border border-neutral-200 bg-white p-1">
            <TabsTrigger
              className="rounded-md data-[state=active]:bg-neutral-100"
              value="health"
            >
              Health
            </TabsTrigger>
            <TabsTrigger
              className="rounded-md data-[state=active]:bg-neutral-100"
              value="persona-chat"
            >
              Persona + Chat
            </TabsTrigger>
            <TabsTrigger
              className="rounded-md data-[state=active]:bg-neutral-100"
              value="retrieval"
            >
              Retrieval
            </TabsTrigger>
          </TabsList>

          <TabsContent className="mt-4 space-y-4" value="health">
            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">Service Health</CardTitle>
                <CardDescription className="text-neutral-600">
                  Verify backend health and runtime status.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    className="rounded-md"
                    disabled={healthLoading}
                    onClick={refreshHealth}
                    variant="outline"
                  >
                    {healthLoading ? "Checking..." : "Run Health Check"}
                  </Button>
                  {health?.status ? (
                    <Badge
                      className="rounded-md border-neutral-300 bg-neutral-100 text-neutral-900"
                      variant="outline"
                    >
                      {health.status}
                    </Badge>
                  ) : null}
                </div>
                {healthError ? (
                  <p className="text-sm text-neutral-700">{healthError}</p>
                ) : null}
                {health ? (
                  <div className="grid gap-3 rounded-md border border-neutral-200 bg-white p-4 text-sm sm:grid-cols-2">
                    <div>
                      <p className="text-neutral-500">Environment</p>
                      <p className="font-medium">{health.environment}</p>
                    </div>
                    <div>
                      <p className="text-neutral-500">Version</p>
                      <p className="font-medium">{health.version}</p>
                    </div>
                    <div>
                      <p className="text-neutral-500">Database</p>
                      <p className="font-medium">
                        {health.database ? "Connected" : "Not configured"}
                      </p>
                    </div>
                    <div>
                      <p className="text-neutral-500">Timestamp</p>
                      <p className="font-medium">{formatDate(health.timestamp)}</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-neutral-600">
                    No health response yet.
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent className="mt-4 space-y-4" value="persona-chat">
            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">Person Profiles</CardTitle>
                <CardDescription className="text-neutral-600">
                  Create, select, and patch persona profiles.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex flex-wrap gap-3">
                  <Button
                    className="rounded-md"
                    disabled={personLoading}
                    onClick={refreshPersons}
                    variant="outline"
                  >
                    {personLoading ? "Refreshing..." : "Refresh Persons"}
                  </Button>
                  {activePerson ? (
                    <Badge
                      className="rounded-md border-neutral-300 bg-neutral-100 text-neutral-900"
                      variant="outline"
                    >
                      Active: {activePerson.name}
                    </Badge>
                  ) : (
                    <Badge
                      className="rounded-md border-neutral-300 bg-neutral-100 text-neutral-700"
                      variant="outline"
                    >
                      No Active Person
                    </Badge>
                  )}
                </div>

                {personError ? (
                  <p className="text-sm text-neutral-700">{personError}</p>
                ) : null}
                {personSuccess ? (
                  <p className="text-sm text-neutral-700">{personSuccess}</p>
                ) : null}

                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-3 rounded-md border border-neutral-200 p-4">
                    <h3 className="text-sm font-medium">Create Person</h3>
                    <div className="space-y-2">
                      <Label htmlFor="create-name">Name</Label>
                      <Input
                        id="create-name"
                        onChange={(event) => setCreateName(event.target.value)}
                        placeholder="Person X"
                        value={createName}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="create-role">Role</Label>
                      <Input
                        id="create-role"
                        onChange={(event) => setCreateRole(event.target.value)}
                        placeholder="Engineering Manager"
                        value={createRole}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="create-department">Department</Label>
                      <Input
                        id="create-department"
                        onChange={(event) =>
                          setCreateDepartment(event.target.value)
                        }
                        placeholder="Platform"
                        value={createDepartment}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="create-prompt">Base System Prompt</Label>
                      <Textarea
                        className="min-h-[84px]"
                        id="create-prompt"
                        onChange={(event) => setCreatePrompt(event.target.value)}
                        placeholder="You are concise and pragmatic."
                        value={createPrompt}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="create-style">Communication Style JSON</Label>
                      <Textarea
                        className="min-h-[84px] font-mono text-xs"
                        id="create-style"
                        onChange={(event) =>
                          setCreateStyleJson(event.target.value)
                        }
                        placeholder='{"tone":"direct","formality":"medium"}'
                        value={createStyleJson}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="create-metadata">Metadata JSON</Label>
                      <Textarea
                        className="min-h-[84px] font-mono text-xs"
                        id="create-metadata"
                        onChange={(event) =>
                          setCreateMetadataJson(event.target.value)
                        }
                        placeholder='{"location":"remote"}'
                        value={createMetadataJson}
                      />
                    </div>
                    <Button
                      className="w-full rounded-md"
                      onClick={handleCreatePerson}
                      variant="outline"
                    >
                      Create Person
                    </Button>
                  </div>

                  <div className="space-y-3 rounded-md border border-neutral-200 p-4">
                    <h3 className="text-sm font-medium">Patch Active Person</h3>
                    <div className="space-y-2">
                      <Label htmlFor="update-role">Role</Label>
                      <Input
                        id="update-role"
                        onChange={(event) => setUpdateRole(event.target.value)}
                        placeholder="Optional new role"
                        value={updateRole}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="update-department">Department</Label>
                      <Input
                        id="update-department"
                        onChange={(event) => setUpdateDepartment(event.target.value)}
                        placeholder="Optional new department"
                        value={updateDepartment}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="update-prompt">Base System Prompt</Label>
                      <Textarea
                        className="min-h-[84px]"
                        id="update-prompt"
                        onChange={(event) => setUpdatePrompt(event.target.value)}
                        placeholder="Optional override"
                        value={updatePrompt}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="update-style">
                        Communication Style JSON
                      </Label>
                      <Textarea
                        className="min-h-[84px] font-mono text-xs"
                        id="update-style"
                        onChange={(event) => setUpdateStyleJson(event.target.value)}
                        placeholder='{"tone":"analytical"}'
                        value={updateStyleJson}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="update-metadata">Metadata JSON</Label>
                      <Textarea
                        className="min-h-[84px] font-mono text-xs"
                        id="update-metadata"
                        onChange={(event) =>
                          setUpdateMetadataJson(event.target.value)
                        }
                        placeholder='{"timezone":"UTC"}'
                        value={updateMetadataJson}
                      />
                    </div>
                    <Button
                      className="w-full rounded-md"
                      onClick={handleUpdatePerson}
                      variant="outline"
                    >
                      Patch Active Person
                    </Button>
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <h3 className="text-sm font-medium">Available Persons</h3>
                  {persons.length === 0 ? (
                    <p className="text-sm text-neutral-600">
                      No person profiles found.
                    </p>
                  ) : (
                    <div className="grid gap-3">
                      {persons.map((person) => (
                        <button
                          className="rounded-md border border-neutral-200 p-3 text-left transition-colors hover:bg-neutral-50"
                          key={person.id}
                          onClick={() => setActivePersonId(person.id)}
                          type="button"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="space-y-1">
                              <p className="text-sm font-medium">{person.name}</p>
                              <p className="text-xs text-neutral-600">
                                {person.role ?? "No role"} |{" "}
                                {person.department ?? "No department"}
                              </p>
                            </div>
                            <Badge
                              className="rounded-md border-neutral-300 bg-neutral-100 text-neutral-800"
                              variant="outline"
                            >
                              {person.id === activePersonId
                                ? "Active"
                                : "Select"}
                            </Badge>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">Knowledge Entries</CardTitle>
                <CardDescription className="text-neutral-600">
                  Add and review person-scoped knowledge.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {knowledgeError ? (
                  <p className="text-sm text-neutral-700">{knowledgeError}</p>
                ) : null}
                {knowledgeSuccess ? (
                  <p className="text-sm text-neutral-700">{knowledgeSuccess}</p>
                ) : null}

                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-3 rounded-md border border-neutral-200 p-4">
                    <h3 className="text-sm font-medium">Add Knowledge</h3>
                    <div className="space-y-2">
                      <Label htmlFor="knowledge-title">Title</Label>
                      <Input
                        id="knowledge-title"
                        onChange={(event) => setKnowledgeTitle(event.target.value)}
                        placeholder="Deployment note"
                        value={knowledgeTitle}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="knowledge-summary">Summary</Label>
                      <Textarea
                        className="min-h-[72px]"
                        id="knowledge-summary"
                        onChange={(event) =>
                          setKnowledgeSummary(event.target.value)
                        }
                        placeholder="Short summary"
                        value={knowledgeSummary}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="knowledge-source-type">Source Type</Label>
                      <Input
                        id="knowledge-source-type"
                        onChange={(event) =>
                          setKnowledgeSourceType(event.target.value)
                        }
                        value={knowledgeSourceType}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="knowledge-source-ref">
                        Source Reference
                      </Label>
                      <Input
                        id="knowledge-source-ref"
                        onChange={(event) =>
                          setKnowledgeSourceRef(event.target.value)
                        }
                        placeholder="docs/deploy.md"
                        value={knowledgeSourceRef}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="knowledge-tags">Tags (comma-separated)</Label>
                      <Input
                        id="knowledge-tags"
                        onChange={(event) => setKnowledgeTags(event.target.value)}
                        placeholder="deploy,release"
                        value={knowledgeTags}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="knowledge-priority">Priority (1-10)</Label>
                      <Input
                        id="knowledge-priority"
                        onChange={(event) =>
                          setKnowledgePriority(event.target.value)
                        }
                        value={knowledgePriority}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="knowledge-metadata">Metadata JSON</Label>
                      <Textarea
                        className="min-h-[84px] font-mono text-xs"
                        id="knowledge-metadata"
                        onChange={(event) =>
                          setKnowledgeMetadataJson(event.target.value)
                        }
                        placeholder='{"audience":"eng"}'
                        value={knowledgeMetadataJson}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="knowledge-content">Content</Label>
                      <Textarea
                        className="min-h-[140px]"
                        id="knowledge-content"
                        onChange={(event) =>
                          setKnowledgeContent(event.target.value)
                        }
                        placeholder="Detailed knowledge content"
                        value={knowledgeContent}
                      />
                    </div>
                    <Button
                      className="w-full rounded-md"
                      onClick={handleAddKnowledge}
                      variant="outline"
                    >
                      Add Knowledge Entry
                    </Button>
                  </div>

                  <div className="space-y-3 rounded-md border border-neutral-200 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-sm font-medium">Current Knowledge</h3>
                      <Button
                        className="rounded-md"
                        disabled={knowledgeLoading || !activePersonId}
                        onClick={refreshKnowledge}
                        variant="outline"
                      >
                        {knowledgeLoading ? "Refreshing..." : "Refresh"}
                      </Button>
                    </div>
                    {!activePersonId ? (
                      <p className="text-sm text-neutral-600">
                        Select a person to view knowledge.
                      </p>
                    ) : knowledge.length === 0 ? (
                      <p className="text-sm text-neutral-600">
                        No knowledge entries yet.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {knowledge.map((entry) => (
                          <div
                            className="rounded-md border border-neutral-200 p-3"
                            key={entry.id}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="space-y-1">
                                <p className="text-sm font-medium">
                                  {entry.title ?? "Untitled"}
                                </p>
                                <p className="text-xs text-neutral-600">
                                  {entry.source_type} | priority {entry.priority}
                                </p>
                              </div>
                              <p className="text-xs text-neutral-500">
                                {formatDate(entry.created_at)}
                              </p>
                            </div>
                            <p className="mt-2 line-clamp-4 text-sm text-neutral-800">
                              {entry.content}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">Chat (Gemini Path)</CardTitle>
                <CardDescription className="text-neutral-600">
                  Send persona-aware chat requests with optional retrieval.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {chatError ? <p className="text-sm text-neutral-700">{chatError}</p> : null}

                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-3 rounded-md border border-neutral-200 p-4">
                    <div className="space-y-2">
                      <Label htmlFor="conversation-id">Conversation ID</Label>
                      <Input
                        id="conversation-id"
                        onChange={(event) => setConversationId(event.target.value)}
                        placeholder="Optional existing conversation id"
                        value={conversationId}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="chat-system-prompt">
                        System Prompt Override
                      </Label>
                      <Textarea
                        className="min-h-[90px]"
                        id="chat-system-prompt"
                        onChange={(event) =>
                          setChatSystemPrompt(event.target.value)
                        }
                        placeholder="Optional system prompt override"
                        value={chatSystemPrompt}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="chat-identity">Person Identity Override</Label>
                      <Textarea
                        className="min-h-[90px]"
                        id="chat-identity"
                        onChange={(event) =>
                          setChatPersonIdentity(event.target.value)
                        }
                        placeholder="Optional identity block"
                        value={chatPersonIdentity}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="chat-knowledge-text">
                        Inline Knowledge Text
                      </Label>
                      <Textarea
                        className="min-h-[90px]"
                        id="chat-knowledge-text"
                        onChange={(event) =>
                          setChatKnowledgeText(event.target.value)
                        }
                        placeholder="Optional inline knowledge"
                        value={chatKnowledgeText}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="chat-knowledge-files">
                        Knowledge Files (comma-separated paths)
                      </Label>
                      <Input
                        id="chat-knowledge-files"
                        onChange={(event) =>
                          setChatKnowledgeFiles(event.target.value)
                        }
                        placeholder="data/knowledge_base/deploy_notes.txt"
                        value={chatKnowledgeFiles}
                      />
                    </div>
                    <div className="flex flex-wrap items-center gap-5 rounded-md border border-neutral-200 px-3 py-2">
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={chatUseRetrieval}
                          id="use-retrieval"
                          onCheckedChange={(checked) => setChatUseRetrieval(checked)}
                        />
                        <Label htmlFor="use-retrieval">Use Retrieval</Label>
                      </div>
                      <div className="flex items-center gap-2">
                        <Label htmlFor="chat-top-k">Top K</Label>
                        <Input
                          className="w-20"
                          id="chat-top-k"
                          onChange={(event) => setChatTopK(event.target.value)}
                          value={chatTopK}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3 rounded-md border border-neutral-200 p-4">
                    <div className="space-y-2">
                      <Label htmlFor="chat-message">Message</Label>
                      <Textarea
                        className="min-h-[140px]"
                        id="chat-message"
                        onChange={(event) => setChatMessage(event.target.value)}
                        placeholder="Ask a question to the active person"
                        value={chatMessage}
                      />
                    </div>
                    <Button
                      className="w-full rounded-md"
                      disabled={chatLoading}
                      onClick={handleChat}
                      variant="outline"
                    >
                      {chatLoading ? "Sending..." : "Send Chat Request"}
                    </Button>
                    {chatMetadata ? <JsonView value={chatMetadata} /> : null}
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <h3 className="text-sm font-medium">Conversation Log</h3>
                  {chatTurns.length === 0 ? (
                    <p className="text-sm text-neutral-600">
                      No messages sent yet.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {chatTurns.map((turn) => (
                        <div
                          className="rounded-md border border-neutral-200 p-3"
                          key={turn.id}
                        >
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <Badge
                              className="rounded-md border-neutral-300 bg-neutral-100 text-neutral-900"
                              variant="outline"
                            >
                              {turn.role}
                            </Badge>
                            <span className="text-xs text-neutral-500">
                              {formatDate(turn.timestamp)}
                            </span>
                          </div>
                          <p className="whitespace-pre-wrap text-sm text-neutral-900">
                            {turn.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent className="mt-4 space-y-4" value="retrieval">
            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">Retrieval Indexing</CardTitle>
                <CardDescription className="text-neutral-600">
                  Index text/files into person-scoped retrieval storage.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {indexError ? <p className="text-sm text-neutral-700">{indexError}</p> : null}
                {indexStatus ? <p className="text-sm text-neutral-700">{indexStatus}</p> : null}
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="index-source">Source</Label>
                    <Input
                      id="index-source"
                      onChange={(event) => setIndexSource(event.target.value)}
                      placeholder="runbook"
                      value={indexSource}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="index-files">
                      Knowledge Files (comma-separated paths)
                    </Label>
                    <Input
                      id="index-files"
                      onChange={(event) => setIndexKnowledgeFiles(event.target.value)}
                      placeholder="data/knowledge_base/deploy_notes.txt"
                      value={indexKnowledgeFiles}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="index-text">Knowledge Text</Label>
                  <Textarea
                    className="min-h-[140px]"
                    id="index-text"
                    onChange={(event) => setIndexKnowledgeText(event.target.value)}
                    placeholder="Text to index for retrieval"
                    value={indexKnowledgeText}
                  />
                </div>
                <Button
                  className="rounded-md"
                  disabled={indexLoading}
                  onClick={handleIndexKnowledge}
                  variant="outline"
                >
                  {indexLoading ? "Indexing..." : "Index Knowledge"}
                </Button>
              </CardContent>
            </Card>

            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">Retrieval Search</CardTitle>
                <CardDescription className="text-neutral-600">
                  Query indexed chunks and inspect sources/scores.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {searchError ? (
                  <p className="text-sm text-neutral-700">{searchError}</p>
                ) : null}
                <div className="grid gap-4 lg:grid-cols-3">
                  <div className="space-y-2 lg:col-span-2">
                    <Label htmlFor="search-query">Query</Label>
                    <Input
                      id="search-query"
                      onChange={(event) => setSearchQuery(event.target.value)}
                      placeholder="How do we deploy safely?"
                      value={searchQuery}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="search-top-k">Top K</Label>
                      <Input
                        id="search-top-k"
                        onChange={(event) => setSearchTopK(event.target.value)}
                        value={searchTopK}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="search-min-score">Min Score</Label>
                      <Input
                        id="search-min-score"
                        onChange={(event) => setSearchMinScore(event.target.value)}
                        value={searchMinScore}
                      />
                    </div>
                  </div>
                </div>
                <Button
                  className="rounded-md"
                  disabled={searchLoading}
                  onClick={handleSearchKnowledge}
                  variant="outline"
                >
                  {searchLoading ? "Searching..." : "Search Retrieval"}
                </Button>
                {searchResults.length === 0 ? (
                  <p className="text-sm text-neutral-600">
                    No retrieval results yet.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {searchResults.map((result) => (
                      <div
                        className="rounded-md border border-neutral-200 p-3"
                        key={result.id}
                      >
                        <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                          <Badge
                            className="rounded-md border-neutral-300 bg-neutral-100 text-neutral-900"
                            variant="outline"
                          >
                            score {result.score.toFixed(3)}
                          </Badge>
                          {result.source ? (
                            <Badge
                              className="rounded-md border-neutral-300 bg-neutral-100 text-neutral-900"
                              variant="outline"
                            >
                              {result.source}
                            </Badge>
                          ) : null}
                          {result.retrieval_mode ? (
                            <Badge
                              className="rounded-md border-neutral-300 bg-neutral-100 text-neutral-900"
                              variant="outline"
                            >
                              {result.retrieval_mode}
                            </Badge>
                          ) : null}
                        </div>
                        <p className="whitespace-pre-wrap text-sm text-neutral-900">
                          {result.content}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">
                  Retrieval Source Lifecycle
                </CardTitle>
                <CardDescription className="text-neutral-600">
                  Delete or replace all chunks for a source.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {sourceActionError ? (
                  <p className="text-sm text-neutral-700">{sourceActionError}</p>
                ) : null}
                {sourceActionStatus ? (
                  <p className="text-sm text-neutral-700">{sourceActionStatus}</p>
                ) : null}
                <div className="space-y-2">
                  <Label htmlFor="source-action-source">Source</Label>
                  <Input
                    id="source-action-source"
                    onChange={(event) => setSourceActionSource(event.target.value)}
                    placeholder="runbook"
                    value={sourceActionSource}
                  />
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="replace-knowledge-text">
                      Replace Knowledge Text
                    </Label>
                    <Textarea
                      className="min-h-[120px]"
                      id="replace-knowledge-text"
                      onChange={(event) =>
                        setReplaceKnowledgeText(event.target.value)
                      }
                      placeholder="New text for replacement"
                      value={replaceKnowledgeText}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="replace-knowledge-files">
                      Replace Knowledge Files
                    </Label>
                    <Input
                      id="replace-knowledge-files"
                      onChange={(event) =>
                        setReplaceKnowledgeFiles(event.target.value)
                      }
                      placeholder="data/knowledge_base/new_runbook.txt"
                      value={replaceKnowledgeFiles}
                    />
                  </div>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button
                    className="rounded-md"
                    disabled={sourceActionLoading}
                    onClick={handleDeleteSource}
                    variant="outline"
                  >
                    {sourceActionLoading ? "Working..." : "Delete Source Chunks"}
                  </Button>
                  <Button
                    className="rounded-md"
                    disabled={sourceActionLoading}
                    onClick={handleReplaceSource}
                    variant="outline"
                  >
                    {sourceActionLoading ? "Working..." : "Replace Source Chunks"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
