"use client"

import { useState } from "react"

export default function GetInTouchPage() {
  const [status, setStatus] = useState(null)

  function onSubmit(e) {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const name = formData.get("name")
    setStatus(`Thanks ${name || "there"} — we’ll get back to you shortly.`)
    e.currentTarget.reset()
  }

  return (
    <main className="min-h-[70vh] bg-background text-foreground">
      <section className="mx-auto max-w-3xl px-4 py-12 md:py-16">
        <header className="mb-8 md:mb-10">
          <h1 className="text-balance text-3xl font-semibold md:text-4xl">Get in touch</h1>
          <p className="mt-2 text-muted-foreground">
            Reach us with a quick message, or use email for detailed requests.
          </p>
        </header>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="rounded-lg border border-border bg-card p-5">
            <h2 className="text-lg font-semibold">Contact options</h2>
            <ul className="mt-3 space-y-2">
              <li className="text-sm text-muted-foreground">
                Email:{" "}
                <a className="text-foreground underline" href="mailto:support@example.com">
                  support@example.com
                </a>
              </li>
              <li className="text-sm text-muted-foreground">Hours: Mon–Fri, 9am–5pm</li>
              <li className="text-sm text-muted-foreground">Live chat: use the chat bubble at the bottom-right.</li>
            </ul>
          </div>

          <form onSubmit={onSubmit} className="rounded-lg border border-border bg-card p-5" aria-label="Contact form">
            <div>
              <label htmlFor="name" className="text-sm font-medium">
                Name
              </label>
              <input
                id="name"
                name="name"
                required
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none"
                placeholder="Your name"
              />
            </div>

            <div className="mt-4">
              <label htmlFor="email" className="text-sm font-medium">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none"
                placeholder="you@example.com"
              />
            </div>

            <div className="mt-4">
              <label htmlFor="message" className="text-sm font-medium">
                Message
              </label>
              <textarea
                id="message"
                name="message"
                rows={4}
                required
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none"
                placeholder="How can we help?"
              />
            </div>

            <div className="mt-5 flex items-center gap-3">
              <button
                type="submit"
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
              >
                Send
              </button>
              <a
                href="/"
                className="inline-flex items-center justify-center rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground"
              >
                Back to Home
              </a>
            </div>

            {status && (
              <p className="mt-3 text-sm text-muted-foreground" role="status" aria-live="polite">
                {status}
              </p>
            )}
          </form>
        </div>
      </section>
    </main>
  )
}
