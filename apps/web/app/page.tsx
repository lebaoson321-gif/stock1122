import MarketOverview from "@/components/MarketOverview";
import SearchBar from "@/components/SearchBar";
import StockList from "@/components/StockList";

export default function HomePage() {
  return (
    <div className="flex flex-col gap-8">
      <MarketOverview />

      <div>
        <h1 className="mb-2 font-mono text-2xl font-bold">Tìm mã cổ phiếu</h1>
        <p className="mb-4 text-sm text-neutral-400">
          Nhập mã (VD: FPT, VNM, HPG, VCB) để xem biểu đồ giá, chỉ báo kỹ thuật và phân tích.
        </p>
        <SearchBar />
      </div>

      <StockList />

      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-5 text-sm text-neutral-400">
        Đăng nhập và mở trang{" "}
        <a href="/watchlist" className="text-emerald-400 underline">
          Watchlist
        </a>{" "}
        để lưu danh sách mã theo dõi riêng.
      </div>
    </div>
  );
}
