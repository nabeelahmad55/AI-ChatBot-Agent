export default function FAQ() {
  const faqs = [
    {
      q: "What’s included?",
      a: "A clear structure, responsive design, and accessible components.",
    },
    { q: "Is it fast?", a: "Yes. Lightweight sections keep load times low." },
    { q: "Can I customize it?", a: "Absolutely. Edit copy, styles, and sections." },
    {
      q: "Do I need TypeScript?",
      a: "No. This site uses only JavaScript and JSX.",
    },
  ]

  return (
    <section id="faq" className="border-b border-border bg-secondary">
      <div className="mx-auto max-w-7xl px-4 py-16">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-bold md:text-3xl">Frequently asked</h2>
          <p className="mt-2 text-muted-foreground">Quick, direct answers.</p>
        </div>

        <div className="mx-auto mt-8 max-w-3xl">
          {faqs.map((f, i) => (
            <details key={i} className="group rounded-md border border-border bg-card p-4">
              <summary className="cursor-pointer list-none font-medium">
                {f.q}
                <span className="ml-2 text-muted-foreground group-open:hidden">{"+"}</span>
                <span className="ml-2 text-muted-foreground hidden group-open:inline">{"–"}</span>
              </summary>
              <p className="mt-2 text-sm text-muted-foreground">{f.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}
