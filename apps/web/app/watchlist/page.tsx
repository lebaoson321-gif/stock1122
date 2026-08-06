"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import type { WatchlistOut } from "@/lib/types";

type Status = "loading" | "anonymous" | "ready" | "error";

export default function WatchlistPage() {
  const [status, setStatus] = useState<Status>("loading");
  const [watchlist, setWatchlist] = useState<WatchlistOut | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    let cancelled = false;
    const supabase = createClient();

    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (cancelled) return;
      if (!session) {
        setStatus("anonymous");
        return;
      }
      setAccessToken(session.access_token);
      try {
        const wl = await api.getWatchlist(session.access_token);
        if (cancelled) return;
        setWatchlist(wl);
        setStatus("ready");
      } catch (e) {
        if (cancelled) return;
        setErrorMsg(e instanceof Error ? e.message : "Lỗi không xác định");
        setStatus("error");
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  async function removeItem(stockId: number) {
    if (!accessToken) return;
    const wl = await api.removeWatchlistItem(stockId, accessToken);
    setWatchlist(wl);
  }

  if (status === "loading") {
    return <div className="text-neutral-400">Đang tải…</div>;
  }

  if (status === "anonymous") {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-8 text-center">
        <p className="mb-4 text-neutral-300">Đăng nhập để xem và quản lý watchlist.</p>
        <Link
          href="/login"
          className="rounded-md border border-emerald-500 bg-emerald-500/10 px-5 py-2 font-mono text-sm font-semibold text-emerald-400"
        >
          Đăng nhập
        </Link>
      </div>
    );
  }

  if (status === "error") {
    return <div className="text-red-400">Lỗi tải watchlist: {errorMsg}</div>;
  }

  return (
    <div>
      <h1 className="mb-6 font-mono text-2xl font-bold">Watchlist</h1>
      {watchlist && watchlist.items.length === 0 ? (
        <p className="text-neutral-400">
          Chưa có mã nào. Tìm mã ở trang{" "}
          <Link href="/" className="text-emerald-400 underline">
            Tổng quan
          </Link>{" "}
          rồi bấm &ldquo;Thêm vào watchlist&rdquo;.
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {watchlist?.items.map((item) => (
            <div
              key={item.stock_id}
              className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-3"
            >
              <Link href={`/stock/${item.symbol}`} className="flex items-baseline gap-3">
                <span className="font-mono font-bold text-neutral-100">{item.symbol}</span>
                <span className="text-sm text-neutral-400">{item.company_name}</span>
              </Link>
              <button
                onClick={() => removeItem(item.stock_id)}
                className="text-xs text-neutral-500 hover:text-red-400"
              >
                Xoá
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
