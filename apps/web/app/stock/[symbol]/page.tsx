"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AIPredictionCard from "@/components/AIPredictionCard";
import CandlestickChart from "@/components/CandlestickChart";
import FundamentalsCard from "@/components/FundamentalsCard";
import { MacdPanel, RsiPanel } from "@/components/IndicatorPanel";
import ScoreCard from "@/components/ScoreCard";
import TradePanel from "@/components/TradePanel";
import WatchlistButton from "@/components/WatchlistButton";
import { api } from "@/lib/api";
import { useAutoRefresh, useMarketSession } from "@/lib/useMarketSession";
import { vnTimeWithSeconds } from "@/lib/vnTime";
import type {
  AnalysisResponse,
  FundamentalsResult,
  PredictionResult,
  PricePoint,
  ScoreResult,
} from "@/lib/types";

type Status = "loading" | "ready" | "error";

// Tải history + analysis cho 1 mã; nếu backend báo chưa có dữ liệu (mã
// chưa từng sync), tự gọi POST /sync một lần rồi thử lại. Cùng pattern
// với legacy/frontend/src/StockDashboard.jsx::loadStockData().
async function loadStockData(symbol: string): Promise<{ history: PricePoint[]; analysis: AnalysisResponse }> {
  const fetchBoth = () => Promise.all([api.getHistory(symbol), api.getAnalysis(symbol)]);
  try {
    const [history, analysis] = await fetchBoth();
    return { history, analysis };
  } catch {
    await api.syncStock(symbol);
    const [history, analysis] = await fetchBoth();
    return { history, analysis };
  }
}

