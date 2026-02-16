import pandas as pd
import requests
import folium
from folium.features import DivIcon
import re
import os

# ==========================================
# 1. 환경 설정 및 데이터 로드
# ==========================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx'

# 최고 차수 분석
df['차수_num'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
max_round = df['차수_num'].max()

# ==========================================
# 2. 커스텀 마커 생성 도구함
# ==========================================

def get_number_marker(row):
    """방문회차 1~5: 카카오 공식 숫자 마커 (블루)"""
    val = int(row['방문회차'])
    idx = val - 1  # 1번 숫자는 index 0
    y_offset = (idx * 46) + 10  # 사용자 제공 공식 좌표
    
    icon_html = f"""
    <div style="width: 36px; height: 37px; 
                background: url('https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_number_blue.png') no-repeat;
                background-position: 0px -{y_offset}px;
                background-size: 36px 691px;">
    </div>"""
    return DivIcon(icon_size=(36, 37), icon_anchor=(18, 37), html=icon_html)

def get_x_marker_html():
    """방문회차 9: 기존 핀 모양 유지 + 빨간 X"""
    return f"""
    <div style="position: relative; width: 30px; height: 42px;">
        <svg viewBox="0 0 32 42" xmlns="http://www.w3.org/2000/svg" style="width: 30px; height: 42px;">
            <path fill="white" stroke="red" stroke-width="2.5" 
                  d="M16 0C7.2 0 0 7.2 0 16c0 12 16 26 16 26s16-14 16-26c0-8.8-7.2-16-16-16z"/>
        </svg>
        <div style="position: absolute; top: 5px; left: 50%; transform: translateX(-50%);
                    color: red; font-size: 18px; font-weight: 900; font-family: Arial;">X</div>
    </div>"""

# ==========================================
# 3. 지도 생성 및 마킹 실행
# ==========================================
print("🚀 데이터 분석 및 지도 생성을 시작합니다...")
df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11)

for _, row in df_map.iterrows():
    v_count = row.get('방문회차', 0)
    
    # [분기 로직]
    if v_count == 9:
        # 1순위: 방문회차 9 (X 표시)
        icon = DivIcon(icon_size=(30, 42), icon_anchor=(15, 42), html=get_x_marker_html())
    
    elif 1 <= v_count <= 5:
        # 2순위: 방문회차 1~5 (숫자 마커)
        icon = get_number_marker(row)
        
    else:
        # 3순위: 방문회차 0 또는 기타 (기본 그레이스케일 + 업종 아이콘)
        pin_color = 'black' if row['차수_num'] == max_round else 'lightgray'
        special = str(row.get('특화분야', ''))
        shape = 'industry' if '제조' in special else 'building' if '기타' in special else 'circle'
        icon = folium.Icon(color=pin_color, icon=shape, prefix='fa', icon_color='white')

    folium.Marker(
        location=[row['위도'], row['경도']],
        icon=icon,
        popup=folium.Popup(f"<b>{row['사업장명_공사장명']}</b><br>방문회차: {v_count}회", max_width=250),
        tooltip=f"{row['사업장명_공사장명']} ({v_count}회)"
    ).add_to(m)

# 결과 저장
output = '최종_하이브리드_현황지도.html'
m.save(output)
print(f"✨ 작업 완료! 결과 파일: {os.path.abspath(output)}")