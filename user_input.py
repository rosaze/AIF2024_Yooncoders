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

def get_original_news_url(news_url):
    """네이버 뉴스 링크에서 원본 기사 URL 추출"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(news_url, headers=headers, allow_redirects=True)
        print(f"URL 변환 응답 코드: {response.status_code}")
        print(f"변환된 URL: {response.url}")
        return response.url
    except Exception as e:
        print(f"URL 변환 중 오류: {e}")
        return news_url  # 오류 발생 시 원본 URL 반환
    


def handle_article_selection(item):
    """기사 선택 처리 콜백 함수"""
    logger.info("Article selection callback triggered")
    logger.info(f"Selected article title: {item['title']}")
    
    news_url = item['link']
    try:
        content = extract_news_content(news_url)
        if content:
            logger.info("Successfully extracted article content")
            st.session_state.article_content = content
            st.session_state.selected_article = {
                'title': item['title'],
                'url': news_url
            }
            st.session_state.page = 'generate_webtoon'
            return True
        else:
            logger.error("Failed to extract article content")
            return False
    except Exception as e:
        logger.error(f"Error processing article: {e}")
        return False

def render_news_search():
    """뉴스 검색 페이지 렌더링"""
    st.title("뉴스 검색")
    
    search_option = st.radio("검색 방식 선택", ["키워드 검색", "URL 직접 입력"])
    
    if search_option == "키워드 검색":
        search_query = st.text_input("검색어를 입력하세요:")
        sort_option = st.selectbox("정렬 방식", ["정확도순", "최신순"], key="sort")
        
        if search_query:  # 검색어가 있으면 자동으로 검색
            logger.info(f"Searching for query: {search_query}")
            sort_param = 'sim' if sort_option == "정확도순" else 'date'
            results = search_news(
                search_query, 
                sort_param,
                st.session_state.get('NAVER_CLIENT_ID'),
                st.session_state.get('NAVER_CLIENT_SECRET')
            )
            
            if results and 'items' in results:
                for idx, item in enumerate(results['items']):
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"### {item['title']}")
                        st.write(item['description'])
                    
                    with col2:
                        # 간단한 숫자 키 사용
                        if st.button("웹툰 만들기", key=f"btn_{idx}"):
                            logger.info(f"Button clicked for article {idx}")
                            news_url = item['link']
                            
                            with st.spinner("기사를 불러오는 중..."):
                                try:
                                    content = extract_news_content(news_url)
                                    if content:
                                        st.session_state.article_content = content
                                        st.session_state.selected_article = {
                                            'title': item['title'],
                                            'url': news_url
                                        }
                                        st.session_state.page = 'generate_webtoon'
                                        logger.info("Successfully processed article")
                                        st.rerun()
                                    else:
                                        st.error("기사 내용을 가져올 수 없습니다.")
                                        logger.error("Failed to extract content")
                                except Exception as e:
                                    st.error(f"오류 발생: {str(e)}")
                                    logger.error(f"Error processing article: {e}")
    
    else:  # URL 직접 입력
        article_url = st.text_input("뉴스 기사 URL을 입력하세요:")
        if article_url:
            if st.button("기사 가져오기", key="fetch_url"):
                with st.spinner("기사를 불러오는 중..."):
                    content = extract_news_content(article_url)
                    if content:
                        st.session_state.article_content = content
                        st.session_state.selected_article = {
                            "title": "직접 입력한 기사",
                            "url": article_url
                        }
                        st.success("기사 내용을 성공적으로 가져왔습니다!")
                        
                        if st.button("웹툰 만들기", key="create_webtoon"):
                            st.session_state.page = 'generate_webtoon'
                            st.rerun()
                    else:
                        st.error("기사를 가져오는데 실패했습니다.")

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
        article = soup.select_one('#dic_area')
        
        if not article:
            article = soup.select_one('#articeBody')
            
        if article:
            for tag in article.select('script, iframe, style'):
                tag.decompose()
            
            content = article.get_text(strip=True)
            content = re.sub(r'\s+', ' ', content)
            logger.info(f"Successfully extracted content (length: {len(content)})")
            return content
        
        logger.warning("No article content found")
        return None
        
    except Exception as e:
        logger.error(f"Error in extract_news_content: {e}")
        return None