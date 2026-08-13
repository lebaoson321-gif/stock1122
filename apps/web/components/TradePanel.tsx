"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import type { PortfolioOut, PortfolioResult } from "@/lib/types";

type Status = "loading" | "anonymous" | "no-portfolio" | "ready" | "error";

function fmtVnd(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("vi-VN", { maximumFractionDigits: 0 });
}

/** Giá lưu theo nghìn VND (biểu đồ hiện 70.70); tiền theo VND. */
const PRICE_UNIT_VND = 1000;

function toneOf(n: number | null | undefined): string {
  if (n === null || n === undefined) return "text-neutral-200";
  return n >= 0 ? "text-emerald-400" : "text-red-400";
}

/** "+1.234.000đ (+2,15%)" — dấu + hiện tường minh để phân biệt ngay với lỗ. */
function signed(amount: number | null | undefined, pct: number | null | undefined): string {
  if (amount === null || amount === undefined) return "—";
  const sign = amount >= 0 ? "+" : "";
  const pctText =
    pct === null || pct === undefined ? "" : ` (${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%)`;
  return `${sign}${fmtVnd(amount)}đ${pctText}`;
}

function Row({
  label,
  value,
  tone = "text-neutral-200",
  hint,
}: {
  label: string;
  value: string;
  tone?: string;
  hint?: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2 text-sm">
      <span className="whitespace-nowrap text-neutral-500">{label}</span>
      <span className={`text-right font-mono ${tone}`}>
        {value}
        {hint && <span className="ml-1 text-[10px] text-neutral-600">{hint}</span>}
      </span>
    </div>
  );
}

/**
 * `referencePrice` là giá đóng cửa gần nhất mà trang chi tiết đã tải sẵn
 * — dùng để ước tính thành tiền khi CHƯA nắm mã (lúc đó danh mục không
 * có current_price cho mã này). Chỉ là ước tính hiển thị: giá khớp thật
 * do backend quyết định lúc đặt lệnh.
 */
export default function TradePanel({
  symbol,
  referencePrice,
}: {
  symbol: string;
  referencePrice?: number | null;
}) {
  const [status, setStatus] = useState<Status>("loading");
  const [portfolio, setPortfolio] = useState<PortfolioOut | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [quantity, setQuantity] = useState("100");
  const [errorMsg, setErrorMsg] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const applyPortfolio = useCallback((result: PortfolioResult) => {
    if (result.available === false) {
      setPortfolio(null);
      setStatus("no-portfolio");
    } else {
      setPortfolio(result as PortfolioOut);
      setStatus("ready");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    createClient()
      .auth.getSession()
      .then(async ({ data: { session } }) => {
        if (cancelled) return;
        if (!session) {
          setStatus("anonymous");
          return;
        }
        setAccessToken(session.access_token);
        try {
          const result = await api.getPortfolio(session.access_token);
          if (!cancelled) applyPortfolio(result);
        } catch (e) {
          if (cancelled) return;
          setErrorMsg(e instanceof Error ? e.message : "Lỗi không xác định");
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [applyPortfolio]);

  async function submit(side: "buy" | "sell") {
    if (!accessToken) return;
    const qty = Number(quantity);
    if (!Number.isInteger(qty) || qty <= 0) {
      setErrorMsg("Số lượng phải là số nguyên dương.");
      return;
    }
    setBusy(true);
    setErrorMsg("");
    setNotice("");
    try {
      const result = await api.placeOrder(symbol, side, qty, accessToken);
      setPortfolio(result.portfolio);
      const t = result.transaction;
      setNotice(
        `${side === "buy" ? "Đã mua" : "Đã bán"} ${t.quantity} ${t.symbol} @ ${t.price} — ${fmtVnd(
          t.amount,
        )}đ${t.price_source === "close" ? " (giá đóng cửa gần nhất)" : " (giá trong phiên)"}`,
      );
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Lỗi không xác định");
    } finally {
      setBusy(false);
    }
  }

  const holding = portfolio?.positions.find((p) => p.symbol === symbol);
  const qtyNum = Number(quantity) || 0;
  const estPrice = holding?.current_price ?? referencePrice ?? null;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
      <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Giao dịch ảo
      </div>

      {status === "loading" && <div className="text-sm text-neutral-400">Đang tải…</div>}

      {status === "anonymous" && (
        <div className="text-sm text-neutral-400">
          <Link href="/login" className="text-emerald-400 underline">
            Đăng nhập
          </Link>{" "}
          để mua bán bằng tiền ảo.
        </div>
      )}

      {status === "no-portfolio" && (
        <div className="text-sm text-neutral-400">
          Chưa có danh mục.{" "}
          <Link href="/portfolio" className="text-emerald-400 underline">
            Tạo danh mục
          </Link>{" "}
          để bắt đầu.
        </div>
      )}

      {status === "error" && <div className="text-sm text-red-400">{errorMsg}</div>}

      {status === "ready" && portfolio && (
        <div className="flex flex-col gap-3">
          <Row label="Tiền mặt" value={`${fmtVnd(portfolio.cash_balance)}đ`} />
          <Row
            label="Giá hiện tại"
            value={estPrice !== null ? String(estPrice) : "—"}
            hint={holding?.price_source === "close" ? "đóng cửa" : undefined}
          />

          {holding ? (
            <>
              <Row label="Đang nắm" value={`${holding.quantity} cp @ ${holding.avg_cost}`} />
              <Row label="Giá trị mã này" value={`${fmtVnd(holding.market_value)}đ`} />
              <Row
                label="Lãi/lỗ mã này"
                value={signed(holding.pnl, holding.pnl_pct)}
                tone={toneOf(holding.pnl)}
              />
            </>
          ) : (
            <Row label="Đang nắm" value="—" />
          )}

          <div className="border-t border-neutral-800 pt-3">
            <Row
              label="Lãi/lỗ toàn danh mục"
              value={signed(portfolio.total_pnl, portfolio.total_pnl_pct)}
              tone={toneOf(portfolio.total_pnl)}
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="number"
              min={1}
              step={1}
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 font-mono text-sm text-neutral-100"
              aria-label="Số lượng cổ phiếu"
            />
            <span className="whitespace-nowrap text-xs text-neutral-500">cp</span>
          </div>

          {estPrice !== null && qtyNum > 0 && (
            <div className="text-xs text-neutral-500">
              Ước tính: {fmtVnd(qtyNum * estPrice * PRICE_UNIT_VND)}đ (giá {estPrice})
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={() => submit("buy")}
              disabled={busy}
              className="flex-1 rounded-md border border-emerald-500 bg-emerald-500/10 px-4 py-2 font-mono text-sm font-semibold text-emerald-400 disabled:opacity-50"
            >
              MUA
            </button>
            <button
              onClick={() => submit("sell")}
              disabled={busy || !holding}
              className="flex-1 rounded-md border border-red-500 bg-red-500/10 px-4 py-2 font-mono text-sm font-semibold text-red-400 disabled:opacity-40"
            >
              BÁN
            </button>
          </div>

          {notice && <div className="text-xs text-emerald-400">{notice}</div>}
          {errorMsg && <div className="text-xs text-red-400">{errorMsg}</div>}

          <Link href="/portfolio" className="text-xs text-neutral-500 underline hover:text-neutral-300">
            Xem danh mục
          </Link>
        </div>
      )}
    </div>
  );
}
