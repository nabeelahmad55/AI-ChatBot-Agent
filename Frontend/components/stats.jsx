export default function Stats() {
  const stats = [
    { label: "Load time", value: "< 1s" },
    { label: "Sections", value: "6+" },
    { label: "Accessibility", value: "AA+" },
    { label: "Lines of copy", value: "~120" },
  ]

  return (
    <section id="stats" className="border-b border-border bg-secondary">
      <div className="mx-auto max-w-7xl px-4 py-12">
        <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="rounded-md bg-card p-4 text-center">
              <div className="text-2xl font-bold">{s.value}</div>
              <div className="text-xs text-muted-foreground">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
