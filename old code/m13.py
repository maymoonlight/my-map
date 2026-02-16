import pandas as pd
import requests
import folium
from folium import plugins
import re
import math 

# ==============================================================================
# [BLOCK 0-1] 팝업 표시용 엑셀 열(Column) 매핑
# ==============================================================================
COL_MAIN_OFFICE   = '주사업장'           
COL_PHONE         = '전화번호'           
COL_SITE_MANAGER  = '사업장담당자명직위' 
COL_MANAGER_PHONE = '사업장담당자연락처' 
COL_EMAIL         = '담당자이메일'       

# ==============================================================================
# [BLOCK 0-2] 사용자 설정 (USER CONFIGURATION)
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


# [BLOCK 1] 업종별 아이콘 스타일 통합 설정 (색상, 아이콘모양)
# 아이콘 이름 참고: gear(톱니), building(빌딩), truck(트럭), leaf(나뭇잎), wrench(렌치) 등
# shopping-cart, archive, truck, briefcase, leaf
# 제조업 : industry, gear, gears, plug, wrench, truck, 
sector_config_map = {
    '도소매 및 소비자용품수리업': {'color': 'beige',      'icon': 'shopping-cart'}, 
    '창고업':                   {'color': 'pink',       'icon': 'building'}, 
    '육상화물취급업':            {'color': 'lightblue',  'icon': 'building'}, 
    '사업서비스업':              {'color': 'lightgreen', 'icon': 'gear'}, 
    '위생 및 유사서비스업':      {'color': 'green',      'icon': 'gear'}, 
    '제조업':                   {'color': 'cadetblue',  'icon': 'gear'},
    '기타의 사업':              {'color': 'orange',     'icon': 'gear'},
    '사업서비스업#':            {'color': 'darkpurple',  'icon': 'wifi'}
}


BATTERY_ICONS = {1: 'battery-empty', 2: 'battery-quarter', 3: 'battery-half', 4: 'battery-three-quarters', 5: 'battery-full'}
ICON_9_NAME = 'close' 
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
# [BLOCK 3] 요원별 레이어 생성 (미배정 단일화 버전)
# ==============================================================================
agent_layer_dict = {}
# 동일 좌표 마커 개수를 추적하기 위한 장부 (절대 삭제 금지!)
location_counts = {}


for agent in df_map['수행요원'].unique():
    # 수행요원이 '정보없음'인 경우 (미배정 상태)
    if agent == '정보없음':
        agent_layer_dict[agent] = {
            'single': folium.FeatureGroup(name="미배정", show=True).add_to(m)
        }
    # 수행요원이 지정된 경우 (기존 방식 유지)
    else:
        agent_layer_dict[agent] = {
            'unvisited': folium.FeatureGroup(name=f"{agent}: 방문전", show=False).add_to(m),
            'visited': folium.FeatureGroup(name=f"{agent}: 진행중", show=False).add_to(m)
        }




# ==============================================================================
# [BLOCK 4] 스타일 및 툴팁 설정
# ==============================================================================
POPUP_FONT = "'Malgun Gothic', sans-serif"
POPUP_WIDTH = 280; TITLE_SIZE = "20px"; BODY_SIZE = "20px"; FOOTER_SIZE = "18px"; BTN_TEXT_SIZE = "18px"
LINK_COLOR = "#0022ff"; EMAIL_COLOR = "#228b22"
TOOLTIP_OFFSET = (0, -35)




