import type { PartyResult } from "@/lib/types";

export default function ResultBars({ results }: { results: PartyResult[] }) {
  if (results.length === 0) {
    return <p style={{ fontSize: 13, color: "#888" }}>Još nema obrađenih rezultata.</p>;
  }
  return (
    <div>
      {results.map((r) => (
        <div key={r.short_name} style={{ marginBottom: 10 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 13,
              color: "#555",
              marginBottom: 3,
            }}
          >
            <span>{r.name}</span>
            <span style={{ fontWeight: 500, color: "#222" }}>{r.pct.toFixed(1)}%</span>
          </div>
          <div style={{ background: "#EEEDE7", borderRadius: 4, height: 10, overflow: "hidden" }}>
            <div
              style={{
                width: `${r.pct}%`,
                height: "100%",
                background: r.color_hex || "#378ADD",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
