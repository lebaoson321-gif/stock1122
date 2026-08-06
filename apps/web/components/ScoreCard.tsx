import type { ScoreResult } from "@/lib/types";

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  const v = value ?? 0;
  const pct = (v / 10) * 100;
  const color = v >= 7 ? "#00C076" : v >= 4 ? "#F0B90B" : "#F6465D";
  return (
    <div className="mb-3">
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-neutral-400">{label}</span>
        <span className="font-mono text-neutral-200">{value !== null ? value.toFixed(1) : "—"}/10</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-neutral-800">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

interface Props {
  score: ScoreResult;
}

export default function ScoreCard({ score }: Props) {
  if (!score.available) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-5">
        <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Điểm chấm cổ phiếu
        </div>
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="mb-2 text-2xl">⏳</div>
          <div className="text-sm text-neutral-400">{score.message}</div>
        </div>
      </div>
    );
  }

  const total = score.total_score;
  const totalColor = total !== null && total >= 7 ? "#00C076" : total !== null && total >= 4 ? "#F0B90B" : "#F6465D";

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-5">
      <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Điểm chấm cổ phiếu
      </div>
      <div className="mb-4 text-center">
        <div className="font-mono text-3xl font-bold" style={{ color: totalColor }}>
          {total !== null ? total.toFixed(1) : "—"}
          <span className="text-base text-neutral-500">/10</span>
        </div>
        <div className="text-xs text-neutral-500">Tổng điểm</div>
      </div>
      <ScoreBar label="Xu hướng" value={score.trend_score} />
      <ScoreBar label="Thanh khoản" value={score.liquidity_score} />
      <ScoreBar label="Ổn định (biến động thấp)" value={score.volatility_score} />
    </div>
  );
}
