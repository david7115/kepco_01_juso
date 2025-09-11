# KEPCO 신·재생e 주소/지번 조회 (Streamlit)

## 실제 네트워크 캡처를 반영한 주소검색 프로세스:
1) `POST /ew/cpct/retrieveAddrInit` (페이로드 없음) → **시/도**: `dlt_sido[*].ADDR_DO`
2) `GET /isDevSystem` → 환경확인
3) `POST /ssoCheck` ({"userId":"","userMngSeqno":"0","name":"","autoLogin":"Y"}) → 로그인 체크
4) `POST /ew/cpct/retrieveAddrGbn` 단계별
   - **시**: `gbn=0`, body.dma_addrGbn.addr_do 설정 → `dlt_addrGbn[*].ADDR_SI`
   - **구/군**: `gbn=1` (addr_do, addr_si) → `ADDR_GU`
   - **읍/면/동**: `gbn=2` (addr_do, addr_si, addr_gu) → `ADDR_LIDONG`
   - **리**: `gbn=3` (addr_do, addr_si, addr_gu, addr_lidong) → `ADDR_LI`
   - **지번**: `gbn=4` (… + addr_li, `addr_jibun:""`) → `ADDR_JIBUN`  ← **한전이 등록한 특정 지번**

## 동작 요약 (플레이스홀더/초기값 적용 + 6단계 셀렉트)
1) 6개의 셀렉트박스 모두 처음에는 플레이스홀더(시/도 선택, 시 선택, …, 상세번지 선택) 로 보입니다.
상위가 선택되면 하위가 활성화되고, 응답 값이 바로 옵션으로 채워집니다.
“초기화”를 누르면 전부 플레이스홀더로 되돌아갑니다.
모든 단계가 선택되어야 “검색” 버튼이 활성화됩니다.
참고: Streamlit의 selectbox에는 placeholder 파라미터가 있지만, 버전 호환을 위해 옵션 첫 항목에 플레이스홀더를 넣는 방식으로 구현했습니다(가장 안정적).

2) 시/군구/읍면동/리 단계에서 API가 빈 배열을 주면 옵션을 ['-기타지역'] 으로 자동 보강합니다.
목록이 있어도 항상 -기타지역을 맨 앞에 둬서, 필요 시 사용자가 직접 선택할 수 있습니다.
사용자가 -기타지역을 선택하더라도 다음 단계 API는 그대로 호출되어 목록이 이어집니다(예: addr_gu='-기타지역' 로 호출).
지번 단계는 서버가 제공하는 특정 지번 목록만 표시합니다(임의 추가 X).

## "리" 오류로 세부번지 검색 불가 오류 수정
def split_tokenize(s: str):
    """문자열을 숫자/문자 토큰으로 분리"""
    buf = ""
    out = []
    for ch in str(s):
        if ch.isdigit():
            buf += ch
        else:
            if buf:
                out.append(buf)
                buf = ""
            out.append(ch)
    if buf:
        out.append(buf)
    return out

def nat_sort_uniq(items: List[str]) -> List[str]:
    """
    자연스러운 정렬 + 중복 제거.
    숫자 토큰은 (0, int), 문자 토큰은 (1, str) 형태의 키로 변환하여
    int vs str 비교 오류를 제거.
    """
    def nat_key(x: str):
        key = []
        for t in split_tokenize(x):
            if t.isdigit():
                key.append((0, int(t)))
            else:
                key.append((1, t))
        return tuple(key)

    items = [x for x in items if x is not None and str(x).strip() != ""]
    return sorted(set(items), key=nat_key)
참고: extract_field(...)에서 이미 str(r.get(...))로 캐스팅하고 있지만,
서버가 하이픈(-), 한글+숫자("산117", "11-4") 등을 섞어서 주면 위와 같은 타입 혼합 문제가 생길 수 있어 위처럼 키 정규화를 해야 합니다.

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