function fmt(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export default function StockPage({ params }: { params: { symbol: string } }) {
  const symbol = params.symbol.toUpperCase();

  const [history, setHistory] = useState<PricePoint[] | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [score, setScore] = useState<ScoreResult>({
    symbol, available: false, message: "Đang tải…",
  });
  const [prediction, setPrediction] = useState<PredictionResult>({
    symbol, available: false, message: "Đang tải…",
  });
  const [fundamentals, setFundamentals] = useState<FundamentalsResult | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [retryKey, setRetryKey] = useState(0);
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null);
  const session = useMarketSession();

  // Trong phiên thì giá đổi liên tục -> tải lại số liệu. Ngoài giờ thì
  // không, vì dữ liệu đứng yên (xem lib/useMarketSession.ts).
  useAutoRefresh(session?.is_open, () => {
    Promise.all([api.getHistory(symbol), api.getAnalysis(symbol)])
      .then(([h, a]) => {
        setHistory(h);
        setAnalysis(a);
        setRefreshedAt(new Date());
      })
      .catch(() => {
        // Giữ nguyên dữ liệu cũ nếu một nhịp làm mới lỗi — tốt hơn là
        // đá người dùng về màn hình báo lỗi khi trang vẫn đang dùng được.
      });
  });

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    setErrorMsg("");
    loadStockData(symbol)
      .then(({ history, analysis }) => {
        if (cancelled) return;
        setHistory(history);
        setAnalysis(analysis);
        setStatus("ready");
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setErrorMsg(e.message || "Lỗi không xác định");
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, retryKey]);

  useEffect(() => {
    let cancelled = false;
    // Điểm chấm + dự đoán AI là dữ liệu bổ sung — không chặn trang
    // chính nếu lỗi/chưa có.
    api
      .getScore(symbol)
      .then((s) => {
        if (!cancelled) setScore(s);
      })
      .catch(() => {
        if (!cancelled) setScore({ symbol, available: false, message: "Không tải được điểm chấm." });
      });
    api
      .getPrediction(symbol)
      .then((p) => {
        if (!cancelled) setPrediction(p);
      })
      .catch(() => {
        if (!cancelled) setPrediction({ symbol, available: false, message: "Không tải được dự đoán." });
      });
    api
      .getFundamentals(symbol)
      .then((f) => {
        if (!cancelled) setFundamentals(f);
      })
      .catch(() => {
        if (!cancelled)
          setFundamentals({ symbol, available: false, message: "Không tải được thông tin doanh nghiệp." });
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, retryKey]);

  if (status === "loading") {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-10 text-center">
        <div className="text-neutral-300">Đang tải dữ liệu {symbol} từ backend…</div>
        <div className="mt-2 text-xs text-neutral-500">
          Nếu là lần đầu xem mã này, hệ thống sẽ tự đồng bộ dữ liệu từ HOSE — có thể mất một chút thời gian.
        </div>
      </div>
    );
  }

  if (status === "error" || !history || !analysis) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-10 text-center">
        <div className="mb-3 text-red-400">Lỗi tải dữ liệu: {errorMsg}</div>
        <button
          onClick={() => setRetryKey((k) => k + 1)}
          className="rounded-md border border-emerald-500 bg-emerald-500/10 px-5 py-2 font-mono text-sm font-semibold text-emerald-400"
        >
          Thử lại
        </button>
      </div>
    );
  }

  const trendUp = analysis.trend === "bullish";

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-mono text-2xl font-bold">{symbol}</h1>
        </div>
        <WatchlistButton symbol={symbol} />
      </div>

      <div className="flex flex-wrap items-baseline gap-4 border-b border-neutral-800 pb-4">
        <span className={`font-mono text-4xl font-bold ${analysis.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
          {fmt(analysis.current_price)}
        </span>
        <span className={`font-mono text-base font-semibold ${analysis.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
          {analysis.change_pct >= 0 ? "▲" : "▼"} {fmt(Math.abs(analysis.change_pct))}%
        </span>
        {analysis.price_source === "close" && (
          <span className="text-[11px] text-neutral-600">giá đóng cửa gần nhất</span>
        )}
        {refreshedAt && (
          <span className="text-[11px] text-neutral-600">
            cập nhật {vnTimeWithSeconds(refreshedAt)}
          </span>
        )}
        <span
          className={`ml-auto rounded-full px-3 py-1 text-xs font-semibold ${
            trendUp ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
          }`}
        >
          {trendUp ? "Xu hướng tăng (MA20 > MA50)" : "Xu hướng giảm (MA20 < MA50)"}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_300px]">
        <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Giá & Moving Average
          </div>
          <CandlestickChart data={history} />
        </div>
        <div className="flex flex-col gap-5">
          <TradePanel symbol={symbol} referencePrice={analysis.current_price} />
          <AIPredictionCard prediction={prediction} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">RSI (14)</span>
            <Link href="/huong-dan#chi-bao" className="text-[11px] text-neutral-600 hover:text-emerald-400" title="RSI nghĩa là gì?">
              ?
            </Link>
          </div>
          <RsiPanel data={history} />
          <div className="mt-2 flex justify-between text-xs">
            <span className="text-neutral-500">Hiện tại</span>
            <span className="font-mono font-semibold text-neutral-200">
              {fmt(analysis.rsi14)} ·{" "}
              {analysis.rsi_status === "overbought"
                ? "Quá mua"
                : analysis.rsi_status === "oversold"
                  ? "Quá bán"
                  : "Trung tính"}
            </span>
          </div>
        </div>

        <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">MACD</span>
            <Link href="/huong-dan#chi-bao" className="text-[11px] text-neutral-600 hover:text-emerald-400" title="MACD nghĩa là gì?">
              ?
            </Link>
          </div>
          <MacdPanel data={history} />
          <div className="mt-2 flex justify-between text-xs">
            <span className="text-neutral-500">Tín hiệu</span>
            <span
              className={`font-mono font-semibold ${
                analysis.macd_signal_status === "buy" ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {analysis.macd_signal_status === "buy" ? "MUA" : "BÁN"}
            </span>
          </div>
        </div>

        <ScoreCard score={score} />
      </div>

      <FundamentalsCard data={fundamentals} />
    </div>
  );
}
