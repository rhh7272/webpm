import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import pandas as pd

# 페이지 기본 설정
st.set_page_config(page_title="뉴스 크롤러", page_icon="📰", layout="wide")

st.title("📰 웹 뉴스 크롤러")
st.markdown("""
선택한 국내 뉴스 채널에서 기사 링크를 자동으로 수집하고, 
각 페이지에 접속하여 **제목**을 추출하는 크롤러입니다.
""")

# ==========================================
# 1. 사이드바 설정 (확장 과제: 타임아웃, 재시도)
# ==========================================
st.sidebar.header("⚙️ 크롤러 상세 설정")
target_count = st.sidebar.number_input("수집할 기사 수", min_value=1, max_value=200, value=50, step=10)
timeout_sec = st.sidebar.slider("타임아웃 (초)", min_value=1, max_value=15, value=3, help="각 페이지 접속 대기 시간입니다.")
max_retries = st.sidebar.slider("실패 시 재시도 횟수", min_value=0, max_value=5, value=2, help="접속 실패 시 다시 시도할 횟수입니다.")

# ==========================================
# 2. 국내 뉴스 채널 선택 UI (체크박스)
# ==========================================
st.subheader("📡 방송/통신사 선택")
col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)
with col_b1:
    use_mbc = st.checkbox("MBC", value=False)
with col_b2:
    use_kbs = st.checkbox("KBS", value=False)
with col_b3:
    use_sbs = st.checkbox("SBS", value=False)
with col_b4:
    use_yonhap = st.checkbox("연합뉴스", value=True)
with col_b5:
    use_ytn = st.checkbox("YTN", value=False)

st.subheader("📰 주요 신문사 선택")
col_n1, col_n2, col_n3, col_n4, col_n5 = st.columns(5)
with col_n1:
    use_hani = st.checkbox("한겨레", value=True)
with col_n2:
    use_chosun = st.checkbox("조선일보")
with col_n3:
    use_joongang = st.checkbox("중앙일보")
with col_n4:
    use_donga = st.checkbox("동아일보")
with col_n5:
    use_khan = st.checkbox("경향신문")

st.markdown("---")
use_custom = st.checkbox("직접 입력 (기타 URL 추가)")
custom_url = ""
if use_custom:
    custom_url = st.text_input("수집할 사이트의 URL을 입력하세요:", value="https://news.ycombinator.com/")

# 체크된 채널들의 URL 리스트 생성
target_channels = []
# 방송/통신사
if use_mbc: target_channels.append(("MBC", "https://imnews.imbc.com/"))
if use_kbs: target_channels.append(("KBS", "https://news.kbs.co.kr/"))
if use_sbs: target_channels.append(("SBS", "https://news.sbs.co.kr/"))
if use_yonhap: target_channels.append(("연합뉴스", "https://www.yna.co.kr/"))
if use_ytn: target_channels.append(("YTN", "https://www.ytn.co.kr/"))
# 신문사
if use_hani: target_channels.append(("한겨레", "https://www.hani.co.kr/"))
if use_chosun: target_channels.append(("조선일보", "https://www.chosun.com/"))
if use_joongang: target_channels.append(("중앙일보", "https://www.joongang.co.kr/"))
if use_donga: target_channels.append(("동아일보", "https://www.donga.com/"))
if use_khan: target_channels.append(("경향신문", "https://www.khan.co.kr/"))
# 직접 입력
if use_custom and custom_url: target_channels.append(("직접 입력", custom_url))

# 중간 결과를 저장하기 위한 Session State 초기화
if 'crawled_data' not in st.session_state:
    st.session_state.crawled_data = []

# ==========================================
# 핵심 크롤링 함수 (확장 과제 반영)
# ==========================================
def fetch_url_with_retry(url, retries, timeout):
    """
    URL에 GET 요청을 보내고 HTML을 반환합니다.
    실패할 경우 설정된 횟수만큼 재시도(Retry)하며, 타임아웃(Timeout)을 적용합니다.
    """
    # 봇 차단을 피하기 위한 기본 User-Agent 헤더
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    for attempt in range(retries + 1):
        try:
            # 타임아웃 설정 적용
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status() # 200번대 응답이 아닐 경우 예외 발생
            return response.text
        except requests.RequestException as e:
            if attempt == retries:
                return None  # 최대 재시도 횟수 초과 시 None 반환
            time.sleep(1) # 실패 시 1초 대기 후 다시 시도
    return None

