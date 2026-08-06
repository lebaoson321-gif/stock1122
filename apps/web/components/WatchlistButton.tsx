"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

interface Props {
  symbol: string;
}

export default function WatchlistButton({ symbol }: Props) {
  const [status, setStatus] = useState<"checking" | "anonymous" | "in" | "out" | "error">("checking");
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [stockId, setStockId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

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
        const watchlist = await api.getWatchlist(session.access_token);
        const item = watchlist.items.find((i) => i.symbol === symbol.toUpperCase());
        if (cancelled) return;
        if (item) {
          setStockId(item.stock_id);
          setStatus("in");
        } else {
          setStatus("out");
        }
      } catch {
        if (!cancelled) setStatus("error");
      }
    });

    return () => {
      cancelled = true;
    };
  }, [symbol]);

  async function toggle() {
    if (!accessToken || busy) return;
    setBusy(true);
    try {
      if (status === "in" && stockId !== null) {
        const watchlist = await api.removeWatchlistItem(stockId, accessToken);
        const item = watchlist.items.find((i) => i.symbol === symbol.toUpperCase());
        setStatus(item ? "in" : "out");
      } else {
        const watchlist = await api.addWatchlistItem(symbol, accessToken);
        const item = watchlist.items.find((i) => i.symbol === symbol.toUpperCase());
        if (item) {
          setStockId(item.stock_id);
          setStatus("in");
        }
      }
    } catch {
      setStatus("error");
    } finally {
      setBusy(false);
    }
  }

  if (status === "checking") return null;

  if (status === "anonymous") {
    return (
      <Link href="/login" className="text-xs text-neutral-400 underline hover:text-neutral-200">
        Đăng nhập để lưu watchlist
      </Link>
    );
  }

  if (status === "error") {
    return <span className="text-xs text-red-400">Lỗi tải watchlist</span>;
  }

  return (
    <button
      onClick={toggle}
      disabled={busy}
      className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
        status === "in"
          ? "border-emerald-500 bg-emerald-500/10 text-emerald-400"
          : "border-neutral-700 text-neutral-400 hover:border-neutral-500"
      } ${busy ? "opacity-50" : ""}`}
    >
      {status === "in" ? "★ Trong watchlist" : "☆ Thêm vào watchlist"}
    </button>
  );
}
