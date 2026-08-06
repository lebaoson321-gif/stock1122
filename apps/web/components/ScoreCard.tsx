export default function ScoreCard() {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-5">
      <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Điểm chấm cổ phiếu
      </div>
      <div className="flex flex-col items-center justify-center py-6 text-center">
        <div className="mb-2 text-2xl">🚧</div>
        <div className="text-sm text-neutral-400">
          Analysis Engine (chấm điểm xu hướng, thanh khoản, biến động) sắp ra mắt.
        </div>
      </div>
    </div>
  );
}