# ==========================================
# 화면 출력용 표 렌더링 함수 (에러 완벽 방지)
# ==========================================
def render_native_dataframe(df):
    """
    Streamlit 데이터프레임 내부의 파싱 오류(Internal Server Error)를 방지하기 위해
    순수 마크다운 테이블 문법을 사용하여 안전하고 깔끔하게 표를 렌더링합니다.
    채널명 컬럼이 추가되었습니다.
    """
    # 마크다운 표 헤더 (채널명 추가)
    md_table = "| No | 기사 제목 | 채널명 | 상태 |\n|:---:|:---|:---:|:---:|\n"
    
    for _, row in df.iterrows():
        # 표 형태나 링크가 깨지지 않도록 방해되는 마크다운 특수문자(|, [, ]) 모두 치환
        safe_title = str(row['제목']).replace('|', ' ').replace('[', ' ').replace(']', ' ').replace('\n', ' ')
        # 괄호나 공백 등이 포함된 URL도 정상 작동하도록 인코딩 처리
        safe_url = str(row['URL']).replace(' ', '%20').replace('(', '%28').replace(')', '%29')
        
        # [제목](URL) 포맷으로 마크다운 하이퍼링크 생성 및 표에 행 추가 (채널명 포함)
        md_table += f"| {row['No']} | [{safe_title}]({safe_url}) | **{row['채널명']}** | {row['상태']} |\n"
    
    # 완성된 마크다운 표 출력 (Streamlit이 자체적으로 예쁜 테이블 형태로 렌더링해 줍니다)
    st.markdown(md_table)

# ==========================================
# 메인 로직 실행 (버튼 클릭 시)
# ==========================================
# 버튼을 나란히 배치하기 위해 컬럼 사용
col1, col2 = st.columns([1, 9])
with col1:
    start_btn = st.button("🚀 크롤링 시작", type="primary")
with col2:
    stop_btn = st.button("🛑 중단")

# ------------------------------------------
# 중단 버튼 로직
# ------------------------------------------
if stop_btn:
    st.warning("사용자에 의해 크롤링이 중단되었습니다.")
    # 중간까지 수집된 데이터가 있다면 화면에 출력
    if st.session_state.crawled_data:
        st.info(f"중단 전까지 총 {len(st.session_state.crawled_data)}개의 기사를 수집했습니다.")
        df = pd.DataFrame(st.session_state.crawled_data)
        
        # URL 숨김 & 제목 클릭 가능한 깔끔한 마크다운 표 출력
        render_native_dataframe(df)
        
        # 다운로드는 원본 데이터(df) 사용 (URL과 제목 분리 보존)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 중간 결과 CSV로 다운로드",
            data=csv,
            file_name='crawled_news_partial.csv',
            mime='text/csv',
        )
    st.stop() # 더 이상 아래의 코드가 실행되지 않도록 완전 정지

