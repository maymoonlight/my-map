import pandas as pd
import requests
import folium
from folium import plugins
from branca.element import Element
import re

# 1. 설정 및 API 키
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
excel_file = '현황.xlsx'

# 2. 데이터 로드
try:
    df = pd.read_excel(excel_file, sheet_name='맵핑', dtype={'사업장관리번호': str, '개시번호': str})
except Exception as e:
    print(f"파일 로딩 실패: {e}")

# 3. 주소 분석 함수
def get_coords(address):
    if pd.isna(address): return None, None
    clean_addr = re.sub(r'\(.*\)', '', str(address)).strip()
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={clean_addr}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if res.get('documents'):
            pos = res['documents'][0]['address']
            return float(pos['x']), float(pos['y'])
    except: pass
    return None, None

print("위경도 좌표 분석 중...")
df['경도'], df['위도'] = zip(*df['현장주소'].apply(get_coords))
df.to_excel('현황_좌표업데이트.xlsx', index=False)

# 4. 지도 생성 및 레이어/클러스터 통합 설정
valid_df = df.dropna(subset=['위도', '경도'])
m = folium.Map(location=[valid_df['위도'].mean(), valid_df['경도'].mean()], zoom_start=11)

# [비법] 클러스터 색상 빨간색 고정 CSS
custom_style = """
<style>
    .marker-cluster-small { background-color: rgba(255, 0, 0, 0.6) !important; }
    .marker-cluster-small div { background-color: rgba(255, 0, 0, 0.8) !important; color: white !important; font-weight: bold; }
    .marker-cluster-medium { background-color: rgba(255, 0, 0, 0.6) !important; }
    .marker-cluster-medium div { background-color: rgba(255, 0, 0, 0.8) !important; color: white !important; font-weight: bold; }
    .marker-cluster-large { background-color: rgba(255, 0, 0, 0.6) !important; }
    .marker-cluster-large div { background-color: rgba(255, 0, 0, 0.8) !important; color: white !important; font-weight: bold; }
</style>
"""
m.get_root().header.add_child(Element(custom_style))

# [핵심] 전체 숫자가 합산되어 보이는 단 하나의 통합 클러스터
total_cluster = plugins.MarkerCluster(name="전체 사업장 관리").add_to(m)

# 수행요원별 레이어 그룹 (토글용)
agent_groups = {}
agent_col = '수행요원' if '수행요원' in valid_df.columns else '담당자'
for agent in valid_df[agent_col].unique():
    # 개별 클러스터 대신 그룹으로 생성하여 통합 클러스터 안에 담길 준비를 합니다.
    agent_groups[agent] = folium.FeatureGroup(name=f"수행요원: {agent}").add_to(m)

# 방문/업종 설정
visit_colors = {1: 'red', 2: 'orange', 3: 'yellow', 4: 'green', 5: 'blue'}
industry_map = {'자동차': 'red', '화학': 'blue', '섬유': 'green', '기계': 'black', '전기': 'yellow', '식품': 'orange', '건설': 'cadetblue'}

