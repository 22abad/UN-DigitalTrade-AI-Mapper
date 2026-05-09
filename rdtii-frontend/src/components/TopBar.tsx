import type { Status } from "../types";

type TopBarProps = {
  country: string;
  provider: string;
  status: Status;
  mappingsCount: number;
  pendingCount: number;
  sourceUrl: string;
};

export function TopBar({
  country,
  provider,
  status,
  mappingsCount,
  pendingCount,
  sourceUrl,
}: TopBarProps) {
  const headerStatus =
    status === "loading"
      ? sourceUrl
        ? "Crawling..."
        : "Extracting…"
      : status === "error"
        ? "Error"
        : status === "ready"
          ? `${mappingsCount} mapping${mappingsCount === 1 ? "" : "s"} · ${pendingCount} pending`
          : "Idle";

  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">UN ESCAP DTAM</p>
        <h1>Digital Trade Evidence Workbench</h1>
      </div>
      <div className="status-strip">
        <span>Country {country}</span>
        <span>Provider {provider}</span>
        <span className={status === "error" ? "warn" : "ok"}>{headerStatus}</span>
      </div>
    </header>
  );
}
