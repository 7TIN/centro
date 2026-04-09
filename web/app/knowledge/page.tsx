"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  addKnowledgeEntry,
  demoBootstrap,
  getPersonWiki,
  getTeamWiki,
  ingestGitHub,
  listKnowledgeEntries,
  upsertTeamKnowledge,
  type DemoBootstrapResponse,
  type GitHubIngestResponse,
  type KnowledgeEntryResponse,
  type PersonWikiOverviewResponse,
  type TeamWikiOverviewResponse,
} from "@/lib/api";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed.";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export default function KnowledgePage() {
  const searchParams = useSearchParams();
  const personIdFromQuery = searchParams.get("personId");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const [bootstrap, setBootstrap] = useState<DemoBootstrapResponse | null>(null);
  const [teamWiki, setTeamWiki] = useState<TeamWikiOverviewResponse | null>(null);
  const [personWiki, setPersonWiki] = useState<PersonWikiOverviewResponse | null>(null);
  const [entries, setEntries] = useState<KnowledgeEntryResponse[]>([]);
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);

  const [teamTitle, setTeamTitle] = useState("");
  const [teamContent, setTeamContent] = useState("");
  const [githubOwner, setGitHubOwner] = useState("acme");
  const [githubRepo, setGitHubRepo] = useState("payments-service");
  const [githubMaxItems, setGitHubMaxItems] = useState("10");
  const [personTitle, setPersonTitle] = useState("");
  const [personContent, setPersonContent] = useState("");
  const [savingTeam, setSavingTeam] = useState(false);
  const [ingestingGitHub, setIngestingGitHub] = useState(false);
  const [savingPerson, setSavingPerson] = useState(false);

  const loadAll = useCallback(
    async (preferredPersonId?: string | null) => {
      setLoading(true);
      setError(null);

      try {
        const demo = await demoBootstrap();
        const resolvedPersonId =
          preferredPersonId ||
          personIdFromQuery ||
          demo.default_person_id ||
          (demo.persons.length > 0 ? demo.persons[0].id : null);

        const [team, personWikiResp, knowledge] = await Promise.all([
          getTeamWiki(),
          resolvedPersonId ? getPersonWiki(resolvedPersonId) : Promise.resolve(null),
          resolvedPersonId ? listKnowledgeEntries(resolvedPersonId) : Promise.resolve([]),
        ]);

        setBootstrap(demo);
        setSelectedPersonId(resolvedPersonId);
        setTeamWiki(team);
        setPersonWiki(personWikiResp);
        setEntries(knowledge);
      } catch (loadError: unknown) {
        setError(getErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    },
    [personIdFromQuery],
  );

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const activePerson = useMemo(() => {
    if (!bootstrap || !selectedPersonId) {
      return null;
    }
    return bootstrap.persons.find((person) => person.id === selectedPersonId) ?? null;
  }, [bootstrap, selectedPersonId]);

  async function submitTeamKnowledge() {
    const title = teamTitle.trim();
    const content = teamContent.trim();
    if (!title || !content) {
      return;
    }

    setSavingTeam(true);
    setActionMessage(null);
    try {
      const response = await upsertTeamKnowledge({
        title,
        content,
        updated_by: "knowledge-page-ui",
        tags: ["manual"],
      });
      setTeamTitle("");
      setTeamContent("");
      setActionMessage(
        `Team knowledge updated: ${response.page_path} (synced ${response.synced_person_wikis} person wikis).`,
      );
      await loadAll(selectedPersonId);
    } catch (submitError: unknown) {
      setError(getErrorMessage(submitError));
    } finally {
      setSavingTeam(false);
    }
  }

  async function submitGitHubIngest() {
    const owner = githubOwner.trim();
    const repo = githubRepo.trim();
    const parsedMaxItems = Number.parseInt(githubMaxItems, 10);
    const maxItems = Number.isNaN(parsedMaxItems)
      ? 10
      : Math.max(1, Math.min(parsedMaxItems, 50));

    if (!owner || !repo) {
      return;
    }

    setIngestingGitHub(true);
    setActionMessage(null);
    try {
      const response: GitHubIngestResponse = await ingestGitHub({
        owner,
        repo,
        person_id: selectedPersonId ?? undefined,
        max_items: maxItems,
        attach_to_person: true,
        updated_by: "knowledge-page-ui",
      });
      setActionMessage(
        `GitHub ingested for ${response.repository}. Team page: ${response.team_page_path}. Synced ${response.synced_person_wikis} person wikis.`,
      );
      await loadAll(selectedPersonId);
    } catch (submitError: unknown) {
      setError(getErrorMessage(submitError));
    } finally {
      setIngestingGitHub(false);
    }
  }

  async function submitPersonKnowledge() {
    const content = personContent.trim();
    if (!selectedPersonId || !content) {
      return;
    }

    setSavingPerson(true);
    setActionMessage(null);
    try {
      await addKnowledgeEntry(selectedPersonId, {
        title: personTitle.trim() || undefined,
        content,
        source_type: "manual",
        priority: 7,
        metadata: { from: "knowledge-page-ui" },
      });
      setPersonTitle("");
      setPersonContent("");
      setActionMessage("Person knowledge added and markdown wiki updated.");
      await loadAll(selectedPersonId);
    } catch (submitError: unknown) {
      setError(getErrorMessage(submitError));
    } finally {
      setSavingPerson(false);
    }
  }

  return (
    <main className="min-h-screen bg-neutral-50 px-4 py-8 text-neutral-900 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Team + Person Knowledge</h1>
            <p className="text-sm text-neutral-600">
              Add new team or person knowledge and watch wiki updates/sync happen immediately.
            </p>
          </div>
          <Button asChild className="rounded-md" variant="outline">
            <Link href="/">Back to Chat</Link>
          </Button>
        </div>

        {loading ? (
          <Card className="border-neutral-200 bg-white shadow-none">
            <CardContent className="py-8 text-sm text-neutral-600">Loading wiki data...</CardContent>
          </Card>
        ) : null}

        {error ? (
          <Card className="border-red-200 bg-red-50 shadow-none">
            <CardContent className="py-4 text-sm text-red-700">{error}</CardContent>
          </Card>
        ) : null}

        {actionMessage ? (
          <Card className="border-emerald-200 bg-emerald-50 shadow-none">
            <CardContent className="py-4 text-sm text-emerald-700">{actionMessage}</CardContent>
          </Card>
        ) : null}

        {!loading && !error && bootstrap ? (
          <Card className="border-neutral-200 bg-white shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Select Person Context</CardTitle>
              <CardDescription>
                Team pages: {bootstrap.team_pages} · Persons: {bootstrap.persons.length} · Synced wikis: {bootstrap.synced_person_wikis}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-2 text-sm">
              {bootstrap.persons.map((person) => (
                <button
                  key={person.id}
                  className={`rounded-md border px-3 py-2 text-left ${
                    person.id === selectedPersonId
                      ? "border-neutral-800 bg-neutral-100 text-neutral-900"
                      : "border-neutral-200 bg-neutral-50 text-neutral-700"
                  }`}
                  onClick={() => {
                    void loadAll(person.id);
                  }}
                  type="button"
                >
                  {person.name} {person.role ? `- ${person.role}` : ""}
                </button>
              ))}
            </CardContent>
          </Card>
        ) : null}

        {!loading && !error ? (
          <Card className="border-neutral-200 bg-white shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Ingest From GitHub</CardTitle>
              <CardDescription>
                Fetch PRs/issues from a repo, update team wiki, and attach summary to selected person.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-3">
                <Input
                  onChange={(event) => setGitHubOwner(event.target.value)}
                  placeholder="Repo owner (org/user)"
                  value={githubOwner}
                />
                <Input
                  onChange={(event) => setGitHubRepo(event.target.value)}
                  placeholder="Repository name"
                  value={githubRepo}
                />
                <Input
                  onChange={(event) => setGitHubMaxItems(event.target.value)}
                  placeholder="Max items (1-50)"
                  value={githubMaxItems}
                />
              </div>
              <Button
                disabled={ingestingGitHub || !githubOwner.trim() || !githubRepo.trim()}
                onClick={() => void submitGitHubIngest()}
                variant="outline"
              >
                {ingestingGitHub ? "Ingesting..." : "Ingest GitHub Snapshot"}
              </Button>
            </CardContent>
          </Card>
        ) : null}

        {!loading && !error ? (
          <Card className="border-neutral-200 bg-white shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Add Team Knowledge</CardTitle>
              <CardDescription>
                Updates team wiki then syncs snapshots into all person wikis.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                onChange={(event) => setTeamTitle(event.target.value)}
                placeholder="Team knowledge title"
                value={teamTitle}
              />
              <Textarea
                className="min-h-[120px]"
                onChange={(event) => setTeamContent(event.target.value)}
                placeholder="Write shared team knowledge..."
                value={teamContent}
              />
              <Button
                disabled={savingTeam || !teamTitle.trim() || !teamContent.trim()}
                onClick={() => void submitTeamKnowledge()}
                variant="outline"
              >
                {savingTeam ? "Saving..." : "Add Team Knowledge"}
              </Button>
            </CardContent>
          </Card>
        ) : null}

        {!loading && !error ? (
          <Card className="border-neutral-200 bg-white shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Add Knowledge To Selected Person</CardTitle>
              <CardDescription>
                Person wiki updates immediately and continues using team-first context.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                onChange={(event) => setPersonTitle(event.target.value)}
                placeholder="Person knowledge title (optional)"
                value={personTitle}
              />
              <Textarea
                className="min-h-[120px]"
                onChange={(event) => setPersonContent(event.target.value)}
                placeholder="Write person-specific knowledge..."
                value={personContent}
              />
              <Button
                disabled={savingPerson || !selectedPersonId || !personContent.trim()}
                onClick={() => void submitPersonKnowledge()}
                variant="outline"
              >
                {savingPerson ? "Saving..." : "Add Person Knowledge"}
              </Button>
            </CardContent>
          </Card>
        ) : null}

        {!loading && !error && teamWiki ? (
          <Card className="border-neutral-200 bg-white shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Core Team Wiki</CardTitle>
              <CardDescription>{teamWiki.team_name}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <pre className="max-h-[220px] overflow-auto rounded-md bg-neutral-100 p-3 text-xs whitespace-pre-wrap">
                {teamWiki.index_content}
              </pre>
              <div className="grid gap-2 text-sm">
                {teamWiki.pages.map((page) => (
                  <p key={page.path} className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
                    {page.path} · {formatDate(page.updated_at)}
                  </p>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : null}

        {!loading && !error && personWiki ? (
          <Card className="border-neutral-200 bg-white shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Selected Person Wiki</CardTitle>
              <CardDescription>
                {activePerson ? `${activePerson.name} (${activePerson.role ?? "Role N/A"})` : personWiki.person_id}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <pre className="max-h-[220px] overflow-auto rounded-md bg-neutral-100 p-3 text-xs whitespace-pre-wrap">
                {personWiki.index_content}
              </pre>
              <div className="grid gap-2 text-sm">
                {personWiki.pages.map((page) => (
                  <p key={page.path} className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
                    {page.path} · {formatDate(page.updated_at)}
                  </p>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : null}

        {!loading && !error ? (
          <Card className="border-neutral-200 bg-white shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Selected Person Knowledge Entries</CardTitle>
              <CardDescription>{entries.length} markdown-backed entries</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {entries.length === 0 ? (
                <p className="text-sm text-neutral-600">No knowledge entries available.</p>
              ) : null}
              {entries.map((entry) => (
                <article key={entry.id} className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
                  <div className="mb-2 text-xs text-neutral-500">
                    <p>{entry.source_type} · priority {entry.priority}</p>
                    <p>{formatDate(entry.updated_at)}</p>
                  </div>
                  <p className="mb-2 text-sm font-medium text-neutral-800">{entry.title ?? entry.id}</p>
                  <pre className="max-h-[200px] overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-neutral-700">
                    {entry.content}
                  </pre>
                </article>
              ))}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </main>
  );
}