# ------------------------------------------
# 크롤링 시작 로직
# ------------------------------------------
if start_btn:
    st.session_state.crawled_data = [] # 새로운 크롤링 시작 시 이전 결과 초기화
    
    if not target_channels:
        st.warning("수집할 뉴스 채널을 하나 이상 체크해주세요.")
    else:
        # UI 업데이트용 요소 준비
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # ------------------------------------------
        # 요구사항 1: 선택한 모든 채널에서 URL 목록 가져오기
        # ------------------------------------------
        status_text.info("1. 선택한 채널들에서 링크 목록을 수집 중입니다...")
        
        # 채널별로 링크를 따로 저장할 딕셔너리 준비
        channel_links = {channel_name: [] for channel_name, _ in target_channels}
        seen_urls = set() # 전체 중복 URL 방지용
        
        for channel_name, b_url in target_channels:
            main_html = fetch_url_with_retry(b_url, max_retries, timeout_sec)
            
            if not main_html:
                st.toast(f"⚠️ {channel_name} 접속 실패")
            else:
                soup = BeautifulSoup(main_html, 'html.parser')
                
                # 페이지 내의 모든 a 태그(링크) 추출
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    link_text = a_tag.get_text(strip=True)
                    # 상대 경로를 절대 경로로 변환
                    full_url = urljoin(b_url, href)
                    
                    # 유효한 http/https 링크인지 검사
                    # 한글 뉴스 제목은 길이가 짧을 수 있으므로 필터링 기준을 10자로 조정
                    if full_url.startswith('http') and full_url != b_url and len(link_text) > 10:
                        if full_url not in seen_urls:
                            seen_urls.add(full_url)
                            # 해당 채널의 리스트에 링크 추가
                            channel_links[channel_name].append(full_url)
        
        # ------------------------------------------
        # 수집할 기사 수를 채널별로 번갈아가며 분배 (라운드 로빈)
        # ------------------------------------------
        urls_to_crawl = []
        while len(urls_to_crawl) < target_count:
            added_in_this_round = False
            for channel_name, _ in target_channels:
                # 목표 개수를 채웠으면 즉시 중단
                if len(urls_to_crawl) >= target_count:
                    break
                
                # 해당 채널에 남은 링크가 있다면 앞에서부터 하나씩 꺼내기
                if channel_links[channel_name]:
                    url = channel_links[channel_name].pop(0)
                    urls_to_crawl.append((url, channel_name))
                    added_in_this_round = True
                    
            # 모든 채널의 링크를 다 소진했다면 더 이상 추가할 수 없으므로 루프 종료
            if not added_in_this_round:
                break

        total_collected = len(urls_to_crawl)
        
        if total_collected == 0:
            st.error("수집할 링크를 찾지 못했습니다. 사이트 구조가 변경되었거나 접근이 차단되었을 수 있습니다.")
        else:
            # ------------------------------------------
            # 요구사항 2 & 3: 각 URL 접속 및 제목 추출
            # ------------------------------------------
            for i, (url, channel_name) in enumerate(urls_to_crawl):
                # 진행 상태 업데이트
                status_text.info(f"2. 기사 수집 중... ({i+1}/{total_collected}) : [{channel_name}] {url}")
                
                # 각 링크 접속 시도
                html = fetch_url_with_retry(url, max_retries, timeout_sec)
                
                if html:
                    page_soup = BeautifulSoup(html, 'html.parser')
                    # HTML 문서에서 <title> 태그 추출
                    title_tag = page_soup.find('title')
                    if title_tag and title_tag.text:
                        title = title_tag.text.strip()
                    else:
                        title = "제목 태그 없음"
                    status = "성공"
                else:
                    title = "추출 실패"
                    status = "접속 실패 (에러/타임아웃)"
                    
                # session_state에 즉시 저장하여 중단 시점의 데이터를 보존 (채널명 추가)
                st.session_state.crawled_data.append({
                    "No": i + 1,
                    "제목": title,
                    "채널명": channel_name,
                    "URL": url,
                    "상태": status
                })
                
                # 진행률 바 업데이트
                progress_bar.progress((i + 1) / total_collected)
                
            status_text.success(f"🎉 총 {total_collected}개의 기사 제목 추출을 완료했습니다!")
            
            # 수집 결과를 데이터프레임으로 변환
            df = pd.DataFrame(st.session_state.crawled_data)
            
            # URL 숨김 & 제목 클릭 가능한 깔끔한 마크다운 표 출력 (채널명 포함)
            render_native_dataframe(df)
            
            # 다운로드는 원본 데이터(df) 사용 (URL과 제목 분리 보존)
            csv = df.to_csv(index=False).encode('utf-8-sig') # 엑셀에서 한글 깨짐 방지 utf-8-sig
            st.download_button(
                label="📥 결과를 CSV로 다운로드",
                data=csv,
                file_name='crawled_news_titles.csv',
                mime='text/csv',
            )