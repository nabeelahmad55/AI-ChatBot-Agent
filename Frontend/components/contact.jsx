"use client"

import { useState } from "react"

export default function Contact() {
  const [status, setStatus] = useState(null)

  function handleSubmit(e) {
    e.preventDefault()
    // Simulate sending message
    setStatus("Thanks! We’ll reply soon.")
  }

  return (
    <section id="contact" className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 py-16">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-bold md:text-3xl">Contact</h2>
          <p className="mt-2 text-muted-foreground">Short message. Quick reply.</p>
        </div>

        <form onSubmit={handleSubmit} className="mx-auto mt-8 max-w-xl rounded-lg border border-border bg-card p-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="flex flex-col gap-2">
              <label htmlFor="name" className="text-sm">
                Name
              </label>
              <input
                id="name"
                name="name"
                className="rounded-md border border-input bg-background px-3 py-2"
                placeholder="Your name"
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="email" className="text-sm">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                className="rounded-md border border-input bg-background px-3 py-2"
                placeholder="you@example.com"
                required
              />
            </div>
          </div>

          <div className="mt-4 flex flex-col gap-2">
            <label htmlFor="message" className="text-sm">
              Message
            </label>
            <textarea
              id="message"
              name="message"
              rows={4}
              className="rounded-md border border-input bg-background px-3 py-2"
              placeholder="How can we help?"
              required
            />
          </div>

          <div className="mt-6 flex items-center gap-3">
            <button
              type="submit"
              className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground"
            >
              Send
            </button>
            {status && <p className="text-sm text-muted-foreground">{status}</p>}
          </div>
        </form>
      </div>
    </section>
  )
}
