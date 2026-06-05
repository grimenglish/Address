import csv
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from html import escape

import streamlit as st

st.set_page_config(page_title="식혜명가 주소록 즐겨찾기", page_icon="📮", layout="wide")

FIELDS_KR = ["분류", "이름", "전화번호", "우편번호", "주소", "수량", "상품명", "배송메세지", "메모"]
CATEGORIES = ["지인", "거래처"]

CJ_HEADERS = [
    "번호", "묶음배송번호", "주문번호", "택배사", "운송장번호", "분리배송 Y/N", "분리배송 출고예정일",
    "주문시 출고예정일", "출고일(발송일)", "주문일", "등록상품명", "등록옵션명", "노출상품명(옵션명)",
    "노출상품ID", "옵션ID", "최초등록등록상품명/옵션명", "업체상품코드", "바코드", "결제액", "배송비구분",
    "배송비", "도서산간 추가배송비", "구매수(수량)", "옵션판매가(판매단가)", "구매자", "구매자전화번호",
    "수취인이름", "수취인전화번호", "우편번호", "수취인 주소", "배송메세지", "상품별 추가메시지", "주문자 추가메시지",
    "배송완료일", "구매확정일자", "개인통관번호(PCCC)", "통관용수취인전화번호", "기타", "결제위치", "배송유형"
]


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


def category(value):
    value = s(value)
    return value if value in CATEGORIES else "지인"


def get_secret(name, default=""):
    try:
        return s(st.secrets.get(name, default))
    except Exception:
        return default


def supabase_base_url():
    url = get_secret("SUPABASE_URL")
    url = url.rstrip("/")
    url = url.replace("/rest/v1", "")
    return url


def supabase_key():
    return get_secret("SUPABASE_KEY")


