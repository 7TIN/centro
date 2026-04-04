"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  PersonAiChat,
  type PersonAiChatMessage,
} from "@/components/person-ai-chat";
import { ApiError, addKnowledgeEntry, chat, createPerson } from "@/lib/api";
import {
  AUTO_PROFILE,
  AUTO_SUGGESTED_QUESTIONS,
} from "@/lib/demo-person-data";

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

export function FrontendWorkbench() {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<PersonAiChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");

  const [setupLoading, setSetupLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const bootstrappedRef = useRef(false);

  async function bootstrapDemoPerson() {
    setSetupError(null);
    setSetupLoading(true);

    try {
      const person = await createPerson({
        name: AUTO_PROFILE.name,
        role: AUTO_PROFILE.role,
        department: AUTO_PROFILE.department,
        base_system_prompt: AUTO_PROFILE.basePrompt,
      });

      await addKnowledgeEntry(person.id, {
        content: AUTO_PROFILE.knowledge,
        source_type: "manual",
        priority: 8,
      });

      setSession({
        personId: person.id,
        personName: person.name,
        conversationId: "",
      });
      setMessages([]);
      setChatInput(AUTO_PROFILE.firstQuestion);
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
    void bootstrapDemoPerson();
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

  if (setupLoading && !session) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-white px-4 py-10 text-neutral-950 sm:px-6 lg:px-8">
        <Card className="w-full max-w-md rounded-md border-neutral-200 shadow-none">
          <CardContent className="py-8 text-center text-sm text-neutral-600">
            Preparing demo person...
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
              onClick={() => void bootstrapDemoPerson()}
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
      messages={messages}
      chatInput={chatInput}
      chatLoading={chatLoading}
      chatError={chatError}
      suggestedQuestions={AUTO_SUGGESTED_QUESTIONS}
      onSend={() => void sendMessage()}
      onChatInputChange={setChatInput}
      onPickSuggestedQuestion={pickSuggestedQuestion}
    />
  );
}
