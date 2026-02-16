import pandas as pd # 엑셀 데이터 처리를 위한 라이브러리
import requests     # 카카오 API 호출을 위한 라이브러리
import folium       # 지도 생성 및 마커 표시를 위한 라이브러리
from folium import plugins # 지도의 부가 기능(레이어 그룹 등) 사용
import re           # 정규표현식(숫자 추출 등) 사용

# ==============================================================================
# [BLOCK 0] 팝업 표시용 엑셀 열(Column) 매핑
# ==============================================================================
COL_MAIN_OFFICE   = '주사업장'           # 본사 또는 주사업장 열 이름
COL_PHONE         = '전화번호'           # 대표 전화번호 열 이름
COL_SITE_MANAGER  = '사업장담당자명직위' # 현장 담당자 열 이름
COL_MANAGER_PHONE = '사업장담당자연락처' # 담당자 연락처 열 이름
COL_EMAIL         = '담당자이메일'       # 담당자 이메일 열 이름

# ==============================================================================
# [BLOCK 1] 사용자 설정 (USER CONFIGURATION)
# ==============================================================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673' # 카카오 API 키
FILE_NAME = '현황1.xlsx' # 대상 엑셀 파일명

# # 업종별 핀 배경색 설정
# sector_color_map = {
#     '사업서비스업': 'red', 
#     '창고업': 'darkblue', 
#     '육상화물 취급업': 'orange', 
#     '건설업': 'darkpurple', 
#     '제조업': 'darkgreen', 
#     '기타의 사업': 'cadetblue',
#     '운수업': 'pink'  # <-- 이렇게 한 줄만 추가!
# }

# [BLOCK 1] 수정: 업종별 '아이콘' 컬러 매핑
# 핀 내부 아이콘(gear, building 등)에 입혀질 색상입니다.
sector_icon_color_map = {
    '사업서비스업': 'red', 
    '창고업': 'blue',          # darkblue보다는 아이콘에서 잘 보이는 blue 추천
    '육상화물 취급업': 'orange', 
    '건설업': 'purple', 
    '제조업': 'green', 
    '기타의 사업': 'cadetblue'
}


# 방문 회차별 배터리 아이콘 매핑
BATTERY_ICONS = {
    1: 'battery-empty', 
    2: 'battery-quarter', 
    3: 'battery-half', 
    4: 'battery-three-quarters', 
    5: 'battery-full'}
ICON_9_NAME = 'ban' # 9회차 전용 아이콘
OPACITY_9 = 0.5     # 9회차 전용 불투명도

# ==============================================================================
# [BLOCK 2] 데이터 준비 및 좌표 변환
# ==============================================================================
def get_coordinates(address): # 주소를 위경도로 바꾸는 함수
    if pd.isna(address) or address == "": return None, None
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if res.get('documents'): return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
    except: pass
    return None, None

df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl') # 데이터 로드
df = df.fillna('정보없음') # 빈 칸(NaN)을 모두 '정보없음'으로 일괄 변경

# 배정차수에서 숫자만 추출하여 최고 차수 계산
df['차수_temp'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
max_round_val = df['차수_temp'].max()

df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x))) # 좌표 변환
df_map = df.dropna(subset=['위도', '경도']).copy() # 좌표 없는 데이터 제외
m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11) # 지도 객체 생성

# ==============================================================================
# [BLOCK 3] 레이어 저장소 생성 (12개 병렬 구조)
# ==============================================================================
agent_layer_dict = {} # 요원별 레이어를 담을 딕셔너리
agents = df_map['수행요원'].unique() # 중복 없는 수행요원 명단

for agent in agents:
    agent_layer_dict[agent] = {
        'unvisited': folium.FeatureGroup(name=f"{agent}: 방문전", show=True), # 방문전 그룹
        'visited': folium.FeatureGroup(name=f"{agent}: 진행중", show=True)    # 진행중 그룹
    }
    agent_layer_dict[agent]['unvisited'].add_to(m) # 지도에 등록
    agent_layer_dict[agent]['visited'].add_to(m)

# ==============================================================================
# [BLOCK 4] 팝업 스타일 및 공통 변수 설정
# ==============================================================================
POPUP_FONT = "'Malgun Gothic', sans-serif" # 팝업 글꼴
POPUP_WIDTH = 280      # 팝업 너비
TITLE_SIZE = "18px"    # 제목 크기
BODY_SIZE = "16px"     # 본문 크기
FOOTER_SIZE = "14px"   # 하단 크기
BTN_TEXT_SIZE = "18px" # 버튼 글자 크기
LINK_COLOR = "#0022ff" # 링크 색상
EMAIL_COLOR = "#228b22"# 이메일 색상

