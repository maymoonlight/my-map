import pandas as pd
import requests
import folium

# 1. 여기에 아까 확인한 'REST API 키'를 넣으세요!
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
excel_file = '배정명단.xlsx'

# 마커 색상을 결정하는 함수
def get_color(industry):
    if '도소매 및 소비자용품수리업' in industry: return 'green', 'shopping-cart'  # 초록색 + 카트
    if '창고업' in industry: return 'red', 'home'
    if '사업서비스업' in industry: return 'blue'
    if '위생 및 유사서비스업' in industry: return 'orange'
    if '육상화물취급업' in industry: return 'darkgreen'
    return 'gray'

def get_coordinates(addr):
    """
    주소를 위도(Lat), 경도(Lon)로 변환하는 함수.
    정제된 코드로 가독성과 에러 처리를 최적화했습니다.
    """
    # 1. 예외 처리: 주소가 비어있으면 즉시 반환
    if not addr or pd.isna(addr):
        return None, None
        
    # 2. 주소 전처리: ( ) 괄호와 공백 제거
    clean_addr = addr.split('(')[0].strip()
    
    url = 'https://dapi.kakao.com/v2/local/search/address.json'
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {'query': clean_addr}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        # HTTP 상태 코드가 200이 아닐 경우 에러 발생
        response.raise_for_status() 
        result = response.json()
        
        # 3. 데이터 추출: .get()을 사용하여 안정적으로 접근
        documents = result.get('documents')
        if documents:
            lat = float(documents[0]['y'])
            lon = float(documents[0]['x'])
            return lat, lon
        
        # 검색 결과가 없는 경우만 로그 출력
        print(f"⚠️ 결과 없음: {clean_addr}")
            
    except Exception as e:
        print(f"❌ API 통신 오류 ({clean_addr}): {e}")
        
    return None, None

# 2. 업로드했던 파일 읽기
df = pd.read_excel(excel_file, engine='openpyxl')

# 3. 지도 객체 만들기 (광주시청 좌표 중심)
m = folium.Map(location=[37.408, 127.253], zoom_start=12)

# 4. 데이터 행마다 마커 추가
for _, row in df.iterrows():
    lat, lon = get_coordinates(row['현장주소'])
    if lat and lon:
        # 마커를 클릭했을 때 나올 팝업 내용
        info = f"<b>{row['사업장명_공사장명']}</b><br>{row['중업종']}"
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(info, max_width=300),
            tooltip=row['주사업장명'],
            icon=folium.Icon(color=get_color(row['중업종']), icon='nfo-sign') # 색상과 아이콘 변경!
        ).add_to(m)

# 5. 결과물을 웹페이지(HTML)로 저장
m.save('현장배정_결과지도.html')
print("지도 생성 완료! 폴더 안에 '현장배정_결과지도.html' 파일이 생겼을 겁니다.")
