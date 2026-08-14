"use client";

import { useState } from "react";
import type { FundamentalsResult } from "@/lib/types";

/** Rút gọn số tiền lớn về tỷ/nghìn tỷ — vốn hoá HOSE thường 10-12 chữ số,
 *  in đầy đủ thì không ai đọc nổi. */
function fmtBigVnd(n: number | null): string | null {
  if (n === null || n === undefined) return null;
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${(n / 1e12).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} nghìn tỷ`;
  if (abs >= 1e9) return `${(n / 1e9).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} tỷ`;
  return `${n.toLocaleString("vi-VN", { maximumFractionDigits: 0 })}đ`;
}

function fmtNum(n: number | null, suffix = ""): string | null {
  if (n === null || n === undefined) return null;
  return `${n.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}${suffix}`;
}

function fmtShares(n: number | null): string | null {
  if (n === null || n === undefined) return null;
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} triệu cp`;
  return `${n.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} cp`;
}

export default function FundamentalsCard({ data }: { data: FundamentalsResult | null }) {
  const [expanded, setExpanded] = useState(false);

  if (data === null) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Thông tin doanh nghiệp
        </div>
        <div className="text-sm text-neutral-400">Đang tải…</div>
      </div>
    );
  }

  if (data.available === false) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Thông tin doanh nghiệp
        </div>
        <div className="text-sm text-neutral-400">{data.message}</div>
      </div>
    );
  }

  // Chỉ hiện chỉ số thực sự lấy được: provider không chính thức và mỗi
  // loại hình doanh nghiệp có bộ chỉ số khác nhau, nên hàng loạt dấu "—"
  // vô nghĩa sẽ chỉ làm nhiễu.
  const metrics = [
    { label: "Vốn hoá", value: fmtBigVnd(data.market_cap) },
    { label: "P/E", value: fmtNum(data.pe) },
    { label: "P/B", value: fmtNum(data.pb) },
    { label: "EPS", value: data.eps !== null ? `${fmtNum(data.eps)}đ` : null },
    { label: "ROE", value: fmtNum(data.roe, "%") },
    { label: "ROA", value: fmtNum(data.roa, "%") },
    { label: "Tỷ suất cổ tức", value: fmtNum(data.dividend_yield, "%") },
    { label: "SL lưu hành", value: fmtShares(data.issue_share) },
    { label: "Vốn điều lệ", value: fmtBigVnd(data.charter_capital) },
  ].filter((m) => m.value !== null);

  const fetched = new Date(data.fetched_at);
  const daysOld = Math.floor((Date.now() - fetched.getTime()) / 86_400_000);

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Thông tin doanh nghiệp
        </span>
        {data.industry && <span className="text-xs text-neutral-400">{data.industry}</span>}
      </div>

      {data.source === "vnstock" && (
        <div className="mb-3 rounded-md border border-amber-900/50 bg-amber-950/20 p-3 text-xs text-amber-200/90">
          Đang dùng nguồn dự phòng (VCI) — ROE/ROA/EPS có thể sai lệch đáng kể. Kiểm tra biến
          FIREANT_TOKEN trên Render.
        </div>
      )}

      {metrics.length === 0 ? (
        <div className="text-sm text-neutral-400">
          Chưa lấy được chỉ số nào cho mã này (nguồn dữ liệu không có sẵn chỉ số cơ bản).
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
          {metrics.map((m) => (
            <div key={m.label}>
              <div className="text-[11px] text-neutral-500">{m.label}</div>
              <div className="font-mono text-sm font-semibold text-neutral-100">{m.value}</div>
            </div>
          ))}
        </div>
      )}

      {data.company_profile && (
        <div className="mt-4 border-t border-neutral-800 pt-3">
          <p className={`text-xs leading-relaxed text-neutral-400 ${expanded ? "" : "line-clamp-3"}`}>
            {data.company_profile}
          </p>
          {data.company_profile.length > 180 && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="mt-1 text-[11px] text-emerald-400 hover:underline"
            >
              {expanded ? "Thu gọn" : "Xem thêm"}
            </button>
          )}
        </div>
      )}

      <div className="mt-3 text-[10px] text-neutral-600">
        Cập nhật {daysOld === 0 ? "hôm nay" : `${daysOld} ngày trước`}
        {data.source === "fireant" ? " · Nguồn: FireAnt" : " · nguồn VCI qua vnstock (không phải dữ liệu chính thức từ HOSE)"}
      </div>
    </div>
  );
}
