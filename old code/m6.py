import pandas as pd
import requests
import folium
import re
import os

# ==============================================================================
# [USER CONFIGURATION - 사용자 설정 영역]
# ==============================================================================

# 1. 파일 및 API 설정
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx'

# 2. 방문회차(1~5회) 상세 설정 (배터리 게이지 시각화)
VISIT_CONFIG = {
    1: {'color': 'lightblue',  'icon': 'battery-empty',          'icon_color': 'white'},
    2: {'color': 'cadetblue',  'icon': 'battery-quarter',        'icon_color': 'white'},
    3: {'color': 'blue',       'icon': 'battery-half',           'icon_color': 'white'},
    4: {'color': 'darkblue',   'icon': 'battery-three-quarters', 'icon_color': 'white'},
    5: {'color': 'darkpurple', 'icon': 'battery-full',           'icon_color': 'white'}
}

# 3. 기타 상태 아이콘 및 색상 설정 (0회차 업종구분 및 9회차 경고)
ICON_CONFIG = {
    # [제조] 방문 0회일 때 아이콘 및 내부색
    'MANUFACTURING': {'icon': 'gear', 'icon_color': 'white'}, 
    # [기타] 방문 0회일 때 아이콘 및 내부색
    'OTHERS':        {'icon': 'building', 'icon_color': 'white'},
    # [그외] 방문 0회일 때 아이콘 및 내부색
    'DEFAULT':       {'icon': 'bank',     'icon_color': 'white'},
    # [경고] 방문 9회일 때 (사용자 요청: 회색 핀, X 아이콘)
    'WARNING':       {'icon': 'close',    'icon_color': 'black', 'color': 'lightgray', 'opacity': 0.5}    

}

# 4. 배정차수 테마 (방문 0회일 때만 적용되는 무채색 규칙)
THEME_COLORS = {
    'MAX_ROUND': 'gray',   # 최고 차수 (예: 2차) -> 진한 회색
    'SUB_ROUND': 'lightgray'   # 일반 차수 (예: 1차) -> 연한 회색
}

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

# 파일 로드
try:
    df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl')
except:
    try:
        df = pd.read_csv(FILE_NAME, encoding='utf-8-sig')
    except:
        df = pd.read_csv(FILE_NAME, encoding='cp949')

# 배정차수 숫자 분석
df['차수_int'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
max_round_val = df['차수_int'].max()

print("🚀 방문 0회차 무채색 테마 및 9회차 X마커 로직 적용 중...")
df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11)

for _, row in df_map.iterrows():
    v_count = row.get('방문회차', 0)
    spec_field = str(row.get('특화분야', ''))
    
    # --- [마커 결정 로직] ---
    
    # 1. 방문회차 9 (경고/종료)
    if v_count == 9:
        style = ICON_CONFIG['WARNING']
        m_color = style.get('color', 'gray')
        i_name = style['icon']
        i_color = style['icon_color']
        
    # 2. 방문회차 1~5 (진행 중 - 배터리 색상 적용)
    elif 1 <= v_count <= 5:
        conf = VISIT_CONFIG.get(v_count)
        m_color = conf['color']
        i_name = conf['icon']
        i_color = conf['icon_color']
        
    # 3. 방문회차 0 (미방문 - 철저히 무채색 적용)
    else:
        # [핵심 수정] 배정차수가 최고라도 0회차면 무조건 Gray 계열로 지정
        m_color = THEME_COLORS['MAX_ROUND'] if row['차수_int'] == max_round_val else THEME_COLORS['SUB_ROUND']
        
        if '제조' in spec_field:
            target = ICON_CONFIG['MANUFACTURING']
        elif '기타' in spec_field:
            target = ICON_CONFIG['OTHERS']
        else:
            target = ICON_CONFIG['DEFAULT']
        i_name = target['icon']
        i_color = target['icon_color']

    folium.Marker(
        location=[row['위도'], row['경도']],
        icon=folium.Icon(color=m_color, icon=i_name, prefix='fa', icon_color=i_color),
        popup=f"<b>{row['사업장명_공사장명']}</b><br>방문회차: {v_count}회",
        tooltip=row['사업장명_공사장명']
    ).add_to(m)

m.save('무채색테마_현황지도.html')
print(f"✨ 완료! '무채색테마_현황지도.html' 파일을 확인하세요.")