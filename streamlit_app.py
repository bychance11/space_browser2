"""
Space Browser — Streamlit 호스팅 래퍼
---------------------------------------------------
HTML 데모를 그대로 iframe으로 띄웁니다.
데이터(위키 조회수 상위)는 방문자 브라우저가 열 때마다 실시간으로 받아오므로,
배포 후 따로 갱신하지 않아도 매일 최신 데이터가 표시됩니다.

배포 방법(요약):
1) 이 파일 + requirements.txt + 사용할 *.html 들을 GitHub 저장소에 올림
2) share.streamlit.io 접속 → 저장소 연결 → Main file 에 streamlit_app.py 지정 → Deploy
"""
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(page_title="Space Browser", layout="wide")

# 여백/메뉴 제거해서 화면을 꽉 채움
st.markdown(
    "<style>.block-container{padding:0 !important;max-width:100% !important;}"
    "header,#MainMenu,footer{visibility:hidden;}</style>",
    unsafe_allow_html=True,
)

# 보여줄 모드들 (저장소에 있는 파일만 자동으로 표시)
FILES = {
    "🌌 밤하늘 (데스크톱)": "space-browser-nightsky.html",
    "📱 밤하늘 (모바일)": "space-browser-nightsky-mobile.html",
    "🚀 우주 유영": "space-browser-live.html",
    "🗿 스톤헨지 (모바일)": "space-browser-stonehenge-mobile.html",
}
avail = {k: v for k, v in FILES.items() if Path(__file__).with_name(v).exists()}

if not avail:
    st.error("표시할 HTML 파일을 찾지 못했습니다. streamlit_app.py와 같은 폴더에 *.html을 올려주세요.")
    st.stop()

choice = st.sidebar.radio("모드 선택", list(avail.keys()))
st.sidebar.caption("데이터는 페이지를 열 때마다 위키백과에서 실시간으로 받아옵니다 (매일 자동 갱신).")

html = Path(__file__).with_name(avail[choice]).read_text(encoding="utf-8")
components.html(html, height=860, scrolling=False)
