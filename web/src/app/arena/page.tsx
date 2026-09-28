import { TopBar } from "@/components/topbar";
import { Container } from "@/components/ui/primitives";
import { ArenaMasthead } from "@/components/sections/arena-masthead";
import { ArenaBrief } from "@/components/sections/arena-brief";
import { ArenaCharts } from "@/components/sections/arena-charts";
import { ArenaSwapLog } from "@/components/sections/arena-swaplog";
import { ArenaMethod } from "@/components/sections/arena-method";
import { Colophon } from "@/components/sections/colophon";

export const metadata = {
  title: "The Battle Arena · Parakh",
  description:
    "Round 2 of Innov8 4.0: a six-hour live hiring market, 116 seats, 51 competing teams, and the agent that filled every seat and then upgraded 70 of them.",
};

export default function ArenaPage() {
  return (
    <>
      <TopBar />
      <main className="flex-1">
        <ArenaMasthead />
        <ArenaBrief />
        <ArenaCharts />
        <ArenaSwapLog />
        <ArenaMethod />
        <div className="border-b border-rule py-10">
          <Container>
            <p className="font-mono text-[11px] leading-relaxed text-ink-3">
              Full narrative, architecture diagrams, and an honest account of what did not
              work: see{" "}
              <a
                href="https://github.com/harshkawatra11/parakh-iitd-hack/blob/main/arena/ARENA_README.md"
                target="_blank"
                rel="noreferrer"
                className="text-seal hover:underline"
              >
                arena/ARENA_README.md
              </a>{" "}
              in the source repository, or return to the{" "}
              <a href="/" className="text-seal hover:underline">
                round 1 console
              </a>
              .
            </p>
          </Container>
        </div>
      </main>
      <Colophon />
    </>
  );
}
