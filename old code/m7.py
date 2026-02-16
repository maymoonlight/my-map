import pandas as pd
import requests
import folium
import re

# ==============================================================================
# [USER CONFIGURATION - 사용자가 직접 수정하는 영역]
# ==============================================================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx'


# ------------------------------------------------------------------------------
# [Folium 공식 지원 컬러 리스트] - 아래 명칭만 사용 가능합니다.
# ------------------------------------------------------------------------------
# 1. 기본 계열: 'red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred'
# 2. 파스텔/밝은 계열: 'beige', 'pink', 'lightblue', 'lightgreen', 'lightgray'
# 3. 어두운/전문 계열: 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple'
# 4. 무채색 계열: 'white', 'gray', 'black'
# ------------------------------------------------------------------------------


# 1. 중업종별 내부 아이콘 컬러 설정 (방문회차 0일 때 적용)
sector_color_map = {
    '사업서비스업': 'red',
    '창고업': 'blue',
    '육상화물 취급업': 'orange',
    '건설업': 'purple',
    '제조업': 'darkgreen',
    '기타의 사업': 'cadetblue'
}

# 2. 방문회차별 배터리 아이콘 맵핑 (1~5회)
BATTERY_ICONS = {
    1: 'battery-empty',
    2: 'battery-quarter',
    3: 'battery-half',
    4: 'battery-three-quarters',
    5: 'battery-full'
}

# 3. 방문회차 9 (특이사항/종결) 전용 설정
ICON_9_NAME = 'ban'    # 아이콘 모양 (추천: ban, times, exclamation-triangle)
OPACITY_9   = 0.5      # 9회차일 때의 불투명도 (0.0 ~ 1.0)

# 4. 배정차수 무채색 테마 (방문 0회 전용 배경색)
THEME_COLORS = {'MAX_ROUND': 'gray', 'SUB_ROUND': 'lightgray'}
# ==============================================================================

def get_coordinates(address):
    if pd.isna(address) or address == "": return None, None
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if res.get('documents'):
            return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
    except: pass
    return None, None

# 데이터 로드
df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl')

# 배정차수 숫자 추출
df['차수_temp'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
max_round_val = df['차수_temp'].max()

# 좌표 변환
df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11)

for _, row in df_map.iterrows():
    v_count = row.get('방문회차', 0)
    spec_field = str(row.get('특화분야', ''))
    disaster = row.get('재해여부', 0)
    current_sector = str(row.get('중업종', ''))
    
    # --- [Step 1] 배경색(color) 및 아이콘 모양(icon) 결정 ---
    if v_count == 0:
        # 0회차: 무채색 배경 + 업종 아이콘
        m_color = THEME_COLORS['MAX_ROUND'] if row['차수_temp'] == max_round_val else THEME_COLORS['SUB_ROUND']
        if '제조' in spec_field: i_name = 'gear'
        elif '기타' in spec_field: i_name = 'building'
        else: i_name = 'flash'
        m_opacity = 1.0
    elif 1 <= v_count <= 5:
        # 1~5회차: 업종 배경 + 배터리 아이콘
        if '제조' in spec_field: m_color = 'darkblue'   #제조업종 핀의 배경컬러 blue / darkblue
        elif '기타' in spec_field: m_color = 'darkgreen'    #기타업종 핀의 배경컬러 blue / darkgreen
        else: m_color = 'orange'                        #예외업종 핀의 배경컬러 orange
        i_name = BATTERY_ICONS.get(v_count, 'battery-full')
        m_opacity = 1.0
    elif v_count == 9:
        # 9회차: 사용자 정의 아이콘 및 불투명도 적용
        m_color = 'gray'
        i_name = ICON_9_NAME
        m_opacity = OPACITY_9
    else:
        m_color = 'gray'
        i_name = 'info-circle'
        m_opacity = 1.0

    # --- [Step 2] 내부 아이콘 색상(icon_color) 결정 (우선순위 로직) ---
    if disaster != 0:
        i_color = 'black'        # 재해 발생 시 무조건 Black
    elif v_count == 0:
        i_color = sector_color_map.get(current_sector, 'white') # 0회차 업종별 색상
    else:
        i_color = 'white'        # 진행 중이거나 재해 없으면 White

    # 마커 추가 (Folium 오리지널 핀 형태 유지)
    folium.Marker(
        location=[row['위도'], row['경도']],
        icon=folium.Icon(
            color=m_color,
            icon=i_name,
            icon_color=i_color,
            prefix='fa'
        ),
        opacity=m_opacity,
        popup=f"<b>{row['사업장명_공사장명']}</b>",
        tooltip=row['사업장명_공사장명']
    ).add_to(m)

m.save('최종_업무자동화_지도.html')
print("✨ 9회차 아이콘 및 투명도 설정까지 포함된 최종 지도가 완성되었습니다!")