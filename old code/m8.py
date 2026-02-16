import pandas as pd
import requests
import folium
from folium import plugins
import re
import os

# ==============================================================================
# [USER CONFIGURATION - 모든 시각화 속성을 여기서 제어하세요]
# ==============================================================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx'

# 1. 핀(Marker) 전체 크기 및 투명도 설정
MARKER_WIDTH   = 35    # 핀 가로
MARKER_HEIGHT  = 48    # 핀 세로
GLOBAL_OPACITY = 1.0   # 투명도 (0.0~1.0)

# 2. 내부 아이콘 크기 설정 (px)
SIZE_0 = 15            # 0회차 (업종)
SIZE_NUM = 18          # 1~5회차 (배터리)
SIZE_9 = 22            # 9회차 (X)

# 3. 방문회차(1~5회) 상세 설정
VISIT_CONFIG = {
    1: {'color': 'lightblue',  'icon': 'battery-empty',          'i_color': 'white'},
    2: {'color': 'cadetblue',  'icon': 'battery-quarter',        'i_color': 'white'},
    3: {'color': 'blue',       'icon': 'battery-half',           'i_color': 'white'},
    4: {'color': 'darkblue',   'icon': 'battery-three-quarters', 'i_color': 'white'},
    5: {'color': 'darkpurple', 'icon': 'battery-full',           'i_color': 'white'}
}

# 4. 기타 상태 및 9회차 경고 설정
ICON_CONFIG = {
    'MANUFACTURING': {'icon': 'industry', 'i_color': 'white'}, 
    'OTHERS':        {'icon': 'building', 'i_color': 'white'},
    'DEFAULT':       {'icon': 'bank',     'i_color': 'white'},
    'WARNING':       {'icon': 'close',    'i_color': 'black', 'color': 'lightgray', 'opacity': 0.5}
}

# 5. 무채색 테마 (방문 0회 전용)
THEME_COLORS = {
    'MAX_ROUND': 'gray',       # 최고 배정차수 (진한 회색)
    'SUB_ROUND': 'lightgray'   # 일반 배정차수 (연한 회색)
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
    print(f"✅ 엑셀 파일 로드 성공")
except Exception as e:
    print(f"❌ 파일 로드 실패: {e}")
    exit()

# --- 데이터 분석 및 오타 수정 구간 ---
# 1. '배정차수' 열에서 숫자만 추출하여 '차수_temp' 열 생성
df['차수_temp'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)

# 2. '차수_temp'를 참조하여 최고 차수 계산 (KeyError 해결)
max_round_val = df['차수_temp'].max()
print(f"📊 분석 결과: 현재 최고 배정차수는 {max_round_val}차입니다.")

# 좌표 변환
print("🚀 주소 변환 및 마커 생성 중...")
df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11)

for _, row in df_map.iterrows():
    v_count = row.get('방문회차', 0)
    spec_field = str(row.get('특화분야', ''))
    
    # 스타일 결정 로직
    if v_count == 9:
        conf = ICON_CONFIG['WARNING']
        m_color, i_name, i_color, i_size = conf['color'], conf['icon'], conf['i_color'], SIZE_9
        m_alpha = conf.get('opacity', GLOBAL_OPACITY)
    elif 1 <= v_count <= 5:
        conf = VISIT_CONFIG.get(v_count)
        m_color, i_name, i_color, i_size = conf['color'], conf['icon'], conf['i_color'], SIZE_NUM
        m_alpha = GLOBAL_OPACITY
    else:
        # 배정차수 비교 시 수정된 임시 열 이름(차수_temp) 사용
        m_color = THEME_COLORS['MAX_ROUND'] if row['차수_temp'] == max_round_val else THEME_COLORS['SUB_ROUND']
        m_alpha = GLOBAL_OPACITY
        target = ICON_CONFIG['MANUFACTURING'] if '제조' in spec_field else ICON_CONFIG['OTHERS'] if '기타' in spec_field else ICON_CONFIG['DEFAULT']
        i_name, i_color, i_size = target['icon'], target['i_color'], SIZE_0

    icon = plugins.BeautifyIcon(
        icon=i_name,
        icon_shape='marker',
        background_color=m_color,
        border_color='white',
        text_color=i_color,
        icon_size=[MARKER_WIDTH, MARKER_HEIGHT],
        icon_anchor=[MARKER_WIDTH / 2, MARKER_HEIGHT],
        inner_icon_style=f'font-size:{i_size}px; line-height:{MARKER_HEIGHT*0.65}px;'
    )

    folium.Marker(
        location=[row['위도'], row['경도']],
        icon=icon,
        opacity=m_alpha,
        popup=f"<b>{row['사업장명_공사장명']}</b><br>방문회차: {v_count}회",
        tooltip=row['사업장명_공사장명']
    ).add_to(m)

m.save('최종_업무현황지도.html')
print(f"✨ 작업 완료! '최종_업무현황지도.html' 파일을 확인해 주세요.")