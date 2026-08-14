"use client";

import { ColorType, IChartApi, ISeriesApi, LineStyle, createChart } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import type { PricePoint } from "@/lib/types";

const COLORS = {
  bg: "#0A0E12",
  grid: "#1C242E",
  text: "#7C8794",
  up: "#00C076",
  down: "#F6465D",
  ma20: "#F0B90B",
  ma50: "#C960E8",
  bb: "#4A9DFF",
};

interface Props {
  data: PricePoint[];
}

// lightweight-charts@4.x — chart.addCandlestickSeries()/addLineSeries()/
// addHistogramSeries(). Đây là API v4, ĐÃ ĐỔI ở v5 (chart.addSeries(...)).
// Version pin cứng trong package.json — nâng cấp phải sửa component này.
export default function CandlestickChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const ma20SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const ma50SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bbUpperSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bbLowerSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  // Mặc định tắt: 2 đường MA + 2 dải Bollinger cùng lúc làm biểu đồ rối,
  // và dải Bollinger chỉ hữu ích khi đang xem biến động/vùng quá mua-bán.
  const [showBollinger, setShowBollinger] = useState(false);

  // Tạo chart đúng 1 lần. React 18 Strict Mode (dev) gọi effect 2 lần
  // (mount -> cleanup -> mount) — cleanup ở đây gọi chart.remove() để
  // không rò rỉ canvas/context giữa 2 lần mount.
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: COLORS.bg }, textColor: COLORS.text },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      autoSize: false,
      timeScale: { borderColor: COLORS.grid },
      rightPriceScale: { borderColor: COLORS.grid },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: COLORS.up, downColor: COLORS.down,
      borderUpColor: COLORS.up, borderDownColor: COLORS.down,
      wickUpColor: COLORS.up, wickDownColor: COLORS.down,
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

    const ma20Series = chart.addLineSeries({ color: COLORS.ma20, lineWidth: 1, title: "MA20" });
    const ma50Series = chart.addLineSeries({ color: COLORS.ma50, lineWidth: 1, title: "MA50" });

    // Chỉ vẽ dải TRÊN và DƯỚI: dải giữa của Bollinger chính là MA20
    // (cùng công thức, xem apps/api/app/processing/indicators.py) nên vẽ
    // thêm sẽ là một đường trùng khít lên MA20.
    const bbOptions = { color: COLORS.bb, lineWidth: 1 as const, lineStyle: LineStyle.Dashed };
    const bbUpperSeries = chart.addLineSeries({ ...bbOptions, title: "BB trên" });
    const bbLowerSeries = chart.addLineSeries({ ...bbOptions, title: "BB dưới" });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    ma20SeriesRef.current = ma20Series;
    ma50SeriesRef.current = ma50Series;
    bbUpperSeriesRef.current = bbUpperSeries;
    bbLowerSeriesRef.current = bbLowerSeries;

    // Tự đo & resize bằng ResizeObserver thay vì autoSize — autoSize
    // xung đột với việc tự gọi applyOptions({width,height}) và kém tin
    // cậy hơn trong layout flex/grid.
    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      chart.applyOptions({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  // Cập nhật dữ liệu khi đổi mã — dùng setData() trên series đã có, KHÔNG
  // tạo lại chart (mượt hơn, tránh churn khi Strict Mode double-invoke).
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return;
    if (data.length === 0) return;

    candleSeriesRef.current.setData(
      data.map((d) => ({ time: d.date, open: d.open, high: d.high, low: d.low, close: d.close }))
    );
    volumeSeriesRef.current.setData(
      data.map((d) => ({
        time: d.date,
        value: d.volume,
        color: d.close >= d.open ? "rgba(0,192,118,0.5)" : "rgba(246,70,93,0.5)",
      }))
    );
    ma20SeriesRef.current?.setData(
      data.filter((d) => d.ma20 !== null).map((d) => ({ time: d.date, value: d.ma20 as number }))
    );
    ma50SeriesRef.current?.setData(
      data.filter((d) => d.ma50 !== null).map((d) => ({ time: d.date, value: d.ma50 as number }))
    );
    bbUpperSeriesRef.current?.setData(
      data.filter((d) => d.bb_upper !== null).map((d) => ({ time: d.date, value: d.bb_upper as number }))
    );
    bbLowerSeriesRef.current?.setData(
      data.filter((d) => d.bb_lower !== null).map((d) => ({ time: d.date, value: d.bb_lower as number }))
    );
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  // Ẩn/hiện bằng `visible` thay vì xoá & tạo lại series: giữ nguyên dữ
  // liệu đã setData, bật lại không phải nạp lại.
  useEffect(() => {
    bbUpperSeriesRef.current?.applyOptions({ visible: showBollinger });
    bbLowerSeriesRef.current?.applyOptions({ visible: showBollinger });
  }, [showBollinger]);

  const live = data.length > 0 && data[data.length - 1].is_intraday === true;

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-2">
        {live ? (
          <span
            className="flex items-center gap-1.5 text-[11px] text-amber-400"
            title="Cây nến cuối là phiên đang diễn ra, giá cao/thấp/đóng cửa còn thay đổi tới khi hết phiên."
          >
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
            Nến cuối: phiên đang diễn ra
          </span>
        ) : (
          <span />
        )}
        <button
          onClick={() => setShowBollinger((v) => !v)}
          aria-pressed={showBollinger}
          className={`rounded-md border px-2 py-1 text-[11px] transition-colors ${
            showBollinger
              ? "border-sky-500 bg-sky-500/10 text-sky-400"
              : "border-neutral-700 text-neutral-500 hover:text-neutral-300"
          }`}
        >
          Bollinger Bands
        </button>
      </div>
      {/* Container cần height cố định TRƯỚC khi chart mount (client
          effect), tránh layout shift lúc trang vừa tải. */}
      <div ref={containerRef} style={{ width: "100%", height: 400 }} />
      {showBollinger && (
        <div className="mt-2 text-[10px] text-neutral-600">
          Dải giữa của Bollinger chính là MA20 (đường vàng) nên không vẽ lặp lại.
        </div>
      )}
    </div>
  );
}
