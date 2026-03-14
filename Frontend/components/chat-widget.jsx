"use client";

import React, { useState, useRef, useEffect } from "react";

export default function ChatWidget() {
  const [messages, setMessages] = useState([]); // start empty
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Scroll behavior
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ✅ On page load, get AI’s first dynamic greeting
  useEffect(() => {
    const fetchInitialMessage = async () => {
      const pageText = document.body.innerText.slice(0, 4000);
      try {
        const res = await fetch("http://localhost:3000/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pageContent: pageText,
            userMessage: "", // no user input yet
          }),
        });
        const data = await res.json();
        setMessages([{ id: Date.now(), role: "assistant", content: data.answer }]);
      } catch (err) {
        setMessages([
          { id: Date.now(), role: "assistant", content: "⚠️ Failed to load greeting." },
        ]);
      }
    };

    fetchInitialMessage();
  }, []);

  // ✅ Send message to backend
  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = { id: Date.now(), role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const pageText = document.body.innerText.slice(0, 4000);

    try {
      const res = await fetch("http://localhost:3000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pageContent: pageText,
          userMessage: input,
        }),
      });

      const data = await res.json();
      const botMsg = {
        id: Date.now() + 1,
        role: "assistant",
        content: data.answer || "No response from AI.",
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 2,
          role: "assistant",
          content: "⚠️ Error: Could not connect to server.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[28rem] border rounded-xl bg-card shadow-md">
      {/* Messages */}
      <div
        ref={messagesEndRef}
        className="flex-1 overflow-y-auto p-3 space-y-3 bg-background"
      >
        {messages.map((m) => (
          <div
            key={m.id}
            className={
              m.role === "user"
                ? "ml-auto max-w-[85%] rounded-lg bg-primary text-primary-foreground px-3 py-2 text-sm"
                : "mr-auto max-w-[85%] rounded-lg bg-muted text-muted-foreground px-3 py-2 text-sm"
            }
          >
            {m.content}
          </div>
        ))}
        {loading && (
          <div className="text-gray-500 text-sm italic">AI is typing...</div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="p-2 border-t border-border bg-card">
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="inline-flex items-center justify-center h-9 px-3 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
