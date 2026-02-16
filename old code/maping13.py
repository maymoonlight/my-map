import pandas as pd
import requests
import folium
from folium import plugins
from branca.element import Element
import re

# 1. 설정 및 데이터 로드
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
excel_file = '현황.xlsx'

try:
    df = pd.read_excel(excel_file, sheet_name='맵핑', dtype={'사업장관리번호': str, '개시번호': str})
except Exception as e:
    print(f"파일 로딩 실패: {e}")

# 2. 주소 분석 함수
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

# 3. 지도 및 스타일 설정
valid_df = df.dropna(subset=['위도', '경도'])
m = folium.Map(location=[valid_df['위도'].mean(), valid_df['경도'].mean()], zoom_start=11)

custom_style = """
<style>
    .marker-cluster-small { background-color: rgba(255, 0, 0, 0.6) !important; }
    .marker-cluster-small div { background-color: rgba(255, 0, 0, 0.8) !important; color: white !important; font-weight: bold; }
    .marker-cluster-medium { background-color: rgba(255, 0, 0, 0.6) !important; }
    .marker-cluster-medium div { background-color: rgba(255, 0, 0, 0.8) !important; color: white !important; font-weight: bold; }
    .marker-cluster-large { background-color: rgba(255, 0, 0, 0.6) !important; }
    .marker-cluster-large div { background-color: rgba(255, 0, 0, 0.8) !important; color: white !important; font-weight: bold; }
    .leaflet-popup-close-button {
        font-size: 25px !important; /* x 표시 크기 (기본보다 훨씬 크게) */
        padding: 10px 10px 0 0 !important; /* 터치하기 편하게 여백 추가 */
        color: #333 !important; /* 단추 색상 */
        font-weight: bold !important;
    }
</style>
"""
m.get_root().header.add_child(Element(custom_style))

# 4. 수행요원별 독립 클러스터 생성
agent_clusters = {}
agent_col = '수행요원' if '수행요원' in valid_df.columns else '담당자'
for agent in valid_df[agent_col].unique():
    cluster = plugins.MarkerCluster(name=f"수행요원: {agent}", show=True).add_to(m)
    agent_clusters[agent] = cluster

visit_colors = {1: 'red', 2: 'orange', 3: 'yellow', 4: 'green', 5: 'blue'}
industry_map = {'자동차': 'red', '화학': 'blue', '섬유': 'green', '기계': 'black', '판매': 'yellow', '식품': 'orange', '창고': 'cadetblue'}

