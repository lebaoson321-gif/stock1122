"""
Test parsing/mapping của FireAntAdapter bằng dữ liệu THẬT đã ghi lại (gọi
qua trình duyệt, tài khoản fireant.vn đã đăng nhập, 2026-08-14) cho
DHC/VCB/HPG — không gọi mạng, không cần FIREANT_TOKEN, chạy trong CI mặc
định. Mốc so sánh (P/E, EPS, ROE, ROA) đối chiếu với bảng giá công ty
chứng khoán — xem docstring fireant_adapter.py về lý do đổi nguồn từ VCI
(VCI tính P/E/EPS sai ~1,9 lần do dùng cơ sở lợi nhuận chỉ bằng nửa TTM).

Test gọi FireAnt THẬT qua mạng nằm ở tests/integration/test_fireant_adapter.py
(cần FIREANT_TOKEN, không chạy mặc định — xem `pytest.ini`).
"""
import httpx
import pytest

from app.collectors.fireant_adapter import FireAntAdapter

_FIXTURES = {
    "DHC": {
        "fundamental": {
            "symbol": None, "companyType": 0, "sharesOutstanding": 106249620.0,
            "freeShares": 48921268.0, "beta": 0.77, "dividend": 1000.0,
            "dividendYield": 0.03246753, "marketCap": 3718736700000.0,
            "low52Week": 26012.2, "high52Week": 36868.53, "priceChange1y": 0.28047,
            "avgVolume10d": 454440.0, "avgVolume3m": 267636.0,
            "pe": 6.7666247180924559, "eps": 5172.4458586298942,
            "sales_TTM": 3937755856269.0, "netProfit_TTM": 549570406950.0,
            "insiderOwnership": 0.18981074, "institutionOwnership": 0.26200508,
            "foreignOwnership": 0.34480879,
        },
        "financial-indicators": [
            {"name": "P/E", "value": 6.766624718092456},
            {"name": "P/B", "value": 1.4790746692713683},
            {"name": "EPS", "value": 5172.445858629894},
            {"name": "ROA (%)", "value": 14.859109},
            {"name": "ROE (%)", "value": 23.958614999999998},
        ],
        "profile": {"charterCapital": 1062496200000, "overview": "Cùng với sự tăng trưởng và phát triển kinh tế..."},
    },
    "VCB": {
        "fundamental": {
            "symbol": None, "companyType": 1, "sharesOutstanding": 8355675094,
            "freeShares": 757380795, "beta": 0.77, "dividend": 450,
            "dividendYield": 0.00753769, "marketCap": 488806992999000,
            "low52Week": 52600, "high52Week": 78149.36, "priceChange1y": -0.03307,
            "avgVolume10d": 5794230, "avgVolume3m": 5430407,
            "pe": 11.736377011575556, "eps": 4984.502452699126,
            "sales_TTM": 136083621000000, "netProfit_TTM": 41648883000000,
            "insiderOwnership": 0.00001756, "institutionOwnership": 0.89859432,
            "foreignOwnership": 0.20143753,
        },
        "financial-indicators": [
            {"name": "P/E", "value": 11.876812292053867},
            {"name": "P/B", "value": 1.9906433188428567},
            {"name": "EPS", "value": 4984.5024527},
            {"name": "ROA (%)", "value": 1.708645},
            {"name": "ROE (%)", "value": 18.020460999999997},
        ],
        "profile": {"charterCapital": 83556750940000, "overview": None},
    },
    "HPG": {
        "fundamental": {
            "symbol": None, "companyType": 0, "sharesOutstanding": 8442964520,
            "freeShares": 4810216010, "beta": 0.75, "dividend": 500,
            "dividendYield": 0.02217295, "marketCap": 182368033632000,
            "low52Week": 20100, "high52Week": 27541.95, "priceChange1y": -0.135,
            "avgVolume10d": 21865980, "avgVolume3m": 22021212,
            "pe": 7.855837020414037, "eps": 2749.547876804296,
            "sales_TTM": 190643650555249, "netProfit_TTM": 23214335169900,
            "insiderOwnership": 0.33375999, "institutionOwnership": 0.00562665,
            "foreignOwnership": 0.21751523,
        },
        "financial-indicators": [
            {"name": "P/E", "value": 7.764912980825912},
            {"name": "P/B", "value": 1.2797106606875264},
            {"name": "EPS", "value": 2749.547876804296},
            {"name": "ROA (%)", "value": 8.908814},
            {"name": "ROE (%)", "value": 17.594913000000002},
        ],
        "profile": {"charterCapital": 84429645200000, "overview": None},
    },
}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _install_fake_get(monkeypatch, symbol: str):
    fixtures = _FIXTURES[symbol]

    def fake_get(self, url, headers=None):
        for path, payload in fixtures.items():
            if url.endswith(f"/symbols/{symbol}/{path}"):
                return _FakeResponse(payload)
        raise AssertionError(f"URL không có trong fixture test: {url}")

    monkeypatch.setattr(httpx.Client, "get", fake_get)


@pytest.mark.parametrize(
    "symbol,expected_pe,expected_eps,expected_roe,expected_roa,expected_market_cap,expected_shares",
    [
        # Mốc đối chiếu bảng giá công ty chứng khoán (2026-08): DHC P/E
        # ~6,8 (KHÔNG phải 13,0 như VCI), EPS ~5.172đ, ROE ~24-26%.
        ("DHC", 6.77, 5172.4, 23.96, 14.86, 3_718_736_700_000, 106_249_620),
        ("VCB", 11.74, 4984.5, 18.02, 1.71, 488_806_992_999_000, 8_355_675_094),
        ("HPG", 7.86, 2749.5, 17.59, 8.91, 182_368_033_632_000, 8_442_964_520),
    ],
)
def test_maps_real_fireant_payload(
    monkeypatch, symbol, expected_pe, expected_eps, expected_roe, expected_roa,
    expected_market_cap, expected_shares,
):
    _install_fake_get(monkeypatch, symbol)
    adapter = FireAntAdapter(token="fake-token-not-used-in-test")

    data = adapter.get_company_fundamentals(symbol)

    assert data.symbol == symbol
    assert data.pe == pytest.approx(expected_pe, abs=0.01)
    assert data.eps == pytest.approx(expected_eps, abs=0.1)
    assert data.pb is not None
    # ROE/ROA của FireAnt đã là phần trăm sẵn — adapter KHÔNG được nhân
    # thêm 100 hay áp công thức suy đơn vị của VCI (fundamentals_math.py).
    assert data.roe == pytest.approx(expected_roe, abs=0.01)
    assert data.roa == pytest.approx(expected_roa, abs=0.01)
    assert data.market_cap == pytest.approx(expected_market_cap, rel=1e-6)
    assert data.issue_share == pytest.approx(expected_shares, rel=1e-6)
    assert data.charter_capital is not None
    assert data.industry is None  # FireAnt chỉ trả icbCode, không có tên ngành
    assert data.raw["_source"] == "fireant"


def test_response_symbol_null_does_not_override_requested_symbol(monkeypatch):
    # /fundamental trả "symbol": null — phải tự gán từ tham số gọi.
    _install_fake_get(monkeypatch, "DHC")
    adapter = FireAntAdapter(token="fake-token-not-used-in-test")
    data = adapter.get_company_fundamentals("dhc")
    assert data.symbol == "DHC"
