import requests
import streamlit as st
from typing import List, Optional, Dict, Any

st.set_page_config(page_title="한전 신·재생e 주소/지번 조회", page_icon="🔌", layout="centered")

BASE = "https://online.kepco.co.kr"
URL_INIT = f"{BASE}/ew/cpct/retrieveAddrInit"   # (1) 시/도
URL_DEV  = f"{BASE}/isDevSystem"                # (1-2) 환경 확인
URL_SSO  = f"{BASE}/ssoCheck"                   # (1-3) SSO 체크
URL_GBN  = f"{BASE}/ew/cpct/retrieveAddrGbn"    # (2~6) 단계별

COMMON_HEADERS = {
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
    sido_list="dlt_sido",  # retrieveAddrInit
    si="ADDR_SI",
    gu="ADDR_GU",
    lidong="ADDR_LIDONG",
    li="ADDR_LI",
    jibun="ADDR_JIBUN",
)

# -------- utilities --------
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

# -------- API client --------
class KepcoClient:
    def __init__(self, timeout: int = 20):
        self.sess = requests.Session()
        self.timeout = timeout

    def _post(self, url: str, body: Dict[str, Any], submissionid: Optional[str] = None) -> Dict[str, Any]:
        headers = dict(COMMON_HEADERS)
        if submissionid:
            headers["submissionid"] = submissionid
        r = self.sess.post(url, headers=headers, json=body, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _get(self, url: str) -> Dict[str, Any]:
        r = self.sess.get(url, headers={"accept": "application/json"}, timeout=self.timeout)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {"_text": r.text}

    def retrieve_addr_init(self) -> Dict[str, Any]:
        return self._post(URL_INIT, {}, submissionid=SBM_INIT)

    def is_dev_system(self) -> Dict[str, Any]:
        return self._get(URL_DEV)

    def sso_check(self) -> Dict[str, Any]:
        body = {"userId": "", "userMngSeqno": "0", "name": "", "autoLogin": "Y"}
        return self._post(URL_SSO, body)

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

# -------- cache wrappers --------
@st.cache_data(show_spinner=False)
def cached_init() -> List[str]:
    client = KepcoClient()
    _ = client.is_dev_system()   # 초기 핸드셰이크(옵션)
    _ = client.sso_check()       # 인증상태 확인(옵션)
    data = client.retrieve_addr_init()
    return extract_sido(data)

@st.cache_data(show_spinner=False)
def cached_si(addr_do: str) -> List[str]:
    client = KepcoClient()
    res = client.retrieve_addr_gbn(GBN["si"], addr_do=addr_do)
    return extract_field(res, RESP_KEY["si"])

@st.cache_data(show_spinner=False)
def cached_gu(addr_do: str, addr_si: str) -> List[str]:
    client = KepcoClient()
    res = client.retrieve_addr_gbn(GBN["gu"], addr_do=addr_do, addr_si=addr_si)
    return extract_field(res, RESP_KEY["gu"])

@st.cache_data(show_spinner=False)
def cached_lidong(addr_do: str, addr_si: str, addr_gu: str) -> List[str]:
    client = KepcoClient()
    res = client.retrieve_addr_gbn(GBN["lidong"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu)
    return extract_field(res, RESP_KEY["lidong"])

@st.cache_data(show_spinner=False)
def cached_li(addr_do: str, addr_si: str, addr_gu: str, addr_lidong: str) -> List[str]:
    client = KepcoClient()
    res = client.retrieve_addr_gbn(GBN["li"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu, addr_lidong=addr_lidong)
    return extract_field(res, RESP_KEY["li"])

@st.cache_data(show_spinner=False)
def cached_jibun(addr_do: str, addr_si: str, addr_gu: str, addr_lidong: str, addr_li: str) -> List[str]:
    client = KepcoClient()
    res = client.retrieve_addr_gbn(GBN["jibun"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu,
                                   addr_lidong=addr_lidong, addr_li=addr_li, addr_jibun="")
    return extract_field(res, RESP_KEY["jibun"])

# -------- UI --------
def main():
    st.title("🔌 한전 신·재생e 주소/지번 조회")
    st.caption("프로세스: retrieveAddrInit → isDevSystem → ssoCheck → retrieveAddrGbn(시→군/구→읍/면/동→리→지번)")

    # 0) 시/도 selectbox (addr_do) — ★ 수정 포인트
    with st.spinner("시/도 목록 불러오는 중..."):
        sido_options = cached_init()
    if not sido_options:
        st.error("시/도 목록을 불러오지 못했습니다.")
        return

    # 기본값(예시)을 목록에 있으면 그걸로, 없으면 0번으로
    default_do = "강원특별자치도" if "강원특별자치도" in sido_options else sido_options[0]
    addr_do = st.selectbox("도(시/도)", options=sido_options, index=sido_options.index(default_do))

    # 1) 시 (gbn=0)
    si_options = cached_si(addr_do) if addr_do else []
    if not si_options:
        st.warning("선택한 시/도에 시 목록이 없습니다.")
        return
    default_si = "강릉시" if "강릉시" in si_options else si_options[0]
    addr_si = st.selectbox("시", options=si_options, index=si_options.index(default_si))

    # 2) 구/군 (gbn=1)
    gu_options = cached_gu(addr_do, addr_si) if addr_si else []
    default_gu = "-기타지역" if "-기타지역" in gu_options else (gu_options[0] if gu_options else "")
    addr_gu = st.selectbox("군/구(또는 -기타지역)", options=gu_options, index=gu_options.index(default_gu) if default_gu else 0)

    # 3) 읍/면/동 (gbn=2)
    lidong_options = cached_lidong(addr_do, addr_si, addr_gu) if addr_gu else []
    default_lidong = "강동면" if "강동면" in lidong_options else (lidong_options[0] if lidong_options else "")
    addr_lidong = st.selectbox("읍/면/동", options=lidong_options, index=lidong_options.index(default_lidong) if default_lidong else 0)

    # 4) 리 (gbn=3)
    li_options = cached_li(addr_do, addr_si, addr_gu, addr_lidong) if addr_lidong else []
    default_li = "모전리" if "모전리" in li_options else (li_options[0] if li_options else "")
    addr_li = st.selectbox("리", options=li_options, index=li_options.index(default_li) if default_li else 0)

    # 5) 지번 (gbn=4) — 한전 등록 "특정 지번" 목록
    jibun_options = cached_jibun(addr_do, addr_si, addr_gu, addr_lidong, addr_li) if addr_li else []
    st.success(f"지번 {len(jibun_options)}개 조회")
    if jibun_options:
        selected_jibun = st.selectbox("지번", options=jibun_options, index=0)
        st.write(f"선택한 지번: **{selected_jibun}**")

    st.caption("셀렉트박스는 상위 선택이 바뀌면 자동으로 다시 조회됩니다(캐시 활용).")

if __name__ == "__main__":
    main()