def api_request(method, table_path, payload=None, query=""):
    base = supabase_base_url()
    key = supabase_key()
    if not base or not key:
        raise RuntimeError("Streamlit Secrets에 SUPABASE_URL, SUPABASE_KEY가 필요합니다.")

    url = f"{base}/rest/v1/{table_path}{query}"
    data = None
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if method in ["POST", "PATCH", "DELETE"]:
        headers["Prefer"] = "return=representation"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return []
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Supabase 오류 {e.code}: {body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Supabase 연결 오류: {e}")


@st.cache_data(ttl=5)
def fetch_rows():
    q = "?select=*&order=created_at.desc,id.desc"
    rows = api_request("GET", "addresses", query=q)
    return rows if isinstance(rows, list) else []


def clear_cache():
    fetch_rows.clear()


def insert_row(row):
    payload = {
        "category": category(row.get("category")),
        "name": s(row.get("name")),
        "phone": phone(row.get("phone")),
        "zipcode": s(row.get("zipcode")),
        "address": s(row.get("address")),
        "quantity": qty(row.get("quantity")),
        "product_name": s(row.get("product_name")),
        "delivery_message": s(row.get("delivery_message")) or "문 앞",
        "memo": s(row.get("memo")),
    }
    result = api_request("POST", "addresses", payload=payload)
    clear_cache()
    return result


def update_row(row_id, row):
    payload = {
        "category": category(row.get("category")),
        "name": s(row.get("name")),
        "phone": phone(row.get("phone")),
        "zipcode": s(row.get("zipcode")),
        "address": s(row.get("address")),
        "quantity": qty(row.get("quantity")),
        "product_name": s(row.get("product_name")),
        "delivery_message": s(row.get("delivery_message")) or "문 앞",
        "memo": s(row.get("memo")),
    }
    q = f"?id=eq.{urllib.parse.quote(str(row_id))}"
    result = api_request("PATCH", "addresses", payload=payload, query=q)
    clear_cache()
    return result


def delete_row(row_id):
    q = f"?id=eq.{urllib.parse.quote(str(row_id))}"
    result = api_request("DELETE", "addresses", query=q)
    clear_cache()
    return result


def css():
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(180deg, #fffaf3 0%, #fffdf8 100%); }
        .main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1220px; }
        .hero-card {
            background: linear-gradient(135deg, #fff8ed 0%, #fff0d8 55%, #ffe2b0 100%);
            border: 1px solid #e9c17d; border-radius: 26px; padding: 1.1rem 1.25rem;
            box-shadow: 0 10px 28px rgba(142, 85, 17, 0.11); margin-bottom: 1rem;
        }
        .hero-grid { display:grid; grid-template-columns: 180px 1fr; gap:20px; align-items:center; }
        .hero-title { font-weight: 900; font-size: 1.9rem; color:#653b05; margin-bottom:6px; }
        .hero-sub { color:#85571a; line-height:1.55; font-size:1rem; }
        .stamp { display:inline-block; margin:9px 6px 0 0; padding:6px 12px; border-radius:999px; background:white; border:1px dashed #c99042; color:#80500d; font-weight:800; font-size:.86rem; }
        .card { background:#ffffffd9; border:1px solid #efe1c5; border-radius:18px; padding:14px 16px; margin-bottom:12px; box-shadow: 0 4px 14px rgba(80,56,14,.05); }
        .folder-chip { display:inline-block; padding:4px 10px; margin-right:6px; border-radius:999px; background:#fff7ea; border:1px solid #efcf97; color:#8b5a16; font-weight:800; font-size:.83rem; }
        .small-note { color:#8a6b3d; font-size:.92rem; }
        div[data-testid="stMetric"] { background:#fffaf0; border:1px solid #f0d8a8; border-radius:18px; padding:10px 14px; }
        div[data-testid="stForm"] { background:rgba(255,255,255,.84); border:1px solid #efdfc0; border-radius:20px; padding:12px; }
        div.stButton > button, div.stDownloadButton > button {
            border-radius:14px; border:1px solid #d39a52; background:linear-gradient(180deg,#fff8ee 0%,#ffe8c2 100%); color:#6b4008; font-weight:800;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero():
    # 파일을 따로 올리지 않도록 app.py 안에 SVG 일러스트를 직접 넣음
    svg = """
    <svg viewBox="0 0 220 160" width="170" height="124" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="delivery illustration">
      <defs>
        <linearGradient id="g1" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#ffe6b7"/><stop offset="1" stop-color="#ffbd63"/></linearGradient>
        <linearGradient id="g2" x1="0" x2="1"><stop offset="0" stop-color="#f8fbff"/><stop offset="1" stop-color="#fff4df"/></linearGradient>
      </defs>
      <rect x="5" y="10" width="210" height="135" rx="28" fill="url(#g2)" stroke="#e2b46f" stroke-width="2"/>
      <circle cx="178" cy="42" r="18" fill="#ffd28b" opacity=".8"/>
      <rect x="28" y="57" width="92" height="56" rx="10" fill="url(#g1)" stroke="#b77420" stroke-width="2"/>
      <rect x="42" y="45" width="65" height="28" rx="8" fill="#fff7e7" stroke="#b77420" stroke-width="2"/>
      <path d="M42 60 L74 83 L107 60" fill="none" stroke="#9a5b0f" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
      <rect x="132" y="70" width="48" height="35" rx="6" fill="#df6b32" stroke="#8a3d12" stroke-width="2"/>
      <path d="M132 80 h48" stroke="#ffdd9b" stroke-width="4"/>
      <path d="M145 70 v35" stroke="#ffdd9b" stroke-width="4"/>
      <rect x="34" y="116" width="118" height="12" rx="6" fill="#6e450d" opacity=".18"/>
      <circle cx="57" cy="130" r="9" fill="#70420a"/><circle cx="151" cy="130" r="9" fill="#70420a"/>
      <path d="M39 130 h125" stroke="#6e450d" stroke-width="6" stroke-linecap="round"/>
      <path d="M169 90 c17 1 24 10 25 23" fill="none" stroke="#8a5617" stroke-width="5" stroke-linecap="round"/>
      <text x="37" y="33" fill="#8a5617" font-size="16" font-weight="700">ADDRESS BOOK</text>
    </svg>
    """
    st.markdown(
        f"""
        <div class="hero-card">
          <div class="hero-grid">
            <div>{svg}</div>
            <div>
              <div class="hero-title">식혜명가 주소록 즐겨찾기</div>
              <div class="hero-sub">
                자주 보내는 지인과 거래처 주소를 즐겨찾기처럼 저장하고, 발송할 때 상품명과 배송메세지를 바로 조정합니다.<br>
                앱을 껐다 켜거나 재배포해도 주소록은 Supabase에 계속 남습니다.
              </div>
              <span class="stamp">📁 지인</span><span class="stamp">🏢 거래처</span><span class="stamp">💾 영구저장</span><span class="stamp">✍️ 발송 전 수정</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="{dimension}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetData>{''.join(rows_xml)}</sheetData></worksheet>'''
    workbook = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs></styleSheet>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
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
        product = s(row.get("product_name"))
        data = {h: "" for h in CJ_HEADERS}
        data["번호"] = i
        data["주문번호"] = f"ADDR-{order_date}-{i:04d}"
        data["택배사"] = "CJ대한통운"
        data["주문일"] = today
        data["등록상품명"] = product
        data["노출상품명(옵션명)"] = product
        data["구매수(수량)"] = qty(row.get("quantity"))
        data["구매자"] = s(row.get("name"))
        data["구매자전화번호"] = phone(row.get("phone"))
        data["수취인이름"] = s(row.get("name"))
        data["수취인전화번호"] = phone(row.get("phone"))
        data["우편번호"] = s(row.get("zipcode"))
        data["수취인 주소"] = s(row.get("address"))
        data["배송메세지"] = s(row.get("delivery_message")) or "문 앞"
        data["기타"] = f"[{category(row.get('category'))}] {s(row.get('memo'))}".strip()
        data["배송유형"] = "일반배송"
        table.append([data[h] for h in CJ_HEADERS])
    return table


def make_backup_csv(rows):
    bio = io.StringIO()
    writer = csv.DictWriter(bio, fieldnames=FIELDS_KR)
    writer.writeheader()
    for r in rows:
        writer.writerow({
            "분류": category(r.get("category")),
            "이름": s(r.get("name")),
            "전화번호": phone(r.get("phone")),
            "우편번호": s(r.get("zipcode")),
            "주소": s(r.get("address")),
            "수량": qty(r.get("quantity")),
            "상품명": s(r.get("product_name")),
            "배송메세지": s(r.get("delivery_message")),
            "메모": s(r.get("memo")),
        })
    return bio.getvalue().encode("utf-8-sig")


def import_csv(uploaded_file):
    raw = uploaded_file.getvalue()
    text = raw.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    items = []
    for row in reader:
        item = {
            "category": category(row.get("분류") or row.get("폴더") or row.get("구분") or "지인"),
            "name": s(row.get("이름") or row.get("수취인이름") or row.get("받는분")),
            "phone": phone(row.get("전화번호") or row.get("수취인전화번호") or row.get("연락처")),
            "zipcode": s(row.get("우편번호")),
            "address": s(row.get("주소") or row.get("수취인 주소")),
            "quantity": qty(row.get("수량") or row.get("구매수(수량)") or 1),
            "product_name": s(row.get("상품명") or row.get("등록상품명")),
            "delivery_message": s(row.get("배송메세지")) or "문 앞",
            "memo": s(row.get("메모") or row.get("기타")),
        }
        if item["name"] and item["address"]:
            items.append(item)
    return items


def row_matches(row, keyword, folder):
    text = " ".join([
        category(row.get("category")), s(row.get("name")), s(row.get("phone")), s(row.get("zipcode")),
        s(row.get("address")), s(row.get("product_name")), s(row.get("delivery_message")), s(row.get("memo")),
    ]).lower()
    keyword_ok = not keyword or keyword.lower() in text
    folder_ok = folder == "전체" or category(row.get("category")) == folder
    return keyword_ok and folder_ok


def main():
    app_pw = get_secret("APP_PASSWORD")
    if app_pw:
        typed = st.text_input("비밀번호", type="password")
        if typed != app_pw:
            st.stop()

    css()
    hero()

    if not supabase_base_url() or not supabase_key():
        st.error("Streamlit Secrets에 SUPABASE_URL, SUPABASE_KEY를 먼저 넣어야 합니다.")
        st.code('SUPABASE_URL = "https://xxxxx.supabase.co"\nSUPABASE_KEY = "sb_secret_xxxxx"\nAPP_PASSWORD = "원하는비밀번호"', language="toml")
        st.stop()

    try:
        rows = fetch_rows()
    except Exception as e:
        st.error("Supabase 연결에 실패했습니다.")
        st.exception(e)
        st.info("SQL Editor에서 addresses 테이블을 만들었는지, Secrets의 URL/KEY가 맞는지 확인하세요.")
        st.stop()

    total = len(rows)
    friends = sum(1 for r in rows if category(r.get("category")) == "지인")
    vendors = sum(1 for r in rows if category(r.get("category")) == "거래처")
    c1, c2, c3 = st.columns(3)
    c1.metric("전체 주소", total)
    c2.metric("지인", friends)
    c3.metric("거래처", vendors)

    with st.sidebar:
        st.subheader("DB 상태")
        st.success("Supabase 연결됨")
        st.caption("앱을 재배포해도 주소록은 DB에 남습니다.")
        st.divider()
        st.subheader("백업 / 가져오기")
        st.download_button(
            "주소록 CSV 백업",
            data=make_backup_csv(rows),
            file_name="address_book_backup.csv",
            mime="text/csv",
            use_container_width=True,
        )
        uploaded = st.file_uploader("CSV 가져오기", type=["csv"])
        if uploaded is not None and st.button("Supabase에 가져오기", use_container_width=True):
            items = import_csv(uploaded)
            ok = 0
            for item in items:
                insert_row(item)
                ok += 1
            st.success(f"{ok}건 가져오기 완료")
            st.rerun()

    tab_add, tab_manage, tab_export = st.tabs(["📮 주소 등록", "📁 지인 / 거래처", "🚚 엑셀 다운로드"])

    with tab_add:
        st.subheader("새 주소 추가")
        with st.form("add_form", clear_on_submit=True):
            f1, f2 = st.columns([1, 1])
            with f1:
                add_category = st.radio("폴더", CATEGORIES, horizontal=True)
                name = st.text_input("이름")
                tel = st.text_input("전화번호", placeholder="010-0000-0000")
                zipcode = st.text_input("우편번호")
                quantity = st.number_input("수량", min_value=1, value=1, step=1)
            with f2:
                product_name = st.text_input("상품명", placeholder="예: 식혜 1L / 호박감주 1L")
                delivery_message = st.text_input("배송메세지", value="문 앞")
                address = st.text_area("주소", height=110)
                memo = st.text_area("메모", height=90)
            submitted = st.form_submit_button("Supabase에 저장", use_container_width=True)
            if submitted:
                if not name or not address:
                    st.error("이름과 주소는 필수입니다.")
                else:
                    insert_row({
                        "category": add_category,
                        "name": name,
                        "phone": tel,
                        "zipcode": zipcode,
                        "address": address,
                        "quantity": quantity,
                        "product_name": product_name,
                        "delivery_message": delivery_message,
                        "memo": memo,
                    })
                    st.success("저장 완료")
                    st.rerun()

    with tab_manage:
        st.subheader("검색 / 수정 / 삭제")
        m1, m2 = st.columns([1, 1.5])
        with m1:
            folder = st.radio("폴더 보기", ["전체", "지인", "거래처"], horizontal=True)
        with m2:
            keyword = st.text_input("검색", placeholder="이름 / 전화번호 / 주소 / 상품명")
        filtered = [r for r in rows if row_matches(r, keyword, folder)]
        st.caption(f"현재 표시: {len(filtered)}건")

        if filtered:
            labels = [f"[{category(r.get('category'))}] {s(r.get('name'))} / {phone(r.get('phone'))} / 수량 {qty(r.get('quantity'))} / {s(r.get('product_name'))}" for r in filtered]
            selected = st.selectbox("수정할 주소 선택", labels)
            row = filtered[labels.index(selected)]
            row_id = row.get("id")
            with st.form("edit_form"):
                e_category = st.radio("폴더 ", CATEGORIES, index=CATEGORIES.index(category(row.get("category"))), horizontal=True)
                e1, e2 = st.columns([1, 1])
                with e1:
                    e_name = st.text_input("이름 ", value=s(row.get("name")))
                    e_tel = st.text_input("전화번호 ", value=phone(row.get("phone")))
                    e_zip = st.text_input("우편번호 ", value=s(row.get("zipcode")))
                    e_quantity = st.number_input("수량 ", min_value=1, value=qty(row.get("quantity")), step=1)
                with e2:
                    e_product = st.text_input("상품명 ", value=s(row.get("product_name")))
                    e_message = st.text_input("배송메세지 ", value=s(row.get("delivery_message")) or "문 앞")
                    e_address = st.text_area("주소 ", value=s(row.get("address")), height=110)
                    e_memo = st.text_area("메모 ", value=s(row.get("memo")), height=90)
                b1, b2 = st.columns(2)
                update = b1.form_submit_button("수정 저장", use_container_width=True)
                delete = b2.form_submit_button("삭제", use_container_width=True)
                if update:
                    update_row(row_id, {
                        "category": e_category,
                        "name": e_name,
                        "phone": e_tel,
                        "zipcode": e_zip,
                        "address": e_address,
                        "quantity": e_quantity,
                        "product_name": e_product,
                        "delivery_message": e_message,
                        "memo": e_memo,
                    })
                    st.success("수정 완료")
                    st.rerun()
                if delete:
                    delete_row(row_id)
                    st.success("삭제 완료")
                    st.rerun()

            st.markdown("---")
            st.subheader("주소록 목록")
            for r in filtered:
                st.markdown(
                    f"""
                    <div class="card">
                        <span class="folder-chip">{escape(category(r.get('category')))}</span>
                        <b>{escape(s(r.get('name')))}</b> &nbsp; {escape(phone(r.get('phone')))} &nbsp; 수량 {qty(r.get('quantity'))}<br>
                        <span class="small-note">상품명:</span> {escape(s(r.get('product_name')))}<br>
                        <span class="small-note">주소:</span> {escape(s(r.get('zipcode')))} {escape(s(r.get('address')))}<br>
                        <span class="small-note">배송메세지:</span> {escape(s(r.get('delivery_message')))}<br>
                        <span class="small-note">메모:</span> {escape(s(r.get('memo')))}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("표시할 주소가 없습니다.")

    with tab_export:
        st.subheader("발송 엑셀 다운로드")
        st.caption("주소록 기본값을 불러온 뒤, 이번 발송에 맞게 상품명·수량·배송메세지를 수정해서 엑셀로 뽑을 수 있습니다.")

        x1, x2 = st.columns([1, 1.4])
        with x1:
            export_folder = st.radio("내보낼 폴더", ["전체", "지인", "거래처"], horizontal=True)
        with x2:
            export_keyword = st.text_input("내보내기 검색", placeholder="이름 / 주소 / 상품명")

        export_rows = [r for r in rows if row_matches(r, export_keyword, export_folder)]
        export_labels = [
            f"#{r.get('id')} [{category(r.get('category'))}] {s(r.get('name'))} / {phone(r.get('phone'))} / 수량 {qty(r.get('quantity'))} / {s(r.get('product_name'))}"
            for r in export_rows
        ]

        if export_labels:
            chosen = st.multiselect("보낼 사람 선택", export_labels, default=export_labels)
            chosen_rows = [export_rows[export_labels.index(label)] for label in chosen]
            st.write(f"선택된 발송 건수: **{len(chosen_rows)}건**")

            if chosen_rows:
                st.markdown("#### 엑셀 출력 전 수정")
                st.caption("아래 표에서 바꾸는 내용은 우선 다운로드 엑셀에 반영됩니다. 필요하면 버튼으로 주소록 기본값에도 저장할 수 있습니다.")

                edit_table = []
                for r in chosen_rows:
                    edit_table.append({
                        "id": r.get("id"),
                        "폴더": category(r.get("category")),
                        "이름": s(r.get("name")),
                        "전화번호": phone(r.get("phone")),
                        "주소": f"{s(r.get('zipcode'))} {s(r.get('address'))}".strip(),
                        "수량": qty(r.get("quantity")),
                        "상품명": s(r.get("product_name")),
                        "배송메세지": s(r.get("delivery_message")) or "문 앞",
                        "메모": s(r.get("memo")),
                    })

                edited_table = st.data_editor(
                    edit_table,
                    hide_index=True,
                    use_container_width=True,
                    num_rows="fixed",
                    disabled=["id", "폴더", "이름", "전화번호", "주소", "메모"],
                    column_config={
                        "id": st.column_config.NumberColumn("ID", width="small"),
                        "수량": st.column_config.NumberColumn("수량", min_value=1, step=1, width="small"),
                        "상품명": st.column_config.TextColumn("상품명", width="medium"),
                        "배송메세지": st.column_config.TextColumn("배송메세지", width="medium"),
                    },
                    key="export_editor",
                )

                by_id = {str(r.get("id")): r for r in chosen_rows}
                final_rows = []
                for item in edited_table:
                    original = by_id.get(str(item.get("id")))
                    if not original:
                        continue
                    new_row = dict(original)
                    new_row["quantity"] = qty(item.get("수량"))
                    new_row["product_name"] = s(item.get("상품명"))
                    new_row["delivery_message"] = s(item.get("배송메세지")) or "문 앞"
                    final_rows.append(new_row)

                save_col, down_col = st.columns([1, 1])
                with save_col:
                    if st.button("현재 수정내용을 주소록 기본값으로 저장", use_container_width=True):
                        for r in final_rows:
                            update_row(r.get("id"), r)
                        st.success("주소록 기본값 저장 완료")
                        st.rerun()

                with down_col:
                    st.download_button(
                        "CJ 양식 엑셀 다운로드",
                        data=make_xlsx("Delivery", make_cj_table(final_rows)),
                        file_name=f"CJ_DeliveryList_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        disabled=not final_rows,
                    )
            else:
                st.info("보낼 사람을 선택하세요.")
        else:
            st.info("내보낼 대상이 없습니다.")


if __name__ == "__main__":
    main()
