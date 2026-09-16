import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="서울 100년 기온 변화 분석",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_and_process_data():
    """GitHub에서 서울 기온 데이터를 불러와 연도별 통계 데이터로 가공합니다."""
    url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/seoul.csv"
    
    # 인코딩 호환성을 고려한 데이터 읽기
    try:
        df = pd.read_csv(url, encoding='utf-8')
    except Exception:
        df = pd.read_csv(url, encoding='cp949')
    
    # 열 이름 공백 제거 및 통일
    df.columns = df.columns.str.strip()
    
    rename_map = {}
    for col in df.columns:
        if '날짜' in col:
            rename_map[col] = '날짜'
        elif '평균' in col:
            rename_map[col] = '평균기온'
        elif '최저' in col:
            rename_map[col] = '최저기온'
        elif '최고' in col:
            rename_map[col] = '최고기온'
    
    df = df.rename(columns=rename_map)
    
    # 날짜 파싱 및 결측치 처리
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜'])
    df['연도'] = df['날짜'].dt.year
    
    for col in ['평균기온', '최저기온', '최고기온']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    df = df.dropna(subset=['평균기온'])
    
    # 연도별 집계
    yearly_df = df.groupby('연도').agg(
        연평균기온=('평균기온', 'mean'),
        연평균최저기온=('최저기온', 'mean'),
        연평균최고기온=('최고기온', 'mean'),
        일최고기온=('최고기온', 'max'),
        일최저기온=('최저기온', 'min'),
        데이터수=('평균기온', 'count')
    ).reset_index()
    
    # 관측 일수가 부족한 연도 제외 (300일 이상만)
    yearly_df = yearly_df[yearly_df['데이터수'] >= 300].copy()
    
    # 소수점 둘째 자리 정리
    for col in ['연평균기온', '연평균최저기온', '연평균최고기온']:
        yearly_df[col] = yearly_df[col].round(2)
        
    return yearly_df

try:
    yearly_data = load_and_process_data()
    data_loaded = True
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    data_loaded = False

st.title("🌡️ 서울 100년 기온 변화 분석 시각화")
st.markdown("""
지난 100여 년간 서울의 기온 데이터(`seoul.csv`)를 바탕으로 **연평균 기온의 변화 추이와 기후변화 경향**을 한눈에 확인할 수 있는 대시보드입니다.
""")
st.divider()

