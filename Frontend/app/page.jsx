import Navbar from "@/components/site-navbar"
import Hero from "@/components/hero"
import Features from "@/components/features"
import Stats from "@/components/stats"
import Testimonials from "@/components/testimonials"
import FAQ from "@/components/faq"
import Contact from "@/components/contact"
import Footer from "@/components/site-footer"

export default function HomePage() {
  return (
    <div className="bg-background text-foreground">
      <header>
        <Navbar />
      </header>

      <main>
        <Hero />
        <Features />
        <Stats />
        <Testimonials />
        <FAQ />
        <Contact />
      </main>

      <Footer />
    </div>
  )
}
