import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

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

def extract_news_info(article_url):
    """네이버 뉴스 기사 내용 추출"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(article_url, headers=headers)
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
            return content
        else:
            return "기사 내용을 찾을 수 없습니다."
            
    except Exception as e:
        st.error(f"기사 내용 추출 중 오류 발생: {str(e)}")
        return None

def render_news_search():
    """뉴스 검색 페이지 렌더링"""
    st.title("뉴스 검색")
    
    search_option = st.radio("검색 방식 선택", ["키워드 검색", "URL 직접 입력"])
    
    if search_option == "키워드 검색":
        search_query = st.text_input("검색어를 입력하세요:")
        sort_option = st.selectbox("정렬 방식", ["정확도순", "최신순"], key="sort")
        
        if st.button("검색") and search_query:
            sort_param = 'sim' if sort_option == "정확도순" else 'date'
            results = search_news(
                search_query, 
                sort_param,
                st.session_state.get('NAVER_CLIENT_ID'),
                st.session_state.get('NAVER_CLIENT_SECRET')
            )
            
            if results and 'items' in results:
                st.session_state.search_results = results['items']
                for idx, item in enumerate(results['items']):
                    st.markdown(f"### {item['title']}")
                    st.write(item['description'])
                    if st.button(f"이 기사로 웹툰 만들기", key=f"select_{idx}"):
                        st.session_state.selected_article = item
                        st.session_state.article_content = extract_news_info(item['originallink'])
                        st.session_state.page = "generate_webtoon"
                        st.rerun()
    
    else:  # URL 직접 입력
        article_url = st.text_input("뉴스 기사 URL을 입력하세요:")
        if st.button("기사 가져오기") and article_url:
            content = extract_news_info(article_url)
            if content:
                st.session_state.article_content = content
                st.success("기사 내용을 성공적으로 가져왔습니다!")
                st.markdown("### 가져온 기사 내용")
                st.text_area("", value=content, height=300)
                
                if st.button("이 기사로 웹툰 만들기"):
                    st.session_state.page = "generate_webtoon"
                    st.rerun()
            else:
                st.error("기사 내용을 가져오는데 실패했습니다.")