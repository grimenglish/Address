import csv
import io
import os
import re
import zipfile
from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="주소록 CJ택배 엑셀", layout="wide")

DATA_FILE = Path("address_book.csv")
FIELDS = ["이름", "전화번호", "우편번호", "주소", "수량", "상품명", "배송메세지", "메모"]

CJ_HEADERS = [
    "번호", "묶음배송번호", "주문번호", "택배사", "운송장번호", "분리배송 Y/N", "분리배송 출고예정일",
    "주문시 출고예정일", "출고일(발송일)", "주문일", "등록상품명", "등록옵션명", "노출상품명(옵션명)",
    "노출상품ID", "옵션ID", "최초등록등록상품명/옵션명", "업체상품코드", "바코드", "결제액", "배송비구분",
    "배송비", "도서산간 추가배송비", "구매수(수량)", "옵션판매가(판매단가)", "구매자", "구매자전화번호",
    "수취인이름", "수취인전화번호", "우편번호", "수취인 주소", "배송메세지", "상품별 추가메시지", "주문자 추가메시지",
    "배송완료일", "구매확정일자", "개인통관번호(PCCC)", "통관용수취인전화번호", "기타", "결제위치", "배송유형"
]

DEFAULT_PRODUCTS = ["일반식혜 1L", "단호박식혜 1L", "기타"]


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


def load_rows():
    if not DATA_FILE.exists():
        return []
    rows = []
    with DATA_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = {k: s(row.get(k, "")) for k in FIELDS}
            item["전화번호"] = phone(item["전화번호"])
            item["수량"] = str(qty(item["수량"]))
            item["상품명"] = item["상품명"] or "일반식혜 1L"
            item["배송메세지"] = item["배송메세지"] or "문 앞"
            rows.append(item)
    return rows


def save_rows(rows):
    with DATA_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            item = {k: s(row.get(k, "")) for k in FIELDS}
            item["전화번호"] = phone(item["전화번호"])
            item["수량"] = str(qty(item["수량"]))
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
    # 외부 라이브러리 없이 만드는 기본 xlsx. Streamlit Cloud에서 설치 오류를 줄이기 위함.
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
    table = [CJ_HEADERS]
    for i, row in enumerate(rows, start=1):
        product = s(row.get("상품명")) or "일반식혜 1L"
        amount = qty(row.get("수량"))
        data = {h: "" for h in CJ_HEADERS}
        data["번호"] = i
        data["주문번호"] = f"ADDR-{datetime.now().strftime('%Y%m%d')}-{i:04d}"
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
        data["기타"] = s(row.get("메모"))
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
        # 다른 이름의 컬럼도 최대한 자동 인식
        item["이름"] = item["이름"] or s(row.get("수취인이름", "")) or s(row.get("받는분", ""))
        item["전화번호"] = phone(item["전화번호"] or row.get("수취인전화번호", "") or row.get("연락처", ""))
        item["우편번호"] = item["우편번호"] or s(row.get("우편번호", ""))
        item["주소"] = item["주소"] or s(row.get("수취인 주소", "")) or s(row.get("주소", ""))
        item["수량"] = str(qty(item["수량"] or row.get("구매수(수량)", "1")))
        item["상품명"] = item["상품명"] or s(row.get("등록상품명", "")) or "일반식혜 1L"
        item["배송메세지"] = item["배송메세지"] or s(row.get("배송메세지", "")) or "문 앞"
        if item["이름"] and item["주소"]:
            imported.append(item)
    return imported


# 비밀번호는 Streamlit Secrets에 APP_PASSWORD가 있을 때만 적용
password = ""
try:
    password = st.secrets.get("APP_PASSWORD", "")
except Exception:
    password = ""

if password:
    typed = st.text_input("비밀번호", type="password")
    if typed != password:
        st.stop()

load_state()

st.title("주소록 관리 + CJ택배 엑셀 다운로드")
st.caption("이름 / 주소 / 전화번호 / 수량을 저장하고, 보낼 사람만 골라 CJ택배 업로드용 엑셀로 받을 수 있습니다.")

