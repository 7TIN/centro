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
  listKnowledgeEntries,
  listPersons,
  retrievalDeleteSource,
  retrievalIndex,
  retrievalReplaceSource,
  retrievalSearch,
  type HealthResponse,
  type KnowledgeEntryResponse,
  type PersonResponse,
  type RetrievedDocument,
} from "@/lib/api";

type ChatTurn = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

function optional(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function parseCsv(value: string): string[] | undefined {
  const values = value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return values.length > 0 ? values : undefined;
}

function asError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed.";
}

export function FrontendWorkbench() {
  const apiBaseUrl = getApiBaseUrl();

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);

  const [persons, setPersons] = useState<PersonResponse[]>([]);
  const [activePersonId, setActivePersonId] = useState("");
  const [personName, setPersonName] = useState("");
  const [personRole, setPersonRole] = useState("");
  const [personDepartment, setPersonDepartment] = useState("");
  const [personPrompt, setPersonPrompt] = useState("");
  const [personStatus, setPersonStatus] = useState<string | null>(null);
  const [personError, setPersonError] = useState<string | null>(null);
  const [personLoading, setPersonLoading] = useState(false);

  const [knowledgeContent, setKnowledgeContent] = useState("");
  const [knowledgeSourceType, setKnowledgeSourceType] = useState("manual");
  const [knowledgeEntries, setKnowledgeEntries] = useState<KnowledgeEntryResponse[]>([]);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [knowledgeStatus, setKnowledgeStatus] = useState<string | null>(null);
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null);

  const [chatMessage, setChatMessage] = useState("");
  const [chatUseRetrieval, setChatUseRetrieval] = useState(false);
  const [chatTopK, setChatTopK] = useState("5");
  const [conversationId, setConversationId] = useState("");
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const [indexSource, setIndexSource] = useState("manual");
  const [indexText, setIndexText] = useState("");
  const [indexStatus, setIndexStatus] = useState<string | null>(null);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [indexLoading, setIndexLoading] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<RetrievedDocument[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);

  const [sourceName, setSourceName] = useState("");
  const [replaceText, setReplaceText] = useState("");
  const [sourceStatus, setSourceStatus] = useState<string | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [sourceLoading, setSourceLoading] = useState(false);

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
      setHealthError(asError(error));
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
        if (currentId && !response.some((item) => item.id === currentId)) {
          return response[0]?.id ?? "";
        }
        return currentId;
      });
    } catch (error: unknown) {
      setPersonError(asError(error));
    } finally {
      setPersonLoading(false);
    }
  }, []);

  const refreshKnowledge = useCallback(async () => {
    if (!activePersonId) {
      setKnowledgeEntries([]);
      return;
    }
    setKnowledgeLoading(true);
    setKnowledgeError(null);
    try {
      const response = await listKnowledgeEntries(activePersonId);
      setKnowledgeEntries(response);
    } catch (error: unknown) {
      setKnowledgeError(asError(error));
    } finally {
      setKnowledgeLoading(false);
    }
  }, [activePersonId]);

  useEffect(() => {
    void refreshHealth();
    void refreshPersons();
  }, [refreshHealth, refreshPersons]);

  useEffect(() => {
    void refreshKnowledge();
  }, [refreshKnowledge]);

  async function handleCreatePerson() {
    setPersonError(null);
    setPersonStatus(null);
    if (!personName.trim()) {
      setPersonError("Person name is required.");
      return;
    }

    try {
      const created = await createPerson({
        name: personName.trim(),
        role: optional(personRole),
        department: optional(personDepartment),
        base_system_prompt: optional(personPrompt),
      });
      setPersonStatus(`Created ${created.name}.`);
      setPersonName("");
      setPersonRole("");
      setPersonDepartment("");
      setPersonPrompt("");
      await refreshPersons();
      setActivePersonId(created.id);
    } catch (error: unknown) {
      setPersonError(asError(error));
    }
  }

  async function handleAddKnowledge() {
    if (!activePersonId) {
      setKnowledgeError("Select a person first.");
      return;
    }
    setKnowledgeError(null);
    setKnowledgeStatus(null);
    if (!knowledgeContent.trim()) {
      setKnowledgeError("Knowledge content is required.");
      return;
    }

    try {
      await addKnowledgeEntry(activePersonId, {
        content: knowledgeContent.trim(),
        source_type: knowledgeSourceType.trim() || "manual",
        priority: 5,
      });
      setKnowledgeStatus("Knowledge entry added.");
      setKnowledgeContent("");
      await refreshKnowledge();
    } catch (error: unknown) {
      setKnowledgeError(asError(error));
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

    setChatLoading(true);
    const message = chatMessage.trim();
    setChatTurns((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: message }]);

    try {
      const topK = Number(chatTopK);
      const response = await chat({
        person_id: activePersonId,
        message,
        conversation_id: optional(conversationId),
        use_retrieval: chatUseRetrieval,
        retrieval_top_k: Number.isFinite(topK) && topK > 0 ? Math.trunc(topK) : undefined,
      });

      setConversationId(response.conversation_id);
      setChatTurns((prev) => [
        ...prev,
        { id: response.message_id, role: "assistant", content: response.response },
      ]);
      setChatMessage("");
    } catch (error: unknown) {
      setChatError(asError(error));
    } finally {
      setChatLoading(false);
    }
  }

  async function handleIndex() {
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
        source: optional(indexSource),
        knowledge_text: optional(indexText),
      });
      setIndexStatus(`Indexed ${response.indexed_chunks} chunks for ${response.source}.`);
      setIndexText("");
    } catch (error: unknown) {
      setIndexError(asError(error));
    } finally {
      setIndexLoading(false);
    }
  }

  async function handleSearch() {
    if (!activePersonId) {
      setSearchError("Select a person first.");
      return;
    }
    if (!searchQuery.trim()) {
      setSearchError("Query is required.");
      return;
    }

    setSearchError(null);
    setSearchLoading(true);
    try {
      const response = await retrievalSearch({
        person_id: activePersonId,
        query: searchQuery.trim(),
        top_k: 5,
        min_score: 0,
      });
      setSearchResults(response.results);
    } catch (error: unknown) {
      setSearchError(asError(error));
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }

  async function handleDeleteSource() {
    if (!activePersonId) {
      setSourceError("Select a person first.");
      return;
    }
    if (!sourceName.trim()) {
      setSourceError("Source name is required.");
      return;
    }

    setSourceError(null);
    setSourceStatus(null);
    setSourceLoading(true);
    try {
      const response = await retrievalDeleteSource({
        person_id: activePersonId,
        source: sourceName.trim(),
      });
      setSourceStatus(`Deleted ${response.deleted_chunks} chunks for ${response.source}.`);
    } catch (error: unknown) {
      setSourceError(asError(error));
    } finally {
      setSourceLoading(false);
    }
  }

  async function handleReplaceSource() {
    if (!activePersonId) {
      setSourceError("Select a person first.");
      return;
    }
    if (!sourceName.trim()) {
      setSourceError("Source name is required.");
      return;
    }

    setSourceError(null);
    setSourceStatus(null);
    setSourceLoading(true);
    try {
      const response = await retrievalReplaceSource({
        person_id: activePersonId,
        source: sourceName.trim(),
        knowledge_text: optional(replaceText),
        knowledge_files: parseCsv(""),
      });
      setSourceStatus(
        `Replaced ${response.source}: deleted ${response.deleted_chunks}, indexed ${response.indexed_chunks}.`,
      );
      setReplaceText("");
    } catch (error: unknown) {
      setSourceError(asError(error));
    } finally {
      setSourceLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-white text-neutral-950">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="rounded-md border border-neutral-200 p-6">
          <p className="text-xs uppercase tracking-[0.16em] text-neutral-500">Person X AI Assistant</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">Frontend Console (Phases 1-3)</h1>
          <p className="mt-2 text-sm text-neutral-600">App Router + TypeScript + Tailwind + shadcn/ui.</p>
          <p className="mt-2 text-xs text-neutral-500">API Base URL: <code>{apiBaseUrl}</code></p>
        </header>

        <Tabs className="mt-6" defaultValue="phase-1">
          <TabsList className="grid h-auto grid-cols-3 rounded-md border border-neutral-200 bg-white p-1">
            <TabsTrigger className="rounded-md data-[state=active]:bg-neutral-100" value="phase-1">Phase 1</TabsTrigger>
            <TabsTrigger className="rounded-md data-[state=active]:bg-neutral-100" value="phase-2">Phase 2</TabsTrigger>
            <TabsTrigger className="rounded-md data-[state=active]:bg-neutral-100" value="phase-3">Phase 3</TabsTrigger>
          </TabsList>

          <TabsContent className="mt-4" value="phase-1">
            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">Foundation Health</CardTitle>
                <CardDescription>Health endpoint validation for backend baseline.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button className="rounded-md" disabled={healthLoading} onClick={refreshHealth} variant="outline">
                  {healthLoading ? "Checking..." : "Run Health Check"}
                </Button>
                {healthError ? <p className="text-sm text-neutral-700">{healthError}</p> : null}
                {health ? (
                  <div className="grid gap-2 rounded-md border border-neutral-200 p-3 text-sm sm:grid-cols-2">
                    <p><span className="text-neutral-500">status:</span> {health.status}</p>
                    <p><span className="text-neutral-500">environment:</span> {health.environment}</p>
                    <p><span className="text-neutral-500">version:</span> {health.version}</p>
                    <p><span className="text-neutral-500">database:</span> {health.database ? "connected" : "not configured"}</p>
                  </div>
                ) : (
                  <p className="text-sm text-neutral-600">No health response yet.</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent className="mt-4 space-y-4" value="phase-2">
            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">Persons</CardTitle>
                <CardDescription>Create and select persona profiles.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Button className="rounded-md" disabled={personLoading} onClick={refreshPersons} variant="outline">
                    {personLoading ? "Refreshing..." : "Refresh Persons"}
                  </Button>
                  <Badge className="rounded-md" variant="outline">
                    {activePerson ? `Active: ${activePerson.name}` : "No Active Person"}
                  </Badge>
                </div>
                {personError ? <p className="text-sm text-neutral-700">{personError}</p> : null}
                {personStatus ? <p className="text-sm text-neutral-700">{personStatus}</p> : null}

                <div className="grid gap-3 lg:grid-cols-2">
                  <div className="space-y-2 rounded-md border border-neutral-200 p-3">
                    <Label htmlFor="person-name">Name</Label>
                    <Input id="person-name" onChange={(event) => setPersonName(event.target.value)} value={personName} />
                    <Label htmlFor="person-role">Role</Label>
                    <Input id="person-role" onChange={(event) => setPersonRole(event.target.value)} value={personRole} />
                    <Label htmlFor="person-department">Department</Label>
                    <Input id="person-department" onChange={(event) => setPersonDepartment(event.target.value)} value={personDepartment} />
                    <Label htmlFor="person-prompt">Base Prompt</Label>
                    <Textarea id="person-prompt" onChange={(event) => setPersonPrompt(event.target.value)} value={personPrompt} />
                    <Button className="w-full rounded-md" onClick={handleCreatePerson} variant="outline">Create Person</Button>
                  </div>

                  <div className="space-y-2 rounded-md border border-neutral-200 p-3">
                    {persons.length === 0 ? (
                      <p className="text-sm text-neutral-600">No persons yet.</p>
                    ) : (
                      persons.map((person) => (
                        <button
                          className="w-full rounded-md border border-neutral-200 p-3 text-left hover:bg-neutral-50"
                          key={person.id}
                          onClick={() => setActivePersonId(person.id)}
                          type="button"
                        >
                          <p className="text-sm font-medium">{person.name}</p>
                          <p className="text-xs text-neutral-600">{person.role ?? "No role"} | {person.department ?? "No department"}</p>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">Knowledge + Chat</CardTitle>
                <CardDescription>Phase 2 persona knowledge and chat flow.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-2 rounded-md border border-neutral-200 p-3">
                    <Label htmlFor="knowledge-source">Source Type</Label>
                    <Input id="knowledge-source" onChange={(event) => setKnowledgeSourceType(event.target.value)} value={knowledgeSourceType} />
                    <Label htmlFor="knowledge-content">Knowledge Content</Label>
                    <Textarea
                      id="knowledge-content"
                      onChange={(event) => setKnowledgeContent(event.target.value)}
                      value={knowledgeContent}
                    />
                    <Button className="w-full rounded-md" onClick={handleAddKnowledge} variant="outline">Add Knowledge</Button>
                    {knowledgeError ? <p className="text-sm text-neutral-700">{knowledgeError}</p> : null}
                    {knowledgeStatus ? <p className="text-sm text-neutral-700">{knowledgeStatus}</p> : null}
                  </div>

                  <div className="space-y-2 rounded-md border border-neutral-200 p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">Knowledge Entries</p>
                      <Button className="rounded-md" disabled={knowledgeLoading} onClick={refreshKnowledge} variant="outline">Refresh</Button>
                    </div>
                    {knowledgeEntries.length === 0 ? (
                      <p className="text-sm text-neutral-600">No knowledge entries.</p>
                    ) : (
                      knowledgeEntries.map((entry) => (
                        <div className="rounded-md border border-neutral-200 p-2" key={entry.id}>
                          <p className="text-xs text-neutral-500">{entry.source_type}</p>
                          <p className="line-clamp-3 text-sm">{entry.content}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <Separator />

                <div className="space-y-2 rounded-md border border-neutral-200 p-3">
                  <Label htmlFor="chat-message">Chat Message</Label>
                  <Textarea id="chat-message" onChange={(event) => setChatMessage(event.target.value)} value={chatMessage} />
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Switch checked={chatUseRetrieval} id="chat-retrieval" onCheckedChange={setChatUseRetrieval} />
                      <Label htmlFor="chat-retrieval">Use Retrieval</Label>
                    </div>
                    <Input className="w-20" onChange={(event) => setChatTopK(event.target.value)} value={chatTopK} />
                    <Input
                      className="max-w-sm"
                      onChange={(event) => setConversationId(event.target.value)}
                      placeholder="Optional conversation id"
                      value={conversationId}
                    />
                    <Button className="rounded-md" disabled={chatLoading} onClick={handleChat} variant="outline">
                      {chatLoading ? "Sending..." : "Send Chat"}
                    </Button>
                  </div>
                  {chatError ? <p className="text-sm text-neutral-700">{chatError}</p> : null}
                  <div className="space-y-2">
                    {chatTurns.length === 0 ? (
                      <p className="text-sm text-neutral-600">No chat turns yet.</p>
                    ) : (
                      chatTurns.map((turn) => (
                        <div className="rounded-md border border-neutral-200 p-2" key={turn.id}>
                          <p className="text-xs uppercase tracking-wide text-neutral-500">{turn.role}</p>
                          <p className="text-sm">{turn.content}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent className="mt-4 space-y-4" value="phase-3">
            <Card className="rounded-md border-neutral-200 shadow-none">
              <CardHeader>
                <CardTitle className="text-lg">Retrieval Index + Search</CardTitle>
                <CardDescription>Phase 3 retrieval workflows.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-2 rounded-md border border-neutral-200 p-3">
                    <Label htmlFor="index-source">Index Source</Label>
                    <Input id="index-source" onChange={(event) => setIndexSource(event.target.value)} value={indexSource} />
                    <Label htmlFor="index-text">Knowledge Text</Label>
                    <Textarea id="index-text" onChange={(event) => setIndexText(event.target.value)} value={indexText} />
                    <Button className="w-full rounded-md" disabled={indexLoading} onClick={handleIndex} variant="outline">
                      {indexLoading ? "Indexing..." : "Index"}
                    </Button>
                    {indexError ? <p className="text-sm text-neutral-700">{indexError}</p> : null}
                    {indexStatus ? <p className="text-sm text-neutral-700">{indexStatus}</p> : null}
                  </div>

                  <div className="space-y-2 rounded-md border border-neutral-200 p-3">
                    <Label htmlFor="search-query">Search Query</Label>
                    <Input id="search-query" onChange={(event) => setSearchQuery(event.target.value)} value={searchQuery} />
                    <Button className="rounded-md" disabled={searchLoading} onClick={handleSearch} variant="outline">
                      {searchLoading ? "Searching..." : "Search"}
                    </Button>
                    {searchError ? <p className="text-sm text-neutral-700">{searchError}</p> : null}
                    <div className="space-y-2">
                      {searchResults.length === 0 ? (
                        <p className="text-sm text-neutral-600">No results.</p>
                      ) : (
                        searchResults.map((result) => (
                          <div className="rounded-md border border-neutral-200 p-2" key={result.id}>
                            <p className="text-xs text-neutral-500">score {result.score.toFixed(3)} | {result.source ?? "unknown"}</p>
                            <p className="line-clamp-3 text-sm">{result.content}</p>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-2 rounded-md border border-neutral-200 p-3">
                    <Label htmlFor="source-name">Source Name</Label>
                    <Input id="source-name" onChange={(event) => setSourceName(event.target.value)} value={sourceName} />
                    <Button className="rounded-md" disabled={sourceLoading} onClick={handleDeleteSource} variant="outline">
                      {sourceLoading ? "Working..." : "Delete Source"}
                    </Button>
                  </div>

                  <div className="space-y-2 rounded-md border border-neutral-200 p-3">
                    <Label htmlFor="replace-text">Replace Text</Label>
                    <Textarea id="replace-text" onChange={(event) => setReplaceText(event.target.value)} value={replaceText} />
                    <Button className="rounded-md" disabled={sourceLoading} onClick={handleReplaceSource} variant="outline">
                      {sourceLoading ? "Working..." : "Replace Source"}
                    </Button>
                  </div>
                </div>

                {sourceError ? <p className="text-sm text-neutral-700">{sourceError}</p> : null}
                {sourceStatus ? <p className="text-sm text-neutral-700">{sourceStatus}</p> : null}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}


