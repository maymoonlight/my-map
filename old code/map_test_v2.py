import pandas as pd
import requests
import folium

KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
excel_file = '배정명단.xlsx' # 파일명 확인!

# --- [위치 1] 함수 정의 구역에 넣으세요 ---
def get_color(industry):
    """업종에 따라 색상을 결정하는 로직"""
    if '도소매' in industry: return 'green'
    if '창고' in industry: return 'red'
    if '서비스' in industry: return 'blue'
    return 'gray'

def get_coordinates(addr):
    # (기존 get_coordinates 함수 내용은 동일)
    clean_addr = addr.split('(')[0].strip()
    url = 'https://dapi.kakao.com/v2/local/search/address.json'
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {'query': clean_addr}
    try:
        response = requests.get(url, headers=headers, params=params)
        result = response.json()
        if result['documents']:
            return float(result['documents'][0]['y']), float(result['documents'][0]['x'])
    except:
        pass
    return None, None

# 2. 파일 읽기
df = pd.read_csv(excel_file)

# 3. 지도 초기화
m = folium.Map(location=[37.408, 127.253], zoom_start=12)

# 4. 데이터 반복문
for _, row in df.iterrows():
    lat, lon = get_coordinates(row['현장주소'])
    if lat and lon:
        # --- [위치 2] 반복문 내부에서 색상을 결정합니다 ---
        target_color = get_color(row['중업종']) # 여기서 함수 호출!
        
        info = f"<b>{row['사업장명_공사장명']}</b><br>{row['중업종']}"
        
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(info, max_width=300),
            tooltip=row['주사업장명'],
            # [적용] 결정된 색상을 여기에 대입합니다
            icon=folium.Icon(color=target_color, icon='info-sign') 
        ).add_to(m)

# 5. 저장
m.save('현장배정_결과지도_컬러.html')
print("컬러 지도가 완성되었습니다!")