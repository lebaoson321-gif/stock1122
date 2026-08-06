import React, { useState, useEffect } from "react";
import {
  ResponsiveContainer, ComposedChart, Line, Area, Bar, Cell, XAxis, YAxis,
  Tooltip, CartesianGrid, ReferenceLine,
} from "recharts";
import { api } from "./api";

// ----------------------------------------------------------------------
// Bảng màu lấy theo đúng quy ước bảng điện giao dịch HOSE:
// xanh = tăng, đỏ = giảm, vàng = tham chiếu, tím = trần, lam = sàn
// ----------------------------------------------------------------------
const COLORS = {
  bg: "#0A0E12",
  surface: "#12181F",
  surfaceRaised: "#161D25",
  border: "#232B35",
  textPrimary: "#E9EDF1",
  textMuted: "#7C8794",
  up: "#00C076",
  down: "#F6465D",
  ref: "#F0B90B",
  ceiling: "#C960E8",
  floor: "#34D2F0",
};

// ----------------------------------------------------------------------
// Dữ liệu giá + chỉ báo lấy từ backend FastAPI thật (xem src/api.js).
// ----------------------------------------------------------------------

// Chuyển PricePoint (snake_case, từ backend) sang field name mà chart
// đang dùng (camelCase cho macd_signal/macd_hist, cộng dateLabel để hiển thị).
function mapHistory(points) {
  return points.map((p) => {
    const d = new Date(p.date);
    return {
      date: d,
      dateLabel: d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" }),
      open: p.open, high: p.high, low: p.low, close: p.close, volume: p.volume,
      ma20: p.ma20, ma50: p.ma50, ma200: p.ma200,
      rsi: p.rsi, macd: p.macd, macdSignal: p.macd_signal, macdHist: p.macd_hist,
    };
  });
}

// Lấy history + analysis cho một mã; nếu backend báo chưa có dữ liệu
// (mã chưa từng sync), tự gọi POST /sync một lần rồi thử lại.
async function loadStockData(symbol) {
  const fetchBoth = () =>
    Promise.all([api.getHistory(symbol), api.getAnalysis(symbol)]);
  try {
    const [history, analysis] = await fetchBoth();
    return { history, analysis };
  } catch (e) {
    await api.syncStock(symbol);
    const [history, analysis] = await fetchBoth();
    return { history, analysis };
  }
}

const WATCHLIST = [
  { symbol: "FPT", name: "FPT Corporation", sector: "Công nghệ" },
  { symbol: "VNM", name: "Vinamilk", sector: "Hàng tiêu dùng" },
  { symbol: "HPG", name: "Hòa Phát", sector: "Vật liệu" },
  { symbol: "VCB", name: "Vietcombank", sector: "Ngân hàng" },
];

const FUNDAMENTALS = {
  FPT: { profitGrowth: 8, roe: 9, debt: 7, pe: 18.4, eps: 5230 },
  VNM: { profitGrowth: 6, roe: 7, debt: 9, pe: 15.1, eps: 4120 },
  HPG: { profitGrowth: 5, roe: 6, debt: 5, pe: 11.8, eps: 2010 },
  VCB: { profitGrowth: 7, roe: 8, debt: 8, pe: 13.6, eps: 4890 },
};

const NEWS = {
  FPT: { headline: "FPT ký hợp đồng chuyển đổi số trị giá lớn với đối tác Nhật Bản", sentiment: 0.85 },
  VNM: { headline: "Vinamilk mở rộng thị phần sữa hạt tại thị trường Đông Nam Á", sentiment: 0.42 },
  HPG: { headline: "Giá thép thế giới điều chỉnh giảm, áp lực lên biên lợi nhuận quý tới", sentiment: -0.31 },
  VCB: { headline: "Vietcombank duy trì tỷ lệ nợ xấu thấp nhất hệ thống ngân hàng", sentiment: 0.6 },
};

