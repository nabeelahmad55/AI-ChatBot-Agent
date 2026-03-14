export default function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer className="bg-card">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 py-8 md:flex-row">
        <p className="text-sm text-muted-foreground">© {year} ReactSite. All rights reserved.</p>
        <div className="flex items-center gap-4">
          {/* Top takes you to the homepage */}
          <a href="/" className="text-sm text-muted-foreground hover:text-foreground">
            Top
          </a>
          {/* Features page route */}
          <a href="/features" className="text-sm text-muted-foreground hover:text-foreground">
            Features
          </a>
          {/* Get in touch page route */}
          <a href="/get-in-touch" className="text-sm text-muted-foreground hover:text-foreground">
            Get in touch
          </a>
        </div>
      </div>
    </footer>
  )
}
