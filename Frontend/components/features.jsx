function Feature({ title, desc, iconAlt }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <img src="/feature-icon.png" alt={iconAlt} className="h-12 w-12" />
      <h3 className="mt-3 text-lg font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{desc}</p>
    </div>
  )
}

export default function Features() {
  const items = [
    {
      title: "Clear structure",
      desc: "Simple sections that help visitors find answers fast.",
      iconAlt: "Blocks icon",
    },
    {
      title: "Friendly content",
      desc: "Plain language that fits on one screen where possible.",
      iconAlt: "Chat bubble icon",
    },
    {
      title: "Responsive by default",
      desc: "Looks great on phones, tablets, and desktops.",
      iconAlt: "Devices icon",
    },
    {
      title: "Fast to load",
      desc: "Lightweight UI and assets so pages feel instant.",
      iconAlt: "Lightning icon",
    },
    {
      title: "Accessible",
      desc: "Good contrast, alt text, and semantic HTML.",
      iconAlt: "Accessibility icon",
    },
    {
      title: "Easy to maintain",
      desc: "Small components that are quick to edit.",
      iconAlt: "Wrench icon",
    },
  ]

  return (
    <section id="features" className="border-b border-border">
      <div className="mx-auto max-w-7xl px-4 py-16">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-2xl font-bold md:text-3xl">Features that matter</h2>
          <p className="mt-2 text-muted-foreground">Focused, useful pieces—no fluff.</p>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((f) => (
            <Feature key={f.title} title={f.title} desc={f.desc} iconAlt={f.iconAlt} />
          ))}
        </div>
      </div>
    </section>
  )
}
