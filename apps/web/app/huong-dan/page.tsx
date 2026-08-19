import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Hướng dẫn chứng khoán cơ bản — Stock Intelligence",
  description:
    "Giải thích các chỉ báo và chỉ số mà dashboard đang hiển thị: đâu là tín hiệu tốt, đâu là tín hiệu xấu, và những yếu tố ảnh hưởng tới giá cổ phiếu Việt Nam.",
};

/* Trang tĩnh hoàn toàn (Server Component, không "use client"): nội dung
   không đổi theo dữ liệu nên không cần fetch gì, tải nhanh và index được. */

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20">
      <h2 className="mb-3 border-b border-neutral-800 pb-2 font-mono text-lg font-bold text-neutral-100">
        {title}
      </h2>
      <div className="flex flex-col gap-3 text-sm leading-relaxed text-neutral-300">{children}</div>
    </section>
  );
}

/** Luật giao dịch khác nhau giữa 3 sàn (giờ khớp lệnh liên tục giống
 *  nhau, khác ở ATO/ATC và biên độ) — xem app/services/market_session.py
 *  phía backend, đây là bảng tương ứng phía nội dung giải thích. */
function ExchangeRulesTable() {
  const rows = [
    {
      exchange: "HOSE",
      hours: "9:00–11:30, 13:00–14:45 (+ thoả thuận tới 15:00)",
      atoAtc: "Có ATO (9:00–9:15) và ATC (14:30–14:45)",
      band: "±7%",
    },
    {
      exchange: "HNX",
      hours: "9:00–11:30, 13:00–14:45 (+ thoả thuận tới 15:00)",
      atoAtc: "Có ATC (14:30–14:45), không có ATO",
      band: "±10%",
    },
    {
      exchange: "UPCoM",
      hours: "9:00–11:30, 13:00–15:00",
      atoAtc: "Không có ATO/ATC — chỉ khớp lệnh liên tục",
      band: "±15%",
    },
  ];
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-neutral-800 text-left text-xs uppercase tracking-wide text-neutral-500">
            <th className="w-[12%] pb-2 pr-3">Sàn</th>
            <th className="w-[36%] pb-2 pr-3">Giờ giao dịch</th>
            <th className="w-[36%] pb-2 pr-3">ATO / ATC</th>
            <th className="w-[16%] pb-2">Biên độ</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.exchange} className="border-b border-neutral-800/60 align-top">
              <td className="py-3 pr-3 font-mono font-semibold text-neutral-100">{r.exchange}</td>
              <td className="py-3 pr-3 text-neutral-300">{r.hours}</td>
              <td className="py-3 pr-3 text-neutral-300">{r.atoAtc}</td>
              <td className="py-3 font-mono text-neutral-300">{r.band}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Bảng 4 cột dùng chung cho phần chỉ báo và chỉ số — cột "cạm bẫy" là
 *  cột quan trọng nhất: người mới thường đọc tín hiệu mà bỏ qua bối cảnh
 *  khiến tín hiệu đó sai. */