# ==============================================================================
# [BLOCK 5] 마커 개별 생성 및 레이어 배정 로직 (핵심 루프)
# ==============================================================================
for _, row in df_map.iterrows():
    # 1. 데이터 추출 및 가공
    v_count = row.get('방문회차', 0)
    spec_field = str(row.get('특화분야', ''))
    disaster = row.get('재해여부', 0)
    agent_name = row.get('수행요원', '미지정')
    current_sector = str(row.get('중업종', ''))
    lat, lon = row['위도'], row['경도']
    
    main_office = row.get(COL_MAIN_OFFICE, '정보없음')
    phone = row.get(COL_PHONE, '정보없음')
    site_manager = row.get(COL_SITE_MANAGER, '정보없음')
    manager_phone = row.get(COL_MANAGER_PHONE, '정보없음')
    email = str(row.get(COL_EMAIL, '정보없음')).strip()
    
    # 이메일 링크 처리
    email_link = f"mailto:{email}" if email != '정보없음' else "#"
    
    # 내비게이션 주소 생성
    tmap_url = f"tmap://route?goalname={row['사업장명_공사장명']}&goalx={lon}&goaly={lat}"
    kakao_url = f"kakaomap://route?ep={lat},{lon}&by=CAR"

    # 재해 여부 디자인 결정
    d_display = f"⚠️재해발생({disaster}건)" if disaster != 0 else "✅무재해"
    d_color = "red" if disaster != 0 else "blue"

    # 2. 마커 스타일(색상, 아이콘) 결정
    if v_count == 0:
        m_color = 'gray' if row['차수_temp'] == max_round_val else 'lightgray'
        i_name = 'gear' if '제조' in spec_field else 'building' if '기타' in spec_field else 'flash'
    
    
    if v_count == 0:
        m_color = 'gray' if row['차수_temp'] == max_round_val else 'lightgray'
        i_name = 'gear' if '제조' in spec_field else 'building' if '기타' in spec_field else 'flash'
        i_color = sector_icon_color_map.get(current_sector, 'white') if disaster == 0 else 'black'
        m_opacity = 1.0
    
    elif 1 <= v_count <= 5:
        # (진행 중일 때는 핀 색상 자체가 유채색이므로 아이콘은 white/black으로 대비를 줍니다)
        m_color = 'darkblue' if '제조' in spec_field else 'darkgreen' if '기타' in spec_field else 'orange'
        i_name = BATTERY_ICONS.get(v_count, 'battery-full')
        i_color = 'black' if disaster != 0 else 'white'
        m_opacity = 1.0
    
    elif v_count == 9:
        m_color = 'lightgray'; i_name = ICON_9_NAME; i_color = 'black' if disaster != 0 else 'white'; m_opacity = OPACITY_9
    else: continue


    # 3. 상세 HTML 팝업 구성
    popup_html = f"""
    <div style="width:{POPUP_WIDTH}px; font-family:{POPUP_FONT}; line-height:1.8; padding:5px;">
        <h3 style="margin:0 0 8px 0;"><span style="color:#888; font-size:13px;">[{main_office}]</span><br>
        <b style="font-size:{TITLE_SIZE}; color:#000;">{row['사업장명_공사장명']}</b></h3>
        <hr style="margin:8px 0; border:0; border-top:2px solid #444;">
        <div style="font-size:{BODY_SIZE};">
            <b>대표번호:</b> <a href="tel:{phone}" style="color:{LINK_COLOR}; font-weight:bold;">{phone}</a><br>
            <b>담당자명:</b> {site_manager}<br>
            <b>담당자폰:</b> <a href="tel:{manager_phone}" style="color:{LINK_COLOR}; font-weight:bold;">{manager_phone}</a><br>
            <b>이메일:</b> <a href="{email_link}" style="color:{EMAIL_COLOR}; font-weight:bold;">{email}</a>
        </div>
        <div style="margin-top:15px; display:flex; gap:8px;">
            <a href="{tmap_url}" style="background-color:#0022FF; color:white; padding:10px; border-radius:6px; font-size:{BTN_TEXT_SIZE}; font-weight:bold; flex:1; text-align:center; text-decoration:none;">T맵</a>
            <a href="{kakao_url}" style="background-color:#FAE100; color:#3C1E1E; padding:10px; border-radius:6px; font-size:{BTN_TEXT_SIZE}; font-weight:bold; flex:1; text-align:center; text-decoration:none;">카카오맵</a>
        </div>
        <hr style="margin:12px 0; border:0; border-top:1px solid #eee;">
        <div style="font-size:{FOOTER_SIZE}; color:#666;">
            <b>주소:</b> {row['현장주소']}<br>
            <b>분야:</b> {spec_field}<br>
            <b>업종:</b> {current_sector}<br>
            <b>방문:</b> {v_count}회 / <span style="color:{d_color}; font-weight:bold;">{d_display}</span>
        </div>
    </div>
    """

    # 4. 마커 생성 및 레이어 배정
    marker = folium.Marker(
        location=[lat, lon],
        icon=folium.Icon(color=m_color, icon=i_name, icon_color=i_color, prefix='fa'),
        opacity=m_opacity,
        popup=folium.Popup(popup_html, max_width=POPUP_WIDTH+20),
        tooltip=row['사업장명_공사장명']
    )
    
    # 5. 요원별 레이어 배정 (12줄 리스트)
    if v_count == 0 or v_count == 9: marker.add_to(agent_layer_dict[agent_name]['unvisited'])
    elif 1 <= v_count <= 5: marker.add_to(agent_layer_dict[agent_name]['visited'])

