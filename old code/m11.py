import pandas as pd
import requests
import folium
from folium import plugins
import re

# ==============================================================================
# [BLOCK 0] 팝업 표시용 엑셀 열(Column) 매핑
# ==============================================================================
COL_MAIN_OFFICE   = '주사업장'           
COL_PHONE         = '전화번호'           
COL_SITE_MANAGER  = '사업장담당자명직위' 
COL_MANAGER_PHONE = '사업장담당자연락처' 
COL_EMAIL         = '담당자이메일'       

# ==============================================================================
# [BLOCK 1] 사용자 설정 (USER CONFIGURATION)
# ==============================================================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx'

sector_icon_color_map = {
    '사업서비스업': 'red', 
    '창고업': 'blue',          
    '육상화물 취급업': 'orange', 
    '건설업': 'purple', 
    '제조업': 'green', 
    '기타의 사업': 'cadetblue'
}

BATTERY_ICONS = {1: 'battery-empty', 2: 'battery-quarter', 3: 'battery-half', 4: 'battery-three-quarters', 5: 'battery-full'}
ICON_9_NAME = 'ban' 

# ==============================================================================
# [BLOCK 2] 데이터 준비 및 지도 초기화
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

df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl')
df = df.fillna('정보없음')

df['차수_temp'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
max_round_val = df['차수_temp'].max()

df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

# 지도 생성 (클러스터 객체 생성 코드를 삭제하여 레이어 메뉴 선 문제를 해결)
m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11)

# ==============================================================================
# [BLOCK 3] 요원별 순수 레이어(FeatureGroup) 생성
# ==============================================================================
agent_layer_dict = {}
agents = df_map['수행요원'].unique()

for agent in agents:
    # MarkerCluster 대신 FeatureGroup을 사용하여 마커가 뭉치지 않게 설정
    agent_layer_dict[agent] = {
        'unvisited': folium.FeatureGroup(name=f"{agent}: 방문전", show=True).add_to(m),
        'visited': folium.FeatureGroup(name=f"{agent}: 진행중", show=True).add_to(m)
    }

# ==============================================================================
# [BLOCK 4] 팝업 스타일 및 공통 변수 설정
# ==============================================================================
POPUP_FONT = "'Malgun Gothic', sans-serif"
POPUP_WIDTH = 280; TITLE_SIZE = "18px"; BODY_SIZE = "16px"; FOOTER_SIZE = "16px"; BTN_TEXT_SIZE = "18px"
LINK_COLOR = "#0022ff"; EMAIL_COLOR = "#228b22"