# 5. 마커 생성 루프
for _, row in valid_df.iterrows():
    v_cnt, disaster_count = int(row['방문회차']), int(row['재해여부'])
    is_disaster = disaster_count > 0
    current_industry_text = str(row['업종']) if pd.notna(row['업종']) else "정보없음"
    bg = next((color for key, color in industry_map.items() if key in current_industry_text), 'grey')
    
    # [핵심] 팝업용 변수 선언 (순서 중요: 팝업 생성 전에 모두 정의되어야 함)
    phone = row['전화번호'] if '전화번호' in valid_df.columns else "정보없음"
    site_manager = row['사업장담당자명직위'] if pd.notna(row['사업장담당자명직위']) else "정보없음"
    manager_phone = row['사업장담당자연락처'] if pd.notna(row['사업장담당자연락처']) else "정보없음"
    
    # 이메일 데이터 처리 및 링크 설정 (그린 컬러, 폰트 10)
    raw_email = row['담당자이메일'] if '담당자이메일' in valid_df.columns and pd.notna(row['담당자이메일']) else ""
    if raw_email:
        email_display = f'<a href="mailto:{raw_email}" style="color: green; font-size: 16px; text-decoration: none;">{raw_email}</a>'
    else:
        email_display = '<span style="color: green; font-size: 16px;">정보없음</span>'
    
    main_office = row['주사업장'] if pd.notna(row['주사업장']) else ""
    lat, lon = row['위도'], row['경도']




    # -----------------------------------------------------------------
    # [A] 미방문 사업장 스타일 설정 (v_cnt == 0)
    # -----------------------------------------------------------------
    if v_cnt == 0:
        special_field = str(row['특화분야'])
        # 제조는 테두리 없음(0px), 일반/기타는 파란색 테두리(2px)
        border_c, border_w = (bg, '0px') if '제조' in special_field else ('blue', '2px')
        
        icon = plugins.BeautifyIcon(
            icon=' ', 
            icon_shape='marker', 
            icon_size=[22, 22],  # 미방문 마커 크기 조절 가능
            border_color=border_c, 
            background_color=bg, 
            inner_icon_style=f'border:{border_w} solid {border_c}; display:none;' # 노란 점 제거
        )

    # -----------------------------------------------------------------
    # [B] 방문 완료 사업장 스타일 설정 (v_cnt > 0)
    # -----------------------------------------------------------------
    else:
        bg = visit_colors.get(v_cnt, 'gray')
        
        # 1. font-size: 숫자 크기 (예: 11px, 12px 등)
        # 2. font-weight: 숫자 두께 (bold 추가 시 더 잘 보임)
        # 3. line-height: 숫자의 상하 위치 (원의 높이인 16px와 맞추면 중앙에 옵니다)
        if not is_disaster:
            inner_style = (
                f'background-color:white; border-radius:50%; '
                f'width:16px; height:16px; '
                f'font-size:12px; font-weight:bold; line-height:16px; ' # <--- 크기와 두께 지정
                f'margin-top:2px; margin-left:2px; ' 
                f'text-align:center; padding-left:0px;'
            )
            txt_c = bg
        else:
            inner_style = (
                f'background-color:black; border-radius:50%; '
                f'width:16px; height:16px; '
                f'font-size:12px; font-weight:bold; line-height:16px; '
                f'margin-top:2px; margin-left:2px; '
                f'text-align:center; padding-left:0px;'
            )
            txt_c = 'white'
        
        icon = plugins.BeautifyIcon(
            icon_shape='marker', 
            icon_size=[28, 28], 
            number=v_cnt, 
            background_color=bg, 
            border_color=bg, 
            text_color=txt_c, 
            inner_icon_style=inner_style
        )

    # 팝업 HTML
    tmap_url = f"tmap://route?goalname={row['사업장명_공사장명']}&goalx={lon}&goaly={lat}"
    d_display, d_color = (f"재해({disaster_count}건)", "red") if is_disaster else ("무재해", "blue")
    
    popup_html = f"""
    <div style="width:280px; font-family: 'Malgun Gothic', sans-serif; line-height: 1.8; padding: 5px;">
        <h3 style="margin:0 0 8px 0; font-size: 18px;"><span style="color: #666; font-size: 14px;">[{main_office}]</span><br><b>{row['사업장명_공사장명']}</b></h3>
        <hr style="margin:8px 0; border-top: 2px solid #333;">
        <div style="font-size: 16px;">
            <b>대표번호:</b> <a href="tel:{phone}" style="color: #0022ff; font-weight: bold; font-size: 16px;">{phone}</a><br>
            <b style="color: #333; font-weight: bold; font-size: 16px;">담당자명:</b> {site_manager}<br>
            <b>담당자폰:</b> <a href="tel:{manager_phone}" style="color: #0022ff; font-weight: bold; font-size: 16px;">{manager_phone}</a><br>
            <b style="color: #333; font-weight: bold; font-size: 16px;">이메일:</b> {email_display}
        </div>
        <div style="margin-top: 15px; display: flex; gap: 8px;">
            <a href="{tmap_url}" style="background-color: #0022FF; color: white; padding: 10px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; flex: 1; text-align: center;">T맵 실행</a>
            <a href="kakaomap://route?ep={lat},{lon}&by=CAR" style="background-color: #FAE100; color: #3C1E1E; padding: 10px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; flex: 1; text-align: center;">카카오맵</a>
        </div>
        <hr style="margin:12px 0; border: 0; border-top: 1px solid #eee;">
        <div style="font-size: 14px; color: #555; line-height: 1.6;">
            <b>주소:</b> {row['현장주소']}<br>
            <b>업종:</b> {current_industry_text}<br>
            <b>방문:</b> {v_cnt}회 / <b>상태:</b> <span style="color: {d_color}; font-weight: bold;">{d_display}</span>
        </div>
    </div>
    """
    folium.Marker(location=[lat, lon], popup=folium.Popup(popup_html, max_width=300), tooltip=row['사업장명_공사장명'], icon=icon).add_to(agent_clusters[row[agent_col]])

# 6. 범례(Legend) 표 추가
legend_items_html = "".join([f'<div style="margin-bottom:12px; display:flex; align-items:center;"><i class="fa fa-map-marker" style="color:{color}; font-size:24px; margin-right:12px; width:20px; text-align:center;"></i><span style="font-size:14px; font-weight:bold; color:#333;">{name}</span></div>' for name, color in industry_map.items()])
legend_html = f"""
<div id="legend-container" style="position: fixed; bottom: 30px; right: 20px; z-index: 9999;">
    <div id="legend-content" style="display: none; background-color: white; border: 1px solid #ddd; border-radius: 15px; padding: 20px; margin-bottom: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); min-width: 160px;">
        <b style="font-size: 15px; display:block; margin-bottom:15px; border-bottom: 2px solid #f0f0f0; padding-bottom:5px; color:#000;">📊 미방문 업종 구분</b>
        {legend_items_html}
        <div style="display:flex; align-items:center;"><i class="fa fa-map-marker" style="color:grey; font-size:24px; margin-right:12px; width:20px; text-align:center;"></i><span style="font-size:14px; font-weight:bold; color:#333;">기타</span></div>
    </div>
    <button onclick="toggleLegend()" style="float: right; width: 50px; height: 50px; background-color: #333; color: white; border: none; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center;"><i class="fa fa-th-list" style="font-size: 20px;"></i></button>
</div>
<script>function toggleLegend() {{ var c = document.getElementById('legend-content'); c.style.display = (c.style.display === 'none') ? 'block' : 'none'; }}</script>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# 7. 제어 도구
folium.LayerControl(collapsed=True).add_to(m)
m.save('사업장_현황지도_최종.html')
print("지도가 성공적으로 생성되었습니다.")