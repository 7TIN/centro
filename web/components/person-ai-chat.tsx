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
    <main className="flex h-[100dvh] w-full items-center justify-center bg-neutral-50/50 p-4 md:p-6 lg:p-8">
      <div className="w-full max-w-6xl h-full max-h-[900px]">
        <Card className="flex h-full flex-col overflow-hidden shadow-lg border-neutral-200/60 bg-white">
          
          {/* --- Header Section --- */}
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
              onClick={onNewSetup} 
              variant="outline" 
              size="sm" 
              className="rounded-full px-4 shadow-sm hover:bg-neutral-100"
            >
              New Setup
            </Button>
          </CardHeader>

          {/* --- Body Section --- */}
          <CardContent className="flex flex-1 flex-col lg:flex-row p-0 overflow-hidden bg-neutral-50/30">
            
            {/* Main Chat Area */}
            <section className="flex flex-1 flex-col overflow-hidden relative">
              
              {/* Messages Container */}
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
                {/* Scroll Anchor */}
                <div ref={endOfMessagesRef} className="h-1" />
              </div>

              {/* Input Area */}
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
                      if (e.key === 'Enter' && !e.shiftKey) {
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

            {/* Sidebar / Suggested Questions */}
            <aside className="w-full lg:w-[320px] bg-neutral-50 border-t lg:border-t-0 lg:border-l border-neutral-200 flex flex-col shrink-0 p-5 z-20">
              
              <p className="text-sm font-bold text-neutral-800 mb-4 flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-neutral-500"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/></svg>
                Suggested Questions
              </p>

              {/* Custom Dropdown (No React state needed) */}
              <details className="group relative w-full mb-3">
                <summary className="flex cursor-pointer items-center justify-between w-full rounded-md border border-neutral-300 bg-white px-3 py-2.5 text-sm text-neutral-700 shadow-sm transition-all hover:bg-neutral-50 list-none [&::-webkit-details-marker]:hidden focus:outline-none focus:ring-2 focus:ring-neutral-900/10">
                  <span className="truncate pr-2">
                    {selectedQuestion || "Select a question..."}
                  </span>
                  <svg className="h-4 w-4 shrink-0 text-neutral-500 transition-transform duration-200 group-open:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </summary>
                
                {/* The Dropdown List Card */}
                <div className="absolute left-0 right-0 z-50 mt-2 bg-white rounded-md border border-neutral-200 shadow-lg overflow-hidden max-h-[50vh] overflow-y-auto scrollbar-thin">
                  {suggestedQuestions.map((question, index) => (
                    <button
                      key={question}
                      type="button"
                      className="w-full px-4 py-3 text-left text-sm text-neutral-600 transition-colors hover:bg-neutral-50 hover:text-neutral-900 border-b border-neutral-100 last:border-0 flex items-start gap-2.5"
                      onClick={(e) => {
                        // Update the selected text
                        onSelectedQuestionChange(question);
                        // Optional UX touch: automatically closes the <details> tag when clicked
                        e.currentTarget.closest('details')?.removeAttribute('open');
                      }}
                    >
                      <span className="text-neutral-300 font-medium mt-[1px] text-xs">
                        {index + 1}.
                      </span> 
                      <span className="leading-snug">
                        {question}
                      </span>
                    </button>
                  ))}
                </div>
              </details>

              <Button
                className="w-full rounded-md shadow-sm"
                onClick={onUseSelectedQuestion}
                variant="secondary"
              >
                Use Selected Question
              </Button>

            </aside>

          </CardContent>
        </Card>
      </div>
    </main>
  );
}
