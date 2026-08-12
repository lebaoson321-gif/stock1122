"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { MarketStatus } from "./types";

/** Nhịp hỏi lại trạng thái phiên. Trạng thái chỉ đổi ở vài mốc cố định
 *  trong ngày nên không cần hỏi dày. */
const STATUS_POLL_MS = 60_000;

/**
 * Trạng thái phiên giao dịch, lấy từ backend chứ KHÔNG tự tính ở trình
 * duyệt: đồng hồ máy người dùng có thể lệch hoặc để sai múi giờ, và giờ
 * giao dịch chỉ nên định nghĩa ở một nơi (apps/api/app/services/market_session.py).
 */
export function useMarketSession(): MarketStatus | null {
  const [status, setStatus] = useState<MarketStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      api
        .getMarketStatus()
        .then((s) => {
          if (!cancelled) setStatus(s);
        })
        .catch(() => {
          // Không hiện lỗi: đây là thông tin phụ trợ, hỏng thì ẩn badge
          // đi chứ đừng chắn nội dung chính.
        });
    };
    load();
    const id = setInterval(load, STATUS_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return status;
}

/**
 * Gọi `onRefresh` định kỳ, CHỈ khi thị trường đang khớp lệnh.
 *
 * Ngoài giờ thì giá không đổi nên làm mới chỉ tốn request và đánh thức
 * backend vô ích (Render gói miễn phí tính theo thời gian chạy). Cũng
 * dừng luôn khi tab bị ẩn — người dùng mở 10 tab nền không có lý do gì
 * phải nhân 10 lượng request.
 */
export function useAutoRefresh(isOpen: boolean | undefined, onRefresh: () => void, intervalMs = 60_000) {
  // Giữ callback trong ref để interval không bị dựng lại mỗi lần render
  // (onRefresh thường là closure mới sau mỗi render).
  const callbackRef = useRef(onRefresh);
  useEffect(() => {
    callbackRef.current = onRefresh;
  }, [onRefresh]);

  useEffect(() => {
    if (!isOpen) return;

    const tick = () => {
      if (document.visibilityState === "visible") callbackRef.current();
    };
    const id = setInterval(tick, intervalMs);

    // Quay lại tab sau một lúc thì làm mới ngay, không đợi hết nhịp.
    const onVisible = () => {
      if (document.visibilityState === "visible") callbackRef.current();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [isOpen, intervalMs]);
}