# ==============================================================================
# [BLOCK 5] 마커 생성 및 레이어 배정 로직 (중복 제거 통합)
# ==============================================================================
for _, row in df_map.iterrows():
    # 1. 기초 데이터 추출
    v_count = row.get('방문회차', 0); spec_field = str(row.get('특화분야', ''))
    disaster = row.get('재해여부', 0); agent_name = row.get('수행요원', '미지정')
    current_sector = str(row.get('중업종', '')); lat, lon = row['위도'], row['경도']
    
    main_office = row.get(COL_MAIN_OFFICE, '정보없음'); phone = row.get(COL_PHONE, '정보없음')
    site_manager = row.get(COL_SITE_MANAGER, '정보없음'); manager_phone = row.get(COL_MANAGER_PHONE, '정보없음')
    email = str(row.get(COL_EMAIL, '정보없음')).strip(); email_link = f"mailto:{email}" if email != '정보없음' else "#"
    tmap_url = f"tmap://route?goalname={row['사업장명_공사장명']}&goalx={lon}&goaly={lat}"
    kakao_url = f"kakaomap://route?ep={lat},{lon}&by=CAR"
    d_display = f"⚠️재해발생({disaster}건)" if disaster != 0 else "✅무재해"; d_color = "red" if disaster != 0 else "blue"

    # 2. 스타일 결정
    if v_count == 0:
        m_color = 'gray' if row['차수_temp'] == max_round_val else 'lightgray'
        i_name = 'gear' if '제조' in spec_field else 'building' if '기타' in spec_field else 'flash'
        i_color = sector_icon_color_map.get(current_sector, 'white') if disaster == 0 else 'black'
    elif 1 <= v_count <= 5:
        m_color = 'darkblue' if '제조' in spec_field else 'darkgreen' if '기타' in spec_field else 'orange'
        i_name = BATTERY_ICONS.get(v_count, 'battery-full'); i_color = 'black' if disaster != 0 else 'white'
    elif v_count == 9:
        m_color = 'lightgray'; i_name = ICON_9_NAME; i_color = 'black' if disaster != 0 else 'white'
    else: continue

    # 3. 팝업 HTML
    popup_html = f"""<div style="width:{POPUP_WIDTH}px; font-family:{POPUP_FONT}; line-height:1.8; padding:5px;">
        <h3 style="margin:0 0 8px 0;"><span style="color:#888; font-size:13px;">[{main_office}]</span><br>
        <b style="font-size:{TITLE_SIZE}; color:#000;">{row['사업장명_공사장명']}</b></h3>
        <hr style="margin:8px 0; border:0; border-top:2px solid #444;">
        <div style="font-size:{BODY_SIZE};">
            <b>대표번호:</b> <a href="tel:{phone}" style="color:{LINK_COLOR}; font-weight:bold;">{phone}</a><br>
            <b>담당자명:</b> <span style="color:#000; font-weight:bold;">{site_manager}</span><br>
            <b>담당자폰:</b> <a href="tel:{manager_phone}" style="color:{LINK_COLOR}; font-weight:bold;">{manager_phone}</a><br>
            <b>이메일:</b> <a href="{email_link}" style="color:{EMAIL_COLOR}; font-weight:bold;">{email}</a>
        </div>
        <div style="margin-top:15px; display:flex; gap:8px;">
            <a href="{tmap_url}" style="background-color:#0022FF; color:white; padding:10px; border-radius:6px; font-size:{BTN_TEXT_SIZE}; font-weight:bold; flex:1; text-align:center; text-decoration:none;">T맵</a>
            <a href="{kakao_url}" style="background-color:#FAE100; color:#3C1E1E; padding:10px; border-radius:6px; font-size:{BTN_TEXT_SIZE}; font-weight:bold; flex:1; text-align:center; text-decoration:none;">카카오맵</a>
        </div>
        <hr style="margin:12px 0; border:0; border-top:1px solid #eee;">
        <div style="font-size:{FOOTER_SIZE}; color:#333;">
            <b>주소:</b> {row['현장주소']}<br><b>분야:</b> {spec_field} / <b>업종:</b> {current_sector}<br>
            <b>방문:</b> {v_count}회 / <span style="color:{d_color}; font-weight:bold;">{d_display}</span>
        </div>
    </div>"""

    # 4. 마커 생성 및 배정 (마커를 단 한 번만 생성하여 레이어에 넣습니다)
    marker = folium.Marker(
        location=[lat, lon],
        icon=folium.Icon(color=m_color, icon=i_name, icon_color=i_color, prefix='fa'),
        popup=folium.Popup(popup_html, max_width=POPUP_WIDTH+20),
        tooltip=folium.Tooltip(row['사업장명_공사장명'], permanent=True, direction='top', offset=(0, -20))
    )

    if v_count == 0 or v_count == 9: 
        marker.add_to(agent_layer_dict[agent_name]['unvisited'])
    elif 1 <= v_count <= 5: 
        marker.add_to(agent_layer_dict[agent_name]['visited'])

# ==============================================================================
# [BLOCK 6] 레이어 컨트롤 UI 
# ==============================================================================
folium.LayerControl(collapsed=True).add_to(m)

# ==============================================================================
# [BLOCK 7] 자바스크립트 및 CSS 스타일
# ==============================================================================
# 줌 레벨에 따라 툴팁(이름표)을 끄고 켜는 스크립트 (중괄호 이중화 처리 완료)
zoom_logic = f"""
<script>
    function setupZoomLogic() {{
        var map = {m.get_name()};
        var mapContainer = map.getContainer();
        
        function updateZoom() {{
            var currentZoom = map.getZoom();
            if (currentZoom < 14) {{
                mapContainer.classList.add('hide-tooltips');
            }} else {{
                mapContainer.classList.remove('hide-tooltips');
            }}
        }}
        map.on('zoomend', updateZoom);
        updateZoom();
    }}
    window.addEventListener('load', setupZoomLogic);
</script>
<style>
    .hide-tooltips .leaflet-tooltip {{ display: none !important; }}
</style>
"""

close_button_style = """
<style>
    .leaflet-popup-close-button {
        width: 35px !important; height: 35px !important;
        font-size: 28px !important; line-height: 35px !important;
        color: #555 !important; font-weight: bold !important;
    }
</style>
"""

m.get_root().html.add_child(folium.Element(zoom_logic))
m.get_root().header.add_child(folium.Element(close_button_style))

# ==============================================================================
# [BLOCK 8] 최종 결과물 저장
# ==============================================================================
m.save('최종_업무지도_완성본.html')
print("✨ [성공] 뭉침 방지 및 모든 수정사항이 반영된 지도가 생성되었습니다.")