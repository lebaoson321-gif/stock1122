import React, { useState, useMemo } from "react";
import {
  ResponsiveContainer, ComposedChart, Line, Area, Bar, Cell, XAxis, YAxis,
  Tooltip, CartesianGrid, ReferenceLine,
} from "recharts";

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
// Sinh dữ liệu mô phỏng (thay cho gọi API thật /api/stocks/:symbol/history)
// Cấu trúc field GIỐNG HỆT response backend để khi nối API thật chỉ cần
// thay hàm loadData() bằng fetch(`${API_BASE_URL}/api/stocks/${symbol}/history`)
// ----------------------------------------------------------------------
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function genSeries(symbol, seed, base, n = 180) {
  const rnd = mulberry32(seed);
  const days = [];
  let price = base;
  const today = new Date();
  for (let i = n; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    if (d.getDay() === 0 || d.getDay() === 6) continue;
    const drift = (rnd() - 0.48) * 0.02;
    price = Math.max(price * (1 + drift), 1);
    const open = price * (1 + (rnd() - 0.5) * 0.006);
    const high = Math.max(open, price) * (1 + rnd() * 0.008);
    const low = Math.min(open, price) * (1 - rnd() * 0.008);
    const volume = Math.round(1_000_000 + rnd() * 6_000_000);
    days.push({ date: d, open, high, low, close: price, volume });
  }
  return computeIndicators(days);
}

function computeIndicators(days) {
  const closes = days.map((d) => d.close);
  const ma = (arr, i, period) => {
    if (i < period - 1) return null;
    let s = 0;
    for (let k = i - period + 1; k <= i; k++) s += arr[k];
    return s / period;
  };
  // RSI(14)
  const rsi = new Array(days.length).fill(null);
  let avgGain = 0, avgLoss = 0;
  for (let i = 1; i < days.length; i++) {
    const diff = closes[i] - closes[i - 1];
    const gain = Math.max(diff, 0);
    const loss = Math.max(-diff, 0);
    if (i <= 14) {
      avgGain += gain / 14;
      avgLoss += loss / 14;
      if (i === 14) rsi[i] = 100 - 100 / (1 + avgGain / (avgLoss || 1e-9));
    } else {
      avgGain = (avgGain * 13 + gain) / 14;
      avgLoss = (avgLoss * 13 + loss) / 14;
      rsi[i] = 100 - 100 / (1 + avgGain / (avgLoss || 1e-9));
    }
  }
  // MACD
  const ema = (period) => {
    const k = 2 / (period + 1);
    const out = new Array(closes.length).fill(null);
    out[0] = closes[0];
    for (let i = 1; i < closes.length; i++) out[i] = closes[i] * k + out[i - 1] * (1 - k);
    return out;
  };
  const ema12 = ema(12), ema26 = ema(26);
  const macd = closes.map((_, i) => ema12[i] - ema26[i]);
  const k9 = 2 / 10;
  const signal = new Array(macd.length).fill(null);
  signal[0] = macd[0];
  for (let i = 1; i < macd.length; i++) signal[i] = macd[i] * k9 + signal[i - 1] * (1 - k9);

  return days.map((d, i) => ({
    ...d,
    dateLabel: d.date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" }),
    ma20: ma(closes, i, 20),
    ma50: ma(closes, i, 50),
    rsi: i >= 14 ? rsi[i] : null,
    macd: macd[i],
    macdSignal: signal[i],
    macdHist: macd[i] - signal[i],
  }));
}

const WATCHLIST = [
  { symbol: "FPT", name: "FPT Corporation", sector: "Công nghệ", seed: 11, base: 128 },
  { symbol: "VNM", name: "Vinamilk", sector: "Hàng tiêu dùng", seed: 22, base: 68 },
  { symbol: "HPG", name: "Hòa Phát", sector: "Vật liệu", seed: 33, base: 27 },
  { symbol: "VCB", name: "Vietcombank", sector: "Ngân hàng", seed: 44, base: 91 },
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
  const items = useMemo(
    () => WATCHLIST.map((s) => {
      const data = genSeries(s.symbol, s.seed, s.base, 40);
      const last = data[data.length - 1];
      const prev = data[data.length - 2];
      const chg = ((last.close - prev.close) / prev.close) * 100;
      return { ...s, price: last.close, chg };
    }),
    []
  );
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
            <span style={{ color: COLORS.textPrimary, fontSize: 13 }}>{fmt(it.price)}</span>
            <span style={{ color: it.chg >= 0 ? COLORS.up : COLORS.down, fontSize: 13 }}>
              {it.chg >= 0 ? "▲" : "▼"} {fmt(Math.abs(it.chg))}%
            </span>
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

export default function StockDashboard() {
  const [symbol, setSymbol] = useState("FPT");
  const stock = WATCHLIST.find((s) => s.symbol === symbol);
  const data = useMemo(() => genSeries(stock.symbol, stock.seed, stock.base), [stock]);
  const latest = data[data.length - 1];
  const prev = data[data.length - 2];
  const chgPct = ((latest.close - prev.close) / prev.close) * 100;
  const trendUp = latest.ma20 !== null && latest.ma50 !== null && latest.ma20 > latest.ma50;
  const rsiStatus = latest.rsi > 70 ? "Quá mua" : latest.rsi < 30 ? "Quá bán" : "Trung tính";
  const rsiColor = latest.rsi > 70 ? COLORS.down : latest.rsi < 30 ? COLORS.up : COLORS.ref;
  const macdBuy = latest.macd > latest.macdSignal;
  const fund = FUNDAMENTALS[symbol];
  const fundTotal = ((fund.profitGrowth + fund.roe + fund.debt) / 3).toFixed(1);
  const news = NEWS[symbol];
  // AI prediction placeholder — mô phỏng xác suất dựa trên trend + RSI, sẽ thay bằng model thật ở Module 5
  const aiProb = Math.max(5, Math.min(95, Math.round(
    50 + (trendUp ? 12 : -12) + (macdBuy ? 8 : -8) + (50 - latest.rsi) * 0.2
  )));

  const chartData = data.slice(-90);

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

          <div style={{ display: "flex", gap: 6 }}>
            {WATCHLIST.map((s) => (
              <button
                key={s.symbol}
                onClick={() => setSymbol(s.symbol)}
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
            {fmt(latest.close, 2)}
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
                {fmt(latest.rsi)} · {rsiStatus}
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
          Dữ liệu mô phỏng để trình bày giao diện. Kết nối API thật qua backend FastAPI (xem README) để hiển thị dữ liệu HOSE thật.
        </div>
      </div>
    </div>
  );
}