# ==============================================================================
# [BLOCK 6] 레이어 컨트롤 UI 구성
# ==============================================================================
folium.LayerControl(collapsed=True).add_to(m) # 우측 상단 접이식 메뉴 추가


# ==============================================================================
# [BLOCK 7] 업종별 아이콘 색상 범례(Legend) 설정
# 설명: 미방문 사업장(회색 핀)의 아이콘 색상 기준을 핀 모양 그대로 범례에 표시합니다.
# ==============================================================================

# 1. 범례 위치 및 디자인 변수
LEGEND_RIGHT  = "15px"    # 오른쪽 여백
LEGEND_BOTTOM = "15px"    # 아래쪽 여백
LEGEND_WIDTH  = "190px"   # 범례창 너비 (핀 모양을 위해 약간 넓게 설정)
LEGEND_TITLE  = "업종별 아이콘 구분" 

# 2. 범례 HTML 구조 시작
legend_html = f"""
<div id="sector-legend" style="
    position: fixed; 
    bottom: {LEGEND_BOTTOM}; right: {LEGEND_RIGHT}; 
    width: {LEGEND_WIDTH};
    z-index: 9999; 
    font-family: 'Malgun Gothic', sans-serif;
    font-size: 13px;
    background-color: transparent;
">
    <div id="legend-toggle" style="
        width: 45px; height: 45px;
        background-color: #333; color: white;
        border-radius: 50%; text-align: center;
        line-height: 45px; cursor: pointer;
        margin-left: auto; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
        font-weight: bold; font-size: 20px;
    ">📍</div>

    <div id="legend-content" style="
        display: none;
        background-color: rgba(255, 255, 255, 0.95);
        border: 2px solid #555;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 8px;
        box-shadow: 3px 3px 15px rgba(0,0,0,0.2);
    ">
        <div style="font-weight: bold; border-bottom: 2px solid #eee; margin-bottom: 10px; padding-bottom: 5px; text-align: center;">
            {LEGEND_TITLE}
        </div>
        <div style="margin-bottom: 10px; font-size: 11px; color: #666; text-align: center;">
            * 미방문(회색 핀) 기준
        </div>
"""

# 3. sector_icon_color_map을 순회하며 '핀 모양' 아이템 생성
for name, color in sector_icon_color_map.items():
    # 회색 핀 배경에 아이콘 색상(color)이 박힌 모습을 HTML로 형상화
    legend_html += f"""
    <div style="display: flex; align-items: center; margin-bottom: 8px;">
        <div style="
            position: relative;
            width: 22px; height: 30px; 
            background-color: #A9A9A9; /* 회색 핀(gray/lightgray) */
            border-radius: 50% 50% 50% 0;
            transform: rotate(-45deg);
            margin-right: 15px;
            display: flex; align-items: center; justify-content: center;
            border: 1px solid #777;
            box-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        ">
            <div style="
                width: 10px; height: 10px; 
                background-color: {color}; 
                border-radius: 50%;
                transform: rotate(45deg);
                border: 1px solid rgba(0,0,0,0.2);
            "></div>
        </div>
        <span style="font-weight: 500;">{name}</span>
    </div>
    """

# 4. 토글 자바스크립트 마무리
legend_html += """
    </div>
</div>

<script>
    document.getElementById('legend-toggle').onclick = function() {
        var content = document.getElementById('legend-content');
        if (content.style.display === 'none') {
            content.style.display = 'block';
            this.innerHTML = '✖';
        } else {
            content.style.display = 'none';
            this.innerHTML = '📍';
        }
    };
</script>
"""

# 지도 객체에 범례 추가
m.get_root().html.add_child(folium.Element(legend_html))


# ==============================================================================
# [BLOCK 8] 최종 결과물 저장 (기존 BLOCK 7에서 번호 변경)
# ==============================================================================
m.save('12줄_범례포함_업무지도.html')
print("✨ [BLOCK 7] 토글형 범례표가 추가되었습니다. 최종 파일이 생성되었습니다.")