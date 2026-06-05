import csv
import io
import re
import zipfile
from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="우체국 느낌 주소록", page_icon="📮", layout="wide")

DATA_FILE = Path("address_book.csv")
FIELDS = ["분류", "이름", "전화번호", "우편번호", "주소", "수량", "상품명", "배송메세지", "메모"]
CATEGORIES = ["지인", "거래처"]

CJ_HEADERS = [
    "번호", "묶음배송번호", "주문번호", "택배사", "운송장번호", "분리배송 Y/N", "분리배송 출고예정일",
    "주문시 출고예정일", "출고일(발송일)", "주문일", "등록상품명", "등록옵션명", "노출상품명(옵션명)",
    "노출상품ID", "옵션ID", "최초등록등록상품명/옵션명", "업체상품코드", "바코드", "결제액", "배송비구분",
    "배송비", "도서산간 추가배송비", "구매수(수량)", "옵션판매가(판매단가)", "구매자", "구매자전화번호",
    "수취인이름", "수취인전화번호", "우편번호", "수취인 주소", "배송메세지", "상품별 추가메시지", "주문자 추가메시지",
    "배송완료일", "구매확정일자", "개인통관번호(PCCC)", "통관용수취인전화번호", "기타", "결제위치", "배송유형"
]


def css():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #fffaf3 0%, #fffdf8 100%);
        }
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        .hero-card {
            background: linear-gradient(135deg, #fff7ec 0%, #fff0d9 55%, #ffe4bd 100%);
            border: 1px solid #efc98f;
            border-radius: 24px;
            padding: 1.2rem 1.4rem;
            box-shadow: 0 10px 26px rgba(181, 102, 21, 0.10);
            margin-bottom: 1rem;
        }
        .hero-top {
            display:flex; gap: 18px; align-items:center;
        }
        .hero-illust {
            width: 112px; height: 112px; border-radius: 20px;
            background: linear-gradient(135deg, #ffedd3 0%, #fff9ee 100%);
            display:flex; align-items:center; justify-content:center;
            font-size: 54px; border:1px solid #efc98f;
            flex: 0 0 112px;
        }
        .hero-title {
            font-weight: 800; font-size: 1.9rem; color: #6a3f06; margin-bottom: 4px;
        }
        .hero-sub {
            color: #8a5a1f; font-size: 1rem; line-height: 1.5;
        }
        .stamp-row { margin-top: 10px; display:flex; gap:8px; flex-wrap:wrap; }
        .stamp {
            display:inline-block; background:#fff; color:#9a6117; border:1px dashed #d29b55;
            border-radius:999px; padding:6px 12px; font-size:0.88rem; font-weight:700;
        }
        div[data-testid="stMetric"] {
            background: #fffaf0; border:1px solid #f0d8a8; border-radius: 18px; padding: 10px 14px;
        }
        div[data-testid="stForm"] {
            background: rgba(255,255,255,0.82); border:1px solid #efdfc0; border-radius: 20px; padding: 12px;
        }
        div.stButton > button, div.stDownloadButton > button {
            border-radius: 14px; border: 1px solid #d39a52; background: linear-gradient(180deg, #fff8ee 0%, #ffe8c2 100%);
            color: #6b4008; font-weight: 700;
        }
        div.stButton > button:hover, div.stDownloadButton > button:hover {
            border-color:#b97c2f; color:#5d3504;
        }
        .folder-chip {
            display:inline-block; padding:4px 10px; margin-right:6px; border-radius:999px;
            background:#fff7ea; border:1px solid #efcf97; color:#8b5a16; font-weight:700; font-size:0.83rem;
        }
        .card {
            background:#ffffffd9; border:1px solid #efe1c5; border-radius:18px; padding:14px 16px; margin-bottom:12px;
            box-shadow: 0 4px 14px rgba(80, 56, 14, 0.05);
        }
        .small-note { color:#8a6b3d; font-size:0.92rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero():
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-top">
                <div class="hero-illust">📮</div>
                <div>
                    <div class="hero-title">우체국 느낌 주소록 · CJ택배 엑셀</div>
                    <div class="hero-sub">
                        지인 / 거래처를 폴더처럼 따로 관리하고, 이름 · 주소 · 전화번호 · 수량 · 상품명을 저장한 뒤<br>
                        필요한 사람만 골라 바로 CJ택배 업로드용 엑셀로 내려받을 수 있게 만든 심플한 앱입니다.
                    </div>
                    <div class="stamp-row">
                        <span class="stamp">📁 지인 폴더</span>
                        <span class="stamp">🏢 거래처 폴더</span>
                        <span class="stamp">✍️ 상품명 직접 입력</span>
                        <span class="stamp">🚚 CJ 양식 다운로드</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def s(value):
    return "" if value is None else str(value).strip()


def phone(value):
    text = s(value)
    digits = re.sub(r"[^0-9]", "", text)
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10 and digits.startswith("02"):
        return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return text


def qty(value):
    try:
        return max(1, int(float(s(value) or 1)))
    except Exception:
        return 1


def ensure_category(value):
    value = s(value)
    return value if value in CATEGORIES else "지인"


def load_rows():
    if not DATA_FILE.exists():
        return []
    rows = []
    with DATA_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = {k: s(row.get(k, "")) for k in FIELDS}
            # 옛 버전 호환
            item["분류"] = ensure_category(row.get("분류", item.get("분류", "지인")))
            item["전화번호"] = phone(item.get("전화번호", ""))
            item["수량"] = str(qty(item.get("수량", 1)))
            item["상품명"] = item.get("상품명") or ""
            item["배송메세지"] = item.get("배송메세지") or "문 앞"
            rows.append(item)
    return rows


def save_rows(rows):
    with DATA_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            item = {k: s(row.get(k, "")) for k in FIELDS}
            item["분류"] = ensure_category(item.get("분류"))
            item["전화번호"] = phone(item.get("전화번호", ""))
            item["수량"] = str(qty(item.get("수량", 1)))
            writer.writerow(item)


def load_state():
    if "rows" not in st.session_state:
        st.session_state.rows = load_rows()


def save_state():
    save_rows(st.session_state.rows)


def col_name(n):
    result = ""
    while n:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def xml_cell(row_idx, col_idx, value):
    cell_ref = f"{col_name(col_idx)}{row_idx}"
    if value is None:
        value = ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{cell_ref}"><v>{value}</v></c>'
    text = escape(str(value), quote=False)
    return f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def make_xlsx(sheet_name, table):
    rows_xml = []
    for r_idx, row in enumerate(table, start=1):
        cells = "".join(xml_cell(r_idx, c_idx, value) for c_idx, value in enumerate(row, start=1))
        rows_xml.append(f'<row r="{r_idx}">{cells}</row>')

    max_col = col_name(len(table[0]) if table else 1)
    max_row = len(table) if table else 1
    dimension = f"A1:{max_col}{max_row}"

    worksheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<dimension ref="{dimension}"/>
<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
<sheetData>{''.join(rows_xml)}</sheetData>
</worksheet>'''

    workbook = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''

    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="1"><fill><patternFill patternType="none"/></fill></fills>
<borders count="1"><border/></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''

    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''

    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/worksheets/sheet1.xml", worksheet)
        z.writestr("xl/styles.xml", styles)
    bio.seek(0)
    return bio.getvalue()


def make_cj_table(rows):
    today = datetime.now().strftime("%Y-%m-%d")
    order_date = datetime.now().strftime("%Y%m%d")
    table = [CJ_HEADERS]
    for i, row in enumerate(rows, start=1):
        product = s(row.get("상품명"))
        amount = qty(row.get("수량"))
        data = {h: "" for h in CJ_HEADERS}
        data["번호"] = i
        data["주문번호"] = f"ADDR-{order_date}-{i:04d}"
        data["택배사"] = "CJ대한통운"
        data["주문일"] = today
        data["등록상품명"] = product
        data["노출상품명(옵션명)"] = product
        data["구매수(수량)"] = amount
        data["구매자"] = s(row.get("이름"))
        data["구매자전화번호"] = phone(row.get("전화번호"))
        data["수취인이름"] = s(row.get("이름"))
        data["수취인전화번호"] = phone(row.get("전화번호"))
        data["우편번호"] = s(row.get("우편번호"))
        data["수취인 주소"] = s(row.get("주소"))
        data["배송메세지"] = s(row.get("배송메세지")) or "문 앞"
        note = s(row.get("메모"))
        category = ensure_category(row.get("분류"))
        data["기타"] = f"[{category}] {note}".strip()
        data["배송유형"] = "일반배송"
        table.append([data[h] for h in CJ_HEADERS])
    return table


def make_address_csv(rows):
    bio = io.StringIO()
    writer = csv.DictWriter(bio, fieldnames=FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: s(row.get(k, "")) for k in FIELDS})
    return bio.getvalue().encode("utf-8-sig")


def import_csv(uploaded_file):
    raw = uploaded_file.getvalue()
    text = raw.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    imported = []
    for row in reader:
        item = {k: s(row.get(k, "")) for k in FIELDS}
        item["분류"] = ensure_category(item.get("분류") or row.get("폴더") or row.get("구분") or "지인")
        item["이름"] = item["이름"] or s(row.get("수취인이름", "")) or s(row.get("받는분", ""))
        item["전화번호"] = phone(item["전화번호"] or row.get("수취인전화번호", "") or row.get("연락처", ""))
        item["우편번호"] = item["우편번호"] or s(row.get("우편번호", ""))
        item["주소"] = item["주소"] or s(row.get("수취인 주소", "")) or s(row.get("주소", ""))
        item["수량"] = str(qty(item["수량"] or row.get("구매수(수량)", "1")))
        item["상품명"] = item["상품명"] or s(row.get("등록상품명", ""))
        item["배송메세지"] = item["배송메세지"] or s(row.get("배송메세지", "")) or "문 앞"
        item["메모"] = item["메모"] or s(row.get("기타", ""))
        if item["이름"] and item["주소"]:
            imported.append(item)
    return imported


def row_matches(row, keyword, category):
    text = " ".join(s(row.get(k, "")) for k in FIELDS).lower()
    keyword_ok = (not keyword) or (keyword.lower() in text)
    category_ok = (category == "전체") or (ensure_category(row.get("분류")) == category)
    return keyword_ok and category_ok


def main():
    password = ""
    try:
        password = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        password = ""

    if password:
        typed = st.text_input("비밀번호", type="password")
        if typed != password:
            st.stop()

    css()
    hero()
    load_state()

    total = len(st.session_state.rows)
    friend_count = sum(1 for r in st.session_state.rows if ensure_category(r.get("분류")) == "지인")
    vendor_count = sum(1 for r in st.session_state.rows if ensure_category(r.get("분류")) == "거래처")

    m1, m2, m3 = st.columns(3)
    m1.metric("전체 주소", total)
    m2.metric("지인 폴더", friend_count)
    m3.metric("거래처 폴더", vendor_count)

    with st.sidebar:
        st.subheader("백업 / 가져오기")
        st.download_button(
            "주소록 CSV 백업",
            data=make_address_csv(st.session_state.rows),
            file_name="address_book_backup.csv",
            mime="text/csv",
            use_container_width=True,
        )
        uploaded = st.file_uploader("CSV 가져오기", type=["csv"])
        if uploaded is not None and st.button("가져오기 실행", use_container_width=True):
            new_rows = import_csv(uploaded)
            st.session_state.rows.extend(new_rows)
            save_state()
            st.success(f"{len(new_rows)}건 가져옴")
            st.rerun()
        st.caption("예전 버전 CSV도 대부분 자동 인식합니다.")

    tab_add, tab_list, tab_export = st.tabs(["📮 주소 등록", "📁 지인 / 거래처", "🚚 CJ 엑셀 다운로드"])

    with tab_add:
        left, right = st.columns([1.05, 0.95])
        with left:
            st.subheader("새 주소 추가")
            with st.form("add_form", clear_on_submit=True):
                category = st.radio("폴더", CATEGORIES, horizontal=True)
                name = st.text_input("이름")
                tel = st.text_input("전화번호", placeholder="010-0000-0000")
                zipcode = st.text_input("우편번호")
                address = st.text_area("주소", height=120)
                q = st.number_input("수량", min_value=1, value=1, step=1)
                product = st.text_input("상품명", placeholder="예: 식혜 1L 2박스 / 호박감주 1L")
                message = st.text_input("배송메세지", value="문 앞")
                memo = st.text_area("메모", height=110)
                submitted = st.form_submit_button("저장", use_container_width=True)
                if submitted:
                    if not name or not address:
                        st.error("이름과 주소는 필수입니다.")
                    else:
                        st.session_state.rows.append({
                            "분류": category,
                            "이름": name,
                            "전화번호": phone(tel),
                            "우편번호": zipcode,
                            "주소": address,
                            "수량": str(q),
                            "상품명": product,
                            "배송메세지": message,
                            "메모": memo,
                        })
                        save_state()
                        st.success("저장 완료")
                        st.rerun()
        with right:
            st.subheader("빠른 안내")
            st.markdown(
                """
                <div class="card">
                    <div class="folder-chip">우체국 느낌 UI</div>
                    <div class="folder-chip">직접 상품명 입력</div>
                    <div class="folder-chip">지인 / 거래처 폴더 분리</div>
                    <p class="small-note" style="margin-top:10px;">
                    • 상품명은 이제 드롭다운이 아니라 자유롭게 입력됩니다.<br>
                    • 지인 / 거래처는 폴더처럼 나뉘어 따로 조회할 수 있습니다.<br>
                    • 저장한 데이터는 같은 저장소의 <b>address_book.csv</b>에 자동 저장됩니다.<br>
                    • 엑셀 다운로드 때는 선택한 주소만 CJ 업로드 양식으로 만들어집니다.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.info("원하면 다음 버전에서 실제 AI 일러스트 배너 이미지도 따로 넣어줄 수 있어요.")

    with tab_list:
        st.subheader("주소록 관리")
        filter_col1, filter_col2 = st.columns([1, 1.4])
        with filter_col1:
            folder_filter = st.radio("폴더 보기", ["전체", "지인", "거래처"], horizontal=True)
        with filter_col2:
            keyword = st.text_input("검색", placeholder="이름 / 전화번호 / 주소 / 상품명")

        filtered = [(i, r) for i, r in enumerate(st.session_state.rows) if row_matches(r, keyword, folder_filter)]
        st.caption(f"현재 표시: {len(filtered)}건")

        if st.session_state.rows:
            labels = []
            index_map = {}
            for real_idx, row in filtered if filtered else []:
                label = f"[{ensure_category(row.get('분류'))}] {row.get('이름','')} / {row.get('전화번호','')} / 수량 {row.get('수량','1')}"
                labels.append(label)
                index_map[label] = real_idx

            if labels:
                selected_label = st.selectbox("수정할 주소 선택", labels)
                edit_idx = index_map[selected_label]
                row = st.session_state.rows[edit_idx]
                with st.form("edit_form"):
                    e_category = st.radio("폴더 ", CATEGORIES, index=CATEGORIES.index(ensure_category(row.get("분류"))), horizontal=True)
                    e_name = st.text_input("이름 ", value=row.get("이름", ""))
                    e_tel = st.text_input("전화번호 ", value=row.get("전화번호", ""))
                    e_zip = st.text_input("우편번호 ", value=row.get("우편번호", ""))
                    e_addr = st.text_area("주소 ", value=row.get("주소", ""), height=120)
                    e_q = st.number_input("수량 ", min_value=1, value=qty(row.get("수량", 1)), step=1)
                    e_product = st.text_input("상품명 ", value=row.get("상품명", ""))
                    e_msg = st.text_input("배송메세지 ", value=row.get("배송메세지", "문 앞"))
                    e_memo = st.text_area("메모 ", value=row.get("메모", ""), height=110)
                    c1, c2 = st.columns(2)
                    update = c1.form_submit_button("수정 저장", use_container_width=True)
                    delete = c2.form_submit_button("삭제", use_container_width=True)
                    if update:
                        st.session_state.rows[edit_idx] = {
                            "분류": e_category,
                            "이름": e_name,
                            "전화번호": phone(e_tel),
                            "우편번호": e_zip,
                            "주소": e_addr,
                            "수량": str(e_q),
                            "상품명": e_product,
                            "배송메세지": e_msg,
                            "메모": e_memo,
                        }
                        save_state()
                        st.success("수정 완료")
                        st.rerun()
                    if delete:
                        st.session_state.rows.pop(edit_idx)
                        save_state()
                        st.success("삭제 완료")
                        st.rerun()
            else:
                st.info("필터 조건에 맞는 주소가 없습니다.")

            st.markdown("---")
            st.subheader("주소록 목록")
            if filtered:
                for _, row in filtered:
                    category = ensure_category(row.get("분류"))
                    st.markdown(
                        f"""
                        <div class="card">
                            <div class="folder-chip">{category}</div>
                            <b>{escape(s(row.get('이름')))}</b> &nbsp;&nbsp; {escape(s(row.get('전화번호')))} &nbsp;&nbsp; 수량 {escape(s(row.get('수량')))}<br>
                            <span class="small-note">상품명:</span> {escape(s(row.get('상품명')))}<br>
                            <span class="small-note">주소:</span> {escape(s(row.get('우편번호')))} {escape(s(row.get('주소')))}<br>
                            <span class="small-note">배송메세지:</span> {escape(s(row.get('배송메세지')))}<br>
                            <span class="small-note">메모:</span> {escape(s(row.get('메모')))}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("표시할 주소가 없습니다.")
        else:
            st.info("아직 등록된 주소가 없습니다.")

    with tab_export:
        st.subheader("CJ택배 엑셀 다운로드")
        exp_col1, exp_col2 = st.columns([1, 1.3])
        with exp_col1:
            export_folder = st.radio("내보낼 폴더", ["전체", "지인", "거래처"], horizontal=True)
        with exp_col2:
            export_keyword = st.text_input("내보내기 검색", placeholder="이름 / 주소 / 상품명")

        export_rows = [(i, r) for i, r in enumerate(st.session_state.rows) if row_matches(r, export_keyword, export_folder)]
        export_labels = [f"[{ensure_category(r.get('분류'))}] {r.get('이름','')} / {r.get('전화번호','')} / 수량 {r.get('수량','1')} / {r.get('상품명','')}" for _, r in export_rows]

        if export_labels:
            chosen = st.multiselect("보낼 사람 선택", export_labels, default=export_labels)
            chosen_rows = [export_rows[export_labels.index(label)][1] for label in chosen]
            st.write(f"선택된 발송 건수: **{len(chosen_rows)}건**")
            xlsx_bytes = make_xlsx("Delivery", make_cj_table(chosen_rows))
            st.download_button(
                "CJ택배 엑셀 다운로드",
                data=xlsx_bytes,
                file_name=f"CJ_DeliveryList_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                disabled=not chosen_rows,
            )
        else:
            st.info("내보낼 대상이 없습니다.")


if __name__ == "__main__":
    main()
