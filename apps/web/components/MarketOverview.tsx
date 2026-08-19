"use client";

import { useEffect, useState } from "react";
import IndexLineChart from "./IndexLineChart";
import { api } from "@/lib/api";
import type { IndexBarOut, IndexCode, IndexQuote } from "@/lib/types";
import { useMarketSession } from "@/lib/useMarketSession";
import { vnCalendarDate, vnDate } from "@/lib/vnTime";

type Status = "loading" | "ready" | "error";

function changeTone(pct: number): string {
  if (pct > 0) return "text-emerald-400";
  if (pct < 0) return "text-red-400";
  return "text-neutral-300";
}

export default function MarketOverview() {
  const [indices, setIndices] = useState<IndexQuote[]>([]);
  const [status, setStatus] = useState<Status>("loading");
  const [expanded, setExpanded] = useState<IndexCode | null>(null);
  const [history, setHistory] = useState<IndexBarOut[]>([]);
  const [historyStatus, setHistoryStatus] = useState<Status>("loading");
  const marketSession = useMarketSession();

  // Chỉ biết "phiên gần nhất" là hôm nay khi hôm nay đúng là ngày giao
  // dịch. Cuối tuần/lễ thì idx.date lệch so với server_time là chuyện
  // bình thường (số của phiên gần nhất trước đó) — không phải dữ liệu cũ.
  const isStale = (indexDate: string): boolean =>
    !!marketSession && marketSession.is_trading_day && indexDate !== vnCalendarDate(marketSession.server_time);

  useEffect(() => {
    api
      .getIndices()
      .then((data) => {
        setIndices(data);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  async function toggleExpand(code: IndexCode) {
    if (expanded === code) {
      setExpanded(null);
      return;
    }
    setExpanded(code);
    setHistoryStatus("loading");
    try {
      const data = await api.getIndexHistory(code);
      setHistory(data);
      setHistoryStatus("ready");
    } catch {
      setHistoryStatus("error");
    }
  }

  if (status === "loading") {
    return <p className="text-sm text-neutral-500">Đang tải chỉ số thị trường…</p>;
  }

  // Chưa từng /indices/sync — đừng chiếm chỗ trên trang chủ bằng 1 khối
  // rỗng, người dùng chưa cần biết tính năng này tồn tại cho tới khi có
  // dữ liệu.
  if (status === "error" || indices.length === 0) {
    return null;
  }

  return (
    <div>
      <h2 className="mb-3 font-mono text-lg font-bold">Tổng quan thị trường</h2>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {indices.map((idx) => (
          <button
            key={idx.code}
            onClick={() => toggleExpand(idx.code)}
            className={`rounded-lg border px-4 py-3 text-left transition-colors ${
              expanded === idx.code
                ? "border-sky-500 bg-sky-500/10"
                : "border-neutral-800 bg-neutral-900 hover:border-neutral-600"
            }`}
          >
            <div className="text-xs text-neutral-400">{idx.name}</div>
            <div className="mt-1 font-mono text-lg font-bold text-neutral-100">
              {idx.close.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}
            </div>
            <div className={`mt-0.5 font-mono text-xs ${changeTone(idx.change_pct)}`}>
              {idx.change_point >= 0 ? "▲" : "▼"} {Math.abs(idx.change_point).toFixed(2)} (
              {Math.abs(idx.change_pct).toFixed(2)}%)
            </div>
            {idx.is_intraday ? (
              <div
                className="mt-0.5 flex items-center gap-1.5 text-[11px] font-medium text-amber-400"
                title="Chỉ số đang cập nhật giữa phiên, số còn thay đổi tới khi hết phiên."
              >
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
                Đang giao dịch
              </div>
            ) : (
              <div
                className={`mt-0.5 text-[11px] ${isStale(idx.date) ? "font-medium text-amber-400" : "text-neutral-500"}`}
              >
                {isStale(idx.date) ? `Phiên ${vnDate(idx.date)}` : vnDate(idx.date)}
              </div>
            )}
          </button>
        ))}
      </div>

      {expanded && (
        <div className="mt-3 rounded-lg border border-neutral-800 bg-neutral-900 p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-semibold text-neutral-200">
              {indices.find((i) => i.code === expanded)?.name}
            </span>
            <span className="text-xs text-neutral-500">
              Cập nhật: {vnDate(indices.find((i) => i.code === expanded)?.date ?? "")}
            </span>
          </div>
          {historyStatus === "loading" && <p className="text-sm text-neutral-500">Đang tải biểu đồ…</p>}
          {historyStatus === "error" && (
            <p className="text-sm text-red-400">Không tải được lịch sử chỉ số.</p>
          )}
          {historyStatus === "ready" && <IndexLineChart data={history} />}
        </div>
      )}
    </div>
  );
}
