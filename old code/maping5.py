import pandas as pd
import requests
import folium
from folium import plugins
import re

# 1. 설정 및 API 키
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
excel_file = '현황.xlsx'

# 2. 데이터 로드 (시트명 '맵핑' 지정 및 데이터 타입 유지)
try:
    df = pd.read_excel(
        excel_file, 
        sheet_name='맵핑', 
        dtype={'사업장관리번호': str, '개시번호': str}
    )
except Exception as e:
    print(f"파일 로딩 실패: {e}")

# 3. 주소 분석 함수 (인식률 최적화)
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

# 4. 지도 생성 및 레이어 그룹화 (담당자 -> 수행요원 명칭 변경)
valid_df = df.dropna(subset=['위도', '경도'])
m = folium.Map(location=[valid_df['위도'].mean(), valid_df['경도'].mean()], zoom_start=11)

# 방문 차수별 색상 매핑
visit_colors = {1: 'red', 2: 'orange', 3: 'yellow', 4: 'green', 5: 'blue'}

# 수행요원별 토글 그룹 생성
agent_groups = {}
agent_col = '수행요원' if '수행요원' in valid_df.columns else '담당자'

for agent in valid_df[agent_col].unique():
    agent_groups[agent] = folium.FeatureGroup(name=f"수행요원: {agent}").add_to(m)

# 5. 마커 및 팝업 생성 로직
for _, row in valid_df.iterrows():
    v_cnt = int(row['방문회차'])
    is_disaster = int(row['재해여부']) > 0
    industry = str(row['업종'])
    phone = row['전화번호'] if '전화번호' in valid_df.columns else "정보없음"
    site_manager = row['사업장담당자명직위'] if pd.notna(row['사업장담당자명직위']) else "정보없음"
    manager_phone = row['사업장담당자연락처'] if pd.notna(row['사업장담당자연락처']) else "정보없음"
    lat, lon = row['위도'], row['경도']

    # [A] 미방문 사업장 스타일 (v_cnt == 0) - 제조 보더 없음 / 일반 보더 있음
    if v_cnt == 0:
        special_field = str(row['특화분야'])
        if '제조' in special_field:
            bg = 'red' if '자동차' in industry else 'blue' if '화학' in industry else 'green' if '섬유' in industry else 'black' if '기계' in industry else 'grey'
             
            border_c, border_w = bg, '0px'
        else:
            bg = 'black' if '서비스' in industry else 'green' if '판매' in industry else 'red' if '창고' in industry else 'grey'
            border_c, border_w = 'blue', '2px'

        icon = plugins.BeautifyIcon(
            icon=' ', icon_shape='marker', icon_size=[22, 22],
            border_color=border_c, background_color=bg,
            inner_icon_style=f'border:{border_w} solid {border_c}; display:none;' # 노란 점 제거
        )

    # [B] 방문 완료 사업장 스타일 (v_cnt > 0) - 사고 시 검정색 반전 강조
    else:
        bg = visit_colors.get(v_cnt, 'gray')
        inner_bg = "black" if is_disaster else "white"
        txt_c = "white" if is_disaster else bg
        # 위치 미세 조정: text-align:center 및 padding-left 적용
        inner_style = f'background-color:{inner_bg}; border-radius:50%; width:16px; height:16px; line-height:16px; margin-top:2px; text-align:center; padding-left:1px;'
        
        icon = plugins.BeautifyIcon(
            icon_shape='marker', icon_size=[40, 40], number=v_cnt,
            background_color=bg, border_color=bg, text_color=txt_c,
            inner_icon_style=inner_style
        )

    # [C] 팝업창 구성 (연락처 및 네비게이션 연동)
    tmap_url = f"tmap://route?goalname={row['사업장명_공사장명']}&goalx={lon}&goaly={lat}"
    
    # 팝업 폰트 설정 가이드 (수정 시 참고)
    # 상호명: 20px / 대표번호: 17px(파랑) / 담당자명: 16px / 담당자폰: 17px(빨강) / 주소: 15px
    popup_html = f"""
    <div style="width:280px; font-family: 'Malgun Gothic', sans-serif; line-height: 1.8; padding: 5px;">
        <h3 style="margin:0 0 8px 0; font-size: 20px;">{row['사업장명_공사장명']}</h3>
        <hr style="margin:8px 0; border-top: 2px solid #333;">
        <div style="font-size: 16px;">
            <b>대표번호:</b> <a href="tel:{phone}" style="color: #007bff; font-weight: bold; font-size: 17px;">{phone}</a><br>
            <b style="color: #333; font-size: 16px;">담당자명:</b> {site_manager}<br>
            <b>담당자폰:</b> <a href="tel:{manager_phone}" style="color: #d9534f; font-weight: bold; font-size: 17px;">{manager_phone}</a>
        </div>
        <div style="margin-top: 15px; display: flex; gap: 8px;">
            <a href="{tmap_url}" style="background-color: #0022FF; color: #FFFFFF; padding: 10px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; flex: 1; text-align: center; border: 1px solid #285ae6;">T맵 실행</a>
            <a href="kakaomap://route?ep={lat},{lon}&by=CAR" style="background-color: #FAE100; color: #3C1E1E; padding: 10px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; flex: 1; text-align: center; border: 1px solid #e3cc00;">카카오맵</a>
        </div>
        <hr style="margin:12px 0; border: 0; border-top: 1px solid #eee;">
        <div style="font-size: 15px; color: #666; word-break: keep-all; line-height: 1.4;">
            <b style="color: #333;">주소:</b> {row['현장주소']}
        </div>
    </div>
    """

    # [D] 마커 배치 (수행요원별 레이어에 추가)
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=row['사업장명_공사장명'],
        icon=icon
    ).add_to(agent_groups[row[agent_col]])

# 6. 제어 도구 추가 및 파일 저장
folium.LayerControl(collapsed=True).add_to(m)
m.save('사업장_현황지도_최종.html')
print("지도가 성공적으로 생성되었습니다.")