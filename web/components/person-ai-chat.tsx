"use client";

import Link from "next/link";
import { ReactNode, useEffect, useMemo, useRef, useState } from "react";

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
  personId: string | null;
  messages: PersonAiChatMessage[];
  chatInput: string;
  chatLoading: boolean;
  chatError: string | null;
  suggestedQuestions: string[];
  onSend: () => void;
  onChatInputChange: (value: string) => void;
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
  personId,
  messages,
  chatInput,
  chatLoading,
  chatError,
  suggestedQuestions,
  onSend,
  onChatInputChange,
  onPickSuggestedQuestion,
}: PersonAiChatProps) {
  const endOfMessagesRef = useRef<HTMLDivElement | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const knowledgeHref = useMemo(() => {
    if (!personId) {
      return "/knowledge";
    }
    return `/knowledge?personId=${encodeURIComponent(personId)}`;
  }, [personId]);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, chatLoading]);

  return (
    <main className="flex h-[100dvh] w-full items-center justify-center bg-neutral-50/50 p-4 md:p-6 lg:p-8">
      <div className="h-full max-h-[900px] w-full max-w-6xl">
        <Card className="flex h-full flex-col overflow-hidden shadow-lg border-neutral-200/60 bg-white">
          <CardHeader className="flex flex-row items-center justify-between border-b bg-white px-6 py-4 shadow-sm z-10">
            <div className="flex flex-col space-y-1.5">
              <CardTitle className="text-xl font-bold tracking-tight text-neutral-900">
                {personName}
              </CardTitle>
              <CardDescription className="text-sm font-medium text-neutral-500">
                Chat with this person AI
              </CardDescription>
            </div>
            <Button
              asChild
              variant="outline"
              size="sm"
              className="rounded-full px-4 shadow-sm hover:bg-neutral-100"
            >
              <Link href={knowledgeHref}>Knowledge</Link>
            </Button>
          </CardHeader>

          <CardContent className="flex flex-1 flex-col p-0 overflow-hidden bg-neutral-50/30">
            <section className="flex flex-1 flex-col overflow-hidden relative">
              <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 scrollbar-thin">
                {messages.length === 0 ? (
                  <div className="flex h-full items-center justify-center">
                    <div className="text-center bg-white p-6 rounded-2xl border border-neutral-200 shadow-sm max-w-sm">
                      <p className="text-sm text-neutral-500 leading-relaxed">
                        Start chatting. Messages from <strong>Anon</strong> appear on the right, and messages from <strong>{personName}</strong> appear on the left.
                      </p>
                    </div>
                  </div>
                ) : null}

                {messages.map((message) => {
                  const isAnon = message.sender === "anon";
                  return (
                    <div
                      key={message.id}
                      className={`flex w-full ${isAnon ? "justify-end" : "justify-start"}`}
                    >
                      <div className={`flex max-w-[85%] md:max-w-[75%] flex-col gap-1 ${isAnon ? "items-end" : "items-start"}`}>
                        <span className="text-[11px] font-semibold tracking-wide text-neutral-400 px-1 uppercase">
                          {isAnon ? "Anon" : personName}
                        </span>

                        <div
                          className={`px-4 py-3 text-[15px] leading-relaxed shadow-sm ${
                            isAnon
                              ? "bg-neutral-900 text-white rounded-2xl rounded-br-sm"
                              : "bg-white border border-neutral-200 text-neutral-800 rounded-2xl rounded-bl-sm"
                          }`}
                        >
                          {renderMessageContent(message.content)}
                        </div>
                      </div>
                    </div>
                  );
                })}
                <div ref={endOfMessagesRef} className="h-1" />
              </div>

              <div className="bg-white border-t border-neutral-200 p-4 md:p-5">
                {chatError ? (
                  <div className="mb-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 border border-red-100 flex items-center">
                    <span className="font-medium">Error:</span>&nbsp;{chatError}
                  </div>
                ) : null}

                <div className="relative flex items-end gap-3 max-w-4xl mx-auto">
                  <Textarea
                    className="min-h-[52px] w-full resize-none rounded-2xl border-neutral-300 bg-neutral-50 px-4 py-3.5 pr-[100px] text-sm focus-visible:ring-1 focus-visible:ring-neutral-400 focus-visible:ring-offset-0 transition-all"
                    onChange={(event) => onChatInputChange(event.target.value)}
                    placeholder="Type a message as Anon..."
                    value={chatInput}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (!chatLoading && chatInput.trim()) onSend();
                      }
                    }}
                  />
                  <div className="absolute right-2 bottom-2">
                    <Button
                      className="rounded-xl px-5 font-semibold shadow-sm transition-all"
                      disabled={chatLoading || !chatInput.trim()}
                      onClick={onSend}
                      size="sm"
                    >
                      {chatLoading ? "Sending..." : "Send"}
                    </Button>
                  </div>
                </div>
              </div>
            </section>
          </CardContent>
        </Card>
      </div>

      {drawerOpen ? (
        <button
          aria-label="Close suggested questions"
          className="fixed inset-0 z-40 bg-black/30"
          onClick={() => setDrawerOpen(false)}
          type="button"
        />
      ) : null}

      <aside
        className={`fixed bottom-0 right-0 z-50 w-full max-w-sm rounded-t-2xl border border-neutral-200 bg-white shadow-xl transition-transform duration-200 sm:bottom-4 sm:right-4 sm:rounded-2xl ${
          drawerOpen ? "translate-y-0" : "translate-y-[110%]"
        }`}
      >
        <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-neutral-900">Suggested Questions</h2>
          <Button
            className="h-8 rounded-md px-3"
            onClick={() => setDrawerOpen(false)}
            size="sm"
            variant="outline"
          >
            Close
          </Button>
        </div>
        <div className="max-h-[60dvh] overflow-y-auto px-2 py-2">
          {suggestedQuestions.map((question, index) => (
            <button
              key={question}
              className="flex w-full items-start gap-2 rounded-lg px-3 py-2 text-left text-sm text-neutral-700 transition hover:bg-neutral-100"
              onClick={() => {
                onPickSuggestedQuestion(question);
                setDrawerOpen(false);
              }}
              type="button"
            >
              <span className="text-xs text-neutral-400">{index + 1}.</span>
              <span>{question}</span>
            </button>
          ))}
        </div>
      </aside>

      <Button
        className="fixed bottom-4 right-4 z-50 rounded-full px-4 shadow-lg sm:bottom-6 sm:right-6"
        onClick={() => setDrawerOpen((prev) => !prev)}
        type="button"
      >
        Questions
      </Button>
    </main>
  );
}