with st.sidebar:
    st.subheader("현재 주소록")
    st.metric("총 등록", len(st.session_state.rows))
    search = st.text_input("검색", placeholder="이름, 전화번호, 주소")

    st.divider()
    st.subheader("백업")
    st.download_button(
        "주소록 CSV 백업",
        data=make_address_csv(st.session_state.rows),
        file_name="address_book_backup.csv",
        mime="text/csv",
        use_container_width=True,
    )
    uploaded = st.file_uploader("CSV 가져오기", type=["csv"])
    if uploaded is not None:
        if st.button("가져오기 실행", use_container_width=True):
            new_rows = import_csv(uploaded)
            st.session_state.rows.extend(new_rows)
            save_state()
            st.success(f"{len(new_rows)}건 가져옴")
            st.rerun()

query = search.strip().lower()
filtered = []
for idx, row in enumerate(st.session_state.rows):
    text = " ".join(s(row.get(k, "")) for k in FIELDS).lower()
    if not query or query in text:
        filtered.append((idx, row))

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("새 주소 추가")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("이름")
        tel = st.text_input("전화번호", placeholder="010-0000-0000")
        zipcode = st.text_input("우편번호")
        address = st.text_area("주소")
        q = st.number_input("수량", min_value=1, value=1, step=1)
        product = st.selectbox("상품명", DEFAULT_PRODUCTS)
        message = st.text_input("배송메세지", value="문 앞")
        memo = st.text_area("메모")
        submitted = st.form_submit_button("저장", use_container_width=True)
        if submitted:
            if not name or not address:
                st.error("이름과 주소는 필수")
            else:
                st.session_state.rows.append({
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

with col2:
    st.subheader("수정 / 삭제")
    if st.session_state.rows:
        labels = [f"{i+1}. {r['이름']} / {r['전화번호']} / {r['주소'][:25]}" for i, r in enumerate(st.session_state.rows)]
        selected_label = st.selectbox("수정할 주소 선택", labels)
        edit_idx = labels.index(selected_label)
        row = st.session_state.rows[edit_idx]
        with st.form("edit_form"):
            e_name = st.text_input("이름 ", value=row.get("이름", ""))
            e_tel = st.text_input("전화번호 ", value=row.get("전화번호", ""))
            e_zip = st.text_input("우편번호 ", value=row.get("우편번호", ""))
            e_addr = st.text_area("주소 ", value=row.get("주소", ""))
            e_q = st.number_input("수량 ", min_value=1, value=qty(row.get("수량", 1)), step=1)
            e_product = st.text_input("상품명 ", value=row.get("상품명", "일반식혜 1L"))
            e_msg = st.text_input("배송메세지 ", value=row.get("배송메세지", "문 앞"))
            e_memo = st.text_area("메모 ", value=row.get("메모", ""))
            c1, c2 = st.columns(2)
            update = c1.form_submit_button("수정 저장", use_container_width=True)
            delete = c2.form_submit_button("삭제", use_container_width=True)
            if update:
                st.session_state.rows[edit_idx] = {
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
        st.info("아직 등록된 주소가 없음")

st.divider()
st.subheader("CJ택배 엑셀 다운로드")

if filtered:
    export_labels = [f"{idx+1}. {row['이름']} / {row['전화번호']} / 수량 {row['수량']}" for idx, row in filtered]
    chosen = st.multiselect("보낼 사람 선택", export_labels, default=export_labels)
    chosen_rows = [filtered[export_labels.index(label)][1] for label in chosen]

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
    st.info("검색 결과가 없거나 주소록이 비어 있음")

st.divider()
st.subheader("주소록 목록")
if filtered:
    for idx, row in filtered:
        st.markdown(
            f"**{idx+1}. {row['이름']}**  |  {row['전화번호']}  |  수량 {row['수량']}  |  {row['상품명']}  \n\n"
            f"{row['우편번호']} {row['주소']}  \n\n"
            f"배송메세지: {row['배송메세지']} / 메모: {row['메모']}"
        )
        st.divider()
else:
    st.info("표시할 주소가 없음")
