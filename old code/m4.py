import pandas as pd
import requests
import folium
from folium.features import DivIcon
import re
import os

# ==========================================
# 1. 환경 설정 및 데이터 로드
# ==========================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx'

def get_coordinates(address):
    """주소를 위경도로 변환 (카카오 API)"""
    if pd.isna(address) or address == "": return None, None
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if res.get('documents'):
            return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
    except: pass
    return None, None

# 데이터 로드
df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl')

# 최고 차수 분석
df['차수_num'] = df['배정차수'].apply(lambda x: int(re.findall(r'\d+', str(x))[0]) if re.findall(r'\d+', str(x)) else 0)
max_round = df['차수_num'].max()

# ==========================================
# 2. 정밀 수제 마커 생성 함수 (DivIcon 방식)
# ==========================================
def create_custom_x_marker(row):
    """
    기존 핀 모양을 유지하면서 내부에 정밀한 'X'를 삽입
    """
    lat, lon = row['위도'], row['경도']
    
    # [No Black Box] HTML/CSS로 마커를 직접 조립합니다.
    icon_html = f"""
    <div style="position: relative; width: 30px; height: 42px;">
        <svg viewBox="0 0 32 42" xmlns="http://www.w3.org/2000/svg" style="width: 30px; height: 42px;">
            <path fill="white" stroke="red" stroke-width="2.5" 
                  d="M16 0C7.2 0 0 7.2 0 16c0 12 16 26 16 26s16-14 16-26c0-8.8-7.2-16-16-16z"/>
        </svg>
        <div style="
            position: absolute;
            top: 5px;           /* 위아래 위치 조정 */
            left: 50%;
            transform: translateX(-50%);
            color: red;
            font-size: 18px;    /* X의 크기 */
            font-weight: 900;   /* 아주 굵게 */
            font-family: 'Arial', sans-serif;
        ">X</div>
    </div>
    """
    
    return folium.Marker(
        location=[lat, lon],
        icon=DivIcon(
            icon_size=(30, 42),
            icon_anchor=(15, 42),
            html=icon_html
        ),
        popup=folium.Popup(f"<b>{row['사업장명_공사장명']}</b><br>방문회차: 9회(긴급)", max_width=250),
        tooltip=f"🚨긴급점검: {row['사업장명_공사장명']}"
    )

# ==========================================
# 3. 지도 생성 및 마커 렌더링
# ==========================================
print("🚀 주소 변환 및 수제 마커 렌더링을 시작합니다...")
df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=11)

for _, row in df_map.iterrows():
    # 조건 1: 방문회차가 9인 경우 (수제 X 마커 적용)
    if row.get('방문회차') == 9:
        marker = create_custom_x_marker(row)
        marker.add_to(m)
        
    # 조건 2: 일반 데이터 (기존 마커 로직)
    else:
        # 핀 색상 (차수 강조)
        pin_color = 'black' if row['차수_num'] == max_round else 'lightgray'
        
        # 특화분야(D열) 아이콘 분기
        special_field = str(row.get('특화분야', ''))
        if '제조' in special_field:
            icon_shape = 'industry'
        elif '기타' in special_field:
            icon_shape = 'building'
        else:
            icon_shape = 'circle'
            
        folium.Marker(
            location=[row['위도'], row['경도']],
            icon=folium.Icon(color=pin_color, icon=icon_shape, prefix='fa', icon_color='white'),
            popup=folium.Popup(f"<b>{row['사업장명_공사장명']}</b><br>차수: {row['배정차수']}", max_width=250),
            tooltip=row['사업장명_공사장명']
        ).add_to(m)

# 결과 저장
output_name = '최종_전문가용_현황지도.html'
m.save(output_name)

print("-" * 40)
print(f"✨ 모든 요구사항이 반영된 지도가 완성되었습니다!")
print(f"📍 방문회차 9회 지점: 수제 'X' 핀 적용")
print(f"📂 결과 파일: {os.path.abspath(output_name)}")
print("-" * 40)