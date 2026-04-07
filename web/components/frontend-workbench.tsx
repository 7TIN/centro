"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  PersonAiChat,
  type PersonAiChatMessage,
  type PersonSelectorOption,
} from "@/components/person-ai-chat";
import { ApiError, chat, demoBootstrap, type DemoPersonSummary } from "@/lib/api";

type ChatSession = {
  personId: string;
  personName: string;
  conversationId: string;
};

function nowIso(): string {
  return new Date().toISOString();
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed.";
}

function findPerson(persons: DemoPersonSummary[], personId: string | null): DemoPersonSummary | null {
  if (!personId) {
    return null;
  }
  return persons.find((person) => person.id === personId) ?? null;
}

export function FrontendWorkbench() {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [persons, setPersons] = useState<DemoPersonSummary[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState<PersonAiChatMessage[]>([]);

  const [setupLoading, setSetupLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [switchingPerson, setSwitchingPerson] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);

  const bootstrappedRef = useRef(false);

  const activePerson = useMemo(
    () => findPerson(persons, session?.personId ?? null),
    [persons, session?.personId],
  );

  const suggestedQuestions = activePerson?.suggested_questions ?? [];

  const personOptions = useMemo<PersonSelectorOption[]>(
    () =>
      persons.map((person) => ({
        id: person.id,
        label: person.role ? `${person.name} (${person.role})` : person.name,
      })),
    [persons],
  );

  async function bootstrapFromServer() {
    setSetupError(null);
    setSetupLoading(true);

    try {
      const payload = await demoBootstrap();
      const resolvedPersons = payload.persons;
      const defaultPersonId =
        payload.default_person_id ??
        (resolvedPersons.length > 0 ? resolvedPersons[0].id : null);
      const defaultPerson = findPerson(resolvedPersons, defaultPersonId);

      if (!defaultPersonId || !defaultPerson) {
        throw new Error("No demo persons were returned by server bootstrap.");
      }

      setPersons(resolvedPersons);
      setSession({
        personId: defaultPerson.id,
        personName: defaultPerson.name,
        conversationId: "",
      });
      setMessages([]);
      setChatInput(defaultPerson.first_question ?? "");
    } catch (error: unknown) {
      setSetupError(getErrorMessage(error));
    } finally {
      setSetupLoading(false);
    }
  }

  useEffect(() => {
    if (bootstrappedRef.current) {
      return;
    }
    bootstrappedRef.current = true;
    void bootstrapFromServer();
  }, []);

  async function sendMessage() {
    if (!session) {
      return;
    }
    const content = chatInput.trim();
    if (!content) {
      return;
    }

    setChatError(null);
    const userMessage: PersonAiChatMessage = {
      id: crypto.randomUUID(),
      sender: "anon",
      content,
      timestamp: nowIso(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setChatInput("");
    setChatLoading(true);

    try {
      const response = await chat({
        person_id: session.personId,
        message: content,
        conversation_id: session.conversationId || undefined,
        use_retrieval: false,
      });

      setSession((prev) => {
        if (!prev) {
          return prev;
        }
        return {
          ...prev,
          conversationId: response.conversation_id,
        };
      });

      const personMessage: PersonAiChatMessage = {
        id: response.message_id,
        sender: "person",
        content: response.response,
        timestamp: nowIso(),
      };

      setMessages((prev) => [...prev, personMessage]);
    } catch (error: unknown) {
      setChatError(getErrorMessage(error));
    } finally {
      setChatLoading(false);
    }
  }

  function pickSuggestedQuestion(question: string) {
    setChatInput(question);
  }

  function switchPerson(personId: string) {
    if (!personId) {
      return;
    }
    if (session?.personId === personId) {
      return;
    }

    const selected = findPerson(persons, personId);
    if (!selected) {
      return;
    }

    setSwitchingPerson(true);
    setChatError(null);
    setMessages([]);
    setSession({
      personId: selected.id,
      personName: selected.name,
      conversationId: "",
    });
    setChatInput(selected.first_question ?? "");
    Promise.resolve().then(() => setSwitchingPerson(false));
  }

  if (setupLoading && !session) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-white px-4 py-10 text-neutral-950 sm:px-6 lg:px-8">
        <Card className="w-full max-w-md rounded-md border-neutral-200 shadow-none">
          <CardContent className="py-8 text-center text-sm text-neutral-600">
            Preparing team and person demo wikis...
          </CardContent>
        </Card>
      </main>
    );
  }

  if (setupError && !session) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-white px-4 py-10 text-neutral-950 sm:px-6 lg:px-8">
        <Card className="w-full max-w-md rounded-md border-neutral-200 shadow-none">
          <CardContent className="space-y-4 py-8 text-center">
            <p className="text-sm text-neutral-700">{setupError}</p>
            <Button
              className="rounded-md"
              disabled={setupLoading}
              onClick={() => void bootstrapFromServer()}
              variant="outline"
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <PersonAiChat
      personName={session?.personName ?? "Person AI"}
      personId={session?.personId ?? null}
      persons={personOptions}
      selectedPersonId={session?.personId ?? null}
      messages={messages}
      chatInput={chatInput}
      chatLoading={chatLoading}
      chatError={chatError}
      suggestedQuestions={suggestedQuestions}
      switchingPerson={switchingPerson}
      onSend={() => void sendMessage()}
      onChatInputChange={setChatInput}
      onPickSuggestedQuestion={pickSuggestedQuestion}
      onSelectPerson={switchPerson}
    />
  );
}
