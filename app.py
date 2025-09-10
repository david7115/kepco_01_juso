import requests
import streamlit as st
from typing import List, Optional, Dict, Any

st.set_page_config(page_title="한전 신·재생e 주소/지번 조회", page_icon="🔌", layout="centered")

BASE = "https://online.kepco.co.kr"
URL_INIT = f"{BASE}/ew/cpct/retrieveAddrInit"   # (1) 시/도
URL_DEV  = f"{BASE}/isDevSystem"                # (1-2) 환경 확인
URL_SSO  = f"{BASE}/ssoCheck"                   # (1-3) SSO 체크
URL_GBN  = f"{BASE}/ew/cpct/retrieveAddrGbn"    # (2~6) 단계별

# 공통 헤더(네트워크 캡처 반영)
COMMON_HEADERS = {
    "accept": "application/json",
    "content-type": 'application/json; charset="UTF-8"',
    "referer": "https://online.kepco.co.kr/EWM092D00",
    "user-agent": "Mozilla/5.0",
}
SBM_INIT = "mf_wfm_layout_sbm_retrieveAddrInit"
SBM_GBN  = "mf_wfm_layout_sbm_retrieveAddrGbn"

# gbn 매핑 (사용자 제공 자료)
#  - 시: gbn=0
#  - 구/군: gbn=1
#  - 읍/면/동: gbn=2
#  - 리: gbn=3
#  - 지번 목록: gbn=4
GBN = dict(si=0, gu=1, lidong=2, li=3, jibun=4)

# 응답 키 (사용자 제공 자료로 확정)
RESP_KEY = dict(
    sido_list="dlt_sido",
    si="ADDR_SI",
    gu="ADDR_GU",
    lidong="ADDR_LIDONG",
    li="ADDR_LI",
    jibun="ADDR_JIBUN",
)

def split_tokenize(s: str):
    tok, buf = [], ""
    for ch in s:
        if ch.isdigit():
            buf += ch
        else:
            if buf:
                tok.append(buf); buf = ""
            tok.append(ch)
    if buf:
        tok.append(buf)
    return tok

def nat_sort_uniq(xs: List[str]) -> List[str]:
    xs = [x for x in xs if x]
    return sorted(set(xs), key=lambda x: [int(t) if t.isdigit() else t for t in split_tokenize(x)])

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

    # 1) 시/도
    def retrieve_addr_init(self) -> Dict[str, Any]:
        # 요청 페이로드: 없음
        return self._post(URL_INIT, {}, submissionid=SBM_INIT)

    # 1-2) 환경확인
    def is_dev_system(self) -> Dict[str, Any]:
        return self._get(URL_DEV)

    # 1-3) SSO 체크
    def sso_check(self) -> Dict[str, Any]:
        body = {"userId": "", "userMngSeqno": "0", "name": "", "autoLogin": "Y"}
        return self._post(URL_SSO, body)

    # 2~6) 단계별 조회
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

def extract_list_from_sido(data: Dict[str, Any]) -> List[str]:
    # retrieveAddrInit 응답: dlt_sido[*].ADDR_DO
    rows = data.get("dlt_sido") or []
    vals = []
    for r in rows:
        if isinstance(r, dict) and r.get("ADDR_DO"):
            vals.append(str(r["ADDR_DO"]).strip())
    return nat_sort_uniq(vals)

def extract_list(data: Dict[str, Any], field_key: str) -> List[str]:
    # retrieveAddrGbn 응답: dlt_addrGbn[*].<field_key>
    rows = data.get("dlt_addrGbn") or []
    vals = []
    for r in rows:
        if isinstance(r, dict) and r.get(field_key):
            vals.append(str(r[field_key]).strip())
    return nat_sort_uniq(vals)

