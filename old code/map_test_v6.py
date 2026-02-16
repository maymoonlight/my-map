import pandas as pd
import requests
import folium
from folium.plugins import MarkerCluster  # [추가] 클러스터 기능 도구 가져오기
from branca.element import Element

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
    if not addr or pd.isna(addr): return None, None
    
    # [컴닥터의 특급 전처리]
    # 1. 괄호 내용 제거 (예: (양벌동) -> 삭제)
    clean_addr = addr.split('(')[0].strip()
    
    # 2. 상세 주소 패턴 제거 (숫자로 끝나는 지점까지만 남기기)
    # "성남대로779번길 17 4,5층" -> "성남대로779번길 17"까지만 잘라냅니다.
    import re
    # 주소 뒤에 붙은 '층', '호', 또는 공백 뒤의 숫자/문자열을 제거하는 정규식
    clean_addr = re.sub(r'\s\d+층.*$', '', clean_addr) # 층 제거
    clean_addr = re.sub(r'\s\d+호.*$', '', clean_addr) # 호 제거
    # 만약 주소가 '길 17 709' 처럼 끝나면 마지막 숫자뭉치를 지워봅니다.
    parts = clean_addr.split()
    if len(parts) > 4: # 주소가 너무 길면 상세주소가 붙었을 확률이 큼
        clean_addr = " ".join(parts[:4]) 
    
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    url = 'https://dapi.kakao.com/v2/local/search/address.json'
    
    try:
        response = requests.get(url, headers=headers, params={'query': clean_addr})
        result = response.json()
        
        if result.get('documents'):
            return float(result['documents'][0]['y']), float(result['documents'][0]['x'])
        else:
            # 주소로 실패 시 '번지' 등을 빼고 재시도
            retry_addr = clean_addr.replace('번지', '').strip()
            response = requests.get(url, headers=headers, params={'query': retry_addr})
            result = response.json()
            if result.get('documents'):
                return float(result['documents'][0]['y']), float(result['documents'][0]['x'])
    except:
        pass
        
    print(f"⚠️ 최종 실패: {addr} (정제주소: {clean_addr})")
    return None, None
# 2. 업로드했던 파일 읽기
df = pd.read_excel(excel_file, engine='openpyxl')

# 3. 지도 객체 만들기 (광주시청 좌표 중심)
m = folium.Map(location=[37.408, 127.253], zoom_start=12)
# [위치 2] 반복문 시작 전, 마커들을 담을 바구니를 미리 만듭니다!
# 대문자로 시작하는 MarkerCluster()는 도구 이름이고, 소문자 marker_cluster는 바구니 이름입니다.
marker_cluster = MarkerCluster().add_to(m)

# 2. 클러스터 아이콘의 색상을 빨간색으로 강제하는 CSS 주입 (컴닥터의 비법!)
custom_style = """
<style>
    .marker-cluster-small { background-color: rgba(255, 0, 0, 0.6) !important; }
    .marker-cluster-small div { background-color: rgba(255, 0, 0, 0.6) !important; color: white !important; }
    .marker-cluster-medium { background-color: rgba(255, 0, 0, 0.6) !important; }
    .marker-cluster-medium div { background-color: rgba(255, 0, 0, 0.6) !important; color: white !important; }
    .marker-cluster-large { background-color: rgba(255, 0, 0, 0.6) !important; }
    .marker-cluster-large div { background-color: rgba(255, 0, 0, 0.6) !important; color: white !important; }
</style>
"""
m.get_root().header.add_child(Element(custom_style))




# 4. 마커 추가
for _, row in df.iterrows():
    lat, lon = get_coordinates(row['현장주소'])
    
    if lat and lon:
        color, label = get_info(row['중업종'])
        phone = row['전화번호'] if '전화번호' in df.columns else "정보없음"
       
# 팝업창 구성 (전화번호 통화 + 내비게이션 호출)
        popup_html = f"""
        <div style="width:260px; font-family: 'Malgun Gothic', sans-serif; line-height: 1.8; padding: 5px;">
            <h3 style="margin:0 0 8px 0; color: #000; font-size: 18px; word-break: keep-all;">{row['사업장명_공사장명']}</h3>
            <hr style="margin:8px 0; border: 0; border-top: 2px solid #333;">
            
            <div style="font-size: 15px;">
                <b style="color: #555;">업종:</b> {label}<br>
                <b style="color: #555;">연락처:</b> 
                <a href="tel:{phone}" style="color: #007bff; text-decoration: underline; font-weight: bold; font-size: 17px;">{phone}</a>
            </div>

            <div style="margin-top: 15px; display: flex; gap: 8px;">
                <a href="tmap://route?goalname={row['사업장명_공사장명']}&goalpos={lon},{lat}" 
                   style="background-color: #FFD400; color: #000; padding: 10px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; flex: 1; text-align: center; border: 1px solid #e5c100;">T맵 실행</a>
                
                <a href="kakaomap://route?ep={lat},{lon}&by=CAR" 
                   style="background-color: #FAE100; color: #3C1E1E; padding: 10px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; flex: 1; text-align: center; border: 1px solid #e3cc00;">카카오맵</a>
            </div>
            
            <hr style="margin:12px 0; border: 0; border-top: 1px solid #eee;">
            <div style="font-size: 13px; color: #666; word-break: break-all;">
                <b>주소:</b> {row['현장주소']}
            </div>
        </div>
        """
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row['주사업장명'],
            icon=folium.Icon(color=color) 
        ).add_to(marker_cluster)



# 5. 범례(Legend) 추가 (HTML/CSS 주입)
legend_html = f"""
     <div style="position: fixed; 
                 bottom: 10px; right: 10px; width: 200px; 
                 border:2px solid grey; z-index:9999; font-size:13px;
                 background-color:white; opacity: 0.9; padding: 10px;">
     <b>📊 업종별 범례</b><br>
     <i class="fa fa-map-marker" style="color:#70AD26"></i> 도소매 및 소비자용품수리업<br>
     <i class="fa fa-map-marker" style="color:#C22F2D"></i> 창고업<br>
     <i class="fa fa-map-marker" style="color:#37A8DA"></i> 사업서비스업<br>
     <i class="fa fa-map-marker" style="color:#F2932C"></i> 위생서비스업<br>
     <i class="fa fa-map-marker" style="color:#728224"></i> 육상화물취급업<br>
     <i class="fa fa-map-marker" style="color:#575757"></i> 기타
     </div>
     """
m.get_root().html.add_child(folium.Element(legend_html))

# 6. 저장
m.save('현장배정_최종지도.html')
print("전화번호와 범례가 포함된 지도가 완성되었습니다!")
