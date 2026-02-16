import pandas as pd
import requests
import folium
from folium import plugins
import re

# ==============================================================================
# [BLOCK 0] 팝업 표시용 엑셀 열(Column) 매핑
# 설명: 엑셀 파일의 열 이름과 아래 명칭이 일치해야 팝업에 정보가 나타납니다.
# ==============================================================================
COL_MAIN_OFFICE   = '주사업장'     # 엑셀의 본사 정보 열
COL_PHONE         = '전화번호'     # 사업장 대표 번호
COL_SITE_MANAGER  = '사업장담당자명직위'   # 현장 관리자 성함
COL_MANAGER_PHONE = '사업장담당자연락처' # 관리자 휴대폰 번호
COL_EMAIL         = '담당자이메일'       # 담당자 이메일
# ==============================================================================


# ==============================================================================
# [BLOCK 1] 사용자 설정 (USER CONFIGURATION)
# 설명: 업무 규칙(색상, 아이콘, 파일명)을 한곳에서 관리합니다.
# ==============================================================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx'

# 중업종별 컬러 매핑 (방문 전 아이콘 색상)
sector_color_map = {
    '사업서비스업': 'red', '창고업': 'darkblue', '육상화물 취급업': 'orange', 
    '건설업': 'darkpurple', '제조업': 'darkgreen', '기타의 사업': 'cadetblue'
}

# 방문회차별 배터리 아이콘
BATTERY_ICONS = {1: 'battery-empty', 2: 'battery-quarter', 3: 'battery-half', 4: 'battery-three-quarters', 5: 'battery-full'}

# 9회차(거부/종결) 전용 설정
ICON_9_NAME = 'ban'
OPACITY_9 = 0.3

# ==============================================================================
# [BLOCK 2] 데이터 준비 및 좌표 변환
# 설명: 주소를 위경도로 바꾸고 엑셀 데이터를 지도가 읽을 수 있게 가공합니다.
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

# 데이터 로드
df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl')
# 엑셀의 모든 빈 칸(NaN)을 '정보없음'이라는 글자로 한꺼번에 바꿉니다.
df = df.fillna('정보없음')


# 배정차수 숫자 추출
df['차수_temp'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
max_round_val = df['차수_temp'].max()

# 좌표 변환 적용
df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

# 기본 지도 생성
m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11)


# ==============================================================================
# [BLOCK 3] 레이어 저장소 생성 (12개 병렬 구조)
# 설명: '성함: 상태' 형식의 레이어 12개를 생성하여 지도에 등록합니다.
# ==============================================================================
agent_layer_dict = {}
agents = df_map['수행요원'].unique()

for agent in agents:
    # 12줄로 깔끔하게 표시하기 위해 아이콘을 제거하고 "이름: 상태"로 명칭 통일
    agent_layer_dict[agent] = {
        'unvisited': folium.FeatureGroup(name=f"{agent}: 방문전", show=True),
        'visited': folium.FeatureGroup(name=f"{agent}: 진행중", show=True)
    }
    # 각 레이어를 독립적으로 지도에 추가 (LayerControl에서 12줄로 나열됨)
    agent_layer_dict[agent]['unvisited'].add_to(m)
    agent_layer_dict[agent]['visited'].add_to(m)


# ==============================================================================
# [BLOCK 4] 마커 개별 생성 및 레이어 배정 로직
# 설명: 마커 하나하나의 색상과 아이콘을 결정하고 적절한 요원 레이어에 넣습니다.
# ==============================================================================
for _, row in df_map.iterrows():
    v_count = row.get('방문회차', 0)
    spec_field = str(row.get('특화분야', ''))
    disaster = row.get('재해여부', 0)
    agent_name = row.get('수행요원', '미지정')
    current_sector = str(row.get('중업종', ''))

    # 스타일 결정: 방문 0회차
    if v_count == 0:
        m_color = 'gray' if row['차수_temp'] == max_round_val else 'lightgray'
        i_name = 'gear' if '제조' in spec_field else 'building' if '기타' in spec_field else 'flash'
        i_color = sector_color_map.get(current_sector, 'white') if disaster == 0 else 'black'
        m_opacity = 1.0
    # 스타일 결정: 방문 1~5회차
    elif 1 <= v_count <= 5:
        m_color = 'darkblue' if '제조' in spec_field else 'darkgreen' if '기타' in spec_field else 'orange'
        i_name = BATTERY_ICONS.get(v_count, 'battery-full')
        i_color = 'black' if disaster != 0 else 'white'
        m_opacity = 1.0
    # 스타일 결정: 방문 9회차
    elif v_count == 9:
        m_color = 'lightgray'; i_name = ICON_9_NAME; i_color = 'black' if disaster != 0 else 'white'
        m_opacity = OPACITY_9
    else: continue



