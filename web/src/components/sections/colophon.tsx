import { Container } from "@/components/ui/primitives";

export function Colophon() {
  return (
    <footer className="py-14">
      <Container>
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="font-serif text-xl text-ink">परख · Parakh</div>
            <p className="mt-2 max-w-sm font-mono text-[11px] leading-relaxed text-ink-3">
              Built for Innov8 4.0 · Eightfold.ai × ARIES, IIT Delhi.
              <br />
              Team IdeaForge.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-x-10 gap-y-2 font-mono text-[11px] text-ink-3">
            <a
              href="https://github.com/harshkawatra11/parakh-iitd-hack"
              className="hover:text-ink"
              target="_blank"
              rel="noreferrer"
            >
              Source →
            </a>
            <span>Next.js · shadcn/ui</span>
            <span>Framer Motion · GSAP</span>
            <span>Chart.js</span>
          </div>
        </div>
      </Container>
    </footer>
  );
}
