import streamlit as st
import sqlite3
import pandas as pd
import os
import platform
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# ---------------------------------------------------------
# 1. 초기 설정 및 데이터베이스 연결
# ---------------------------------------------------------
st.set_page_config(page_title="공공자전거 데이터 대시보드", layout="wide")
st.title("🚲 공공자전거 이용 분석 대시보드")
st.markdown("SQLite 데이터베이스와 Streamlit을 활용한 데이터 분석 결과입니다.")

# DB 파일 존재 여부 확인 (친절한 에러 메시지)
db_path = "bicycle.db"
if not os.path.exists(db_path):
    st.error("🚨 앗! 'bicycle.db' 파일을 찾을 수 없습니다.")
    st.warning("app.py와 같은 폴더에 'bicycle.db' 파일이 있는지 다시 한 번 확인해 주세요!")
    st.stop() # DB가 없으면 여기서 실행을 멈춥니다.

# DB 쿼리 실행을 위한 도우미 함수
@st.cache_data # 데이터를 캐싱하여 앱 속도를 높입니다.
def load_data(query):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# 한글 폰트 설정 (워드클라우드용)
def get_font_path():
    system_name = platform.system()
    if system_name == "Windows":
        return "c:/Windows/Fonts/malgun.ttf" # 맑은 고딕
    elif system_name == "Darwin":
        return "/System/Library/Fonts/Supplemental/AppleGothic.ttf" # 맥 애플고딕
    else:
        return None

# ---------------------------------------------------------
# 차트 1. 인기있는 대여소 Top 5 (워드클라우드)
# ---------------------------------------------------------
st.header("1️⃣ 인기있는 대여소 Top 5")
sql1 = """
SELECT 대여소.보관소명, SUM(이용정보.이용건수) AS 총이용건수 
FROM 대여소 
JOIN 이용정보 ON 대여소.대여소번호 = 이용정보.대여소번호
GROUP BY 대여소.대여소번호, 대여소.보관소명
ORDER BY 총이용건수 DESC
LIMIT 5
"""
df1 = load_data(sql1)

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("**② 사용한 SQL**")
    st.code(sql1, language="sql")
    
    st.markdown("**③ 인사이트**")
    st.info("- 대중교통(지하철역)과 인접하거나 큰 공원 근처의 대여소 이용량이 압도적으로 높습니다.\n- 출퇴근 시간대 라스트 마일(Last Mile) 이동 수단으로 활발히 사용되고 있음을 유추할 수 있습니다.")

with col2:
    st.markdown("**① 시각화 (워드클라우드)**")
    # 워드클라우드를 위한 딕셔너리 변환 (보관소명: 총이용건수)
    word_dict = dict(zip(df1['보관소명'], df1['총이용건수']))
    
    font_path = get_font_path()
    wc = WordCloud(font_path="H2GTRM.TTF", width=400, height=400, background_color='white', colormap='Set2')
    wordcloud = wc.generate_from_frequencies(word_dict)
    
    fig1, ax1 = plt.subplots(figsize=(5, 5))
    ax1.imshow(wordcloud, interpolation='bilinear')
    ax1.axis('off')
    st.pyplot(fig1)

st.divider() # 구분선

# ---------------------------------------------------------
# 차트 2. 강수량에 따른 대여량 변화 (꺾은선 + 막대그래프)
# ---------------------------------------------------------
st.header("2️⃣ 강수량에 따른 대여량 변화")
sql2 = """
SELECT 
    이용정보.대여일자 AS 년월,
    강수량.강수량,
    SUM(이용정보.이용건수) AS 대여량
FROM 이용정보
JOIN 강수량 
ON 이용정보.대여일자 = 강수량.년월
GROUP BY 이용정보.대여일자, 강수량.강수량
ORDER BY 이용정보.대여일자
"""
df2 = load_data(sql2)

col3, col4 = st.columns([1, 1])

with col3:
    st.markdown("**① 시각화 (이중축 그래프)**")
    # Plotly 이중축 그래프 생성
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 막대 그래프 (강수량)
    fig2.add_trace(go.Bar(x=df2['년월'], y=df2['강수량'], name="강수량", opacity=0.5, marker_color='blue'), secondary_y=False)
    # 꺾은선 그래프 (이용건수)
    fig2.add_trace(go.Scatter(x=df2['년월'], y=df2['대여량'], name="총 대여량", mode='lines+markers', marker_color='red'), secondary_y=True)
    
    fig2.update_layout(title_text="강수량과 자전거 대여량 추이", height=400)
    fig2.update_yaxes(title_text="강수량", secondary_y=False)
    fig2.update_yaxes(title_text="총 대여량 (건)", secondary_y=True)
    
    st.plotly_chart(fig2, use_container_width=True)

with col4:
    st.markdown("**② 사용한 SQL**")
    st.code(sql2, language="sql")
    
    st.markdown("**③ 인사이트**")
    st.warning("- 강수량이 높은 월(여름철 장마 등)에는 자전거 대여량이 급격히 감소하는 역상관관계가 나타납니다.\n- 날씨가 자전거 이용에 가장 큰 영향을 미치는 외부 요인임을 확인할 수 있습니다.")

st.divider()

# ---------------------------------------------------------
# 차트 3. 성별별 이용도가 높은 자치구 Top 5 (누적 막대그래프)
# ---------------------------------------------------------
st.header("3️⃣ 성별별 이용도가 높은 자치구 Top 5")
sql3 = """
SELECT * FROM (
    SELECT 
        대여소.자치구,
        이용정보.성별,
        SUM(이용정보.이용건수) AS 총이용건수,
        RANK() OVER (
            PARTITION BY 이용정보.성별       -- 성별이 바뀔 때마다 순위 초기화
            ORDER BY SUM(이용정보.이용건수) DESC
        ) AS 순위
    FROM 대여소, 이용정보
    WHERE 대여소.대여소번호 = 이용정보.대여소번호
        AND 이용정보.성별 IS NOT NULL
    GROUP BY 대여소.자치구, 이용정보.성별
)
WHERE 순위 <= 5
ORDER BY 성별, 순위
"""
df3 = load_data(sql3)

col5, col6 = st.columns([1, 1])

with col5:
    st.markdown("**② 사용한 SQL**")
    st.code(sql3, language="sql")
    
    st.markdown("**③ 인사이트**")
    st.success("- 상위 5개 자치구 모두 대체로 남성(M)의 이용 비율이 여성(F)보다 약간 더 높게 나타납니다.\n- 한강 자전거도로가 잘 구축되어 있거나 평지가 많은 자치구가 Top 5에 포진해 있습니다.")

with col6:
    st.markdown("**① 시각화 (그룹 막대그래프)**")
    # Plotly 그룹 막대 그래프
    fig3 = px.bar(df3, x='자치구', y='총이용건수', color='성별', barmode='group',
                  color_discrete_map={'M': 'royalblue', 'F': 'lightcoral'},
                  title="Top 5 자치구의 성별 이용건수")
    st.plotly_chart(fig3, use_container_width=True)

st.balloons() # 축하 애니메이션!
