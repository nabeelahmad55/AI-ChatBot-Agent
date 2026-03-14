import Navbar from "@/components/site-navbar"
import Footer from "@/components/site-footer"

export default function FeaturesPage() {
  const features = [
    { title: "Fast performance", desc: "Quick loads and smooth navigation." },
    { title: "Clean UI", desc: "Simple layouts that highlight the content." },
    { title: "Mobile-first", desc: "Looks great on phones, tablets, and desktops." },
    { title: "Accessible", desc: "Built with semantic HTML and ARIA where needed." },
    { title: "Scalable", desc: "Add sections and pages without complexity." },
    { title: "Easy to maintain", desc: "Clear structure, minimal dependencies." },
  ]

  return (
    <div className="bg-background text-foreground">
      <header>
        <Navbar />
      </header>

      <main className="min-h-[70vh] bg-background text-foreground">
        <section className="mx-auto max-w-5xl px-4 py-12 md:py-16">
          <header className="mb-8 md:mb-10">
            <h1 className="text-balance text-3xl font-semibold md:text-4xl">All Features</h1>
            <p className="mt-2 text-muted-foreground">A concise overview of what you get, without fluff.</p>
          </header>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <article key={f.title} className="rounded-lg border border-border bg-card p-5" aria-label={f.title}>
                <h2 className="text-lg font-semibold">{f.title}</h2>
                <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
              </article>
            ))}
          </div>

          <div className="mt-10 flex items-center gap-3">
            <a
              href="/"
              className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              Back to Home
            </a>
            <a
              href="/get-in-touch"
              className="inline-flex items-center justify-center rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground"
            >
              Get in touch
            </a>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
