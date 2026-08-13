"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { StockSummary, SyncResult } from "@/lib/types";

type Status = "loading" | "ready" | "error";

function changeTone(pct: number | null): string {
  if (pct === null || pct === undefined) return "text-neutral-200";
  if (pct > 0) return "text-emerald-400";
  if (pct < 0) return "text-red-400";
  return "text-neutral-300";
}

export default function StockList() {
  const [stocks, setStocks] = useState<StockSummary[]>([]);
  const [status, setStatus] = useState<Status>("loading");
  const [syncing, setSyncing] = useState(false);
  const [syncSummary, setSyncSummary] = useState<string | null>(null);

  async function load() {
    try {
      const data = await api.listStocks();
      setStocks(data);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSyncDefaults() {
    setSyncing(true);
    setSyncSummary(null);
    try {
      const results: SyncResult[] = await api.syncDefaults();
      const ok = results.filter((r) => r.rows_synced > 0).length;
      setSyncSummary(`Đồng bộ xong: ${ok}/${results.length} mã thành công.`);
      await load();
    } catch (e) {
      setSyncSummary(e instanceof Error ? `Lỗi: ${e.message}` : "Lỗi không xác định");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-mono text-lg font-bold">Danh sách mã</h2>
        <button
          onClick={handleSyncDefaults}
          disabled={syncing}
          className="rounded-md border border-emerald-500 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-400 disabled:opacity-50"
        >
          {syncing ? "Đang đồng bộ… (có thể mất 1-2 phút)" : "Đồng bộ danh sách mặc định"}
        </button>
      </div>

      {syncSummary && <p className="mb-3 text-xs text-neutral-400">{syncSummary}</p>}

      {status === "loading" && <p className="text-sm text-neutral-500">Đang tải…</p>}

      {status === "error" && <p className="text-sm text-red-400">Không tải được danh sách mã.</p>}

      {status === "ready" && stocks.length === 0 && (
        <p className="text-sm text-neutral-500">
          Chưa có mã nào trong hệ thống. Tìm và mở 1 mã ở trên (sẽ tự đồng bộ), hoặc bấm{" "}
          <span className="text-neutral-300">&ldquo;Đồng bộ danh sách mặc định&rdquo;</span> để lấy sẵn 10
          mã phổ biến.
        </p>
      )}

      {status === "ready" && stocks.length > 0 && (
        <div className="flex flex-col gap-2">
          {stocks.map((s) => (
            <Link
              key={s.symbol}
              href={`/stock/${s.symbol}`}
              className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-3 hover:border-neutral-600"
            >
              <span className="w-16 shrink-0 font-mono font-bold text-neutral-100">{s.symbol}</span>
              <span className="min-w-0 flex-1 truncate px-3 text-sm text-neutral-400">
                {s.company_name}
              </span>
              {s.current_price !== null && (
                <span className="flex shrink-0 items-baseline gap-2 text-right font-mono text-sm">
                  <span className={changeTone(s.change_pct)}>{s.current_price}</span>
                  {s.change_pct !== null && (
                    <span className={`w-16 text-xs ${changeTone(s.change_pct)}`}>
                      {s.change_pct >= 0 ? "▲" : "▼"} {Math.abs(s.change_pct).toFixed(2)}%
                    </span>
                  )}
                  {s.price_source === "close" && (
                    <span className="text-[10px] text-neutral-600" title="Giá đóng cửa gần nhất">
                      ĐC
                    </span>
                  )}
                </span>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
