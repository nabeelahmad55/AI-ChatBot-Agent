function Testimonial({ quote, author, role }) {
  return (
    <figure className="rounded-lg border border-border bg-card p-5">
      <blockquote className="text-pretty">
        {"“"}
        {quote}
        {"”"}
      </blockquote>
      <figcaption className="mt-3 text-sm text-muted-foreground">
        {author} • {role}
      </figcaption>
    </figure>
  )
}

export default function Testimonials() {
  const items = [
    {
      quote: "Clean, fast, and easy to understand. Our bounce rate dropped immediately.",
      author: "Alex P.",
      role: "Founder",
    },
    {
      quote: "The sections guide users to the right place without effort.",
      author: "Priya R.",
      role: "Product Lead",
    },
    {
      quote: "Finally, content that respects attention. It just works.",
      author: "Diego M.",
      role: "Engineer",
    },
  ]

  return (
    <section id="testimonials" className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 py-16">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-bold md:text-3xl">What people say</h2>
          <p className="mt-2 text-muted-foreground">Short, real feedback.</p>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          {items.map((t, i) => (
            <Testimonial key={i} quote={t.quote} author={t.author} role={t.role} />
          ))}
        </div>
      </div>
    </section>
  )
}
