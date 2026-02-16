import pandas as pd
import requests
import folium
from folium import plugins
import re
import math 

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



# ------------------------------------------------------------------------------
# [Folium 공식 지원 컬러 리스트] - 아래 명칭만 사용 가능합니다.
# ------------------------------------------------------------------------------
# 1. 기본 계열: 'red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred'
# 2. 파스텔/밝은 계열: 'beige', 'pink', 'lightblue', 'lightgreen', 'lightgray'
# 3. 어두운/전문 계열: 'darkblue', 'darkgreen', 'cadetblue', 'darkpurple'
# 4. 무채색 계열: 'white', 'gray', 'black'
# ------------------------------------------------------------------------------


sector_icon_color_map = {
    '도소매 및 소비자용품수리업': 'beige', 
    '창고업': 'pink', 
    '육상화물취급업': 'lightblue', 
    '사업서비스업': 'lightgreen', 
    '위생 및 유사서비스업': 'green', 
    '기타의 사업': 'orange'
}

BATTERY_ICONS = {1: 'battery-empty', 2: 'battery-quarter', 3: 'battery-half', 4: 'battery-three-quarters', 5: 'battery-full'}
ICON_9_NAME = 'ban' 
OPACITY_9 = 0.5  # 9회차 전용 불투명도 설정

# ==============================================================================
# [BLOCK 2] 데이터 준비 및 좌표 변환
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

df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl')
df = df.fillna('정보없음')

df['차수_temp'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
max_round_val = df['차수_temp'].max()

df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11)

# ==============================================================================
# [BLOCK 3] 요원별 레이어 생성
# ==============================================================================
agent_layer_dict = {}
for agent in df_map['수행요원'].unique():
    agent_layer_dict[agent] = {
        'unvisited': folium.FeatureGroup(name=f"{agent}: 방문전", show=True).add_to(m),
        'visited': folium.FeatureGroup(name=f"{agent}: 진행중", show=True).add_to(m)
    }

location_counts = {}

# ==============================================================================
# [BLOCK 4] 스타일 및 툴팁 설정
# ==============================================================================
POPUP_FONT = "'Malgun Gothic', sans-serif"
POPUP_WIDTH = 280; TITLE_SIZE = "18px"; BODY_SIZE = "16px"; FOOTER_SIZE = "16px"; BTN_TEXT_SIZE = "18px"
LINK_COLOR = "#0022ff"; EMAIL_COLOR = "#228b22"
TOOLTIP_OFFSET = (0, -35)

