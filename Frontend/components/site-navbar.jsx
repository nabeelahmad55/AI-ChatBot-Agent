"use client"

import { useState } from "react"

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const links = [
    { href: "/features", label: "Features" },
    { href: "#stats", label: "Stats" },
    { href: "#testimonials", label: "Stories" },
    { href: "#faq", label: "FAQ" },
    { href: "/get-in-touch", label: "Contact" },
  ]

  return (
    <nav className="w-full border-b border-border bg-card">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <a href="#" className="flex items-center gap-2" aria-label="Homepage">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground font-semibold">
            R
          </span>
          <span className="font-semibold">ReactSite</span>
        </a>

        <button
          onClick={() => setOpen(!open)}
          className="rounded-md border border-border px-3 py-2 md:hidden"
          aria-expanded={open}
          aria-controls="primary-navigation"
        >
          <span className="sr-only">Toggle menu</span>
          {"≡"}
        </button>

        <ul
          id="primary-navigation"
          className={`absolute left-0 right-0 top-14 z-50 mx-4 flex flex-col gap-2 rounded-md border border-border bg-card p-4 md:static md:z-auto md:mx-0 md:flex md:flex-row md:items-center md:gap-6 md:border-0 md:bg-transparent md:p-0 ${open ? "" : "hidden md:flex"}`}
        >
          {links.map((l) => (
            <li key={l.href}>
              <a
                href={l.href}
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                onClick={() => setOpen(false)}
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  )
}
