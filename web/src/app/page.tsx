import { TopBar } from "@/components/topbar";
import { Masthead } from "@/components/sections/masthead";
import { Brief } from "@/components/sections/brief";
import { Funnel } from "@/components/sections/funnel";
import { Evidence } from "@/components/sections/evidence";
import { Shortlist } from "@/components/sections/shortlist";
import { Ledger } from "@/components/sections/ledger";
import { Validation } from "@/components/sections/validation";
import { Method } from "@/components/sections/method";
import { Colophon } from "@/components/sections/colophon";

export default function Home() {
  return (
    <>
      <TopBar />
      <main className="flex-1">
        <Masthead />
        <Brief />
        <Funnel />
        <Evidence />
        <Shortlist />
        <Ledger />
        <Validation />
        <Method />
      </main>
      <Colophon />
    </>
  );
}