if data_loaded:
    min_year_available = int(yearly_data['연도'].min())
    max_year_available = int(yearly_data['연도'].max())

    st.sidebar.header("⚙️ 분석 설정")
    
    # 연도 범위 선택 슬라이더
    selected_years = st.sidebar.slider(
        "📅 조회 연도 범위 선택",
        min_value=min_year_available,
        max_value=max_year_available,
        value=(min_year_available, max_year_available)
    )
    
    # 이동평균 선택
    ma_window = st.sidebar.selectbox(
        "📈 이동평균(Moving Average) 주기",
        options=[3, 5, 10, 20],
        index=2,
        help="단기 변동성을 완화하여 장기적인 기온 변화 흐름을 파악합니다."
    )
    
    # 추세선 및 옵션 토글
    show_trendline = st.sidebar.checkbox("📐 선형 추세선(Trendline) 표시", value=True)
    show_min_max = st.sidebar.checkbox("📊 연평균 최저/최고 기온 함께 보기", value=False)
    
    # 선택 연도 범위 필터링
    filtered_df = yearly_data[
        (yearly_data['연도'] >= selected_years[0]) & 
        (yearly_data['연도'] <= selected_years[1])
    ].copy()
    
    # 이동평균 계산
    filtered_df[f'{ma_window}년_이동평균'] = filtered_df['연평균기온'].rolling(window=ma_window, min_periods=1).mean().round(2)

    col1, col2, col3, col4 = st.columns(4)
    
    avg_temp_overall = filtered_df['연평균기온'].mean()
    warmest_row = filtered_df.loc[filtered_df['연평균기온'].idxmax()]
    coldest_row = filtered_df.loc[filtered_df['연평균기온'].idxmin()]
    
    # 100년 추세 변화량 계산 (선형 회귀 기울기 이용)
    if len(filtered_df) > 1:
        z = np.polyfit(filtered_df['연도'], filtered_df['연평균기온'], 1)
        temp_rise_per_decade = z[0] * 10
        total_change = z[0] * (filtered_df['연도'].max() - filtered_df['연도'].min())
    else:
        temp_rise_per_decade = 0
        total_change = 0

    with col1:
        st.metric(
            label="📌 기간 내 전체 연평균 기온",
            value=f"{avg_temp_overall:.2f} ℃"
        )
        
    with col2:
        st.metric(
            label="🔥 가장 따뜻했던 해",
            value=f"{int(warmest_row['연도'])}년",
            delta=f"{warmest_row['연평균기온']} ℃"
        )
        
    with col3:
        st.metric(
            label="❄️ 가장 추웠던 해",
            value=f"{int(coldest_row['연도'])}년",
            delta=f"{coldest_row['연평균기온']} ℃",
            delta_color="inverse"
        )
        
    with col4:
        st.metric(
            label="📈 10년당 평균 기온 상승폭",
            value=f"+{temp_rise_per_decade:.2f} ℃",
            delta=f"총 약 {total_change:+.2f} ℃ 변화"
        )

    st.markdown("---")

    st.subheader(f"📊 서울 연평균 기온 추이 ({selected_years[0]}년 ~ {selected_years[1]}년)")
    
    fig = go.Figure()

    # 연평균기온 라인
    fig.add_trace(go.Scatter(
        x=filtered_df['연도'],
        y=filtered_df['연평균기온'],
        mode='lines+markers',
        name='연평균 기온',
        line=dict(color='#FFA500', width=2),
        marker=dict(size=5),
        hovertemplate='%{x}년: <b>%{y} ℃</b><extra></extra>'
    ))

    # 이동평균선
    fig.add_trace(go.Scatter(
        x=filtered_df['연도'],
        y=filtered_df[f'{ma_window}년_이동평균'],
        mode='lines',
        name=f'{ma_window}년 이동평균',
        line=dict(color='#DC2626', width=3, dash='solid'),
        hovertemplate='%{x}년 (' + str(ma_window) + '년 평균): <b>%{y} ℃</b><extra></extra>'
    ))

    # 추세선
    if show_trendline and len(filtered_df) > 1:
        trend_y = z[0] * filtered_df['연도'] + z[1]
        fig.add_trace(go.Scatter(
            x=filtered_df['연도'],
            y=trend_y,
            mode='lines',
            name='장기 추세선 (Linear Trend)',
            line=dict(color='#2563EB', width=2, dash='dash'),
            hovertemplate='%{x}년 추세값: <b>%{y:.2f} ℃</b><extra></extra>'
        ))

    # 옵션: 최저/최고 기온선 추가
    if show_min_max:
        fig.add_trace(go.Scatter(
            x=filtered_df['연도'],
            y=filtered_df['연평균최고기온'],
            mode='lines',
            name='연평균 최고기온',
            line=dict(color='#EF4444', width=1, dash='dot'),
            opacity=0.7
        ))
        fig.add_trace(go.Scatter(
            x=filtered_df['연도'],
            y=filtered_df['연평균최저기온'],
            mode='lines',
            name='연평균 최저기온',
            line=dict(color='#3B82F6', width=1, dash='dot'),
            opacity=0.7
        ))

    # 차트 레이아웃 설정
    fig.update_layout(
        xaxis_title="연도 (Year)",
        yaxis_title="기온 (℃)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=40, r=40, t=40, b=40),
        height=520,
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("💡 기후 분석 주요 발견")
        st.markdown(f"""
        - **장기적인 온난화 경향**: 선택한 기간({selected_years[0]}년~{selected_years[1]}년) 동안 서울의 연평균 기온은 **10년당 약 {temp_rise_per_decade:.2f}℃**씩 꾸준히 상승했습니다.
        - **도시화 및 지구온난화 영향**: 2000년대 이후의 연평균 기온은 20세기 초·중반에 비해 뚜렷하게 높은 수치를 기록하고 있습니다.
        - **최대/최소 기록**: 관측 기간 중 가장 온난했던 해는 **{int(warmest_row['연도'])}년({warmest_row['연평균기온']}℃)** 이며, 가장 추웠던 해는 **{int(coldest_row['연도'])}년({coldest_row['연평균기온']}℃)** 입니다.
        """)

    with col_right:
        st.subheader("📋 연도별 상세 데이터")
        display_cols = ['연도', '연평균기온', '연평균최저기온', '연평균최고기온']
        st.dataframe(
            filtered_df[display_cols].sort_values(by='연도', ascending=False),
            hide_index=True,
            use_container_width=True,
            height=250
        )
        
        # CSV 다운로드 버튼
        csv_data = filtered_df[display_cols].to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 데이터 CSV 다운로드",
            data=csv_data,
            file_name=f"seoul_temperature_{selected_years[0]}_{selected_years[1]}.csv",
            mime="text/csv"
        )

st.markdown("---")
st.caption("Data Source: GitHub repository greatsong/modudata (seoul.csv) | Created for Streamlit Cloud deployment.")
