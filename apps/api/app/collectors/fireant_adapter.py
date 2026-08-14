"""
Adapter cho FireAnt — nguồn CHỈ cho chỉ số tài chính doanh nghiệp (P/E,
EPS, P/B, ROE, ROA, vốn hoá...). Giá và lịch sử giá vẫn đi qua
vnstock_adapter.py, KHÔNG đụng ở đây — xem factory.py phần
get_fundamentals_provider().

Vì sao đổi từ VCI (qua vnstock) cho riêng phần chỉ số tài chính: đối
chiếu DHC với bảng giá công ty chứng khoán (2026-08) cho thấy VCI dùng cơ
sở lợi nhuận ròng chỉ bằng nửa TTM thật (~285 tỷ so với ~550 tỷ) — P/E và
EPS lệch có hệ thống ~1,9 lần. Không phải lỗi đơn vị nên không phép quy
đổi nào ở fundamentals_math.py chữa được, phải đổi nguồn.

Tên trường dưới đây lấy từ dữ liệu THẬT (gọi 3 endpoint restv2.fireant.vn
bằng tài khoản đã đăng nhập, đối chiếu số ra với DHC/VCB/HPG), không phải
đoán:

  GET /symbols/{symbol}/fundamental
      sharesOutstanding, marketCap, pe, eps, dividendYield (TỶ SỐ, ví dụ
      0.0325 = 3,25% — không phải đã-là-phần-trăm), netProfit_TTM...
      Trường "symbol" trong response LUÔN là null — phải tự gán từ tham
      số gọi, không lấy từ response.

  GET /symbols/{symbol}/financial-indicators
      Trả về MẢNG {name, value, ...} chứ không phải object phẳng — phải
      lọc theo "name". Tên đã kiểm chứng: "P/E", "P/B", "EPS", "ROE (%)",
      "ROA (%)". ROE/ROA ở đây ĐÃ LÀ phần trăm sẵn (23.9 nghĩa là 23,9%)
      — khác hẳn VCI (VCI trả tỷ số không rõ đơn vị, phải suy qua
      services/fundamentals_math.py). KHÔNG áp fundamentals_math cho số
      của FireAnt.

  GET /symbols/{symbol}/profile
      charterCapital, overview (hồ sơ doanh nghiệp, dùng cho
      company_profile). KHÔNG có trường tên ngành — chỉ có icbCode (mã
      số), không tra được tên qua endpoint nào lộ ra qua network tab
      (đã thử /industries/{code} -> 404). Vì vậy industry để None thay vì
      đoán tên từ mã số.

Cả 3 endpoint đã kiểm tra chéo với VCB (ngân hàng, companyType khác DHC)
— cùng tên trường, giá trị hợp lý theo đặc thù ngành ngân hàng.
"""
import httpx

from app.collectors.base import CompanyFundamentals

_BASE_URL = "https://restv2.fireant.vn"
_TIMEOUT_SECONDS = 10.0


def _first_number(*values: object) -> float | None:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
    return None


class FireAntAdapter:
    """CHỈ implement get_company_fundamentals — không phải một
    MarketDataProvider đầy đủ, vì giá vẫn đi qua VnstockAdapter (xem
    factory.get_fundamentals_provider, nơi 2 adapter được kết hợp)."""

    def __init__(self, token: str):
        self._token = token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    def _get_json(self, client: httpx.Client, path: str):
        resp = client.get(f"{_BASE_URL}{path}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_company_fundamentals(self, symbol: str) -> CompanyFundamentals:
        symbol = symbol.upper()

        with httpx.Client(timeout=_TIMEOUT_SECONDS) as client:
            # /fundamental là nguồn chính (P/E, EPS, vốn hoá) — lỗi ở đây
            # coi như cả lần gọi thất bại, để factory lùi về vnstock.
            fund = self._get_json(client, f"/symbols/{symbol}/fundamental")

            # /financial-indicators và /profile là nguồn bổ sung (P/B,
            # ROE, ROA, hồ sơ doanh nghiệp) — thiếu một trong hai vẫn còn
            # phần từ /fundamental, tốt hơn là trắng tay cả CompanyFundamentals.
            indicators: dict[str, float] = {}
            try:
                for item in self._get_json(client, f"/symbols/{symbol}/financial-indicators"):
                    name = item.get("name")
                    value = item.get("value")
                    if name is not None and value is not None:
                        indicators[name] = value
            except httpx.HTTPError:
                pass

            profile: dict = {}
            try:
                profile = self._get_json(client, f"/symbols/{symbol}/profile")
            except httpx.HTTPError:
                pass

        dividend_yield_ratio = _first_number(fund.get("dividendYield"))

        return CompanyFundamentals(
            symbol=symbol,
            market_cap=_first_number(fund.get("marketCap")),
            pe=_first_number(fund.get("pe"), indicators.get("P/E")),
            pb=_first_number(indicators.get("P/B")),
            eps=_first_number(fund.get("eps"), indicators.get("EPS")),
            roe=_first_number(indicators.get("ROE (%)")),
            roa=_first_number(indicators.get("ROA (%)")),
            dividend_yield=dividend_yield_ratio * 100 if dividend_yield_ratio is not None else None,
            issue_share=_first_number(fund.get("sharesOutstanding")),
            charter_capital=_first_number(profile.get("charterCapital")),
            company_profile=profile.get("overview") or None,
            industry=None,  # FireAnt chỉ trả icbCode (mã số) — xem docstring trên
            # "_source" để router (fundamentals.py) biết ROE/ROA ở đây ĐÃ
            # LÀ phần trăm, không chạy qua suy đơn vị của fundamentals_math.py
            # (cái đó chỉ dành cho số thô kiểu VCI/vnstock).
            raw={
                "_source": "fireant",
                "fundamental": fund,
                "financial_indicators": indicators,
                "profile": profile,
            },
        )
