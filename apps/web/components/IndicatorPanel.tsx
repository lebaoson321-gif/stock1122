"use client";

import { ColorType, IChartApi, ISeriesApi, createChart } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { PricePoint } from "@/lib/types";

const COLORS = {
  bg: "#0A0E12",
  grid: "#1C242E",
  text: "#7C8794",
  rsi: "#C960E8",
  macd: "#34D2F0",
  signal: "#F0B90B",
};

interface RsiPanelProps {
  data: PricePoint[];
}

export function RsiPanel({ data }: RsiPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: COLORS.bg }, textColor: COLORS.text },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      autoSize: false,
      rightPriceScale: { borderColor: COLORS.grid },
      timeScale: { borderColor: COLORS.grid },
    });
    seriesRef.current = chart.addLineSeries({ color: COLORS.rsi, lineWidth: 2, title: "RSI(14)" });
    chartRef.current = chart;

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
    if (!seriesRef.current || data.length === 0) return;
    seriesRef.current.setData(
      data.filter((d) => d.rsi14 !== null).map((d) => ({ time: d.date, value: d.rsi14 as number }))
    );
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} style={{ width: "100%", height: 140 }} />;
}

interface MacdPanelProps {
  data: PricePoint[];
}

export function MacdPanel({ data }: MacdPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const macdSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const signalSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const histSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: COLORS.bg }, textColor: COLORS.text },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      autoSize: false,
      rightPriceScale: { borderColor: COLORS.grid },
      timeScale: { borderColor: COLORS.grid },
    });
    histSeriesRef.current = chart.addHistogramSeries({ color: COLORS.grid, title: "Hist" });
    macdSeriesRef.current = chart.addLineSeries({ color: COLORS.macd, lineWidth: 2, title: "MACD" });
    signalSeriesRef.current = chart.addLineSeries({ color: COLORS.signal, lineWidth: 2, title: "Signal" });
    chartRef.current = chart;

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
    if (!macdSeriesRef.current || data.length === 0) return;
    macdSeriesRef.current.setData(
      data.filter((d) => d.macd !== null).map((d) => ({ time: d.date, value: d.macd as number }))
    );
    signalSeriesRef.current?.setData(
      data.filter((d) => d.macd_signal !== null).map((d) => ({ time: d.date, value: d.macd_signal as number }))
    );
    histSeriesRef.current?.setData(
      data
        .filter((d) => d.macd_hist !== null)
        .map((d) => ({
          time: d.date,
          value: d.macd_hist as number,
          color: (d.macd_hist as number) >= 0 ? "rgba(0,192,118,0.5)" : "rgba(246,70,93,0.5)",
        }))
    );
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} style={{ width: "100%", height: 140 }} />;
}
