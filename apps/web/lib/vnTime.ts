/**
 * Định dạng thời gian theo giờ Việt Nam, KHÔNG theo múi giờ máy người dùng.
 *
 * Mọi mốc thời gian trong app này đều là giờ thị trường ("mở cửa 9:00",
 * "cập nhật lúc 14:20") nên phải hiển thị thống nhất theo giờ VN. Dùng
 * mặc định của trình duyệt sẽ khiến máy đặt sai múi giờ hiện ra giờ vô
 * nghĩa — đã gặp thật khi kiểm thử trên máy chạy UTC, badge báo "mở lúc
 * 02:00" thay vì 09:00.
 */
const VN_TZ = "Asia/Ho_Chi_Minh";

export function vnTime(value: string | Date): string {
  return new Date(value).toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: VN_TZ,
  });
}

export function vnTimeWithSeconds(value: string | Date): string {
  return new Date(value).toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: VN_TZ,
  });
}

export function vnDateTime(value: string | Date): string {
  return new Date(value).toLocaleString("vi-VN", { timeZone: VN_TZ });
}

/**
 * Định dạng một ngày giao dịch thuần (không có giờ, VD "2026-08-14" từ
 * cột `trade_date`) thành "dd/mm/yyyy". Không đi qua `new Date(value)` +
 * timeZone như các hàm trên: chuỗi "YYYY-MM-DD" được parse là UTC nửa
 * đêm, quy đổi sang giờ VN (+7) sẽ lệch sang 07:00 — vô hại với giờ
 * nhưng không cần thiết và dễ nhầm khi debug; ngày giao dịch vốn đã là
 * ngày lịch VN, không cần quy đổi múi giờ.
 */
export function vnDate(value: string): string {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

/**
 * Ngày lịch VN ("YYYY-MM-DD") của một thời điểm cụ thể (VD `server_time`
 * từ /api/market/status, có kèm offset). Dùng để so sánh với `trade_date`
 * (vốn đã là chuỗi "YYYY-MM-DD") — KHÔNG được lấy ngày qua
 * `new Date(value).getDate()`/toLocaleDateString trần vì đó là quy đổi
 * theo múi giờ máy người dùng, có thể lệch ngày so với giờ VN.
 */
export function vnCalendarDate(value: string | Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: VN_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(value));
  const get = (type: string) => parts.find((p) => p.type === type)!.value;
  return `${get("year")}-${get("month")}-${get("day")}`;
}