# ==============================================================================
# [BLOCK 5] 마커 개별 생성 및 레이어 배정 로직
# ==============================================================================
    # 0. 팝업 전체 스타일 변수 (여기서 한꺼번에 조절하세요)
POPUP_FONT = "'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif" # 글꼴
POPUP_WIDTH = 280            # 팝업 전체 가로 너비 (px)
TITLE_SIZE = "18px"          # 사업장명 크기
BODY_SIZE = "16px"           # 본문(전화번호 등) 크기
FOOTER_SIZE = "14px"         # 하단(주소, 업종 등) 크기
BTN_TEXT_SIZE = "18px"       # 내비게이션 버튼 글자 크기
LINK_COLOR  = "#0022ff"       # 전화번호 링크 색상 (기본 파랑)
EMAIL_COLOR = "#228b22"       # 이메일 링크 색상 (진한 초록 - ForestGreen)

for _, row in df_map.iterrows():
    # 1. 기초 데이터 추출
    v_count = row.get('방문회차', 0)
    spec_field = str(row.get('특화분야', ''))
    disaster = row.get('재해여부', 0)
    agent_name = row.get('수행요원', '미지정')
    current_sector = str(row.get('중업종', ''))
    lat, lon = row['위도'], row['경도']

    # [핵심 추가] BLOCK 0의 매핑 정보를 사용하여 실제 엑셀 데이터를 변수에 할당합니다.
    # 이 부분이 누락되면 popup_html에서 변수를 찾지 못해 에러가 발생합니다.
    main_office = row.get(COL_MAIN_OFFICE, '정보없음')
    phone = row.get(COL_PHONE, '정보없음')
    site_manager = row.get(COL_SITE_MANAGER, '정보없음')
    manager_phone = row.get(COL_MANAGER_PHONE, '정보없음')
    email = row.get(COL_EMAIL, '정보없음')

    # 1. 이메일 데이터 정제 (공백 제거 및 '정보없음' 처리)
    raw_email = str(row.get(COL_EMAIL, '')).strip()
    
    # 이메일 주소가 비어있거나 'nan'인 경우 처리
    if not raw_email or raw_email.lower() == 'nan':
        email_display = "정보없음"
        email_link = "#" # 링크 비활성화
    else:
        email_display = raw_email
        email_link = f"mailto:{raw_email}" # 실제 mailto 링크 생성

    
    # 내비게이션용 URL 생성
    tmap_url = f"tmap://route?goalname={row['사업장명_공사장명']}&goalx={lon}&goaly={lat}"
    kakao_url = f"kakaomap://route?ep={lat},{lon}&by=CAR"

    # 재해여부 표시 가공
    d_display = f"⚠️ 재해발생({disaster}건)" if disaster != 0 else "✅ 무재해"
    d_color = "red" if disaster != 0 else "blue"

    # 2. 스타일 결정 로직 (기존 유지)
    if v_count == 0:
        m_color = 'gray' if row['차수_temp'] == max_round_val else 'lightgray'
        i_name = 'gear' if '제조' in spec_field else 'building' if '기타' in spec_field else 'flash'
        i_color = sector_color_map.get(current_sector, 'white') if disaster == 0 else 'black'
        m_opacity = 1.0
    elif 1 <= v_count <= 5:
        m_color = 'darkblue' if '제조' in spec_field else 'darkgreen' if '기타' in spec_field else 'orange'
        i_name = BATTERY_ICONS.get(v_count, 'battery-full')
        i_color = 'black' if disaster != 0 else 'white'
        m_opacity = 1.0
    elif v_count == 9:
        m_color = 'lightgray'; i_name = ICON_9_NAME; i_color = 'black' if disaster != 0 else 'white'
        m_opacity = OPACITY_9
    else: continue

    # 3. [업그레이드] 팝업 HTML 구성 (세부 디자인 적용)
    popup_html = f"""
    <div style="width:{POPUP_WIDTH}px; font-family: {POPUP_FONT}; line-height: 1.8; padding: 5px; color: #333;">
        <h3 style="margin:0 0 8px 0;">
            <span style="color: #888; font-size: 13px;">[{main_office}]</span><br>
            <b style="font-size: {TITLE_SIZE}; color: #000;">{row['사업장명_공사장명']}</b>
        </h3>
        <hr style="margin:8px 0; border: 0; border-top: 2px solid #444;">
        
        <div style="font-size: {BODY_SIZE};">
            <span style="font-weight: bold;">대표번호:</span> 
            <a href="tel:{phone}" style="color: {LINK_COLOR}; text-decoration: none; font-weight: bold;">{phone}</a><br>
            
            <span style="font-weight: bold;">담당자명:</span> {site_manager}<br>
            
            <span style="font-weight: bold;">담당자폰:</span> 
            <a href="tel:{manager_phone}" style="color: {LINK_COLOR}; text-decoration: none; font-weight: bold;">{manager_phone}</a><br>
            
            <span style="font-weight: bold;">이메일:</span> 
            <a href="{email_link}" style="color: {EMAIL_COLOR}; text-decoration: none; font-weight: bold;">{email_display}</a>
        </div>



        <div style="margin-top: 15px; display: flex; gap: 8px;">
            <a href="{tmap_url}" style="
                background-color: #0022FF; 
                color: white; 
                padding: 10px; 
                text-decoration: none; 
                border-radius: 6px;      /* 모서리 둥글기 */
                font-size: {BTN_TEXT_SIZE}; 
                font-weight: bold; 
                flex: 1; 
                text-align: center;
            ">T맵 실행</a>
            
            <a href="{kakao_url}" style="
                background-color: #FAE100; 
                color: #3C1E1E; 
                padding: 10px; 
                text-decoration: none; 
                border-radius: 6px; 
                font-size: {BTN_TEXT_SIZE}; 
                font-weight: bold; 
                flex: 1; 
                text-align: center;
            ">카카오맵</a>
        </div>


        <hr style="margin:12px 0; border: 0; border-top: 1px solid #eee;">
        <div style="font-size: {FOOTER_SIZE}; color: #666; line-height: 1.6;">
            <b style="color: #444;">주소:</b> {row['현장주소']}<br>
            <b style="color: #444;">분야:</b> {spec_field}<br>
            <b style="color: #444;">업종:</b> {current_sector}<br>
            <b style="color: #444;">방문/상태:</b> {v_count}회 / 
            <span style="color: {d_color}; font-weight: bold;">{d_display}</span>
        </div>
    </div>
    """


    # 4. 최종 마커 생성 및 팝업 결합
    marker = folium.Marker(
        location=[lat, lon],
        icon=folium.Icon(color=m_color, icon=i_name, icon_color=i_color, prefix='fa'),
        opacity=m_opacity,
        popup=folium.Popup(popup_html, max_width=POPUP_WIDTH + 20),
        tooltip=row['사업장명_공사장명']
    )

    # 5. 요원별 레이어 배정 (12줄 리스트)
    if v_count == 0 or v_count == 9:
        marker.add_to(agent_layer_dict[agent_name]['unvisited'])
    elif 1 <= v_count <= 5:
        marker.add_to(agent_layer_dict[agent_name]['visited'])



# ==============================================================================
# [BLOCK 6] 레이어 컨트롤 UI 구성 및 파일 저장
# 설명: 평소에는 닫혀 있다가 클릭 시 12줄이 펼쳐지는 구조입니다.
# ==============================================================================

# collapsed=True: 지도를 처음 열 때 메뉴를 접어둡니다 (아이콘만 표시).
# 클릭하거나 마우스를 올리면 12줄의 [이름: 상태] 리스트가 나타납니다.
folium.LayerControl(collapsed=True).add_to(m)


# ==============================================================================
# [BLOCK 7] # 최종 결과물 저장
# ==============================================================================
m.save('12줄_접이식_업무지도.html')
print("✨ [설정 완료] 레이어 메뉴가 평소에는 접혀 있고, 클릭 시 펼쳐지도록 수정되었습니다.")