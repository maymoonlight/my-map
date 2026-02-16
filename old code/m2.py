import pandas as pd
import requests
import folium
import re
from pathlib import Path

# ==========================================
# 1. 환경 설정 및 데이터 로드
# ==========================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx'

def get_coordinates(address):
    """카카오 API 좌표 변환"""
    if pd.isna(address): return None, None
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if res.get('documents'):
            return float(res['documents'][0]['y']), float(res['documents'][0]['x'])
    except: pass
    return None, None

try:
    df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl')
except Exception as e:
    print(f"❌ 파일 로드 실패: {e}")
    exit()

# 차수 숫자 추출 및 최고 차수 파악
def extract_number(text):
    found = re.findall(r'\d+', str(text))
    return int(found[0]) if found else 0

df['차수_숫자'] = df['배정차수'].apply(extract_number)
max_round = df['차수_숫자'].max()

# ==========================================
# 2. 좌표 변환
# ==========================================
print("🚀 주소 변환 및 마커 생성 중...")
df[['위도', '경도']] = df['현장주소'].apply(lambda x: pd.Series(get_coordinates(x)))
df_map = df.dropna(subset=['위도', '경도']).copy()

# ==========================================
# 3. 지도 시각화 (기본 마커 + 내부 원형 아이콘)
# ==========================================
m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=12)

for _, row in df_map.iterrows():
    # [색상 전략]
    # 최고 차수(2차): 'black' 또는 'darkgray'
    # 일반 차수(1차): 'lightgray'
    is_highest = (row['차수_숫자'] == max_round)
    marker_color = 'black' if is_highest else 'lightgray'
    
    # 기본 핀 마커를 사용하되 내부 아이콘만 'circle'로 변경
    custom_icon = folium.Icon(
        color=marker_color,      # 핀(물방울 전체)의 색상
        icon='industry',           # 내부 기호 (원형)
        prefix='fa',             # Font-Awesome 아이콘 라이브러리 사용
        icon_color='white'       # 내부 원형의 색상
    )
    
    folium.Marker(
        location=[row['위도'], row['경도']],
        icon=custom_icon,
        popup=folium.Popup(f"<b>{row['사업장명_공사장명']}</b><br>{row['배정차수']}", max_width=250),
        tooltip=f"{row['사업장명_공사장명']} ({row['배정차수']})"
    ).add_to(m)

# 결과 저장
output_file = '카카오핀_원형아이콘_결과.html'
m.save(output_file)
print(f"✨ 완료! '{output_file}' 파일을 확인해 보세요.")