"use client";

import { useMarketSession } from "@/lib/useMarketSession";
import type { MarketState } from "@/lib/types";
import { vnDateTime, vnTime } from "@/lib/vnTime";

/** Xanh = đang khớp lệnh, vàng = trong ngày nhưng tạm nghỉ, xám = đóng. */
const TONE: Record<MarketState, string> = {
  ato: "bg-emerald-500/10 text-emerald-400 border-emerald-500/40",
  morning: "bg-emerald-500/10 text-emerald-400 border-emerald-500/40",
  afternoon: "bg-emerald-500/10 text-emerald-400 border-emerald-500/40",
  atc: "bg-emerald-500/10 text-emerald-400 border-emerald-500/40",
  lunch: "bg-amber-500/10 text-amber-400 border-amber-500/40",
  pre_open: "bg-amber-500/10 text-amber-400 border-amber-500/40",
  post: "bg-neutral-700/30 text-neutral-400 border-neutral-700",
  closed: "bg-neutral-700/30 text-neutral-400 border-neutral-700",
  weekend: "bg-neutral-700/30 text-neutral-400 border-neutral-700",
};

export default function MarketStatusBadge() {
  const status = useMarketSession();
  if (!status) return null;

  const tone = TONE[status.state] ?? TONE.closed;
  const hint =
    status.next_change !== null
      ? status.is_open
        ? `đến ${vnTime(status.next_change)}`
        : `mở lúc ${vnTime(status.next_change)}`
      : null;

  return (
    <span
      className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${tone}`}
      title={
        status.last_quote_at
          ? `Giá trong phiên cập nhật gần nhất: ${vnDateTime(status.last_quote_at)} (giờ VN)`
          : "Chưa có dữ liệu giá trong phiên"
      }
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${status.is_open ? "animate-pulse bg-emerald-400" : "bg-neutral-500"}`}
      />
      {status.label}
      {hint && <span className="text-neutral-500">· {hint}</span>}
    </span>
  );
}
