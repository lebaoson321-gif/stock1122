"use client";

import { ColorType, IChartApi, ISeriesApi, createChart } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { IndexBarOut } from "@/lib/types";

const COLORS = {
  bg: "#0A0E12",
  grid: "#1C242E",
  text: "#7C8794",
  line: "#4A9DFF",
};

interface Props {
  data: IndexBarOut[];
}

// Cùng lightweight-charts@4.x với CandlestickChart.tsx — xem component đó
// về lý do pin version. Chỉ vẽ 1 đường close, không cần candle/volume vì
// đây là chỉ số tổng hợp, không có giá mở/cao/thấp có ý nghĩa giao dịch.
export default function IndexLineChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: COLORS.bg }, textColor: COLORS.text },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      autoSize: false,
      timeScale: { borderColor: COLORS.grid },
      rightPriceScale: { borderColor: COLORS.grid },
    });

    const lineSeries = chart.addLineSeries({ color: COLORS.line, lineWidth: 2 });

    chartRef.current = chart;
    lineSeriesRef.current = lineSeries;

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

  useEffect(() => {
    if (!lineSeriesRef.current || data.length === 0) return;
    lineSeriesRef.current.setData(data.map((d) => ({ time: d.date, value: d.close })));
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} style={{ width: "100%", height: 260 }} />;
}