# ==============================================================================
# [BLOCK 5] 마커 스타일 결정 및 생성 로직 (최종 통합 버전)
# ==============================================================================
for _, row in df_map.iterrows():
    # -------------------------------------------------------------------------
    # 1. 기초 데이터 추출 및 타입 교정
    # -------------------------------------------------------------------------
    # [방문회차] 숫자로 변환 (에러 발생 시 0으로 처리)
    try:
        raw_v_count = row.get('방문회차', 0)
        v_count = int(raw_v_count) if pd.notna(raw_v_count) else 0
    except:
        v_count = 0
        
    spec_field = str(row.get('특화분야', ''))      # 특화분야 분류 '특화 기계', '특화 화학', '일반 제조', '일반 기타', '일반 장소'
    agent_name = row.get('수행요원', '미지정')      # 담당 요원
    current_sector = str(row.get('중업종', ''))     # 중업종(설정 컬러 참조용)
    lat, lon = row['위도'], row['경도']             # 기본 좌표

    # [재해여부 전처리] - 기존 disaster 변수를 대체함
    raw_disaster = row.get('재해여부')
    if pd.isna(raw_disaster) or raw_disaster == '정보없음':
        d_count = -1; d_display = "해당없음"; d_color = "white"
    else:
        try:
            d_count = int(raw_disaster)
            if d_count == 0: d_display = "✅무재해"; d_color = "blue"
            else: d_display = f"⚠️재해({d_count}건)"; d_color = "red"
        except:
            d_count = -1; d_display = "해당없음"; d_color = "white"

    # -------------------------------------------------------------------------
    # 2. 업종별 통합 설정(아이콘/컬러) 매칭
    # -------------------------------------------------------------------------
    # sector_config_map에 없으면 기본 아이콘 할당
    config = sector_config_map.get(current_sector)
    if not config:
        if '제조' in current_sector:
            config = {'color': 'white', 'icon': 'industry'}
        else:
            config = {'color': 'white', 'icon': 'building'}



    # -------------------------------------------------------------------------
    # 3. 중복 좌표 분산 로직 (육각형 배치)
    # -------------------------------------------------------------------------
    pos_key = (row['위도'], row['경도'])
    if pos_key not in location_counts:
        location_counts[pos_key] = 0
    else:
        location_counts[pos_key] += 1
        offset_radius = 0.00018 
        angle = location_counts[pos_key] * (2 * math.pi / 6)
        lat += offset_radius * math.cos(angle); lon += offset_radius * math.sin(angle)

    # -------------------------------------------------------------------------
    # 4. 마커 상태별 스타일 결정 (특화분야 5종 및 방문회차 로직)
    # -------------------------------------------------------------------------
    m_opacity = 0.8  # 기본 불투명도

    # [A] 일반 장소 (최우선 고정 스타일) ---# 특화분야에 '일반 장소'가 포함되어 있으면 방문회차 상관없이 고정 스타일 적용
    if '일반 장소' in spec_field:
        m_color = 'red'      # 핀 색상
        i_name = 'info'      # 아이콘 모양
        i_color = 'white'    # 아이콘 내부 색상
        m_opacity = 0.8      # 핀 투명도 필요 시 수정



    # [B] 관리 제외 (9회차)
    elif v_count == 9:
        m_color = 'lightgray'; i_name = ICON_9_NAME
        i_color = 'black' if d_count > 0 else 'white'
        m_opacity = OPACITY_9

    # [C] 방문 전 (0회차) - 현장 파악 모드
    elif v_count == 0:
        m_color = 'gray' if row['차수_temp'] == max_round_val else 'lightgray'
        
        # 특화분야별 모양 결정
        if '특화 기계' in spec_field: i_name = 'gears'
        elif '특화 화학' in spec_field: i_name = 'flask'
        elif '특화 목재' in spec_field: i_name = 'tree'
        elif '일반 제조' in spec_field: i_name = 'industry'
        elif '일반 기타' in spec_field: i_name = 'building'
        else: 
            # 특화분야 키워드가 모두 없으면, sector_config_map에서 설정한 아이콘을 가져옴
            # 만약 map에도 설정이 없다면 그때 'flash'를 기본값으로 사용함
            i_name = config.get('icon', 'quesstion')
        
        # 재해 여부에 따른 아이콘 컬러 강조
        i_color = config['color'] if d_count <= 0 else 'black'

    # [D] 방문 중 (1~8회차) - 공정 관리 모드
    elif 1 <= v_count <= 8:
        # 제조/특화는 darkblue, 기타는 darkgreen으로 핀 색상 통일
        if '제조' in spec_field or '특화' in spec_field:
            m_color = 'darkblue'
            i_name = BATTERY_ICONS.get(v_count, 'battery-full')  # 5단계
        else:
            m_color = 'darkgreen'
            # 기타 업종 3단계 배터리 로직
            if v_count == 1: i_name = 'battery-empty'
            elif v_count == 2: i_name = 'battery-half'
            else: i_name = 'battery-full'
        
        i_color = 'black' if d_count > 0 else 'white'

    else: continue

    # -------------------------------------------------------------------------
    # 5. 팝업 HTML 생성 (여백/줄간격 최적화)
    # -------------------------------------------------------------------------
 
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



    main_office = row.get(COL_MAIN_OFFICE, '정보없음'); phone = row.get(COL_PHONE, '정보없음')
    site_manager = row.get(COL_SITE_MANAGER, '정보없음'); manager_phone = row.get(COL_MANAGER_PHONE, '정보없음')
    email = str(row.get(COL_EMAIL, '정보없음')).strip()
    email_link = f"mailto:{email}" if email != '정보없음' else "#"
    tmap_url = f"tmap://route?goalname={row['사업장명_공사장명']}&goalx={row['경도']}&goaly={row['위도']}"
    kakao_url = f"kakaomap://route?ep={row['위도']},{row['경도']}&by=CAR"

    popup_html = f"""
    <div style="width:{POPUP_WIDTH}px; font-family:{POPUP_FONT}; line-height:1.5; padding:2px;">
        <h3 style="margin:0 0 5px 0; padding:0;">
            <span style="color:#333; font-size:14px;">[{main_office}]</span><br>
            <b style="font-size:{TITLE_SIZE}; color:#000;">{row['사업장명_공사장명']}</b>
        </h3>
        <hr style="margin:5px 0; border:0; border-top:2px solid #444;">
        <div style="font-size:{BODY_SIZE}; line-height:1.5; padding:0;">
            대표번호: <a href="tel:{phone}" style="color:{LINK_COLOR}; font-weight:bold;">{phone}</a><br>
            담당자명: <span style="color:#000; font-weight:bold;">{site_manager}</span><br>
            담당자폰: <a href="tel:{manager_phone}" style="color:{LINK_COLOR}; font-weight:bold;">{manager_phone}</a><br>
            이메일: <a href="{email_link}" style="color:{EMAIL_COLOR}; font-weight:bold;">{email}</a>
        </div>
        <div style="margin-top:10px; display:flex; gap:5px;">
            <a href="{tmap_url}" style="background-color:#0022FF; color:white; padding:6px 0; border-radius:6px; font-size:{BTN_TEXT_SIZE}; font-weight:bold; flex:1; text-align:center; text-decoration:none;">T맵</a>
            <a href="{kakao_url}" style="background-color:#FAE100; color:#3C1E1E; padding:6px 0; border-radius:6px; font-size:{BTN_TEXT_SIZE}; font-weight:bold; flex:1; text-align:center; text-decoration:none;">카카오맵</a>
        </div>
        <hr style="margin:10px 0; border:0; border-top:1px solid #666;">
        <div style="font-size:{FOOTER_SIZE}; color:#000; line-height:1.5;">
            o {row['현장주소']}<br>
            o {spec_field} / {current_sector}<br>
            o 방문 {v_count}회 / <span style="color:{d_color}; font-weight:bold;">{d_display}</span>
        </div>
    </div>"""

    # -------------------------------------------------------------------------
    # 6. 마커 생성 및 레이어 배정
    # -------------------------------------------------------------------------
    marker = folium.Marker(
        location=[lat, lon],
        icon=folium.Icon(color=m_color, icon=i_name, icon_color=i_color, prefix='fa'),
        opacity=m_opacity,
        popup=folium.Popup(popup_html, max_width=POPUP_WIDTH+20),
        tooltip=folium.Tooltip(row['사업장명_공사장명'], permanent=True, direction='top', offset=TOOLTIP_OFFSET)
    )

    # 요원 배정 여부에 따른 레이어 분기
    if agent_name == '정보없음':
        marker.add_to(agent_layer_dict[agent_name]['single'])
    else:
        if v_count == 0 or v_count == 9: 
            marker.add_to(agent_layer_dict[agent_name]['unvisited'])
        elif 1 <= v_count <= 8: 
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