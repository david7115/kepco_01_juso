import os
import requests
import streamlit as st
from typing import List, Dict, Any, Optional

# -------------------------------------------------
# 페이지 설정 & 테마 CSS
# -------------------------------------------------
st.set_page_config(page_title="한전 신·재생e 주소/지번/전산번호 조회", page_icon="🔌", layout="wide")

st.markdown(
    """
    <style>
    /* 카드 느낌의 컨테이너 */
    .card {
        background: #fafafa;
        border-radius: 16px;
        padding: 20px 20px 8px 20px;
        border: 1px solid #eee;
    }
    .pill {
        background: #f1f3f5;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 0.9rem;
        color: #495057;
        border: 1px solid #e9ecef;
        display: inline-block;
    }
    /* 버튼 공통 */
    div.stButton > button {
        padding: 0.6rem 1.2rem;
        border-radius: 12px;
        font-weight: 600;
        border: 1px solid transparent;
    }
    /* 기본 primary=빨강 */
    .stButton > button[kind="primary"] {
        background: #e03131;
        border-color: #e03131;
    }
    .stButton > button[kind="primary"]:hover {
        background: #c92a2a;
        border-color: #c92a2a;
    }
    /* secondary=테두리만 */
    .stButton > button[kind="secondary"] {
        background: #ffffff !important;
        color: #222 !important;
        border-color: #adb5bd !important;
    }
    /* selectbox 라벨 개선 */
    label.css-1cpxqw2, .stSelectbox label {
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------
# 상수/엔드포인트
# -------------------------------------------------
BASE = "https://online.kepco.co.kr"
URL_INIT = f"{BASE}/ew/cpct/retrieveAddrInit"
URL_GBN  = f"{BASE}/ew/cpct/retrieveAddrGbn"

HEADERS = {
    "accept": "application/json",
    "content-type": 'application/json; charset="UTF-8"',
    "referer": "https://online.kepco.co.kr/EWM092D00",
    "user-agent": "Mozilla/5.0",
}
SBM_INIT = "mf_wfm_layout_sbm_retrieveAddrInit"
SBM_GBN  = "mf_wfm_layout_sbm_retrieveAddrGbn"

# gbn 매핑(실측 기반)
GBN = dict(si=0, gu=1, lidong=2, li=3, jibun=4)

# 응답 필드
RESP_KEY = dict(
    sido_list="dlt_sido",  # retrieveAddrInit: dlt_sido[*].ADDR_DO
    si="ADDR_SI",
    gu="ADDR_GU",
    lidong="ADDR_LIDONG",
    li="ADDR_LI",
    jibun="ADDR_JIBUN",
)

# UI 플레이스홀더
PH = {
    "addr_do": "시/도 선택",
    "addr_si": "시 선택",
    "addr_gu": "구/군 선택",
    "addr_lidong": "동/면 선택",
    "addr_li": "리 선택",
    "addr_jibun": "상세번지 선택",
}
ETC = "-기타지역"   # 빈 목록 시 자동 추가

# 전산번호 검색용 (환경변수로 주입)
ESB_API_URL = os.environ.get("KEPCO_ESB_SEARCH_URL", "").strip()  # 예: https://online.kepco.co.kr/ew/cpct/retrieveByEsbNo

# -------------------------------------------------
# 자연 정렬(혼합 토큰 안전)
# -------------------------------------------------
def split_tokenize(s: str) -> List[str]:
    s = "" if s is None else str(s)
    buf = ""
    out: List[str] = []
    for ch in s:
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
    def nat_key(x: str):
        key = []
        for t in split_tokenize(x):
            if t.isdigit(): key.append((0, int(t)))
            else: key.append((1, t))
        return tuple(key)
    cleaned = [str(x).strip() for x in items if x is not None and str(x).strip() != ""]
    return sorted(set(cleaned), key=nat_key)

# -------------------------------------------------
# 응답 파서
# -------------------------------------------------
def extract_sido(data: Dict[str, Any]) -> List[str]:
    rows = data.get("dlt_sido") or []
    vals = [str(r.get("ADDR_DO")).strip() for r in rows if isinstance(r, dict) and r.get("ADDR_DO")]
    return nat_sort_uniq(vals)

def extract_field(data: Dict[str, Any], field_key: str) -> List[str]:
    rows = data.get("dlt_addrGbn") or []
    vals = [str(r.get(field_key)).strip() for r in rows if isinstance(r, dict) and r.get(field_key)]
    return nat_sort_uniq(vals)

def ensure_etc_option(opts: List[str]) -> List[str]:
    if not opts:
        return [ETC]
    if ETC not in opts:
        return [ETC] + opts
    return [ETC] + [o for o in opts if o != ETC]

# -------------------------------------------------
# API Client
# -------------------------------------------------
class KepcoClient:
    def __init__(self, timeout: int = 20):
        self.sess = requests.Session()
        self.timeout = timeout

    def _post(self, url: str, body: Dict[str, Any], submissionid: Optional[str] = None) -> Dict[str, Any]:
        h = dict(HEADERS)
        if submissionid:
            h["submissionid"] = submissionid
        r = self.sess.post(url, headers=h, json=body, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def retrieve_addr_init(self) -> Dict[str, Any]:
        return self._post(URL_INIT, {}, submissionid=SBM_INIT)

    def retrieve_addr_gbn(
        self, gbn: int, addr_do: str = "", addr_si: str = "", addr_gu: str = "",
        addr_lidong: str = "", addr_li: str = "", addr_jibun: str = ""
    ) -> Dict[str, Any]:
        body = {"dma_addrGbn": {
            "gbn": gbn, "addr_do": addr_do, "addr_si": addr_si, "addr_gu": addr_gu,
            "addr_lidong": addr_lidong, "addr_li": addr_li, "addr_jibun": addr_jibun
        }}
        return self._post(URL_GBN, body, submissionid=SBM_GBN)

    def search_by_esb(self, esb_no: str) -> Dict[str, Any]:
        """
        전산번호 검색: 환경변수 KEPCO_ESB_SEARCH_URL 이 지정된 경우에만 호출.
        반환 포맷은 기관 API 규격에 맞춰 사용자가 매핑하면 됨.
        """
        if not ESB_API_URL:
            raise RuntimeError("전산번호 검색 API URL(KEPCO_ESB_SEARCH_URL)이 설정되지 않았습니다.")
        body = {"esbNo": esb_no}
        # 필요 시 헤더/키를 현업 규격에 맞게 조정하세요.
        return self._post(ESB_API_URL, body)  # submissionid 필요시 추가

# -------------------------------------------------
# 캐시 래퍼
# -------------------------------------------------
@st.cache_data(show_spinner=False)
def get_sido_options() -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_init()
    return extract_sido(res)

@st.cache_data(show_spinner=False)
def get_si_options(addr_do: str) -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_gbn(GBN["si"], addr_do=addr_do)
    return ensure_etc_option(extract_field(res, RESP_KEY["si"]))

@st.cache_data(show_spinner=False)
def get_gu_options(addr_do: str, addr_si: str) -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_gbn(GBN["gu"], addr_do=addr_do, addr_si=addr_si)
    return ensure_etc_option(extract_field(res, RESP_KEY["gu"]))

@st.cache_data(show_spinner=False)
def get_lidong_options(addr_do: str, addr_si: str, addr_gu: str) -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_gbn(GBN["lidong"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu)
    return ensure_etc_option(extract_field(res, RESP_KEY["lidong"]))

@st.cache_data(show_spinner=False)
def get_li_options(addr_do: str, addr_si: str, addr_gu: str, addr_lidong: str) -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_gbn(GBN["li"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu, addr_lidong=addr_lidong)
    return ensure_etc_option(extract_field(res, RESP_KEY["li"]))

@st.cache_data(show_spinner=False)
def get_jibun_options(addr_do: str, addr_si: str, addr_gu: str, addr_lidong: str, addr_li: str) -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_gbn(GBN["jibun"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu,
                                addr_lidong=addr_lidong, addr_li=addr_li, addr_jibun="")
    return extract_field(res, RESP_KEY["jibun"])  # 지번은 -기타지역 추가 안 함

# -------------------------------------------------
# 상태 관리
# -------------------------------------------------
def reset_below(level: str):
    order = ["addr_do", "addr_si", "addr_gu", "addr_lidong", "addr_li", "addr_jibun"]
    for k in order[order.index(level)+1:]:
        st.session_state.pop(k, None)

def full_reset():
    for k in ["addr_do","addr_si","addr_gu","addr_lidong","addr_li","addr_jibun",
              "search_done","esb_no","esb_result"]:
        st.session_state.pop(k, None)

# -------------------------------------------------
# 주소로 검색 탭
# -------------------------------------------------
def tab_address():
    st.markdown("### 주소로 검색")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        # 1) 시/도
        try:
            sido = get_sido_options()
        except Exception as e:
            st.error(f"시/도 조회 실패: {e}")
            return

        do_options = [PH["addr_do"]] + sido
        addr_do = st.selectbox("시/도", do_options, index=0, key="addr_do",
                               on_change=reset_below, args=("addr_do",))

        # 2) 시
        si_options = [PH["addr_si"]]
        if addr_do and addr_do != PH["addr_do"]:
            try:
                si_options += get_si_options(addr_do)
            except Exception as e:
                st.error(f"시 조회 실패: {e}")
        addr_si = st.selectbox("시", si_options, index=0, key="addr_si",
                               disabled=(addr_do == PH["addr_do"]),
                               on_change=reset_below, args=("addr_si",))

        # 3) 구/군
        gu_options = [PH["addr_gu"]]
        if addr_si and addr_si != PH["addr_si"]:
            try:
                gu_options += get_gu_options(addr_do, addr_si)
            except Exception as e:
                st.error(f"구/군 조회 실패: {e}")
        addr_gu = st.selectbox("구/군", gu_options, index=0, key="addr_gu",
                               disabled=(addr_si == PH["addr_si"]),
                               on_change=reset_below, args=("addr_gu",))

        # 4) 동/면
        lidong_options = [PH["addr_lidong"]]
        if addr_gu and addr_gu != PH["addr_gu"]:
            try:
                lidong_options += get_lidong_options(addr_do, addr_si, addr_gu)
            except Exception as e:
                st.error(f"동/면 조회 실패: {e}")
        addr_lidong = st.selectbox("동/면", lidong_options, index=0, key="addr_lidong",
                                   disabled=(addr_gu == PH["addr_gu"]),
                                   on_change=reset_below, args=("addr_lidong",))

        # 5) 리
        li_options = [PH["addr_li"]]
        if addr_lidong and addr_lidong != PH["addr_lidong"]:
            try:
                li_options += get_li_options(addr_do, addr_si, addr_gu, addr_lidong)
            except Exception as e:
                st.error(f"리 조회 실패: {e}")
        addr_li = st.selectbox("리", li_options, index=0, key="addr_li",
                               disabled=(addr_lidong == PH["addr_lidong"]),
                               on_change=reset_below, args=("addr_li",))

        # 6) 상세번지(지번)
        jibun_options = [PH["addr_jibun"]]
        if addr_li and addr_li != PH["addr_li"]:
            try:
                jibun_options += get_jibun_options(addr_do, addr_si, addr_gu, addr_lidong, addr_li)
            except Exception as e:
                st.error(f"상세번지 조회 실패: {e}")
        addr_jibun = st.selectbox("상세번지", jibun_options, index=0, key="addr_jibun",
                                  disabled=(addr_li == PH["addr_li"]))

        st.markdown("</div>", unsafe_allow_html=True)  # card end

    # 하단 액션 버튼
    st.write("")
    c1, c2, _ = st.columns([1,1,6])
    with c1:
        if st.button("초기화", type="secondary", use_container_width=True):
            full_reset()
            st.experimental_rerun()
    with c2:
        ready = all([
            st.session_state.get("addr_do") not in (None, "", PH["addr_do"]),
            st.session_state.get("addr_si") not in (None, "", PH["addr_si"]),
            st.session_state.get("addr_gu") not in (None, "", PH["addr_gu"]),
            st.session_state.get("addr_lidong") not in (None, "", PH["addr_lidong"]),
            st.session_state.get("addr_li") not in (None, "", PH["addr_li"]),
            st.session_state.get("addr_jibun") not in (None, "", PH["addr_jibun"]),
        ])
        if st.button("검색", type="primary", disabled=not ready, use_container_width=True):
            st.session_state["search_done"] = True

    # 검색 결과 요약
    if st.session_state.get("search_done"):
        st.success("선택 완료")
        st.json({
            "addr_do": st.session_state.get("addr_do", ""),
            "addr_si": st.session_state.get("addr_si", ""),
            "addr_gu": st.session_state.get("addr_gu", ""),
            "addr_lidong": st.session_state.get("addr_lidong", ""),
            "addr_li": st.session_state.get("addr_li", ""),
            "addr_jibun": st.session_state.get("addr_jibun", "")
        })

# -------------------------------------------------
# 전산번호로 검색 탭
# -------------------------------------------------
def tab_esb():
    st.markdown("### 전산번호로 검색")
    st.markdown('<div class="card">', unsafe_allow_html=True)

    esb_no = st.text_input("전산번호 입력", value=st.session_state.get("esb_no", ""), placeholder="예: 123-456-7890")
    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("초기화(전산번호)", type="secondary", use_container_width=True):
            for k in ["esb_no", "esb_result"]:
                st.session_state.pop(k, None)
            st.experimental_rerun()
    with c2:
        if st.button("검색(전산번호)", type="primary", use_container_width=True):
            st.session_state["esb_no"] = esb_no
            cli = KepcoClient()
            try:
                result = cli.search_by_esb(esb_no)
                st.session_state["esb_result"] = result
            except Exception as e:
                st.error(f"전산번호 검색 실패: {e}")
                st.info("환경변수 KEPCO_ESB_SEARCH_URL 을 설정하면 바로 연동됩니다.")
                st.session_state["esb_result"] = None

    st.write("")
    if st.session_state.get("esb_no"):
        st.caption("입력한 전산번호")
        st.code(st.session_state["esb_no"])

    if st.session_state.get("esb_result") is not None:
        st.caption("전산번호 검색 결과(JSON)")
        st.json(st.session_state["esb_result"])

    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# 메인
# -------------------------------------------------
def main():
    st.title("🔌 한전 신·재생e 주소/지번/전산번호 조회")
    st.caption("주소로 검색: retrieveAddrInit → retrieveAddrGbn(시→구/군→동/면→리→상세번지) | 전산번호로 검색: 기관 API 연동")

    tabs = st.tabs(["주소로 검색", "전산번호로 검색"])
    with tabs[0]:
        tab_address()
    with tabs[1]:
        tab_esb()

if __name__ == "__main__":
    main()
