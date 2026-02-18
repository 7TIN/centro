"use client";

import { ReactNode, useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

export type PersonAiChatMessage = {
  id: string;
  sender: "anon" | "person";
  content: string;
  timestamp: string;
};

type PersonAiChatProps = {
  personName: string;
  messages: PersonAiChatMessage[];
  chatInput: string;
  chatLoading: boolean;
  chatError: string | null;
  selectedQuestion: string;
  suggestedQuestions: string[];
  onNewSetup: () => void;
  onSend: () => void;
  onChatInputChange: (value: string) => void;
  onSelectedQuestionChange: (value: string) => void;
  onUseSelectedQuestion: () => void;
  onPickSuggestedQuestion: (value: string) => void;
};

function renderInlineContent(text: string): ReactNode[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .filter(Boolean)
    .map((part, index) => {
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        return (
          <strong key={`${part}-${index}`} className="font-semibold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return <span key={`${part}-${index}`}>{part}</span>;
    });
}

function renderMessageContent(content: string): ReactNode {
  const lines = content.split("\n");
  return lines.map((line, index) => {
    const trimmedStart = line.trimStart();
    const normalized = trimmedStart.startsWith("* ")
      ? `- ${trimmedStart.slice(2)}`
      : line;

    return (
      <p key={`line-${index}`} className={index > 0 ? "mt-1" : undefined}>
        {renderInlineContent(normalized)}
      </p>
    );
  });
}

export function PersonAiChat({
  personName,
  messages,
  chatInput,
  chatLoading,
  chatError,
  selectedQuestion,
  suggestedQuestions,
  onNewSetup,
  onSend,
  onChatInputChange,
  onSelectedQuestionChange,
  onUseSelectedQuestion,
  onPickSuggestedQuestion,
}: PersonAiChatProps) {
  const endOfMessagesRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, chatLoading]);

  return (
    <main className="min-h-screen bg-white px-4 py-6 text-neutral-950 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <Card className="flex h-[86vh] min-h-0 flex-col rounded-md border-neutral-200 shadow-none">
          <CardHeader className="border-b border-neutral-200 py-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle className="text-lg">{personName}</CardTitle>
                <CardDescription className="text-neutral-600">
                  Chat with this person AI
                </CardDescription>
              </div>
              <Button className="rounded-md" onClick={onNewSetup} variant="outline">
                New Setup
              </Button>
            </div>
          </CardHeader>

          <CardContent className="flex-1 min-h-0 overflow-hidden p-0">
            <div className="grid h-full min-h-0 grid-cols-1 lg:grid-cols-[1fr_320px]">
              <section className="flex min-h-0 flex-col">
                <div className="min-h-0 flex-1 overflow-y-auto px-4 pt-4 pb-6">
                  {messages.length === 0 ? (
                    <p className="text-sm text-neutral-600">
                      Start chatting. Messages from Anon appear on the right and
                      messages from {personName} appear on the left.
                    </p>
                  ) : null}

                  <div className="space-y-3">
                    {messages.map((message) => {
                      const isAnon = message.sender === "anon";
                      return (
                        <div
                          className={
                            isAnon
                              ? "ml-auto max-w-[80%] text-right"
                              : "mr-auto max-w-[80%] text-left"
                          }
                          key={message.id}
                        >
                          <p className="mb-1 text-xs text-neutral-500">
                            {isAnon ? "Anon" : personName}
                          </p>
                          <div className="rounded-md border border-neutral-200 bg-neutral-50 p-3 text-sm text-neutral-900">
                            {renderMessageContent(message.content)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div ref={endOfMessagesRef} />
                </div>

                <div className="border-t border-neutral-200 p-4">
                  {chatError ? (
                    <p className="mb-2 text-sm text-neutral-700">{chatError}</p>
                  ) : null}
                  <div className="space-y-2">
                    <Textarea
                      className="min-h-[90px]"
                      onChange={(event) => onChatInputChange(event.target.value)}
                      placeholder="Type message as Anon"
                      value={chatInput}
                    />
                    <div className="flex justify-end">
                      <Button
                        className="rounded-md"
                        disabled={chatLoading || !chatInput.trim()}
                        onClick={onSend}
                        variant="outline"
                      >
                        {chatLoading ? "Sending..." : "Send"}
                      </Button>
                    </div>
                  </div>
                </div>
              </section>

              <aside className="min-h-0 overflow-y-auto border-t border-neutral-200 p-4 lg:border-l lg:border-t-0">
                <div className="space-y-3">
                  <p className="text-sm font-medium">Suggested Questions</p>
                  <select
                    className="w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm"
                    onChange={(event) => onSelectedQuestionChange(event.target.value)}
                    value={selectedQuestion}
                  >
                    {suggestedQuestions.map((question) => (
                      <option key={question} value={question}>
                        {question}
                      </option>
                    ))}
                  </select>
                  <Button
                    className="w-full rounded-md"
                    onClick={onUseSelectedQuestion}
                    variant="outline"
                  >
                    Use Selected Question
                  </Button>
                  <div className="max-h-[46vh] space-y-2 overflow-y-auto">
                    {suggestedQuestions.map((question, index) => (
                      <button
                        className="w-full rounded-md border border-neutral-200 px-3 py-2 text-left text-xs text-neutral-800 hover:bg-neutral-50"
                        key={question}
                        onClick={() => onPickSuggestedQuestion(question)}
                        type="button"
                      >
                        {index + 1}. {question}
                      </button>
                    ))}
                  </div>
                </div>
              </aside>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
