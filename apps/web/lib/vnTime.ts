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
