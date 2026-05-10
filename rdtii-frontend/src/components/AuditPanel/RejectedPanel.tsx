import type { RejectedExtraction } from "../../types";

type RejectedPanelProps = {
  rejected: RejectedExtraction[];
  open: boolean;
  setOpen: (v: boolean) => void;
};

export function RejectedPanel({ rejected, open, setOpen }: RejectedPanelProps) {
  return (
    <details
      className="rejected-panel"
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
    >
      <summary>Rejected extractions ({rejected.length})</summary>
      <ul>
        {rejected.map((r, i) => (
          <li key={i} className="rejected-item">
            <div className="rejected-reason">{r.reason}</div>
            {r.chunk_preview ? (
              <pre className="rejected-preview">{r.chunk_preview}</pre>
            ) : null}
          </li>
        ))}
      </ul>
    </details>
  );
}
