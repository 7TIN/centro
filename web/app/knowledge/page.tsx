"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ApiError,
  demoBootstrap,
  getPersonWiki,
  getTeamWiki,
  listKnowledgeEntries,
  type DemoBootstrapResponse,
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
  const [bootstrap, setBootstrap] = useState<DemoBootstrapResponse | null>(null);
  const [teamWiki, setTeamWiki] = useState<TeamWikiOverviewResponse | null>(null);
  const [personWiki, setPersonWiki] = useState<PersonWikiOverviewResponse | null>(null);
  const [entries, setEntries] = useState<KnowledgeEntryResponse[]>([]);
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);

  useEffect(() => {
    let canceled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const demo = await demoBootstrap();
        const resolvedPersonId =
          personIdFromQuery ||
          demo.default_person_id ||
          (demo.persons.length > 0 ? demo.persons[0].id : null);

        const [team, personWikiResp, knowledge] = await Promise.all([
          getTeamWiki(),
          resolvedPersonId ? getPersonWiki(resolvedPersonId) : Promise.resolve(null),
          resolvedPersonId ? listKnowledgeEntries(resolvedPersonId) : Promise.resolve([]),
        ]);

        if (canceled) {
          return;
        }

        setBootstrap(demo);
        setSelectedPersonId(resolvedPersonId);
        setTeamWiki(team);
        setPersonWiki(personWikiResp);
        setEntries(knowledge);
      } catch (loadError: unknown) {
        if (canceled) {
          return;
        }
        setError(getErrorMessage(loadError));
      } finally {
        if (!canceled) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      canceled = true;
    };
  }, [personIdFromQuery]);

  const activePerson = useMemo(() => {
    if (!bootstrap || !selectedPersonId) {
      return null;
    }
    return bootstrap.persons.find((person) => person.id === selectedPersonId) ?? null;
  }, [bootstrap, selectedPersonId]);

  return (
    <main className="min-h-screen bg-neutral-50 px-4 py-8 text-neutral-900 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Team + Person Knowledge</h1>
            <p className="text-sm text-neutral-600">
              Team wiki is shared source of truth. Personal wiki adds selected teammate context.
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

        {!loading && !error && bootstrap ? (
          <Card className="border-neutral-200 bg-white shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Server Demo Bootstrap</CardTitle>
              <CardDescription>
                Team pages: {bootstrap.team_pages} · Persons: {bootstrap.persons.length} · Synced wikis: {bootstrap.synced_person_wikis}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-2 text-sm">
              {bootstrap.persons.map((person) => (
                <p
                  key={person.id}
                  className={`rounded-md border px-3 py-2 ${
                    person.id === selectedPersonId
                      ? "border-neutral-800 bg-neutral-100 text-neutral-900"
                      : "border-neutral-200 bg-neutral-50 text-neutral-700"
                  }`}
                >
                  {person.name} {person.role ? `- ${person.role}` : ""}
                </p>
              ))}
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

        {!loading && !error && activePerson ? (
          <Card className="border-neutral-200 bg-white shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Suggested Questions ({activePerson.name})</CardTitle>
              <CardDescription>Served from backend bootstrap metadata.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-2 text-sm">
              {activePerson.suggested_questions.map((question, index) => (
                <p key={question} className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
                  {index + 1}. {question}
                </p>
              ))}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </main>
  );
}
