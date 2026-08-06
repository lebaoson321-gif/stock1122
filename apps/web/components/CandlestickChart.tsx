"use client";

import { ColorType, IChartApi, ISeriesApi, createChart } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { PricePoint } from "@/lib/types";

const COLORS = {
  bg: "#0A0E12",
  grid: "#1C242E",
  text: "#7C8794",
  up: "#00C076",
  down: "#F6465D",
  ma20: "#F0B90B",
  ma50: "#C960E8",
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

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    ma20SeriesRef.current = ma20Series;
    ma50SeriesRef.current = ma50Series;

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
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  // Container cần height cố định TRƯỚC khi chart mount (client effect),
  // tránh layout shift lúc trang vừa tải.
  return <div ref={containerRef} style={{ width: "100%", height: 400 }} />;
}
