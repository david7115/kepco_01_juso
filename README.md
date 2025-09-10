# KEPCO 신·재생e 주소/지번 조회 (Streamlit)

실제 네트워크 캡처를 반영한 주소검색 프로세스:
1) `POST /ew/cpct/retrieveAddrInit` (페이로드 없음) → **시/도**: `dlt_sido[*].ADDR_DO`
2) `GET /isDevSystem` → 환경확인
3) `POST /ssoCheck` ({"userId":"","userMngSeqno":"0","name":"","autoLogin":"Y"}) → 로그인 체크
4) `POST /ew/cpct/retrieveAddrGbn` 단계별
   - **시**: `gbn=0`, body.dma_addrGbn.addr_do 설정 → `dlt_addrGbn[*].ADDR_SI`
   - **구/군**: `gbn=1` (addr_do, addr_si) → `ADDR_GU`
   - **읍/면/동**: `gbn=2` (addr_do, addr_si, addr_gu) → `ADDR_LIDONG`
   - **리**: `gbn=3` (addr_do, addr_si, addr_gu, addr_lidong) → `ADDR_LI`
   - **지번**: `gbn=4` (… + addr_li, `addr_jibun:""`) → `ADDR_JIBUN`  ← **한전이 등록한 특정 지번**

## 실행
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
requests.Session() 으로 쿠키/세션 유지. 헤더는 accept, content-type, referer, (엔드포인트별) submissionid.

응답 필드/gbn이 바뀌면 RESP_KEY/GBN 상수만 수정.

지번 단계는 서버가 보유한 특정 지번 목록만을 그대로 보여줌.
requests.Session() 으로 쿠키/세션 유지. 헤더는 accept, content-type, referer, (엔드포인트별) submissionid.

응답 필드/gbn이 바뀌면 RESP_KEY/GBN 상수만 수정.

지번 단계는 서버가 보유한 특정 지번 목록만을 그대로 보여줌.

# KEPCO 신·재생e 주소/지번 조회 (Streamlit)

- 프로세스: `retrieveAddrInit` → `retrieveAddrGbn(gbn=0~4)`
- 6단계 셀렉트: 시/도 → 시 → 구/군 → 동/면 → 리 → 상세번지
- 시/시군구/읍면동/리 단계에서 목록이 비면 **`-기타지역`** 자동 추가·선택
- 지번은 서버가 가진 **특정 지번 목록만** 표시
- 자연 정렬 키를 안전화하여 `"109"`, `"산117"`, `"11-4"` 등 혼합 값에서도 오류 없음

## 실행
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
