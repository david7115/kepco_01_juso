import requests
import streamlit as st
from typing import List, Dict, Any, Optional

st.set_page_config(page_title="한전 신·재생e 주소/지번 조회", page_icon="🔌", layout="wide")

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

# gbn 매핑(제공 자료 기준)
GBN = dict(si=0, gu=1, lidong=2, li=3, jibun=4)

# 응답 필드명
RESP_KEY = dict(
    sido_list="dlt_sido",  # retrieveAddrInit: dlt_sido[*].ADDR_DO
    si="ADDR_SI",
    gu="ADDR_GU",
    lidong="ADDR_LIDONG",
    li="ADDR_LI",
    jibun="ADDR_JIBUN",
)

# UI 플레이스홀더(초기 문구)
PH = {
    "addr_do": "시/도 선택",
    "addr_si": "시 선택",
    "addr_gu": "구/군 선택",
    "addr_lidong": "동/면 선택",
    "addr_li": "리 선택",
    "addr_jibun": "상세번지 선택",
}
ETC = "-기타지역"   # 비어있을 때 자동 추가/선택

# -------------------- 자연 정렬(오류 수정 버전) --------------------
def split_tokenize(s: str) -> List[str]:
    """문자열을 숫자/문자 토큰으로 분리"""
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
    """
    자연스러운 정렬 + 중복 제거.
    숫자 토큰은 (0, int), 문자 토큰은 (1, str) 키로 변환하여
    int/str 비교 TypeError를 방지한다.
    """
    def nat_key(x: str):
        key = []
        for t in split_tokenize(x):
            if t.isdigit():
                key.append((0, int(t)))
            else:
                key.append((1, t))
        return tuple(key)

    cleaned = [str(x).strip() for x in items if x is not None and str(x).strip() != ""]
    return sorted(set(cleaned), key=nat_key)

# -------------------- 응답 파서 --------------------
def extract_sido(data: Dict[str, Any]) -> List[str]:
    rows = data.get("dlt_sido") or []
    vals = [str(r.get("ADDR_DO")).strip() for r in rows if isinstance(r, dict) and r.get("ADDR_DO")]
    return nat_sort_uniq(vals)

def extract_field(data: Dict[str, Any], field_key: str) -> List[str]:
    rows = data.get("dlt_addrGbn") or []
    vals = [str(r.get(field_key)).strip() for r in rows if isinstance(r, dict) and r.get(field_key)]
    return nat_sort_uniq(vals)

def ensure_etc_option(opts: List[str]) -> List[str]:
    """시/군구/읍면동/리 단계: 빈 목록이면 [-기타지역], 있어도 맨 앞에 -기타지역 배치"""
    if not opts:
        return [ETC]
    if ETC not in opts:
        return [ETC] + opts
    # 이미 있으면 맨 앞에 오도록
    return [ETC] + [o for o in opts if o != ETC]

# -------------------- API 클라이언트 --------------------
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
        # 요청 페이로드 없음
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

# -------------------- 캐시 래퍼 --------------------
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
    # 지번은 서버가 가진 "특정 지번"만 — 임의로 -기타지역 추가하지 않음
    return extract_field(res, RESP_KEY["jibun"])

# -------------------- 상태 관리 --------------------
def reset_below(level: str):
    order = ["addr_do", "addr_si", "addr_gu", "addr_lidong", "addr_li", "addr_jibun"]
    for k in order[order.index(level)+1:]:
        st.session_state.pop(k, None)

# -------------------- UI --------------------
def main():
    st.markdown("## 주소로 검색")

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
            si_options += get_si_options(addr_do)   # 빈 목록이면 ['-기타지역'] 자동 보강
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

    # 6) 상세번지(지번) — 서버 등록 "특정 지번"만
    jibun_options = [PH["addr_jibun"]]
    if addr_li and addr_li != PH["addr_li"]:
        try:
            jibun_options += get_jibun_options(addr_do, addr_si, addr_gu, addr_lidong, addr_li)
        except Exception as e:
            st.error(f"상세번지 조회 실패: {e}")
    addr_jibun = st.selectbox("상세번지", jibun_options, index=0, key="addr_jibun",
                              disabled=(addr_li == PH["addr_li"]))

    # 결과 요약
    st.divider()
    st.markdown("### 최종 선택값")
    st.json({
        "addr_do": addr_do if addr_do != PH["addr_do"] else "",
        "addr_si": addr_si if addr_si != PH["addr_si"] else "",
        "addr_gu": addr_gu if addr_gu != PH["addr_gu"] else "",
        "addr_lidong": addr_lidong if addr_lidong != PH["addr_lidong"] else "",
        "addr_li": addr_li if addr_li != PH["addr_li"] else "",
        "addr_jibun": addr_jibun if addr_jibun != PH["addr_jibun"] else "",
    })

if __name__ == "__main__":
    main()
