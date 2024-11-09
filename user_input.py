import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def search_news(query, sort='sim', client_id=None, client_secret=None):
    """네이버 뉴스 API를 통해 뉴스 검색"""
    url = f"https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {
        "query": query,
        "sort": sort,
        "display": 10
    }
    
    response = requests.get(url, headers=headers, params=params)
    return response.json() if response.status_code == 200 else None

def extract_news_content(url):
    """네이버 뉴스 기사 내용 추출"""
    logger.info(f"Extracting content from: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 여러 가능한 본문 영역을 순차적으로 시도
        article = soup.select_one('#dic_area') or soup.select_one('#articleBodyContents') or soup.select_one('.news_end')
        
        if article:
            for tag in article.select('script, iframe, style'):
                tag.decompose()
            
            content = article.get_text(strip=True)
            logger.info(f"Successfully extracted content (length: {len(content)})")
            return re.sub(r'\s+', ' ', content)
        
        logger.warning("No article content found in any known sections")
        return None

    except Exception as e:
        logger.error(f"Error in extract_news_content: {e}")
        return None


def render_news_search():
    """뉴스 검색 페이지 렌더링"""
    st.markdown("<h1 style='text-align: center;'>뉴스 검색</h1>", unsafe_allow_html=True)
    
    # 검색 옵션과 정렬 방식을 한 줄에 배치
    col1, col2 = st.columns([1, 1])
    with col1:
        search_option = st.radio("검색 방식 선택", ["키워드 검색", "URL 직접 입력"], label_visibility="collapsed", horizontal=True)
    with col2:
        #키워드 검색을 선택해쓸 떄만 정렬 방식 표시 
        if search_option == "키워드 검색":
            sort_option = st.selectbox("정렬 방식", ["정확도순", "최신순"], key="sort")

    if search_option == "키워드 검색":
        search_query = st.text_input("검색어를 입력하세요:")

        if search_query:
            sort_param = 'sim' if sort_option == "정확도순" else 'date'
            results = search_news(search_query, sort_param, st.session_state.get('NAVER_CLIENT_ID'), st.session_state.get('NAVER_CLIENT_SECRET'))
            
            if results and 'items' in results:
                for idx, item in enumerate(results['items']):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        article_title = item['title'].replace('<b>', '').replace('</b>', '')
                        article_url = item.get('originallink', item['link'])
                        st.markdown(f"### [{article_title}]({article_url})", unsafe_allow_html=True)
                        article_description = item['description'].replace('<b>', '').replace('</b>', '')
                        st.write(article_description)
                    
                    with col2:
                        if st.button("웹툰 만들기", key=f"btn_{idx}"):
                            news_url = item['link']
                            content = extract_news_content(news_url)
                            if content:
                                st.session_state.article_content = content
                                st.session_state.selected_article = {'title': item['title'], 'url': news_url}
                                st.session_state.page = 'generate_webtoon'
                                st.rerun()
                            else:
                                st.error("기사 내용을 가져올 수 없습니다.")
    else:  # URL 직접 입력
        article_url = st.text_input("뉴스 기사 URL을 입력하세요:")
        if article_url:
            if st.button("기사 가져오기"):
                content = extract_news_content(article_url)
                if content:
                    st.session_state.article_content = content
                    st.session_state.selected_article = {"title": "직접 입력한 기사", "url": article_url}
                    st.success("기사 내용을 성공적으로 가져왔습니다!")

                # 기사 내용 표시 (스크롤 가능)
                    st.text_area("기사 내용", value=st.session_state.article_content, height=300, max_chars=None)

                # 웹툰 만들기 버튼
                    if st.button("웹툰 만들기"):
                        st.session_state.page = 'generate_webtoon'
                        st.rerun()
                else:
                    st.error("기사를 가져오는데 실패했습니다.")