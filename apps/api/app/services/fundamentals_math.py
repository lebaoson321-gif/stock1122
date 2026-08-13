"""
Chuẩn hoá chỉ số sinh lời từ provider.

Bối cảnh: VCI (qua vnstock) không có tài liệu về đơn vị của ROE/ROA, và
tên cột chỉ lộ ra khi gọi API thật. Lần đầu app hiển thị thẳng số thô kèm
dấu "%" nên ra "ROE 0,14%" — sai 100 lần. Nhân đại 100 cũng không ổn: nếu
có mã nào provider trả sẵn phần trăm thì lại sai theo chiều ngược lại.

Cách xử lý ở đây dựa vào một đẳng thức thay vì dựa vào niềm tin:

    ROE = lợi nhuận / vốn chủ sở hữu
        = (lợi nhuận / số cp) / (vốn chủ / số cp)
        = EPS / giá trị sổ sách mỗi cp

    mà  P/E = giá / EPS   và   P/B = giá / giá trị sổ sách mỗi cp

    =>  ROE = P/B ÷ P/E

P/E và P/B là hai chỉ số đã đối chiếu đúng với thực tế, nên ROE tính từ
chúng đáng tin hơn hẳn field ROE không rõ đơn vị. Với DHC: 1,76/13,01 =
13,5%, khớp với số thô 0,14 hiểu theo nghĩa tỷ số — chứ không phải 0,14%.

ROA không có đẳng thức tương tự (cần bảng cân đối kế toán). Nhưng ROA nằm
cùng một payload với ROE nên dùng chung quy ước đơn vị: suy ra hệ số quy
đổi từ ROE rồi áp cho ROA.
"""

# Không doanh nghiệp niêm yết nào có ROE/ROA vượt ngưỡng này một cách bền
# vững. Vượt là dấu hiệu sai đơn vị hoặc khớp nhầm cột -> thà không hiển
# thị còn hơn hiện một con số sai mà người dùng tưởng thật.
MAX_PLAUSIBLE_PERCENT = 200.0

_SCALE_CANDIDATES = (1.0, 100.0)


def roe_from_pe_pb(pe: float | None, pb: float | None) -> float | None:
    """ROE (%) suy ra từ đẳng thức ROE = P/B ÷ P/E.

    Trả None khi P/E không dương: P/E âm nghĩa là doanh nghiệp đang lỗ,
    lúc đó thương số vẫn tính được nhưng mất ý nghĩa (ROE âm không suy ra
    đúng theo cách này).
    """
    if pe is None or pb is None or pe <= 0:
        return None
    return pb / pe * 100.0


def infer_percent_scale(provider_value: float | None, reference_percent: float | None) -> float | None:
    """Provider đang trả tỷ số (cần ×100) hay đã là phần trăm (×1)?

    So số thô với giá trị tính được từ đẳng thức, chọn hệ số cho ra kết
    quả gần hơn. Nếu cả hai đều lệch quá xa thì không kết luận (trả None)
    — có thể provider đã khớp nhầm cột chứ không phải sai đơn vị.
    """
    if not provider_value or reference_percent is None:
        return None

    best = min(_SCALE_CANDIDATES, key=lambda s: abs(provider_value * s - reference_percent))
    tolerance = max(5.0, abs(reference_percent))
    if abs(provider_value * best - reference_percent) > tolerance:
        return None
    return best


def as_percent(value: float | None, scale: float | None) -> float | None:
    """Áp hệ số quy đổi rồi lọc bỏ giá trị vô lý."""
    if value is None or scale is None:
        return None
    result = value * scale
    if abs(result) > MAX_PLAUSIBLE_PERCENT:
        return None
    return result


def normalise_profitability(
    pe: float | None,
    pb: float | None,
    raw_roe: float | None,
    raw_roa: float | None,
) -> tuple[float | None, float | None]:
    """Trả (roe_phần_trăm, roa_phần_trăm), None cho giá trị không tin được."""
    computed_roe = roe_from_pe_pb(pe, pb)
    scale = infer_percent_scale(raw_roe, computed_roe)

    if scale is None:
        # Không đối chiếu được (thiếu P/E/P/B, hoặc số thô lệch quá xa).
        # VCI trả tỷ số ở mọi mã đã kiểm tra nên dùng quy ước đó, và để
        # bộ lọc vô lý bên dưới chặn trường hợp quy ước sai.
        scale = 100.0

    roe = as_percent(raw_roe, scale)
    roa = as_percent(raw_roa, scale)

    # Ưu tiên số tính từ đẳng thức: nó dựa trên P/E và P/B đã đối chiếu
    # đúng, còn field ROE của provider thì chưa bao giờ kiểm chứng được.
    if computed_roe is not None and abs(computed_roe) <= MAX_PLAUSIBLE_PERCENT:
        roe = computed_roe

    return roe, roa