def main():
    st.title("🔌 한전 신·재생e 주소/지번 조회")
    st.caption("프로세스: retrieveAddrInit → isDevSystem → ssoCheck → retrieveAddrGbn(시→군/구→읍/면/동→리→지번)")

    with st.form("addr_form"):
        st.subheader("주소(기본값은 예시)")
        c1, c2 = st.columns(2)
        with c1:
            addr_do = st.text_input("도(시/도)", value="강원특별자치도")
            addr_gu = st.text_input("군/구", value="-기타지역")
            addr_li = st.text_input("리", value="모전리")
        with c2:
            addr_si = st.text_input("시", value="강릉시")
            addr_lidong = st.text_input("읍/면/동", value="강동면")
        btn = st.form_submit_button("순서대로 조회")

    if not btn:
        st.info("값을 확인하고 버튼을 눌러주세요.")
        return

    client = KepcoClient()

    # 1) 시/도
    with st.spinner("1) 시/도(retrieveAddrInit)"):
        init_res = client.retrieve_addr_init()
        sido_list = extract_list_from_sido(init_res)
        st.success(f"시/도 {len(sido_list)}개")
        with st.expander("응답 미리보기"):
            st.json(init_res)

    # 1-2) isDevSystem
    with st.spinner("1-2) 환경 확인(isDevSystem)"):
        dev_res = client.is_dev_system()
        st.success(f"isDevSystem: {dev_res.get('devPassword', '')}")
        with st.expander("응답 미리보기"):
            st.json(dev_res)

    # 1-3) ssoCheck
    with st.spinner("1-3) SSO 체크(ssoCheck)"):
        sso_res = client.sso_check()
        st.success(f"loginChk={sso_res.get('loginChk','')}")
        with st.expander("응답 미리보기"):
            st.json(sso_res)

    # 2) 시 (gbn=0)
    with st.spinner("2) 시 목록(retrieveAddrGbn gbn=0)"):
        si_res = client.retrieve_addr_gbn(GBN["si"], addr_do=addr_do)
        si_list = extract_list(si_res, RESP_KEY["si"])
        st.write(f"시 {len(si_list)}개")
        if si_list:
            st.selectbox("시(서버 응답값)", si_list, index=si_list.index(addr_si) if addr_si in si_list else 0, key="sel_si")
        with st.expander("응답 미리보기"):
            st.json(si_res)

    # 3) 구/군 (gbn=1)
    with st.spinner("3) 구/군 목록(retrieveAddrGbn gbn=1)"):
        gu_res = client.retrieve_addr_gbn(GBN["gu"], addr_do=addr_do, addr_si=addr_si)
        gu_list = extract_list(gu_res, RESP_KEY["gu"])
        st.write(f"구/군 {len(gu_list)}개")
        if gu_list:
            st.selectbox("구/군(서버 응답값)", gu_list, index=gu_list.index(addr_gu) if addr_gu in gu_list else 0, key="sel_gu")
        with st.expander("응답 미리보기"):
            st.json(gu_res)

    # 4) 읍/면/동 (gbn=2)
    with st.spinner("4) 읍/면/동 목록(retrieveAddrGbn gbn=2)"):
        lidong_res = client.retrieve_addr_gbn(GBN["lidong"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu)
        lidong_list = extract_list(lidong_res, RESP_KEY["lidong"])
        st.write(f"읍/면/동 {len(lidong_list)}개")
        if lidong_list:
            st.selectbox("읍/면/동(서버 응답값)", lidong_list, index=lidong_list.index(addr_lidong) if addr_lidong in lidong_list else 0, key="sel_lidong")
        with st.expander("응답 미리보기"):
            st.json(lidong_res)

    # 5) 리 (gbn=3)
    with st.spinner("5) 리 목록(retrieveAddrGbn gbn=3)"):
        li_res = client.retrieve_addr_gbn(GBN["li"], addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu, addr_lidong=addr_lidong)
        li_list = extract_list(li_res, RESP_KEY["li"])
        st.write(f"리 {len(li_list)}개")
        if li_list:
            st.selectbox("리(서버 응답값)", li_list, index=li_list.index(addr_li) if addr_li in li_list else 0, key="sel_li")
        with st.expander("응답 미리보기"):
            st.json(li_res)

    # 6) 지번 (gbn=4) — 한전이 등록한 "특정 지번 목록"
    with st.spinner("6) 지번 목록(retrieveAddrGbn gbn=4)"):
        jibun_res = client.retrieve_addr_gbn(
            GBN["jibun"],
            addr_do=addr_do, addr_si=addr_si, addr_gu=addr_gu,
            addr_lidong=addr_lidong, addr_li=addr_li, addr_jibun=""
        )
        jibun_list = extract_list(jibun_res, RESP_KEY["jibun"])
        st.success(f"지번 {len(jibun_list)}개")
        if jibun_list:
            st.selectbox("지번 선택", jibun_list, index=0, key="sel_jibun")
        with st.expander("응답 미리보기"):
            st.json(jibun_res)

    st.caption("※ 응답 키/gbn이 바뀌면 RESP_KEY/GBN 상수만 수정하면 됩니다.")
    
if __name__ == "__main__":
    main()
