# 주소록 관리 + CJ택배 엑셀 다운로드

거래처/지인 주소를 저장하고, 보낼 사람만 선택해서 CJ택배 업로드용 엑셀 파일을 다운로드하는 Streamlit 앱입니다.

## GitHub 업로드 파일

저장소 첫 화면에 아래 3개 파일만 바로 보이게 올리세요.

```text
app.py
requirements.txt
README.md
```

폴더째 올리면 안 됩니다. `app.py`가 저장소 첫 화면에 바로 보여야 합니다.

## Streamlit Cloud 설정

- Repository: 이 저장소 선택
- Branch: main
- Main file path: `app.py`
- Python version: 3.11 권장

## 기능

- 이름 / 전화번호 / 우편번호 / 주소 / 수량 / 상품명 / 배송메세지 / 메모 저장
- 주소 검색
- 주소 수정 / 삭제
- CSV 백업 및 CSV 가져오기
- 선택한 사람만 CJ택배 엑셀 다운로드

## 비밀번호 설정 선택사항

Streamlit Cloud의 Secrets에 아래처럼 넣으면 비밀번호가 걸립니다.

```toml
APP_PASSWORD = "원하는비밀번호"
```

비밀번호를 안 넣으면 바로 접속됩니다.
