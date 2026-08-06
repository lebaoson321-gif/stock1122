import type { PredictionResult } from "@/lib/types";

interface Props {
  prediction: PredictionResult;
}

export default function AIPredictionCard({ prediction }: Props) {
  if (!prediction.available) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-5">
        <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
          AI Prediction
        </div>
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="mb-2 text-2xl">🤖</div>
          <div className="text-sm text-neutral-400">{prediction.message}</div>
        </div>
      </div>
    );
  }

  const prob = prediction.prob_up;
  const pct = prob !== null ? Math.round(prob * 100) : null;
  const up = prediction.predicted_label === "up";

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-5">
      <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        AI Prediction
      </div>
      <div className="py-2 text-center">
        <div className={`font-mono text-4xl font-bold ${up ? "text-emerald-400" : "text-red-400"}`}>
          {pct !== null ? `${pct}%` : "—"}
        </div>
        <div className="mt-1 text-xs text-neutral-500">Xác suất tăng giá phiên tới</div>
      </div>
      <div className="mb-3 mt-2 h-1.5 overflow-hidden rounded-full bg-neutral-800">
        <div
          className={`h-full rounded-full ${up ? "bg-emerald-500" : "bg-red-500"}`}
          style={{ width: `${pct ?? 0}%` }}
        />
      </div>
      <div className="text-center text-xs text-neutral-500">
        Model: {prediction.model_name} ({prediction.model_version}) — dữ liệu ngày {prediction.date}
      </div>
    </div>
  );
}
