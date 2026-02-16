import pandas as pd
import requests
import folium
import re
import os

# ==========================================
# 1. 환경 설정 및 데이터 로드
# ==========================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx'

def get_coordinates(address):
    """카카오 API 좌표 변환"""
    if pd.isna(address) or address == "": return None, None
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if res.get('documents'):
            return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
    except: pass
    return None, None

# 엑셀 데이터 로드
df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl')

# 최고 차수 추출 로직
df['차수_num'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
max_round = df['차수_num'].max()

# ==========================================
# 2. 지능형 마커 설정 로직 (개선안 반영)
# ==========================================
def get_marker_settings(row):
    """
    [Logic First] 가독성 개선을 위한 스타일 결정 함수
    - 우선순위 1: 방문회차 9 (강렬한 레드 + 경고 아이콘)
    - 우선순위 2: 일반 데이터 (차수에 따른 그레이스케일 + 업종 아이콘)
    """
    # 1. 방문회차가 9인 경우 (긴급/경고)
    if row.get('방문회차') == 9:
        return {
            'color': 'gray',           # 핀 색상을 빨간색으로 변경 (인지력 극대화)
            'icon': 'exclamation-triangle', # 경고 삼각형 아이콘
            'icon_color': 'red'    # 대비를 위한 노란색 아이콘
        }
    
    # 2. 일반 데이터 (기존 로직 유지)
    # 핀 색상 (최고차수: 검정, 나머지: 연회색)
    pin_color = 'black' if row['차수_num'] == max_round else 'lightgray'
    
    # D열(특화분야) 아이콘 선택
    special_field = str(row.get('특화분야', ''))
    if '제조' in special_field:
        icon_shape = 'industry'
    elif '기타' in special_field:
        icon_shape = 'building'
    else:
        icon_shape = 'circle'
        
    return {
        'color': pin_color,
        'icon': icon_shape,
        'icon_color': 'white'
    }

# ==========================================
# 3. 지도 시각화
# ==========================================
print("🚀 개선된 시각화 로직으로 지도를 생성합니다...")
df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11)

for _, row in df_map.iterrows():
    # 개선된 스타일 설정 가져오기
    style = get_marker_settings(row)
    
    folium.Marker(
        location=[row['위도'], row['경도']],
        icon=folium.Icon(
            color=style['color'],
            icon=style['icon'],
            prefix='fa',
            icon_color=style['icon_color']
        ),
        popup=folium.Popup(f"""
            <div style="width:200px">
                <h4 style="margin-bottom:5px;">{row['사업장명_공사장명']}</h4>
                <b>방문회차: {row['방문회차']}회</b><br>
                차수: {row['배정차수']}<br>
                특화분야: {row['특화분야']}
            </div>
        """, max_width=250),
        tooltip=f"방문 {row['방문회차']}회 - {row['사업장명_공사장명']}"
    ).add_to(m)

# 저장
output_name = '시각개선_현황지도2.html'
m.save(output_name)
print(f"✅ 개선 완료! 빨간색 핀(경고)을 확인해 보세요: {output_name}")