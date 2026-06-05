# 우체국 느낌 주소록 + CJ택배 엑셀

## 파일 구성
- app.py
- requirements.txt
- README.md

## 기능
- 이름 / 전화번호 / 우편번호 / 주소 / 수량 / 상품명 / 배송메세지 / 메모 저장
- 상품명 직접 입력
- `지인` / `거래처` 폴더 분리
- 폴더별 검색 / 수정 / 삭제
- 선택한 주소만 CJ택배 업로드용 엑셀 다운로드
- 주소록 CSV 백업 / 가져오기

## 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud
- Main file path: `app.py`
- Python: `3.11` 권장

## 참고
- 데이터는 실행 후 같은 위치의 `address_book.csv`에 자동 저장됩니다.
- 이전 단순 버전 CSV도 대부분 자동 가져오기 됩니다.
