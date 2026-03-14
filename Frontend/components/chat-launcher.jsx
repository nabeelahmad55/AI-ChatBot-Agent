"use client"

import React from "react"
import ChatWidget from "./chat-widget"

export default function ChatLauncher() {
  const [open, setOpen] = React.useState(false)

  return (
    <>
      {open && <div className="fixed inset-0 z-40 bg-black/20" aria-hidden="true" onClick={() => setOpen(false)} />}

      <div
        className="fixed z-50 bottom-4 right-4 flex flex-col items-end gap-3"
        role="region"
        aria-label="Support chat"
      >
        {open && (
          <div
            className="w-[22rem] max-w-[calc(100vw-2rem)] bg-background text-foreground border border-border rounded-lg shadow-xl overflow-hidden"
            role="dialog"
            aria-modal="true"
            aria-label="Support chat dialog"
          >
            <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-card text-card-foreground">
              <div className="text-sm font-medium">Support</div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="inline-flex items-center justify-center h-8 w-8 rounded hover:bg-accent hover:text-accent-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label="Close support chat"
              >
                <svg
                  aria-hidden="true"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <ChatWidget />
          </div>
        )}

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center justify-center h-12 w-12 rounded-full bg-primary text-primary-foreground shadow-lg hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={open ? "Close support chat" : "Open support chat"}
        >
          {/* chat bubble icon */}
          <svg
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            className="h-6 w-6"
            fill="currentColor"
          >
            <path d="M4 5a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3H9.83L6 19.83A1 1 0 0 1 4.5 19V5Z" />
          </svg>
        </button>
      </div>
    </>
  )
}