# 5. 마커 및 팝업 생성 로직
for _, row in valid_df.iterrows():
    v_cnt, disaster_count = int(row['방문회차']), int(row['재해여부'])
    is_disaster = disaster_count > 0
    industry = str(row['중업종'])
    phone = row['전화번호'] if '전화번호' in valid_df.columns else "정보없음"
    site_manager = row['사업장담당자명직위'] if pd.notna(row['사업장담당자명직위']) else "정보없음"
    manager_phone = row['사업장담당자연락처'] if pd.notna(row['사업장담당자연락처']) else "정보없음"
    main_office = row['주사업장'] if pd.notna(row['주사업장']) else ""
    lat, lon = row['위도'], row['경도']

    bg = next((color for key, color in industry_map.items() if key in industry), 'grey')

    # 아이콘 디자인 설정
    if v_cnt == 0:
        special_field = str(row['특화분야'])
        border_c, border_w = (bg, '0px') if '제조' in special_field else ('blue', '2px')
        icon = plugins.BeautifyIcon(icon=' ', icon_shape='marker', icon_size=[22, 22], border_color=border_c, background_color=bg, inner_icon_style=f'border:{border_w} solid {border_c}; display:none;')
    else:
        v_bg = visit_colors.get(v_cnt, 'gray')
        in_bg, t_c = ("black", "white") if is_disaster else ("white", v_bg)
        icon = plugins.BeautifyIcon(icon_shape='marker', icon_size=[40, 40], number=v_cnt, background_color=v_bg, border_color=v_bg, text_color=t_c, inner_icon_style=f'background-color:{in_bg}; border-radius:50%; width:16px; height:16px; line-height:16px; margin-top:2px; text-align:center; padding-left:1px;')

    # 팝업 HTML 구성
    tmap_url = f"tmap://route?goalname={row['사업장명_공사장명']}&goalx={lon}&goaly={lat}"
    d_display, d_color = (f"재해({disaster_count}건)", "red") if is_disaster else ("무재해", "blue")
    
    popup_html = f"""
    <div style="width:280px; font-family: 'Malgun Gothic', sans-serif; line-height: 1.8; padding: 5px;">
        <h3 style="margin:0 0 8px 0; font-size: 18px;"><span style="color: #666; font-size: 14px;">[{main_office}]</span><br><b>{row['사업장명_공사장명']}</b></h3>
        <hr style="margin:8px 0; border-top: 2px solid #333;">
        <div style="font-size: 16px;">
            <b>대표번호:</b> <a href="tel:{phone}" style="color: #007bff; font-weight: bold; font-size: 17px;">{phone}</a><br>
            <b style="color: #333; font-size: 16px;">담당자명:</b> {site_manager}<br>
            <b>담당자폰:</b> <a href="tel:{manager_phone}" style="color: #d9534f; font-weight: bold; font-size: 17px;">{manager_phone}</a>
        </div>
        <div style="margin-top: 15px; display: flex; gap: 8px;">
            <a href="{tmap_url}" style="background-color: #0022FF; color: white; padding: 10px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; flex: 1; text-align: center;">T맵 실행</a>
            <a href="kakaomap://route?ep={lat},{lon}&by=CAR" style="background-color: #FAE100; color: #3C1E1E; padding: 10px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; flex: 1; text-align: center;">카카오맵</a>
        </div>
        <hr style="margin:12px 0; border: 0; border-top: 1px solid #eee;">
        <div style="font-size: 14px; color: #555; line-height: 1.6;">
            <b>주소:</b> {row['현장주소']}<br>
            <b>방문:</b> {v_cnt}회 / <b>상태:</b> <span style="color: {d_color}; font-weight: bold;">{d_display}</span>
        </div>
    </div>
    """

    # [D] 마커 배치: 수행요원 그룹과 통합 클러스터에 동시에 연결
    marker = folium.Marker(location=[lat, lon], popup=folium.Popup(popup_html, max_width=300), tooltip=row['사업장명_공사장명'], icon=icon)
    marker.add_to(agent_groups[row[agent_col]]) # 담당자별 토글을 위해 그룹에 추가
    marker.add_to(total_cluster) # 전체 합산을 위해 통합 클러스터에 추가

# 6. 범례 및 제어 도구
legend_items_html = "".join([f'<div style="margin-bottom:5px;"><i class="fa fa-map-marker" style="color:{c}"></i> {n}</div>' for n, c in industry_map.items()])
legend_html = f"""
<div id="legend-container" style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;">
    <div id="legend-content" style="display: none; background-color: white; border: 2px solid #ccc; border-radius: 8px; padding: 15px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); min-width: 180px;">
        <b style="font-size: 16px; border-bottom: 1px solid #eee;">📊 업종별 구분</b>{legend_items_html}
        <div style="margin-bottom:5px;"><i class="fa fa-map-marker" style="color:grey"></i> 기타</div>
    </div>
    <button onclick="toggleLegend()" style="float: right; background-color: #333; color: white; border: none; padding: 10px 15px; border-radius: 20px; cursor: pointer; font-weight: bold;">🎨 업종 범례 보기</button>
</div>
<script>function toggleLegend() {{ var c = document.getElementById('legend-content'); c.style.display = (c.style.display === 'none') ? 'block' : 'none'; }}</script>
"""
m.get_root().html.add_child(folium.Element(legend_html))
folium.LayerControl(collapsed=True).add_to(m)
m.save('사업장_현황지도_최종.html')
print("지도가 성공적으로 생성되었습니다.")