function SignalTable({
  rows,
}: {
  rows: { name: string; good: string; bad: string; trap: string }[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-neutral-800 text-left text-xs uppercase tracking-wide text-neutral-500">
            <th className="w-[16%] pb-2 pr-3">Chỉ số</th>
            <th className="w-[26%] pb-2 pr-3 text-emerald-500">Tín hiệu tích cực</th>
            <th className="w-[26%] pb-2 pr-3 text-red-400">Tín hiệu tiêu cực</th>
            <th className="w-[32%] pb-2">Cạm bẫy thường gặp</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.name} className="border-b border-neutral-800/60 align-top">
              <td className="py-3 pr-3 font-mono font-semibold text-neutral-100">{r.name}</td>
              <td className="py-3 pr-3 text-neutral-300">{r.good}</td>
              <td className="py-3 pr-3 text-neutral-300">{r.bad}</td>
              <td className="py-3 text-neutral-400">{r.trap}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const TECHNICAL = [
  {
    name: "MA20 / MA50",
    good: "Giá nằm trên cả hai đường, và MA20 cắt lên MA50 (thị trường quen gọi là “giao cắt vàng”) — xu hướng tăng đang hình thành.",
    bad: "Giá nằm dưới cả hai, MA20 cắt xuống MA50 — xu hướng giảm.",
    trap: "MA là đường trung bình của quá khứ nên luôn phản ứng CHẬM hơn giá. Khi tín hiệu giao cắt xuất hiện thì giá thường đã chạy một đoạn. Trong thị trường đi ngang, hai đường cắt nhau liên tục và hầu hết là tín hiệu nhiễu.",
  },
  {
    name: "MA200",
    good: "Giá duy trì trên MA200 — xu hướng dài hạn còn tăng, thường được xem là “vùng an toàn” của nhà đầu tư dài hạn.",
    bad: "Giá thủng MA200 kèm khối lượng lớn — xu hướng dài hạn có thể đã đảo chiều.",
    trap: "Cần ít nhất 200 phiên dữ liệu mới tính được. Mã mới niêm yết sẽ không có đường này, không phải lỗi hiển thị.",
  },
  {
    name: "RSI (14)",
    good: "Từ dưới 30 bật lên — áp lực bán đã cạn, khả năng hồi phục. Vùng 40–60 cho thấy thị trường cân bằng.",
    bad: "Trên 70 kéo dài rồi quay đầu giảm — quá mua, rủi ro điều chỉnh.",
    trap: "Sai lầm phổ biến nhất: thấy RSI > 70 liền bán. Trong một con sóng tăng mạnh, RSI có thể nằm trên 70 hàng tuần liền và giá vẫn tăng tiếp. RSI chỉ đáng tin khi thị trường đi ngang, không phải khi đang có xu hướng mạnh.",
  },
  {
    name: "MACD",
    good: "Đường MACD cắt lên đường Signal, cột histogram chuyển từ âm sang dương — động lượng đang mạnh lên.",
    bad: "MACD cắt xuống Signal, histogram chuyển âm — động lượng yếu đi.",
    trap: "MACD được tính từ đường trung bình nên cũng chậm. Ở cổ phiếu thanh khoản thấp, chỉ vài lệnh cũng đủ tạo ra tín hiệu cắt giả.",
  },
  {
    name: "Bollinger Bands",
    good: "Hai dải co hẹp lại (thị trường tích luỹ, biến động thấp) thường báo hiệu một cú bứt phá sắp tới — dù chưa cho biết bứt phá theo hướng nào.",
    bad: "Giá chạm dải trên rồi rơi ngược về dải giữa — lực mua đã hụt hơi.",
    trap: "Chạm dải trên KHÔNG có nghĩa là phải bán. Trong xu hướng tăng mạnh, giá có thể bám dải trên suốt nhiều phiên. Dải giữa của Bollinger chính là MA20, nên đừng coi hai chỉ báo này là hai bằng chứng độc lập.",
  },
  {
    name: "Khối lượng",
    good: "Giá tăng kèm khối lượng tăng — dòng tiền thật đang vào, xu hướng đáng tin hơn.",
    bad: "Giá tăng nhưng khối lượng cạn dần — đà tăng thiếu lực đỡ, dễ đảo chiều.",
    trap: "Khối lượng đột biến bất thường ở cổ phiếu nhỏ không phải lúc nào cũng là tin tốt — có thể là hoạt động tạo thanh khoản giả để thu hút người mua.",
  },
];

const FUNDAMENTAL = [
  {
    name: "P/E",
    good: "Thấp hơn trung bình ngành trong khi lợi nhuận vẫn tăng — cổ phiếu có thể đang bị định giá thấp.",
    bad: "Cao vọt so với ngành mà lợi nhuận không tăng tương ứng — kỳ vọng đã bị đẩy quá xa.",
    trap: "P/E thấp không mặc nhiên là rẻ. Thị trường thường định giá thấp những doanh nghiệp mà nó dự đoán lợi nhuận sẽ giảm. Chỉ so P/E trong cùng ngành: ngân hàng, bất động sản và công nghệ có mặt bằng P/E rất khác nhau.",
  },
  {
    name: "P/B",
    good: "Dưới 1 với doanh nghiệp có tài sản thật và làm ăn có lãi — đang giao dịch dưới giá trị sổ sách.",
    bad: "Rất cao trong khi ROE thấp — trả giá đắt cho tài sản sinh lời kém.",
    trap: "Giá trị sổ sách phụ thuộc cách hạch toán. Doanh nghiệp nhiều tài sản vô hình (phần mềm, thương hiệu) luôn có P/B cao một cách tự nhiên, không phải vì đắt.",
  },
  {
    name: "EPS",
    good: "Tăng đều qua nhiều quý — lợi nhuận trên mỗi cổ phiếu đang cải thiện thật.",
    bad: "Giảm liên tiếp, hoặc âm — doanh nghiệp đang thua lỗ.",
    trap: "EPS có thể tăng vọt nhờ khoản thu bất thường (bán tài sản, đánh giá lại) chứ không phải hoạt động kinh doanh cốt lõi. Nên xem lợi nhuận đến từ đâu, không chỉ xem con số.",
  },
  {
    name: "ROE",
    good: "Trên 15% và duy trì ổn định nhiều năm — doanh nghiệp sinh lời tốt trên vốn chủ sở hữu.",
    bad: "Dưới 10% hoặc sụt giảm dần — hiệu quả sử dụng vốn đang kém đi.",
    trap: "ROE cao có thể đến từ vay nợ nhiều chứ không phải kinh doanh giỏi. Nên xem ROE cùng với tỷ lệ nợ.",
  },
  {
    name: "Vốn hoá",
    good: "Vốn hoá lớn thường đi kèm thanh khoản cao, dễ mua bán, ít bị thao túng giá.",
    bad: "Vốn hoá quá nhỏ — giá dễ bị đẩy hoặc dìm bởi một nhóm nhỏ nhà đầu tư.",
    trap: "Vốn hoá lớn không đồng nghĩa an toàn. Doanh nghiệp lớn vẫn có thể giảm giá dài hạn nếu ngành đi xuống.",
  },
];

export default function GuidePage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="mb-2 font-mono text-2xl font-bold">Hướng dẫn chứng khoán cơ bản</h1>
        <p className="text-sm leading-relaxed text-neutral-400">
          Giải thích những gì dashboard này đang hiển thị, dành cho người mới bắt đầu. Trọng tâm không
          phải là học thuộc chỉ báo, mà là hiểu mỗi con số nói lên điều gì và{" "}
          <span className="text-neutral-200">khi nào thì nó nói sai</span>.
        </p>
      </div>

      <nav className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Nội dung
        </div>
        <ol className="grid grid-cols-1 gap-1 text-sm text-emerald-400 sm:grid-cols-2">
          {[
            ["luat-choi", "1. Luật chơi trên sàn HOSE"],
            ["doc-bieu-do", "2. Đọc biểu đồ nến"],
            ["chi-bao", "3. Chỉ báo kỹ thuật"],
            ["chi-so", "4. Chỉ số cơ bản của doanh nghiệp"],
            ["yeu-to", "5. Điều gì làm giá cổ phiếu thay đổi"],
            ["sai-lam", "6. Sai lầm phổ biến của người mới"],
            ["gioi-han", "7. Công cụ này KHÔNG nói lên điều gì"],
          ].map(([id, label]) => (
            <li key={id}>
              <a href={`#${id}`} className="hover:underline">
                {label}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      <Section id="luat-choi" title="1. Luật chơi trên thị trường chứng khoán Việt Nam">
        <p>
          <strong className="text-neutral-100">Cổ phiếu</strong> là phần sở hữu một doanh nghiệp. Mua
          cổ phiếu FPT nghĩa là bạn sở hữu một phần rất nhỏ của FPT, và giá trị phần đó lên xuống theo
          kết quả kinh doanh của doanh nghiệp cùng kỳ vọng của thị trường.
        </p>
        <p>
          App này theo dõi cổ phiếu trên cả 3 sàn — <strong className="text-neutral-100">HOSE</strong>,{" "}
          <strong className="text-neutral-100">HNX</strong>, <strong className="text-neutral-100">UPCoM</strong> —
          và mỗi sàn có giờ giao dịch, quy tắc mở/đóng phiên, và biên độ dao động giá riêng:
        </p>
        <ExchangeRulesTable />
        <ul className="ml-5 list-disc space-y-1.5 text-neutral-300">
          <li>
            <strong className="text-neutral-100">Biên độ:</strong> trong một phiên, giá chỉ được dao
            động tối đa theo % ở bảng trên so với giá tham chiếu. Chạm mức trên gọi là “trần”, mức
            dưới là “sàn”.
          </li>
          <li>
            <strong className="text-neutral-100">Lô chẵn:</strong> mua tối thiểu 100 cổ phiếu mỗi lệnh
            trên cả 3 sàn.
          </li>
          <li>
            <strong className="text-neutral-100">T+2:</strong> mua hôm nay thì khoảng 2 ngày làm việc
            sau cổ phiếu mới về tài khoản và bán được. Đây là lý do không thể “lướt” trong ngày như
            một số thị trường khác.
          </li>
          <li>
            <strong className="text-neutral-100">Chi phí:</strong> phí giao dịch khoảng 0,15–0,35% mỗi
            lệnh, cộng thuế 0,1% khi bán. Nghe nhỏ nhưng mua bán liên tục thì đây là khoản bào mòn lợi
            nhuận đáng kể.
          </li>
        </ul>
        <p className="rounded-md border border-amber-900/50 bg-amber-950/20 p-3 text-xs text-amber-200/90">
          Tính năng <Link href="/portfolio" className="underline">Danh mục ảo</Link> trong app này{" "}
          <strong>cố tình bỏ qua</strong> lô chẵn, phí, thuế và T+2 để bạn dễ thử. Nghĩa là kết quả lãi
          của bạn ở đây sẽ <strong>lạc quan hơn thực tế</strong>. Đừng lấy nó làm thước đo năng lực đầu
          tư thật.
        </p>
      </Section>

      <Section id="doc-bieu-do" title="2. Đọc biểu đồ nến">
        <p>
          Mỗi cây nến là một phiên giao dịch, gói gọn 4 con số: giá mở cửa, giá cao nhất, giá thấp
          nhất, giá đóng cửa.
        </p>
        <ul className="ml-5 list-disc space-y-1.5">
          <li>
            <span className="font-semibold text-emerald-400">Nến xanh</span> — đóng cửa cao hơn mở cửa,
            phiên đó bên mua thắng thế.
          </li>
          <li>
            <span className="font-semibold text-red-400">Nến đỏ</span> — đóng cửa thấp hơn mở cửa, bên
            bán thắng thế.
          </li>
          <li>
            <strong className="text-neutral-100">Bóng nến dài</strong> (đường kẻ mảnh trên/dưới thân
            nến) cho thấy giá đã bị đẩy tới đó rồi bị kéo ngược lại — dấu hiệu hai bên mua bán giằng co
            mạnh.
          </li>
          <li>
            <strong className="text-neutral-100">Cột khối lượng</strong> phía dưới cho biết có bao
            nhiêu cổ phiếu được sang tay. Một cây nến tăng mạnh mà khối lượng thấp thì ít ý nghĩa hơn
            hẳn so với nến tăng kèm khối lượng lớn.
          </li>
        </ul>
      </Section>

      <Section id="chi-bao" title="3. Chỉ báo kỹ thuật">
        <p>
          Chỉ báo kỹ thuật được tính từ chính dữ liệu giá và khối lượng trong quá khứ. Chúng mô tả
          trạng thái hiện tại của thị trường, <strong className="text-neutral-100">không dự đoán</strong>{" "}
          tương lai. Một chỉ báo đơn lẻ gần như luôn cho tín hiệu nhiễu — chúng chỉ có giá trị khi
          nhiều chỉ báo cùng nói một hướng và phù hợp với bối cảnh chung.
        </p>
        <SignalTable rows={TECHNICAL} />
      </Section>

      <Section id="chi-so" title="4. Chỉ số cơ bản của doanh nghiệp">
        <p>
          Nhóm chỉ số này nói về sức khoẻ doanh nghiệp chứ không phải diễn biến giá. Chúng thay đổi
          theo quý, phù hợp cho quyết định nắm giữ dài hạn hơn là mua bán ngắn hạn.
        </p>
        <SignalTable rows={FUNDAMENTAL} />
      </Section>

      <Section id="yeu-to" title="5. Điều gì làm giá cổ phiếu thay đổi">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {[
            {
              t: "Bản thân doanh nghiệp",
              items: [
                "Báo cáo tài chính quý — thường là cú hích lớn nhất",
                "Chia cổ tức, phát hành thêm cổ phiếu (pha loãng sở hữu)",
                "Thay đổi ban lãnh đạo, ký hợp đồng lớn, mở rộng ngành nghề",
                "Tin tiêu cực: kiện tụng, sai phạm, lãnh đạo bán ra lượng lớn",
              ],
            },
            {
              t: "Kinh tế vĩ mô Việt Nam",
              items: [
                "Lãi suất — lãi suất giảm thường có lợi cho chứng khoán, vì tiền gửi kém hấp dẫn hơn",
                "Lạm phát và tỷ giá USD/VND",
                "Tăng trưởng GDP, chính sách tài khoá, đầu tư công",
                "Chính sách riêng từng ngành (bất động sản, ngân hàng, điện...)",
              ],
            },
            {
              t: "Yếu tố quốc tế",
              items: [
                "Lãi suất của Fed và diễn biến chứng khoán Mỹ",
                "Giá dầu, giá thép, giá hàng hoá — tác động trực tiếp lên từng ngành",
                "Kinh tế Trung Quốc, căng thẳng thương mại, thuế quan xuất khẩu",
              ],
            },
            {
              t: "Đặc thù thị trường Việt Nam",
              items: [
                "Khối ngoại mua/bán ròng — quy mô nhỏ nhưng ảnh hưởng tâm lý lớn",
                "Dư nợ margin (vay tiền để mua) cao làm thị trường dễ bị bán tháo dây chuyền",
                "Kỳ cơ cấu rổ chỉ số VN30, các quỹ ETF ngoại",
                "Câu chuyện nâng hạng thị trường từ cận biên lên mới nổi",
                "Tâm lý đám đông — thị trường nhiều nhà đầu tư cá nhân nên biến động cảm tính mạnh",
              ],
            },
          ].map((g) => (
            <div key={g.t} className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
              <div className="mb-2 text-sm font-semibold text-neutral-100">{g.t}</div>
              <ul className="ml-4 list-disc space-y-1 text-xs leading-relaxed text-neutral-400">
                {g.items.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      <Section id="sai-lam" title="6. Sai lầm phổ biến của người mới">
        <ul className="ml-5 list-disc space-y-2">
          <li>
            <strong className="text-neutral-100">Mua vì giá đang tăng mạnh.</strong> Khi một mã đã lên
            mặt báo và các hội nhóm bàn tán, phần lớn mức tăng thường đã diễn ra rồi.
          </li>
          <li>
            <strong className="text-neutral-100">Trung bình giá xuống không có kế hoạch.</strong> Mã
            giảm rồi mua thêm để “gỡ vốn” là cách nhanh nhất biến khoản lỗ nhỏ thành khoản lỗ lớn, nếu
            lý do giảm là doanh nghiệp thực sự xấu đi.
          </li>
          <li>
            <strong className="text-neutral-100">Dồn hết tiền vào một mã.</strong> Dù phân tích kỹ tới
            đâu, luôn có những thứ không lường trước được.
          </li>
          <li>
            <strong className="text-neutral-100">Dùng margin khi chưa hiểu rõ.</strong> Vay để mua
            khuếch đại cả lãi lẫn lỗ, và khi giá giảm tới ngưỡng, công ty chứng khoán bán giải chấp
            không cần hỏi bạn.
          </li>
          <li>
            <strong className="text-neutral-100">Không đặt trước điểm dừng.</strong> Quyết định bán khi
            đang hoảng loạn hầu như luôn tệ hơn quyết định đặt ra lúc đầu óc còn tỉnh táo.
          </li>
          <li>
            <strong className="text-neutral-100">Nhầm chỉ báo với lời tiên tri.</strong> Chỉ báo mô tả
            những gì đã xảy ra. Không có chỉ báo nào biết trước tin tức ngày mai.
          </li>
        </ul>
      </Section>

      <Section id="gioi-han" title="7. Công cụ này KHÔNG nói lên điều gì">
        <p>
          Để bạn dùng dashboard đúng mức, đây là những giới hạn thật của nó:
        </p>
        <ul className="ml-5 list-disc space-y-2">
          <li>
            <strong className="text-neutral-100">Điểm chấm cổ phiếu</strong> chỉ là trung bình cộng của
            ba yếu tố kỹ thuật (xu hướng, thanh khoản, biến động). Nó{" "}
            <strong>không xét tới</strong> sức khoẻ tài chính, ngành nghề hay tin tức. Điểm 8/10 nghĩa
            là đồ thị đang đẹp, không có nghĩa là doanh nghiệp tốt.
          </li>
          <li>
            <strong className="text-neutral-100">Dự đoán AI</strong> là mô hình Random Forest học từ
            dữ liệu giá quá khứ, đưa ra xác suất tăng cho phiên kế tiếp. Độ chính xác thực tế trên thị
            trường Việt Nam <strong>chưa được kiểm chứng</strong>. Con số 70% không có nghĩa là bạn sẽ
            thắng 7 trên 10 lần — hãy coi nó như một góc nhìn tham khảo, không phải khuyến nghị.
          </li>
          <li>
            <strong className="text-neutral-100">Dữ liệu</strong> lấy từ nguồn cộng đồng (vnstock/VCI),
            không phải dữ liệu chính thức từ HOSE, và có độ trễ. Giá trong phiên trên app này có thể
            chậm 5–20 phút so với bảng giá của công ty chứng khoán.
          </li>
          <li>
            <strong className="text-neutral-100">Danh mục ảo</strong> bỏ qua phí, thuế và T+2 nên kết
            quả luôn đẹp hơn giao dịch thật.
          </li>
        </ul>
        <p className="rounded-md border border-neutral-700 bg-neutral-900 p-3 text-xs text-neutral-400">
          Toàn bộ nội dung trang này nhằm mục đích tìm hiểu kiến thức, không phải khuyến nghị đầu tư.
          Đầu tư chứng khoán có rủi ro mất vốn. Hãy tự tìm hiểu kỹ và cân nhắc tham khảo ý kiến chuyên
          gia được cấp phép trước khi quyết định bằng tiền thật.
        </p>
      </Section>

      <div className="flex flex-wrap gap-3 border-t border-neutral-800 pt-5 text-sm">
        <Link href="/" className="text-emerald-400 hover:underline">
          ← Xem danh sách mã
        </Link>
        <Link href="/portfolio" className="text-emerald-400 hover:underline">
          Thử giao dịch bằng tiền ảo →
        </Link>
      </div>
    </div>
  );
}
