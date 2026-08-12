"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import type { PortfolioOut, PortfolioResult, TransactionOut } from "@/lib/types";

type Status = "loading" | "anonymous" | "no-portfolio" | "ready" | "error";

const PRESETS = [
  { label: "100 triệu", value: 100_000_000 },
  { label: "500 triệu", value: 500_000_000 },
  { label: "1 tỷ", value: 1_000_000_000 },
];

function fmtVnd(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("vi-VN", { maximumFractionDigits: 0 });
}

function signClass(n: number | null): string {
  if (n === null || n === undefined) return "text-neutral-200";
  return n >= 0 ? "text-emerald-400" : "text-red-400";
}

export default function PortfolioPage() {
  const [status, setStatus] = useState<Status>("loading");
  const [portfolio, setPortfolio] = useState<PortfolioOut | null>(null);
  const [transactions, setTransactions] = useState<TransactionOut[]>([]);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [capitalInput, setCapitalInput] = useState("100000000");
  const [errorMsg, setErrorMsg] = useState("");
  const [busy, setBusy] = useState(false);

  function apply(result: PortfolioResult) {
    if (result.available === false) {
      setPortfolio(null);
      setStatus("no-portfolio");
    } else {
      setPortfolio(result as PortfolioOut);
      setStatus("ready");
    }
  }

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
          if (cancelled) return;
          apply(result);
          if (result.available !== false) {
            const tx = await api.getTransactions(session.access_token);
            if (!cancelled) setTransactions(tx);
          }
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

  async function refreshTransactions(token: string) {
    try {
      setTransactions(await api.getTransactions(token));
    } catch {
      // Lịch sử là phụ — không chặn trang nếu lỗi.
    }
  }

  async function createPortfolio() {
    if (!accessToken) return;
    const capital = Number(capitalInput);
    if (!Number.isFinite(capital) || capital <= 0) {
      setErrorMsg("Vốn ban đầu phải là số dương.");
      return;
    }
    setBusy(true);
    setErrorMsg("");
    try {
      setPortfolio(await api.createPortfolio(capital, accessToken));
      setStatus("ready");
      await refreshTransactions(accessToken);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Lỗi không xác định");
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    if (!accessToken) return;
    if (!confirm("Xoá toàn bộ vị thế và lịch sử giao dịch, đưa tiền về vốn ban đầu?")) return;
    setBusy(true);
    setErrorMsg("");
    try {
      setPortfolio(await api.resetPortfolio(accessToken));
      await refreshTransactions(accessToken);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Lỗi không xác định");
    } finally {
      setBusy(false);
    }
  }

  if (status === "loading") return <div className="text-neutral-400">Đang tải…</div>;

  if (status === "anonymous") {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-8 text-center">
        <p className="mb-4 text-neutral-300">Đăng nhập để dùng danh mục đầu tư ảo.</p>
        <Link
          href="/login"
          className="rounded-md border border-emerald-500 bg-emerald-500/10 px-5 py-2 font-mono text-sm font-semibold text-emerald-400"
        >
          Đăng nhập
        </Link>
      </div>
    );
  }

  if (status === "error") return <div className="text-red-400">Lỗi: {errorMsg}</div>;

  if (status === "no-portfolio") {
    return (
      <div className="mx-auto max-w-md rounded-lg border border-neutral-800 bg-neutral-900 p-6">
        <h1 className="mb-2 font-mono text-xl font-bold">Tạo danh mục ảo</h1>
        <p className="mb-5 text-sm text-neutral-400">
          Đặt số vốn ảo ban đầu để bắt đầu mua bán theo giá thị trường thật. Có thể làm lại từ đầu bất
          cứ lúc nào.
        </p>

        <div className="mb-3 flex gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.value}
              onClick={() => setCapitalInput(String(p.value))}
              className={`flex-1 rounded-md border px-3 py-2 text-xs ${
                capitalInput === String(p.value)
                  ? "border-emerald-500 bg-emerald-500/10 text-emerald-400"
                  : "border-neutral-700 text-neutral-400 hover:text-neutral-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <label className="mb-1 block text-xs text-neutral-500" htmlFor="capital">
          Vốn ban đầu (VND)
        </label>
        <input
          id="capital"
          type="number"
          min={1}
          value={capitalInput}
          onChange={(e) => setCapitalInput(e.target.value)}
          className="mb-1 w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 font-mono text-sm text-neutral-100"
        />
        <div className="mb-4 text-xs text-neutral-500">
          = {fmtVnd(Number(capitalInput) || 0)}đ
        </div>

        <button
          onClick={createPortfolio}
          disabled={busy}
          className="w-full rounded-md border border-emerald-500 bg-emerald-500/10 px-4 py-2 font-mono text-sm font-semibold text-emerald-400 disabled:opacity-50"
        >
          Tạo danh mục
        </button>
        {errorMsg && <div className="mt-3 text-xs text-red-400">{errorMsg}</div>}
      </div>
    );
  }

  if (!portfolio) return null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-mono text-2xl font-bold">Danh mục ảo</h1>
        <button
          onClick={reset}
          disabled={busy}
          className="rounded-md border border-neutral-700 px-4 py-2 text-xs text-neutral-400 hover:text-red-400 disabled:opacity-50"
        >
          Làm lại từ đầu
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Tổng tài sản", value: `${fmtVnd(portfolio.total_value)}đ`, cls: "text-neutral-100" },
          { label: "Tiền mặt", value: `${fmtVnd(portfolio.cash_balance)}đ`, cls: "text-neutral-100" },
          {
            label: "Giá trị cổ phiếu",
            value: `${fmtVnd(portfolio.holdings_value)}đ`,
            cls: "text-neutral-100",
          },
          {
            label: "Lãi/lỗ",
            value: `${portfolio.total_pnl >= 0 ? "+" : ""}${fmtVnd(portfolio.total_pnl)}đ (${
              portfolio.total_pnl >= 0 ? "+" : ""
            }${portfolio.total_pnl_pct.toFixed(2)}%)`,
            cls: signClass(portfolio.total_pnl),
          },
        ].map((c) => (
          <div key={c.label} className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
            <div className="mb-1 text-xs uppercase tracking-wide text-neutral-500">{c.label}</div>
            <div className={`font-mono text-lg font-bold ${c.cls}`}>{c.value}</div>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
        <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Cổ phiếu đang nắm
        </div>
        {portfolio.positions.length === 0 ? (
          <p className="text-sm text-neutral-400">
            Chưa nắm mã nào. Vào{" "}
            <Link href="/" className="text-emerald-400 underline">
              trang mã
            </Link>{" "}
            rồi bấm MUA ở ô &ldquo;Giao dịch ảo&rdquo;.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-neutral-800 text-left text-xs uppercase text-neutral-500">
                  <th className="pb-2">Mã</th>
                  <th className="pb-2 text-right">SL</th>
                  <th className="pb-2 text-right">Giá vốn</th>
                  <th className="pb-2 text-right">Giá hiện tại</th>
                  <th className="pb-2 text-right">Giá trị</th>
                  <th className="pb-2 text-right">Lãi/lỗ</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((p) => (
                  <tr key={p.stock_id} className="border-b border-neutral-800/60">
                    <td className="py-2">
                      <Link href={`/stock/${p.symbol}`} className="font-mono font-bold text-neutral-100">
                        {p.symbol}
                      </Link>
                    </td>
                    <td className="py-2 text-right font-mono">{p.quantity}</td>
                    <td className="py-2 text-right font-mono">{p.avg_cost}</td>
                    <td className="py-2 text-right font-mono">
                      {p.current_price ?? "—"}
                      {p.price_source === "close" && (
                        <span className="ml-1 text-[10px] text-neutral-600">ĐC</span>
                      )}
                    </td>
                    <td className="py-2 text-right font-mono">{fmtVnd(p.market_value)}đ</td>
                    <td className={`py-2 text-right font-mono ${signClass(p.pnl)}`}>
                      {p.pnl === null
                        ? "—"
                        : `${p.pnl >= 0 ? "+" : ""}${fmtVnd(p.pnl)}đ (${
                            p.pnl_pct !== null ? `${p.pnl_pct >= 0 ? "+" : ""}${p.pnl_pct.toFixed(2)}%` : "—"
                          })`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-2 text-[10px] text-neutral-600">
              ĐC = khớp theo giá đóng cửa gần nhất (ngoài giờ giao dịch hoặc chưa có giá trong phiên).
            </div>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
        <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Lịch sử giao dịch
        </div>
        {transactions.length === 0 ? (
          <p className="text-sm text-neutral-400">Chưa có giao dịch nào.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-neutral-800 text-left text-xs uppercase text-neutral-500">
                  <th className="pb-2">Thời gian</th>
                  <th className="pb-2">Mã</th>
                  <th className="pb-2">Lệnh</th>
                  <th className="pb-2 text-right">SL</th>
                  <th className="pb-2 text-right">Giá</th>
                  <th className="pb-2 text-right">Thành tiền</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.id} className="border-b border-neutral-800/60">
                    <td className="py-2 text-xs text-neutral-400">
                      {new Date(t.executed_at).toLocaleString("vi-VN")}
                    </td>
                    <td className="py-2 font-mono font-bold">{t.symbol}</td>
                    <td className={`py-2 font-mono text-xs font-semibold ${t.side === "buy" ? "text-emerald-400" : "text-red-400"}`}>
                      {t.side === "buy" ? "MUA" : "BÁN"}
                    </td>
                    <td className="py-2 text-right font-mono">{t.quantity}</td>
                    <td className="py-2 text-right font-mono">{t.price}</td>
                    <td className="py-2 text-right font-mono">{fmtVnd(t.amount)}đ</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {errorMsg && <div className="text-sm text-red-400">{errorMsg}</div>}
    </div>
  );
}
