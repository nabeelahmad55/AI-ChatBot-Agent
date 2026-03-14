export default function Hero() {
  return (
    <section id="home" className="border-b border-border bg-card">
      <div className="mx-auto max-w-7xl px-4 py-16 md:py-24">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-pretty text-3xl font-bold leading-tight md:text-5xl">
            Build a clean, concise site users love
          </h1>
          <p className="mt-4 text-balance text-muted-foreground md:text-lg">
            Clear sections. Friendly copy. Fast to scan. Everything you need to ship a simple, effective web presence.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <a href="#features" className="rounded-md bg-primary px-5 py-3 text-sm font-medium text-primary-foreground">
              See features
            </a>
            <a
              href="#contact"
              className="rounded-md border border-border px-5 py-3 text-sm font-medium text-foreground"
            >
              Get in touch
            </a>
          </div>
          <div className="mt-10">
            <img
              src="/product-preview-hero.jpg"
              alt="Product preview"
              className="mx-auto w-full max-w-3xl rounded-lg border border-border"
            />
          </div>
        </div>
      </div>
    </section>
  )
}
