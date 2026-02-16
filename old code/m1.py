import pandas as pd
import requests
import folium
import os
from pathlib import Path

# ==========================================
# 1. 환경 설정 및 데이터 로드 (read_excel로 변경)
# ==========================================
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
FILE_NAME = '현황1.xlsx' 

def get_coordinates(address):
    """카카오 API 주소 변환 함수"""
    if pd.isna(address) or address == "": return None, None
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('documents'):
                return float(result['documents'][0]['y']), float(result['documents'][0]['x'])
    except:
        pass
    return None, None

# [Logic First] 엑셀 파일의 '맵핑' 시트를 직접 읽어옵니다.
try:
    # engine='openpyxl'을 명시하여 xlsx 파일을 안전하게 읽습니다.
    df = pd.read_excel(FILE_NAME, sheet_name='맵핑', engine='openpyxl')
    print(f"✅ '{FILE_NAME}'의 [맵핑] 탭을 성공적으로 로드했습니다.")
except Exception as e:
    print(f"❌ 에러 발생: {e}")
    print("팁: 파일이 열려있다면 닫고 다시 실행해 보세요.")
    exit()

# ==========================================
# 2. 좌표 변환 및 데이터 정제
# ==========================================
print("🚀 주소를 기반으로 지도를 그리는 중입니다...")

# 좌표 추출 (속도 향상을 위해 apply 사용)
coords = df['현장주소'].apply(get_coordinates)
df['위도'], df['경도'] = zip(*coords)

# 좌표가 없는 데이터(주소 불명) 제외
df_map = df.dropna(subset=['위도', '경도']).copy()

# ==========================================
# 3. 지도 시각화 (1차-Blue / 2차-Red)
# ==========================================
if not df_map.empty:
    m = folium.Map(location=[df_map['위도'].mean(), df_map['경도'].mean()], zoom_start=12)

    for _, row in df_map.iterrows():
        # '배정차수' 열의 값을 기준으로 색상 결정
        color = 'blue' if '1차' in str(row['배정차수']) else 'red'
        
        folium.Marker(
            location=[row['위도'], row['경도']],
            popup=folium.Popup(f"<b>{row['사업장명_공사장명']}</b><br>{row['배정차수']}", max_width=300),
            icon=folium.Icon(color=color, icon='map-marker'),
            tooltip=row['사업장명_공사장명']
        ).add_to(m)

    output_file = '카카오맵_매핑결과.html'
    m.save(output_file)
    print(f"✨ 완료! '{output_file}' 파일을 브라우저로 열어보세요.")
else:
    print("⚠️ 좌표로 변환된 데이터가 없습니다. 주소를 확인해 주세요.")