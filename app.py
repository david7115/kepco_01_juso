import requests
import streamlit as st
from typing import List, Dict, Any, Optional

st.set_page_config(page_title="한전 신·재생e 주소/지번 조회", page_icon="🔌", layout="centered")

BASE = "https://online.kepco.co.kr"
URL_INIT = f"{BASE}/ew/cpct/retrieveAddrInit"   # (1) 시/도
URL_DEV  = f"{BASE}/isDevSystem"                # (1-2) 환경 확인
URL_SSO  = f"{BASE}/ssoCheck"                   # (1-3) SSO 체크
URL_GBN  = f"{BASE}/ew/cpct/retrieveAddrGbn"    # (2~6) 단계별

HEADERS = {
    "accept": "application/json",
    "content-type": 'application/json; charset="UTF-8"',
    "referer": "https://online.kepco.co.kr/EWM092D00",
    "user-agent": "Mozilla/5.0",
}
SBM_INIT = "mf_wfm_layout_sbm_retrieveAddrInit"
SBM_GBN  = "mf_wfm_layout_sbm_retrieveAddrGbn"

# gbn 매핑(제공자료 기준)
GBN = dict(si=0, gu=1, lidong=2, li=3, jibun=4)

# 응답 필드명
RESP_KEY = dict(
    sido_list="dlt_sido",   # retrieveAddrInit
    si="ADDR_SI",
    gu="ADDR_GU",
    lidong="ADDR_LIDONG",
    li="ADDR_LI",
    jibun="ADDR_JIBUN",
)

# -------------------- 공통 유틸 --------------------
def split_tokenize(s: str):
    buf = ""; out = []
    for ch in s:
        if ch.isdigit(): buf += ch
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

# -------------------- API 클라이언트 --------------------
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

    def _get(self, url: str) -> Dict[str, Any]:
        r = self.sess.get(url, headers={"accept": "application/json"}, timeout=self.timeout)
        r.raise_for_status()
        try: return r.json()
        except Exception: return {"_text": r.text}

    # (1) 시/도
    def retrieve_addr_init(self) -> Dict[str, Any]:
        return self._post(URL_INIT, {}, submissionid=SBM_INIT)

    # (옵션) 환경/SSO
    def is_dev_system(self) -> Dict[str, Any]:
        return self._get(URL_DEV)

    def sso_check(self) -> Dict[str, Any]:
        body = {"userId": "", "userMngSeqno": "0", "name": "", "autoLogin": "Y"}
        return self._post(URL_SSO, body)

    # (2~6) 단계별
    def retrieve_addr_gbn(
        self,
        gbn: int,
        addr_do: str = "",
        addr_si: str = "",
        addr_gu: str = "",
        addr_lidong: str = "",
        addr_li: str = "",
        addr_jibun: str = "",
    ) -> Dict[str, Any]:
        body = {
            "dma_addrGbn": {
                "gbn": gbn,
                "addr_do": addr_do,
                "addr_si": addr_si,
                "addr_gu": addr_gu,
                "addr_lidong": addr_lidong,
                "addr_li": addr_li,
                "addr_jibun": addr_jibun,
            }
        }
        return self._post(URL_GBN, body, submissionid=SBM_GBN)

# -------------------- 캐시 래퍼 --------------------
@st.cache_data(show_spinner=False)
def get_sido_list() -> (List[str], Dict[str, Any]):
    client = KepcoClient()
    # 초기 handshake (필요시 주석 해제)
    # client.is_dev_system()
    # client.sso_check()
    res = client.retrieve_addr_init()
    return extract_sido(res), res

@st.cache_data(show_spinner=False)
def get_si_list(addr_do: str) -> (List[str], Dict[str, Any]):
    client = KepcoClient()
    res = client.retrieve_addr_gbn(GBN["si"], addr_do=addr_do)
    return extract_field(res, RESP_KEY["si"]), res

@st.cache_data(show_spinner=False)
def get_gu_list(addr_do: str, addr_si: str) -> (List[str], Dict[str, Any]):
    client = KepcoClient()
    res = client.retrieve_addr_gbn(GBN["gu"], addr_do=addr_do, addr_si=addr_si)
    return extract_field(res, RESP_KEY["gu"]), res

