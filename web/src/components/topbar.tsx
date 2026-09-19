export function TopBar() {
  return (
    <div className="sticky top-0 z-50 border-b border-rule bg-paper/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-2.5 md:px-8">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">
          Case File Nº 4.0-P
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">
          IdeaForge <span className="text-rule-strong">·</span> Parakh
        </span>
      </div>
    </div>
  );
}
