import pandas as pd
import requests
import folium
from folium import plugins
import re

# ==============================================================================
# [USER CONFIGURATION]
# ==============================================================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx'

# 1. 중업종별 컬러 매핑
sector_color_map = {'사업서비스업': 'red', '창고업': 'darkblue', '육상화물 취급업': 'orange', '건설업': 'darkpurple', '제조업': 'darkgreen', '기타의 사업': 'cadetblue'}

# 2. 아이콘 설정
BATTERY_ICONS = {1: 'battery-empty', 2: 'battery-quarter', 3: 'battery-half', 4: 'battery-three-quarters', 5: 'battery-full'}
ICON_9_NAME = 'ban'
OPACITY_9 = 0.3

# ==============================================================================

def get_coordinates(address):
    if pd.isna(address) or address == "": return None, None
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if res.get('documents'): return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
    except: pass
    return None, None

# 데이터 로드 및 전처리
df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl')
df['차수_temp'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
max_round_val = df['차수_temp'].max()

# 좌표 변환
df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

# 지도 생성
m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11)







# ------------------------------------------------------------------------------
# [레이어 설정] - 방문회차별 그룹과 수행요원별 그룹 생성
# ------------------------------------------------------------------------------
# 1. 방문회차 그룹 (큰 카테고리)
fg_0 = folium.FeatureGroup(name="🏠 미방문 (0회차)", show=True)
fg_1_5 = folium.FeatureGroup(name="🚚 진행중 (1~5회차)", show=True)
fg_9 = folium.FeatureGroup(name="🚫 종결/거부 (9회차)", show=True)

# 2. 수행요원별 그룹 (이름별로 동적 생성)
agent_groups = {}
agents = df_map['수행요원'].unique()
for agent in agents:
    # 각 요원별 레이어를 생성하고 지도에 추가
    agent_groups[agent] = folium.FeatureGroup(name=f"👤 담당: {agent}", show=True)

# 마커 배치 로직
for _, row in df_map.iterrows():
    v_count = row.get('방문회차', 0)
    spec_field = str(row.get('특화분야', ''))
    disaster = row.get('재해여부', 0)
    agent_name = row.get('수행요원', '미지정')
    current_sector = str(row.get('중업종', ''))

    # [스타일 결정 - 이전 로직 유지]
    if v_count == 0:
        m_color = 'gray' if row['차수_temp'] == max_round_val else 'lightgray'
        i_name = 'gear' if '제조' in spec_field else 'building' if '기타' in spec_field else 'flash'
        i_color = sector_color_map.get(current_sector, 'white') if disaster == 0 else 'black'
        m_opacity = 1.0
        target_fg = fg_0 # 0회차 그룹에 배정
    elif 1 <= v_count <= 5:
        m_color = 'darkblue' if '제조' in spec_field else 'darkgreen' if '기타' in spec_field else 'orange'
        i_name = BATTERY_ICONS.get(v_count, 'battery-full')
        i_color = 'black' if disaster != 0 else 'white'
        m_opacity = 1.0
        target_fg = fg_1_5 # 1~5회차 그룹에 배정
    elif v_count == 9:
        m_color = 'lightgray'; i_name = ICON_9_NAME; i_color = 'black' if disaster != 0 else 'white'
        m_opacity = OPACITY_9
        target_fg = fg_9 # 9회차 그룹에 배정
    else:
        continue

    # 마커 생성
    marker = folium.Marker(
        location=[row['위도'], row['경도']],
        icon=folium.Icon(color=m_color, icon=i_name, icon_color=i_color, prefix='fa'),
        opacity=m_opacity,
        popup=f"요원: {agent_name}<br>방문: {v_count}회",
        tooltip=row['사업장명_공사장명']
    )

    # [중요] 마커를 해당 '방문회차 레이어'와 '수행요원 레이어' 양쪽에 추가하고 싶지만, 
    # Folium 구조상 한 마커는 하나의 부모만 가질 수 있으므로 '방문회차' 그룹에 먼저 넣습니다.
    # 만약 요원별로만 보고 싶다면 요원 레이어에 넣습니다. 
    # 여기서는 '수행요원' 레이어를 메인으로 사용하여 사람별로 껐다 켰다 하게 구성합니다.
    marker.add_to(agent_groups[agent_name])
    
# 모든 요원 그룹을 지도에 추가
for group in agent_groups.values():
    group.add_to(m)

# 회차 그룹도 추가 (필요 시 선택)
# fg_0.add_to(m); fg_1_5.add_to(m); fg_9.add_to(m)

# 레이어 컨트롤러 추가
folium.LayerControl(collapsed=False).add_to(m)

m.save('레이어_필터_업무지도.html')
print("✨ 수행요원별 온오프 기능이 포함된 지도가 생성되었습니다.")