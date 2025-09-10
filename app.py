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

# gbn
GBN = dict(si=0, gu=1, lidong=2, li=3, jibun=4)

# 응답 키
RESP_KEY = dict(
    sido_list="dlt_sido",
    si="ADDR_SI",
    gu="ADDR_GU",
    lidong="ADDR_LIDONG",
    li="ADDR_LI",
    jibun="ADDR_JIBUN",
)

# 플레이스홀더(스크린샷과 동일 문구)
PH = {
    "addr_do": "시/도 선택",
    "addr_si": "시 선택",
    "addr_gu": "구/군 선택",
    "addr_lidong": "동/면 선택",
    "addr_li": "리 선택",
    "addr_jibun": "상세번지 선택",
}

def split_tokenize(s: str):
    buf = ""; out = []
    for ch in s:
        if ch.isdigit():
            buf += ch
        else:
            if buf: out.append(buf); buf = ""
            out.append(ch)
    if buf: out.append(buf)
    return out

def nat_sort_uniq(items: List[str]) -> List[str]:
    items = [x for x in items if x]
    return sorted(set(items), key=lambda x: [int(t) if t.isdigit() else t for t in split_tokenize(x)])

def extract_sido(data: Dict[str, Any]) -> List[str]:
    rows = data.get("dlt_sido") or []
    vals = [str(r.get("ADDR_DO")).strip() for r in rows if isinstance(r, dict) and r.get("ADDR_DO")]
    return nat_sort_uniq(vals)

def extract_field(data: Dict[str, Any], field_key: str) -> List[str]:
    rows = data.get("dlt_addrGbn") or []
    vals = [str(r.get(field_key)).strip() for r in rows if isinstance(r, dict) and r.get(field_key)]
    return nat_sort_uniq(vals)

class KepcoClient:
    def __init__(self, timeout: int = 20):
        self.sess = requests.Session()
        self.timeout = timeout

    def _post(self, url: str, body: Dict[str, Any], submissionid: Optional[str] = None) -> Dict[str, Any]:
        h = dict(HEADERS)
        if submissionid: h["submissionid"] = submissionid
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

# ---- cache wrappers
@st.cache_data(show_spinner=False)
def get_sido_options() -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_init()
    return extract_sido(res)

@st.cache_data(show_spinner=False)
def get_si_options(addr_do: str) -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_gbn(GBN["si"], addr_do=addr_do)
    return extract_field(res, RESP_KEY["si"])

@st.cache_data(show_spinner=False)
def get_gu_options(addr_do: str, addr_si: str) -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_gbn(GBN["gu"], addr_do=addr_do, addr_si=addr_si)
    return extract_field(res, RESP_KEY["gu"])

@st.cache_data(show_spinner=False)
def get_lidong_options(addr_do: str, addr_si: str, addr_gu: str) -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_gbn(GBN["lidong"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu)
    return extract_field(res, RESP_KEY["lidong"])

@st.cache_data(show_spinner=False)
def get_li_options(addr_do: str, addr_si: str, addr_gu: str, addr_lidong: str) -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_gbn(GBN["li"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu, addr_lidong=addr_lidong)
    return extract_field(res, RESP_KEY["li"])

@st.cache_data(show_spinner=False)
def get_jibun_options(addr_do: str, addr_si: str, addr_gu: str, addr_lidong: str, addr_li: str) -> List[str]:
    cli = KepcoClient()
    res = cli.retrieve_addr_gbn(GBN["jibun"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu,
                                addr_lidong=addr_lidong, addr_li=addr_li, addr_jibun="")
    return extract_field(res, RESP_KEY["jibun"])

def reset_below(level: str):
    order = ["addr_do","addr_si","addr_gu","addr_lidong","addr_li","addr_jibun"]
    for k in order[order.index(level)+1:]:
        st.session_state.pop(k, None)

# ---- UI
def main():
    st.markdown("## 주소로 검색")

    # 1) 시/도
    sido = get_sido_options()
    do_options = [PH["addr_do"]] + sido
    addr_do = st.selectbox("시/도", do_options, index=0, key="addr_do",
                           on_change=reset_below, args=("addr_do",))
    st.write("")  # spacing

    # 2) 시
    si_options = [PH["addr_si"]]
    if addr_do and addr_do != PH["addr_do"]:
        si_options += get_si_options(addr_do)
    addr_si = st.selectbox("시", si_options, index=0, key="addr_si",
                           disabled=(addr_do == PH["addr_do"]),
                           on_change=reset_below, args=("addr_si",))

    # 3) 구/군
    gu_options = [PH["addr_gu"]]
    if addr_si and addr_si != PH["addr_si"]:
        gu_options += get_gu_options(addr_do, addr_si)
    addr_gu = st.selectbox("구/군", gu_options, index=0, key="addr_gu",
                           disabled=(addr_si == PH["addr_si"]),
                           on_change=reset_below, args=("addr_gu",))

    # 4) 동/면
    lidong_options = [PH["addr_lidong"]]
    if addr_gu and addr_gu != PH["addr_gu"]:
        lidong_options += get_lidong_options(addr_do, addr_si, addr_gu)
    addr_lidong = st.selectbox("동/면", lidong_options, index=0, key="addr_lidong",
                               disabled=(addr_gu == PH["addr_gu"]),
                               on_change=reset_below, args=("addr_lidong",))

    # 5) 리
    li_options = [PH["addr_li"]]
    if addr_lidong and addr_lidong != PH["addr_lidong"]:
        li_options += get_li_options(addr_do, addr_si, addr_gu, addr_lidong)
    addr_li = st.selectbox("리", li_options, index=0, key="addr_li",
                           disabled=(addr_lidong == PH["addr_lidong"]),
                           on_change=reset_below, args=("addr_li",))

    # 6) 상세번지(지번)
    jibun_options = [PH["addr_jibun"]]
    if addr_li and addr_li != PH["addr_li"]:
        jibun_options += get_jibun_options(addr_do, addr_si, addr_gu, addr_lidong, addr_li)
    addr_jibun = st.selectbox("상세번지", jibun_options, index=0, key="addr_jibun",
                              disabled=(addr_li == PH["addr_li"]))

    st.write("")  # spacing
    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("초기화"):
            for k in ["addr_do","addr_si","addr_gu","addr_lidong","addr_li","addr_jibun"]:
                st.session_state.pop(k, None)
            st.experimental_rerun()
    with c2:
        # 검색 버튼: 플레이스홀더가 하나라도 남아있으면 비활성화
        ready = all([
            addr_do != PH["addr_do"],
            addr_si != PH["addr_si"],
            addr_gu != PH["addr_gu"],
            addr_lidong != PH["addr_lidong"],
            addr_li != PH["addr_li"],
            addr_jibun != PH["addr_jibun"],
        ])
        if st.button("검색", disabled=not ready):
            st.success("선택 완료")
            st.json({
                "addr_do": addr_do,
                "addr_si": addr_si,
                "addr_gu": addr_gu,
                "addr_lidong": addr_lidong,
                "addr_li": addr_li,
                "addr_jibun": addr_jibun
            })

if __name__ == "__main__":
    main()