@st.cache_data(show_spinner=False)
def get_lidong_list(addr_do: str, addr_si: str, addr_gu: str) -> (List[str], Dict[str, Any]):
    client = KepcoClient()
    res = client.retrieve_addr_gbn(GBN["lidong"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu)
    return extract_field(res, RESP_KEY["lidong"]), res

@st.cache_data(show_spinner=False)
def get_li_list(addr_do: str, addr_si: str, addr_gu: str, addr_lidong: str) -> (List[str], Dict[str, Any]):
    client = KepcoClient()
    res = client.retrieve_addr_gbn(GBN["li"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu, addr_lidong=addr_lidong)
    return extract_field(res, RESP_KEY["li"]), res

@st.cache_data(show_spinner=False)
def get_jibun_list(addr_do: str, addr_si: str, addr_gu: str, addr_lidong: str, addr_li: str) -> (List[str], Dict[str, Any]):
    client = KepcoClient()
    res = client.retrieve_addr_gbn(GBN["jibun"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu,
                                   addr_lidong=addr_lidong, addr_li=addr_li, addr_jibun="")
    return extract_field(res, RESP_KEY["jibun"]), res

# -------------------- 상태 초기화(상위 변경 시 하위 리셋) --------------------
def reset_below(level: str):
    chain = ["addr_do", "addr_si", "addr_gu", "addr_lidong", "addr_li", "addr_jibun"]
    idx = chain.index(level)
    for key in chain[idx+1:]:
        st.session_state.pop(key, None)

# -------------------- UI --------------------
def main():
    st.title("🔌 한전 신·재생e 주소/지번 조회")
    st.caption("응답 미리보기의 값이 다음 단계 셀렉트박스 옵션으로 즉시 반영됩니다.")

    # 1) 시/도
    with st.spinner("시/도 목록 로딩…"):
        sido_options, sido_raw = get_sido_list()
    if not sido_options:
        st.error("시/도 목록을 불러오지 못했습니다.")
        return

    st.subheader("주소 선택")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**시/도(addr_do)**")
        addr_do = st.selectbox(
            "시/도",
            options=sido_options,
            index=sido_options.index("강원특별자치도") if "강원특별자치도" in sido_options else 0,
            key="addr_do",
            on_change=reset_below, args=("addr_do",)
        )
    with c2:
        with st.expander("시/도 응답 미리보기"):
            st.json(sido_raw)

    # 2) 시
    with st.spinner("시 목록 로딩…"):
        si_options, si_raw = get_si_list(addr_do)
    addr_si = st.selectbox(
        "시(addr_si)",
        options=si_options,
        index=si_options.index("강릉시") if "강릉시" in si_options else 0,
        key="addr_si",
        on_change=reset_below, args=("addr_si",)
    )
    with st.expander("시 응답 미리보기"):
        st.json(si_raw)

    # 3) 구/군
    with st.spinner("구/군 목록 로딩…"):
        gu_options, gu_raw = get_gu_list(addr_do, addr_si)
    addr_gu = st.selectbox(
        "구/군(addr_gu)",
        options=gu_options,
        index=gu_options.index("-기타지역") if "-기타지역" in gu_options else (0 if gu_options else 0),
        key="addr_gu",
        on_change=reset_below, args=("addr_gu",)
    )
    with st.expander("구/군 응답 미리보기"):
        st.json(gu_raw)

    # 4) 동/면
    with st.spinner("동/면 목록 로딩…"):
        lidong_options, lidong_raw = get_lidong_list(addr_do, addr_si, addr_gu)
    addr_lidong = st.selectbox(
        "동/면(addr_lidong)",
        options=lidong_options,
        index=lidong_options.index("강동면") if "강동면" in lidong_options else (0 if lidong_options else 0),
        key="addr_lidong",
        on_change=reset_below, args=("addr_lidong",)
    )
    with st.expander("동/면 응답 미리보기"):
        st.json(lidong_raw)

    # 5) 리
    with st.spinner("리 목록 로딩…"):
        li_options, li_raw = get_li_list(addr_do, addr_si, addr_gu, addr_lidong)
    addr_li = st.selectbox(
        "리(addr_li)",
        options=li_options,
        index=li_options.index("모전리") if "모전리" in li_options else (0 if li_options else 0),
        key="addr_li",
        on_change=reset_below, args=("addr_li",)
    )
    with st.expander("리 응답 미리보기"):
        st.json(li_raw)

    # 6) 상세번지(지번)
    with st.spinner("상세번지(지번) 목록 로딩…"):
        jibun_options, jibun_raw = get_jibun_list(addr_do, addr_si, addr_gu, addr_lidong, addr_li)
    addr_jibun = st.selectbox(
        "상세번지(addr_jibun)",
        options=jibun_options,
        index=0 if jibun_options else 0,
        key="addr_jibun"
    )
    with st.expander("상세번지 응답 미리보기"):
        st.json(jibun_raw)

    st.divider()
    st.markdown("### 최종 선택값")
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
