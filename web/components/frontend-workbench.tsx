"use client";

import { useMemo, useState } from "react";

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
import { Textarea } from "@/components/ui/textarea";
import {
  PersonAiChat,
  type PersonAiChatMessage,
} from "@/components/person-ai-chat";
import { ApiError, addKnowledgeEntry, chat, createPerson } from "@/lib/api";
import {
  AUTO_PROFILE,
  AUTO_SUGGESTED_QUESTIONS,
} from "@/lib/demo-person-data";

type ViewMode = "chooser" | "manual" | "chat";

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
  const [viewMode, setViewMode] = useState<ViewMode>("chooser");

  const [manualName, setManualName] = useState("");
  const [manualRole, setManualRole] = useState("");
  const [manualDepartment, setManualDepartment] = useState("");
  const [manualPrompt, setManualPrompt] = useState("");
  const [manualKnowledge, setManualKnowledge] = useState("");
  const [manualFirstQuestion, setManualFirstQuestion] = useState("");

  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<PersonAiChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [selectedQuestion, setSelectedQuestion] = useState(
    AUTO_SUGGESTED_QUESTIONS[0],
  );

  const [setupLoading, setSetupLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);

  const canStartManual = useMemo(() => {
    return manualName.trim().length > 0;
  }, [manualName]);

  async function startManualFlow() {
    setSetupError(null);

    if (!manualName.trim()) {
      setSetupError("Person name is required.");
      return;
    }

    setSetupLoading(true);
    try {
      const person = await createPerson({
        name: manualName.trim(),
        role: manualRole.trim() || undefined,
        department: manualDepartment.trim() || undefined,
        base_system_prompt: manualPrompt.trim() || undefined,
      });

      if (manualKnowledge.trim()) {
        await addKnowledgeEntry(person.id, {
          content: manualKnowledge.trim(),
          source_type: "manual",
          priority: 7,
        });
      }

      setSession({
        personId: person.id,
        personName: person.name,
        conversationId: "",
      });
      setMessages([]);
      const initialQuestion = manualFirstQuestion.trim();
      setChatInput(initialQuestion);
      setSelectedQuestion(
        initialQuestion || AUTO_SUGGESTED_QUESTIONS[0],
      );
      setViewMode("chat");
    } catch (error: unknown) {
      setSetupError(getErrorMessage(error));
    } finally {
      setSetupLoading(false);
    }
  }

  async function startAutoFlow() {
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
      setSelectedQuestion(AUTO_PROFILE.firstQuestion);
      setViewMode("chat");
    } catch (error: unknown) {
      setSetupError(getErrorMessage(error));
    } finally {
      setSetupLoading(false);
    }
  }

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
    setSelectedQuestion(question);
    setChatInput(question);
  }

  function useSelectedQuestion() {
    if (!selectedQuestion.trim()) {
      return;
    }
    setChatInput(selectedQuestion);
  }

  function resetToChooser() {
    setViewMode("chooser");
    setSession(null);
    setMessages([]);
    setChatInput("");
    setSelectedQuestion(AUTO_SUGGESTED_QUESTIONS[0]);
    setChatError(null);
    setSetupError(null);
  }

  if (viewMode === "chooser") {
    return (
      <main className="min-h-screen bg-white px-4 py-10 text-neutral-950 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl">
          <Card className="rounded-md border-neutral-200 shadow-none">
            <CardHeader>
              <CardTitle className="text-xl">Start Person AI Chat</CardTitle>
              <CardDescription className="text-neutral-600">
                Choose how you want to prepare a Person AI before opening chat.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {setupError ? (
                <p className="text-sm text-neutral-700">{setupError}</p>
              ) : null}
              <div className="grid gap-3 sm:grid-cols-2">
                <Button
                  className="rounded-md"
                  onClick={() => setViewMode("manual")}
                  variant="outline"
                >
                  Fill Manually
                </Button>
                <Button
                  className="rounded-md"
                  disabled={setupLoading}
                  onClick={() => void startAutoFlow()}
                  variant="outline"
                >
                  {setupLoading ? "Preparing..." : "Auto Fill"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  if (viewMode === "manual") {
    return (
      <main className="min-h-screen bg-white px-4 py-10 text-neutral-950 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl">
          <Card className="rounded-md border-neutral-200 shadow-none">
            <CardHeader>
              <CardTitle className="text-xl">Manual Setup</CardTitle>
              <CardDescription className="text-neutral-600">
                Fill details once, then chat opens directly.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {setupError ? (
                <p className="text-sm text-neutral-700">{setupError}</p>
              ) : null}

              <div className="space-y-2">
                <Label htmlFor="manual-name">Person Name</Label>
                <Input
                  id="manual-name"
                  onChange={(event) => setManualName(event.target.value)}
                  placeholder="Person name"
                  value={manualName}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="manual-role">Role</Label>
                <Input
                  id="manual-role"
                  onChange={(event) => setManualRole(event.target.value)}
                  placeholder="Role"
                  value={manualRole}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="manual-department">Department</Label>
                <Input
                  id="manual-department"
                  onChange={(event) => setManualDepartment(event.target.value)}
                  placeholder="Department"
                  value={manualDepartment}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="manual-prompt">System Prompt</Label>
                <Textarea
                  id="manual-prompt"
                  onChange={(event) => setManualPrompt(event.target.value)}
                  placeholder="How this person should respond"
                  value={manualPrompt}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="manual-knowledge">Knowledge</Label>
                <Textarea
                  className="min-h-[120px]"
                  id="manual-knowledge"
                  onChange={(event) => setManualKnowledge(event.target.value)}
                  placeholder="Key knowledge for this person AI"
                  value={manualKnowledge}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="manual-question">First Chat Question (optional)</Label>
                <Textarea
                  id="manual-question"
                  onChange={(event) => setManualFirstQuestion(event.target.value)}
                  placeholder="Type an initial question to prefill chat"
                  value={manualFirstQuestion}
                />
              </div>

              <div className="flex flex-wrap gap-3">
                <Button className="rounded-md" onClick={resetToChooser} variant="outline">
                  Back
                </Button>
                <Button
                  className="rounded-md"
                  disabled={!canStartManual || setupLoading}
                  onClick={() => void startManualFlow()}
                  variant="outline"
                >
                  {setupLoading ? "Creating..." : "Create and Open Chat"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <PersonAiChat
      personName={session?.personName ?? "Person AI"}
      messages={messages}
      chatInput={chatInput}
      chatLoading={chatLoading}
      chatError={chatError}
      selectedQuestion={selectedQuestion}
      suggestedQuestions={AUTO_SUGGESTED_QUESTIONS}
      onNewSetup={resetToChooser}
      onSend={() => void sendMessage()}
      onChatInputChange={setChatInput}
      onSelectedQuestionChange={setSelectedQuestion}
      onUseSelectedQuestion={useSelectedQuestion}
      onPickSuggestedQuestion={pickSuggestedQuestion}
    />
  );
}