function fmt(n, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function fmtVol(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "tr";
  if (n >= 1_000) return (n / 1_000).toFixed(0) + "k";
  return String(n);
}

function TickerTape() {
  const [quotes, setQuotes] = useState({});

  useEffect(() => {
    let cancelled = false;
    WATCHLIST.forEach(async (s) => {
      try {
        const { analysis } = await loadStockData(s.symbol);
        if (!cancelled) {
          setQuotes((q) => ({ ...q, [s.symbol]: { price: analysis.close, chg: analysis.change_pct } }));
        }
      } catch {
        if (!cancelled) setQuotes((q) => ({ ...q, [s.symbol]: null }));
      }
    });
    return () => { cancelled = true; };
  }, []);

  const items = WATCHLIST.map((s) => ({ ...s, quote: quotes[s.symbol] }));
  const loop = [...items, ...items, ...items];
  return (
    <div style={{
      overflow: "hidden", borderBottom: `1px solid ${COLORS.border}`,
      background: COLORS.surface, padding: "10px 0",
    }}>
      <style>{`
        @keyframes tickerScroll { from { transform: translateX(0); } to { transform: translateX(-33.333%); } }
        .ticker-track { display: flex; width: max-content; animation: tickerScroll 28s linear infinite; }
      `}</style>
      <div className="ticker-track">
        {loop.map((it, idx) => (
          <div key={idx} style={{
            display: "flex", alignItems: "baseline", gap: 8,
            padding: "0 24px", borderRight: `1px solid ${COLORS.border}`,
            fontFamily: "'JetBrains Mono', monospace", whiteSpace: "nowrap",
          }}>
            <span style={{ color: COLORS.textPrimary, fontWeight: 700, fontSize: 13 }}>{it.symbol}</span>
            {it.quote === undefined && (
              <span style={{ color: COLORS.textMuted, fontSize: 13 }}>đang tải…</span>
            )}
            {it.quote === null && (
              <span style={{ color: COLORS.textMuted, fontSize: 13 }}>—</span>
            )}
            {it.quote && (
              <>
                <span style={{ color: COLORS.textPrimary, fontSize: 13 }}>{fmt(it.quote.price)}</span>
                <span style={{ color: it.quote.chg >= 0 ? COLORS.up : COLORS.down, fontSize: 13 }}>
                  {it.quote.chg >= 0 ? "▲" : "▼"} {fmt(Math.abs(it.quote.chg))}%
                </span>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Card({ title, children, style }) {
  return (
    <div style={{
      background: COLORS.surface, border: `1px solid ${COLORS.border}`,
      borderRadius: 10, padding: "18px 20px", ...style,
    }}>
      {title && (
        <div style={{
          fontFamily: "'Space Grotesk', sans-serif", fontSize: 13, fontWeight: 600,
          letterSpacing: "0.03em", textTransform: "uppercase",
          color: COLORS.textMuted, marginBottom: 14,
        }}>{title}</div>
      )}
      {children}
    </div>
  );
}

function ScoreBar({ label, value, max = 10 }) {
  const pct = (value / max) * 100;
  const color = value >= 7 ? COLORS.up : value >= 5 ? COLORS.ref : COLORS.down;
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ fontSize: 13, color: COLORS.textMuted }}>{label}</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: COLORS.textPrimary }}>
          {value}/{max}
        </span>
      </div>
      <div style={{ height: 6, background: COLORS.border, borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
    </div>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{
      background: COLORS.surfaceRaised, border: `1px solid ${COLORS.border}`,
      borderRadius: 6, padding: "8px 12px", fontSize: 12,
      fontFamily: "'JetBrains Mono', monospace", color: COLORS.textPrimary,
    }}>
      <div style={{ color: COLORS.textMuted, marginBottom: 4 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {fmt(p.value)}
        </div>
      ))}
    </div>
  );
}

function WatchlistSwitcher({ symbol, onChange }) {
  return (
    <div style={{ display: "flex", gap: 6 }}>
      {WATCHLIST.map((s) => (
        <button
          key={s.symbol}
          onClick={() => onChange(s.symbol)}
          style={{
            fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 13,
            padding: "8px 16px", borderRadius: 8, cursor: "pointer",
            border: `1px solid ${s.symbol === symbol ? COLORS.up : COLORS.border}`,
            background: s.symbol === symbol ? "rgba(0,192,118,0.1)" : "transparent",
            color: s.symbol === symbol ? COLORS.up : COLORS.textMuted,
          }}
        >
          {s.symbol}
        </button>
      ))}
    </div>
  );
}

export default function StockDashboard() {
  const [symbol, setSymbol] = useState("FPT");
  const [history, setHistory] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [errorMsg, setErrorMsg] = useState("");
  const [retryKey, setRetryKey] = useState(0);

  const stock = WATCHLIST.find((s) => s.symbol === symbol);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    setErrorMsg("");
    loadStockData(symbol)
      .then(({ history, analysis }) => {
        if (cancelled) return;
        setHistory(mapHistory(history));
        setAnalysis(analysis);
        setStatus("ready");
      })
      .catch((e) => {
        if (cancelled) return;
        setErrorMsg(e.message || "Lỗi không xác định");
        setStatus("error");
      });
    return () => { cancelled = true; };
  }, [symbol, retryKey]);

  if (status !== "ready" || !analysis || !history) {
    return (
      <div style={{
        background: COLORS.bg, minHeight: "100%",
        fontFamily: "'Inter', sans-serif", color: COLORS.textPrimary,
      }}>
        <TickerTape />
        <div style={{ maxWidth: 1180, margin: "0 auto", padding: "28px 24px 48px" }}>
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 24 }}>
            <WatchlistSwitcher symbol={symbol} onChange={setSymbol} />
          </div>
          <Card>
            {status === "loading" && (
              <div style={{ textAlign: "center", padding: "48px 0", color: COLORS.textMuted }}>
                <div>Đang tải dữ liệu {symbol} từ backend…</div>
                <div style={{ fontSize: 12, marginTop: 8 }}>
                  Nếu là lần đầu xem mã này, hệ thống sẽ tự đồng bộ dữ liệu từ HOSE — có thể mất một chút thời gian.
                </div>
              </div>
            )}
            {status === "error" && (
              <div style={{ textAlign: "center", padding: "48px 0" }}>
                <div style={{ color: COLORS.down, marginBottom: 12 }}>Lỗi tải dữ liệu: {errorMsg}</div>
                <div style={{ fontSize: 12, color: COLORS.textMuted, marginBottom: 20 }}>
                  Kiểm tra backend đã chạy tại {api.API_BASE_URL} (xem README ở thư mục gốc dự án).
                </div>
                <button
                  onClick={() => setRetryKey((k) => k + 1)}
                  style={{
                    fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 13,
                    padding: "8px 20px", borderRadius: 8, cursor: "pointer",
                    border: `1px solid ${COLORS.up}`, background: "rgba(0,192,118,0.1)", color: COLORS.up,
                  }}
                >
                  Thử lại
                </button>
              </div>
            )}
          </Card>
        </div>
      </div>
    );
  }

  const chgPct = analysis.change_pct;
  const trendUp = analysis.trend === "bullish";
  const rsiValue = analysis.rsi;
  const rsiStatus = analysis.rsi_status === "overbought" ? "Quá mua" : analysis.rsi_status === "oversold" ? "Quá bán" : "Trung tính";
  const rsiColor = analysis.rsi_status === "overbought" ? COLORS.down : analysis.rsi_status === "oversold" ? COLORS.up : COLORS.ref;
  const macdBuy = analysis.macd_signal_status === "buy";
  const fund = FUNDAMENTALS[symbol];
  const fundTotal = ((fund.profitGrowth + fund.roe + fund.debt) / 3).toFixed(1);
  const news = NEWS[symbol];
  // AI prediction placeholder — mô phỏng xác suất dựa trên trend + RSI, sẽ thay bằng model thật ở Module 5
  const aiProb = Math.max(5, Math.min(95, Math.round(
    50 + (trendUp ? 12 : -12) + (macdBuy ? 8 : -8) + (50 - (rsiValue ?? 50)) * 0.2
  )));

  const chartData = history.slice(-90);

  return (
    <div style={{
      background: COLORS.bg, minHeight: "100%",
      fontFamily: "'Inter', sans-serif", color: COLORS.textPrimary,
    }}>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet" />

      <TickerTape />

      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "28px 24px 48px" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24, flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: COLORS.textMuted, marginBottom: 6, letterSpacing: "0.05em" }}>
              STOCK INTELLIGENCE — HOSE
            </div>
            <h1 style={{
              fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700,
              fontSize: 30, margin: 0, letterSpacing: "-0.01em",
            }}>
              {stock.name}
            </h1>
            <div style={{ color: COLORS.textMuted, fontSize: 13, marginTop: 4 }}>{stock.sector}</div>
          </div>

          <WatchlistSwitcher symbol={symbol} onChange={setSymbol} />
        </div>

        {/* Price row */}
        <div style={{
          display: "flex", alignItems: "baseline", gap: 16, marginBottom: 24,
          paddingBottom: 24, borderBottom: `1px solid ${COLORS.border}`, flexWrap: "wrap",
        }}>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 42,
            color: chgPct >= 0 ? COLORS.up : COLORS.down,
          }}>
            {fmt(analysis.close, 2)}
          </span>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: 16, fontWeight: 600,
            color: chgPct >= 0 ? COLORS.up : COLORS.down,
          }}>
            {chgPct >= 0 ? "▲" : "▼"} {fmt(Math.abs(chgPct))}%
          </span>
          <span style={{
            marginLeft: "auto", fontSize: 13, fontWeight: 600, padding: "6px 14px",
            borderRadius: 20, background: trendUp ? "rgba(0,192,118,0.12)" : "rgba(246,70,93,0.12)",
            color: trendUp ? COLORS.up : COLORS.down,
          }}>
            {trendUp ? "Xu hướng tăng (MA20 > MA50)" : "Xu hướng giảm (MA20 < MA50)"}
          </span>
        </div>

        {/* Grid: chart + side cards */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 20, marginBottom: 20 }}>
          <Card title="Giá & Moving Average">
            <ResponsiveContainer width="100%" height={260}>
              <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
                <CartesianGrid stroke={COLORS.border} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="dateLabel" tick={{ fill: COLORS.textMuted, fontSize: 11 }} interval={14} axisLine={{ stroke: COLORS.border }} tickLine={false} />
                <YAxis domain={["auto", "auto"]} tick={{ fill: COLORS.textMuted, fontSize: 11 }} axisLine={false} tickLine={false} width={44} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="close" name="Giá" stroke={COLORS.floor} fill={COLORS.floor} fillOpacity={0.08} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="ma20" name="MA20" stroke={COLORS.ref} strokeWidth={1.4} dot={false} />
                <Line type="monotone" dataKey="ma50" name="MA50" stroke={COLORS.ceiling} strokeWidth={1.4} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>

            <div style={{ height: 90, marginTop: 4 }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                  <XAxis dataKey="dateLabel" hide />
                  <YAxis tick={{ fill: COLORS.textMuted, fontSize: 10 }} axisLine={false} tickLine={false} width={44} tickFormatter={fmtVol} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="volume" name="KL" radius={[2, 2, 0, 0]}>
                    {chartData.map((d, i) => (
                      <Cell key={i} fill={d.close >= d.open ? COLORS.up : COLORS.down} />
                    ))}
                  </Bar>
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card title="AI Prediction">
            <div style={{ textAlign: "center", padding: "8px 0 16px" }}>
              <div style={{
                fontFamily: "'JetBrains Mono', monospace", fontSize: 38, fontWeight: 700,
                color: aiProb >= 50 ? COLORS.up : COLORS.down,
              }}>
                {aiProb}%
              </div>
              <div style={{ fontSize: 12, color: COLORS.textMuted, marginTop: 4 }}>
                Xác suất tăng giá phiên tới
              </div>
            </div>
            <div style={{ height: 6, background: COLORS.border, borderRadius: 3, overflow: "hidden", marginBottom: 8 }}>
              <div style={{ width: `${aiProb}%`, height: "100%", background: aiProb >= 50 ? COLORS.up : COLORS.down }} />
            </div>
            <div style={{ fontSize: 11, color: COLORS.textMuted, lineHeight: 1.5 }}>
              Placeholder — sẽ thay bằng model Random Forest / LSTM khi triển khai Module 5.
            </div>

            <div style={{ borderTop: `1px solid ${COLORS.border}`, marginTop: 16, paddingTop: 16 }}>
              <div style={{ fontSize: 13, color: COLORS.textMuted, marginBottom: 8 }}>Tâm lý thị trường</div>
              <div style={{ fontSize: 13, lineHeight: 1.5, marginBottom: 8 }}>{news.headline}</div>
              <span style={{
                fontSize: 12, fontWeight: 600, padding: "3px 10px", borderRadius: 20,
                background: news.sentiment >= 0 ? "rgba(0,192,118,0.12)" : "rgba(246,70,93,0.12)",
                color: news.sentiment >= 0 ? COLORS.up : COLORS.down,
              }}>
                {news.sentiment >= 0 ? "Tích cực" : "Tiêu cực"} · {fmt(news.sentiment, 2)}
              </span>
            </div>
          </Card>
        </div>

        {/* Grid: RSI, MACD, Fundamentals */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 260px", gap: 20 }}>
          <Card title="RSI (14)">
            <ResponsiveContainer width="100%" height={140}>
              <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
                <XAxis dataKey="dateLabel" hide />
                <YAxis domain={[0, 100]} tick={{ fill: COLORS.textMuted, fontSize: 10 }} axisLine={false} tickLine={false} width={30} />
                <ReferenceLine y={70} stroke={COLORS.down} strokeDasharray="3 3" strokeOpacity={0.5} />
                <ReferenceLine y={30} stroke={COLORS.up} strokeDasharray="3 3" strokeOpacity={0.5} />
                <Tooltip content={<CustomTooltip />} />
                <Line type="monotone" dataKey="rsi" name="RSI" stroke={COLORS.ceiling} strokeWidth={1.6} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
              <span style={{ fontSize: 12, color: COLORS.textMuted }}>Hiện tại</span>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: rsiColor, fontWeight: 700 }}>
                {fmt(rsiValue)} · {rsiStatus}
              </span>
            </div>
          </Card>

          <Card title="MACD">
            <ResponsiveContainer width="100%" height={140}>
              <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
                <XAxis dataKey="dateLabel" hide />
                <YAxis tick={{ fill: COLORS.textMuted, fontSize: 10 }} axisLine={false} tickLine={false} width={36} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="macdHist" name="Hist" fill={COLORS.border} radius={[1, 1, 0, 0]} />
                <Line type="monotone" dataKey="macd" name="MACD" stroke={COLORS.floor} strokeWidth={1.4} dot={false} />
                <Line type="monotone" dataKey="macdSignal" name="Signal" stroke={COLORS.ref} strokeWidth={1.4} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
              <span style={{ fontSize: 12, color: COLORS.textMuted }}>Tín hiệu</span>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: macdBuy ? COLORS.up : COLORS.down, fontWeight: 700 }}>
                {macdBuy ? "MUA" : "BÁN"}
              </span>
            </div>
          </Card>

          <Card title="Điểm cơ bản">
            <ScoreBar label="Tăng trưởng lợi nhuận" value={fund.profitGrowth} />
            <ScoreBar label="ROE" value={fund.roe} />
            <ScoreBar label="An toàn nợ" value={fund.debt} />
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "baseline",
              borderTop: `1px solid ${COLORS.border}`, marginTop: 14, paddingTop: 14,
            }}>
              <span style={{ fontSize: 13, color: COLORS.textMuted }}>Tổng điểm</span>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 20, fontWeight: 700, color: COLORS.up }}>
                {fundTotal}/10
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 12, color: COLORS.textMuted }}>
              <span>P/E {fmt(fund.pe, 1)}</span>
              <span>EPS {fund.eps.toLocaleString("vi-VN")}</span>
            </div>
          </Card>
        </div>

        <div style={{ marginTop: 32, fontSize: 11, color: COLORS.textMuted, textAlign: "center" }}>
          Giá, khối lượng và chỉ báo kỹ thuật (MA/RSI/MACD) lấy từ backend FastAPI thật ({api.API_BASE_URL}).
          Điểm cơ bản, tin tức và AI Prediction vẫn là dữ liệu mô phỏng — backend chưa có các module này.
        </div>
      </div>
    </div>
  );
}
