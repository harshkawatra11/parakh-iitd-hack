import { cn } from "@/lib/utils";

export function Kicker({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "font-mono text-[11px] uppercase tracking-[0.18em] text-seal",
        className
      )}
    >
      {children}
    </div>
  );
}

export function SectionHeading({
  kicker,
  title,
  lede,
  className,
}: {
  kicker: string;
  title: React.ReactNode;
  lede?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-10 md:mb-14", className)}>
      <Kicker className="mb-3">{kicker}</Kicker>
      <h2 className="font-serif text-[2.25rem] md:text-[3rem] leading-[1.05] text-ink">
        {title}
      </h2>
      {lede && (
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-ink-2">
          {lede}
        </p>
      )}
    </div>
  );
}

export function Rule({ className }: { className?: string }) {
  return <div className={cn("h-px w-full bg-rule", className)} />;
}

export function Stat({
  value,
  label,
}: {
  value: React.ReactNode;
  label: string;
}) {
  return (
    <div className="flex flex-col gap-1 border-l border-rule pl-4 first:border-l-0 first:pl-0 md:first:border-l md:first:pl-4">
      <div className="font-mono text-2xl md:text-3xl font-medium text-ink font-tnum">
        {value}
      </div>
      <div className="font-mono text-[11px] uppercase tracking-wide text-ink-3">
        {label}
      </div>
    </div>
  );
}

export function Badge({
  tone = "ink",
  children,
  className,
}: {
  tone?: "ink" | "seal" | "verdigris" | "ochre" | "olive";
  children: React.ReactNode;
  className?: string;
}) {
  const tones: Record<string, string> = {
    ink: "bg-paper-2 text-ink-2 border-rule-strong",
    seal: "bg-seal-tint text-seal border-seal/30",
    verdigris: "bg-verdigris-tint text-verdigris border-verdigris/30",
    ochre: "bg-ochre-tint text-ochre border-ochre/30",
    olive: "bg-paper-2 text-olive border-olive/30",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-[3px] border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function Container({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mx-auto w-full max-w-6xl px-4 md:px-8", className)}>
      {children}
    </div>
  );
}

export function Section({
  children,
  className,
  id,
}: {
  children: React.ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section id={id} className={cn("py-16 md:py-28 border-b border-rule", className)}>
      <Container>{children}</Container>
    </section>
  );
}