# ==============================================================================
# [BLOCK 5] 마커 생성 및 '육각형 분산' + '불투명도' 로직
# ==============================================================================
for _, row in df_map.iterrows():
    v_count = row.get('방문회차', 0); spec_field = str(row.get('특화분야', ''))
    disaster = row.get('재해여부', 0); agent_name = row.get('수행요원', '미지정')
    current_sector = str(row.get('중업종', '')); lat, lon = row['위도'], row['경도']
    
    # 중복 좌표 분산
    pos_key = (row['위도'], row['경도'])
    if pos_key not in location_counts:
        location_counts[pos_key] = 0
    else:
        location_counts[pos_key] += 1
        offset_radius = 0.00018 
        angle = location_counts[pos_key] * (2 * math.pi / 6)
        lat += offset_radius * math.cos(angle)
        lon += offset_radius * math.sin(angle)

    # 마커 기본 불투명도
    m_opacity = 1.0

    # 스타일 결정 및 불투명도 적용
    if v_count == 0:
        m_color = 'gray' if row['차수_temp'] == max_round_val else 'lightgray'
        i_name = 'gear' if '제조' in spec_field else 'building' if '기타' in spec_field else 'flash'
        i_color = sector_icon_color_map.get(current_sector, 'white') if disaster == 0 else 'black'
    elif 1 <= v_count <= 5:
        m_color = 'darkblue' if '제조' in spec_field else 'darkgreen' if '기타' in spec_field else 'orange'
        i_name = BATTERY_ICONS.get(v_count, 'battery-full'); i_color = 'black' if disaster != 0 else 'white'
    elif v_count == 9:
        m_color = 'lightgray'; i_name = ICON_9_NAME; i_color = 'black' if disaster != 0 else 'white'
        m_opacity = OPACITY_9  
    else: continue

    # 팝업 HTML (기존과 동일)
    main_office = row.get(COL_MAIN_OFFICE, '정보없음'); phone = row.get(COL_PHONE, '정보없음')
    site_manager = row.get(COL_SITE_MANAGER, '정보없음'); manager_phone = row.get(COL_MANAGER_PHONE, '정보없음')
    email = str(row.get(COL_EMAIL, '정보없음')).strip(); email_link = f"mailto:{email}" if email != '정보없음' else "#"
    tmap_url = f"tmap://route?goalname={row['사업장명_공사장명']}&goalx={row['경도']}&goaly={row['위도']}"
    kakao_url = f"kakaomap://route?ep={row['위도']},{row['경도']}&by=CAR"
    d_display = f"⚠️재해발생({disaster}건)" if disaster != 0 else "✅무재해"; d_color = "red" if disaster != 0 else "blue"


    
    # 1. 팝업 전체 컨테이너 (너비, 글꼴, 전체 줄간격, 안쪽 여백 설정)
    #       상단 주사업장 (회색, 작은 글씨)
    #       메인 사업장명 (검정색, TITLE_SIZE 적용, 굵게)
    # 2. 제목 섹션 (주사업장 이름 및 사업장명)
    # 3. 구분선 (상단: 진한 회색, 2px 두께)
    # 4. 상세 정보 섹션 (전화번호, 담당자, 이메일 등)
    # 5. 내비게이션 버튼 섹션 (T맵, 카카오맵 버튼 배치)
    #       T맵 버튼 (파란색 배경, 흰색 글씨, 가로 꽉 채움)
    #       카카오맵 버튼 (노란색 배경, 어두운 갈색 글씨)
    # 6. 하단 구분선 (연한 회색, 1px 두께)
    # 7. 푸터 섹션 (주소, 업종, 방문 기록 및 재해 여부)
    #       방문 횟수 및 재해 현황 (재해 여부에 따라 d_color가 빨간색/파란색으로 변경됨)


    popup_html = f"""
    <div style="width:{POPUP_WIDTH}px; font-family:{POPUP_FONT}; line-height:1.4; padding:2px;">
        
        <h3 style="margin:0 0 5px 0; padding:0;">
            <span style="color:#333; font-size:12px;">[{main_office}]</span><br>
            <b style="font-size:{TITLE_SIZE}; color:#000;">{row['사업장명_공사장명']}</b>
        </h3>
        
        <hr style="margin:5px 0; border:0; border-top:2px solid #444;">
        
        <div style="font-size:{BODY_SIZE}; line-height:1.4; padding:0;">
            <b>대표번호:</b> <a href="tel:{phone}" style="color:{LINK_COLOR}; font-weight:bold;">{phone}</a><br>
            <b>담당자명:</b> <span style="color:#000; font-weight:bold;">{site_manager}</span><br>
            <b>담당자폰:</b> <a href="tel:{manager_phone}" style="color:{LINK_COLOR}; font-weight:bold;">{manager_phone}</a><br>
            <b>이메일:</b> <a href="{email_link}" style="color:{EMAIL_COLOR}; font-weight:bold;">{email}</a>
        </div>
        
        <div style="margin-top:10px; display:flex; gap:5px;">
            <a href="{tmap_url}" style="background-color:#0022FF; color:white; padding:8px 0; border-radius:6px; font-size:{BTN_TEXT_SIZE}; font-weight:bold; flex:1; text-align:center; text-decoration:none;">T맵</a>
            <a href="{kakao_url}" style="background-color:#FAE100; color:#3C1E1E; padding:8px 0; border-radius:6px; font-size:{BTN_TEXT_SIZE}; font-weight:bold; flex:1; text-align:center; text-decoration:none;">카카오맵</a>
        </div>
        
        <hr style="margin:10px 0; border:0; border-top:1px solid #666;">
    
        <div style="font-size:{FOOTER_SIZE}; color:#333; line-height:1.2;">
            <b>주소:</b> {row['현장주소']}<br>
            <b>업종:</b> {spec_field} / {current_sector}<br>
            <b>방문:</b> {v_count}회 / <span style="color:{d_color}; font-weight:bold;">{d_display}</span>
        </div>
    </div>"""




    # 마커 생성
    marker = folium.Marker(
        location=[lat, lon],
        icon=folium.Icon(color=m_color, icon=i_name, icon_color=i_color, prefix='fa'),
        opacity=m_opacity, # 불투명도 적용
        popup=folium.Popup(popup_html, max_width=POPUP_WIDTH+20),
        tooltip=folium.Tooltip(row['사업장명_공사장명'], permanent=True, direction='top', offset=TOOLTIP_OFFSET)
    )

    if v_count == 0 or v_count == 9: 
        marker.add_to(agent_layer_dict[agent_name]['unvisited'])
    elif 1 <= v_count <= 5: 
        marker.add_to(agent_layer_dict[agent_name]['visited'])

# [BLOCK 6, 7은 이전과 동일하므로 생략하지 않고 로직만 포함]
folium.LayerControl(collapsed=True).add_to(m)

zoom_and_hide_logic = f"""
<script>
    function setupMapLogic() {{
        var map = {m.get_name()};
        var mapContainer = map.getContainer();
        function updateDisplay() {{
            var currentZoom = map.getZoom();
            if (currentZoom < 15) {{ mapContainer.classList.add('hide-tooltips-by-zoom'); }} 
            else {{ mapContainer.classList.remove('hide-tooltips-by-zoom'); }}
        }}
        map.on('zoomend', updateDisplay);
        updateDisplay();
    }}
    window.addEventListener('load', setupMapLogic);
</script>
<style>
    .hide-tooltips-by-zoom .leaflet-tooltip {{ display: none !important; }}
    .leaflet-popup-pane ~ .leaflet-tooltip-pane {{ display: none !important; }}
    .leaflet-popup-close-button {{
        width: 35px !important; height: 35px !important;
        font-size: 28px !important; line-height: 35px !important;
        color: #555 !important; font-weight: bold !important;
    }}
</style>
"""
m.get_root().html.add_child(folium.Element(zoom_and_hide_logic))

m.save('최종_업무지도_완성본.html')
print("✨ [진짜 완성] 9회차 반투명 효과까지 모두 포함된 지도가 생성되었습니다.")