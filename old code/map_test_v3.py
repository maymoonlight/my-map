import pandas as pd
import requests
import folium
from folium.plugins import MarkerCluster  # [추가] 클러스터 기능 도구 가져오기


# 1. 여기에 아까 확인한 'REST API 키'를 넣으세요!
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
excel_file = '배정명단.xlsx'

# 마커 색상을 결정하는 함수
def get_info(industry):
    if '도소매 및 소비자용품수리업' in industry: return 'green', '도소매 및 소비자용품수리업'
    if '창고업' in industry: return 'red', '창고업'
    if '사업서비스업' in industry: return 'blue', '사업서비스업'
    if '위생 및 유사서비스업' in industry: return 'orange', '위생 및 유사서비스업'
    if '육상화물취급업' in industry: return 'darkgreen', '육상화물취급업'
    return 'gray', '기타'

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

# 4. 마커 추가
for _, row in df.iterrows():
    lat, lon = get_coordinates(row['현장주소'])
    
    if lat and lon:
        color, label = get_info(row['중업종'])
        # I열(전화번호) 가져오기 - 열 이름이 '전화번호'라고 가정하거나 인덱스로 접근
        phone = row['전화번호'] if '전화번호' in df.columns else "정보없음"
        
        # 팝업 내용에 전화번호 추가
        popup_html = f"""
        <div style="width:200px">
            <b>{row['사업장명_공사장명']}</b><br>
            <hr style='margin:5px 0'>
            <b>업종:</b> {row['중업종']}<br>
            <b>연락처:</b> {phone}<br>
            <b>주소:</b> {row['현장주소']}
        </div>
        """
        
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row['주사업장명'],
            icon=folium.Icon(color=color)
        ).add_to(m)

# 5. 범례(Legend) 추가 (HTML/CSS 주입)
legend_html = """
     <div style="position: fixed; 
                 bottom: 50px; right: 50px; width: 150px; height: 120px; 
                 border:2px solid grey; z-index:9999; font-size:14px;
                 background-color:white; opacity: 0.8;
                 padding: 10px;
                 ">
     <b>업종 구분</b><br>
     <i class="fa fa-map-marker" style="color:green"></i>&nbsp; 도소매 및 소비자용품수리업<br>
     <i class="fa fa-map-marker" style="color:red"></i>&nbsp; 창고업<br>
     <i class="fa fa-map-marker" style="color:blue"></i>&nbsp; 사업서비스업<br>
     <i class="fa fa-map-marker" style="color:orange"></i>&nbsp; 위생 및 유사서비스업<br>
     <i class="fa fa-map-marker" style="color:darkgreen"></i>&nbsp; 육상화물취급업<br>
     <i class="fa fa-map-marker" style="color:gray"></i>&nbsp; 기타

     </div>
     """
m.get_root().html.add_child(folium.Element(legend_html))

# 6. 저장
m.save('현장배정_최종지도.html')
print("전화번호와 범례가 포함된 지도가 완성되었습니다!")
