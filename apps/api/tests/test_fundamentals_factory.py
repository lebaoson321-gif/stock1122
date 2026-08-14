"""
_FundamentalsWithFallback là phần dễ gãy âm thầm nhất trong việc đổi
nguồn: nếu nó không lùi về vnstock đúng lúc, người dùng sẽ thấy thẻ trắng
mỗi khi FireAnt (API không chính thức, không SLA) tạm lỗi — xem
factory.py và docstring Bước 2/4 trong yêu cầu gốc.
"""
from app.collectors.base import CompanyFundamentals
from app.collectors.factory import _FundamentalsWithFallback


class _StubProvider:
    def __init__(self, result=None, exc=None):
        self._result = result
        self._exc = exc
        self.calls: list[str] = []

    def get_company_fundamentals(self, symbol: str) -> CompanyFundamentals:
        self.calls.append(symbol)
        if self._exc is not None:
            raise self._exc
        return self._result


def test_falls_back_when_primary_raises():
    fallback_data = CompanyFundamentals(symbol="DHC", pe=6.77)
    primary = _StubProvider(exc=RuntimeError("FireAnt 500"))
    fallback = _StubProvider(result=fallback_data)

    wrapper = _FundamentalsWithFallback(primary, fallback)
    result = wrapper.get_company_fundamentals("DHC")

    assert result is fallback_data
    assert primary.calls == ["DHC"]
    assert fallback.calls == ["DHC"]


def test_falls_back_when_primary_returns_all_empty():
    empty_data = CompanyFundamentals(symbol="XYZ")  # mã không có trên FireAnt
    fallback_data = CompanyFundamentals(symbol="XYZ", pe=1.0)
    primary = _StubProvider(result=empty_data)
    fallback = _StubProvider(result=fallback_data)

    wrapper = _FundamentalsWithFallback(primary, fallback)
    result = wrapper.get_company_fundamentals("XYZ")

    assert result is fallback_data


def test_uses_primary_when_it_succeeds():
    primary_data = CompanyFundamentals(symbol="DHC", pe=6.77, eps=5172.4, market_cap=3_718_736_700_000)
    primary = _StubProvider(result=primary_data)
    fallback = _StubProvider(result=CompanyFundamentals(symbol="DHC"))

    wrapper = _FundamentalsWithFallback(primary, fallback)
    result = wrapper.get_company_fundamentals("DHC")

    assert result is primary_data
    assert fallback.calls == []  # không cần lùi về khi primary đã đủ dữ liệu
