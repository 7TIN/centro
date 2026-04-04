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
  getPerson,
  listKnowledgeEntries,
  listPersons,
  type KnowledgeEntryResponse,
  type PersonResponse,
} from "@/lib/api";
import { AUTO_PROFILE, AUTO_SUGGESTED_QUESTIONS } from "@/lib/demo-person-data";

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
  const [person, setPerson] = useState<PersonResponse | null>(null);
  const [entries, setEntries] = useState<KnowledgeEntryResponse[]>([]);

  useEffect(() => {
    let canceled = false;

    async function loadKnowledge() {
      setLoading(true);
      setError(null);

      try {
        let resolvedPerson: PersonResponse | null = null;

        if (personIdFromQuery) {
          resolvedPerson = await getPerson(personIdFromQuery);
        }

        if (!resolvedPerson) {
          const persons = await listPersons();
          resolvedPerson =
            persons.find((candidate) => candidate.name === AUTO_PROFILE.name) ??
            persons[0] ??
            null;
        }

        let knowledgeEntries: KnowledgeEntryResponse[] = [];
        if (resolvedPerson) {
          knowledgeEntries = await listKnowledgeEntries(resolvedPerson.id);
        }

        if (canceled) {
          return;
        }

        setPerson(resolvedPerson);
        setEntries(knowledgeEntries);
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

    void loadKnowledge();
    return () => {
      canceled = true;
    };
  }, [personIdFromQuery]);

  const activePersonLabel = useMemo(() => {
    if (!person) {
      return "Demo person not resolved yet.";
    }
    return `${person.name}${person.role ? ` - ${person.role}` : ""}`;
  }, [person]);

  return (
    <main className="min-h-screen bg-neutral-50 px-4 py-8 text-neutral-900 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Demo Knowledge</h1>
            <p className="text-sm text-neutral-600">
              Seed data plus stored knowledge for the active demo personality.
            </p>
          </div>
          <Button asChild className="rounded-md" variant="outline">
            <Link href="/">Back to Chat</Link>
          </Button>
        </div>

        <Card className="border-neutral-200 bg-white shadow-none">
          <CardHeader>
            <CardTitle className="text-lg">Demo Profile From File</CardTitle>
            <CardDescription>
              Loaded from `web/lib/demo-person-data.ts`
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              <span className="font-medium">Name:</span> {AUTO_PROFILE.name}
            </p>
            <p>
              <span className="font-medium">Role:</span> {AUTO_PROFILE.role}
            </p>
            <p>
              <span className="font-medium">Department:</span> {AUTO_PROFILE.department}
            </p>
            <p>
              <span className="font-medium">First Question:</span>{" "}
              {AUTO_PROFILE.firstQuestion}
            </p>
          </CardContent>
        </Card>

        <Card className="border-neutral-200 bg-white shadow-none">
          <CardHeader>
            <CardTitle className="text-lg">Demo Seed Knowledge Text</CardTitle>
            <CardDescription>Raw knowledge string used for auto setup.</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="max-h-[420px] overflow-auto rounded-lg bg-neutral-100 p-4 text-xs leading-relaxed whitespace-pre-wrap">
              {AUTO_PROFILE.knowledge}
            </pre>
          </CardContent>
        </Card>

        <Card className="border-neutral-200 bg-white shadow-none">
          <CardHeader>
            <CardTitle className="text-lg">Suggested Questions</CardTitle>
            <CardDescription>These are also available from the chat drawer.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm">
            {AUTO_SUGGESTED_QUESTIONS.map((question, index) => (
              <p
                key={question}
                className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2"
              >
                {index + 1}. {question}
              </p>
            ))}
          </CardContent>
        </Card>

        <Card className="border-neutral-200 bg-white shadow-none">
          <CardHeader>
            <CardTitle className="text-lg">Knowledge Stored In Backend</CardTitle>
            <CardDescription>{activePersonLabel}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? <p className="text-sm text-neutral-600">Loading knowledge...</p> : null}
            {error ? (
              <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            ) : null}
            {!loading && !error && entries.length === 0 ? (
              <p className="text-sm text-neutral-600">
                No knowledge entries found for the resolved person yet.
              </p>
            ) : null}
            {!loading && !error
              ? entries.map((entry) => (
                  <article
                    key={entry.id}
                    className="rounded-lg border border-neutral-200 bg-neutral-50 p-4"
                  >
                    <div className="mb-2 text-xs text-neutral-500">
                      <p>
                        <span className="font-medium text-neutral-700">Source:</span>{" "}
                        {entry.source_type}
                        {entry.source_reference ? ` | ${entry.source_reference}` : ""}
                      </p>
                      <p>
                        <span className="font-medium text-neutral-700">Created:</span>{" "}
                        {formatDate(entry.created_at)}
                      </p>
                    </div>
                    <p className="mb-2 text-sm font-medium text-neutral-800">
                      {entry.title ?? "Untitled knowledge entry"}
                    </p>
                    <pre className="max-h-[280px] overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-neutral-700">
                      {entry.content}
                    </pre>
                  </article>
                ))
              : null}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
