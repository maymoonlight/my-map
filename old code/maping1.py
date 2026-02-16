import pandas as pd
import requests
import folium
from folium import plugins
import re

# 1. 설정 및 API 키
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
excel_file = '현황.xlsx'  # 에러 방지를 위해 파일명 직접 지정

# 2. 데이터 로드 (시트명 '맵핑' 지정 및 데이터 타입 왜곡 방지)
# '사업장관리번호' 등을 텍스트로 처리하여 지수 표기 방지
try:
    df = pd.read_excel(
        excel_file, 
        sheet_name='맵핑', 
        dtype={'사업장관리번호': str, '개시번호': str}
    )
except Exception as e:
    print(f"엑셀 로드 에러: {e}. openpyxl 라이브러리 설치 여부를 확인하세요.")

# 3. 카카오 API 지리정보 분석 함수 (주소 정제 포함)
def get_coords(address):
    if pd.isna(address): return None, None
    # 주소 내 불필요한 괄호 정보 제거하여 인식률 향상
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

# [출력1] 위경도 좌표 업데이트
print("카카오 API를 통한 좌표 분석 및 업데이트 중...")
df['경도'], df['위도'] = zip(*df['현장주소'].apply(get_coords))
df.to_excel('현황_좌표업데이트.xlsx', index=False) # 업데이트 결과 저장

# 4. 지도 생성 및 담당자별 레이어 설정
valid_df = df.dropna(subset=['위도', '경도'])
m = folium.Map(location=[valid_df['위도'].mean(), valid_df['경도'].mean()], zoom_start=11)

# 방문 차수별 배경색 매핑
visit_colors = {1: 'red', 2: 'orange', 3: 'yellow', 4: 'green', 5: 'blue'}

# 담당자별 토글 그룹 생성
agent_groups = {}
for agent in valid_df['담당자'].unique():
    agent_groups[agent] = folium.FeatureGroup(name=f"담당자: {agent}").add_to(m)

# 5. 마커 생성 반복문 (대표님 제시 규칙 적용)
for _, row in valid_df.iterrows():
    v_cnt = int(row['방문회차'])
    is_disaster = int(row['재해여부']) > 0
      
    
    # 5. 마커 생성 반복문 내 미방문(v_cnt == 0) 구간 수정
    if v_cnt == 0:
        # [방문 전] 원형(Circle) 마커 설정
        is_manufacturing = '제조' in str(row['특화분야'])
        
        # 1. 일반 제조인 경우: 배경 흰색
        if is_manufacturing:
            bg = 'white'
            # 대표님 지정 조건: 제조 업종별 내부 점(dot) 색상 분기
            # 데이터 내 별도 조건 열이 없다면 아래와 같이 업종명이나 번호로 매칭 가능합니다.
            t_colors = ['red', 'blue', 'green', 'black']
            txt_c = t_colors[int(row['번호']) % 4] 
        
        # 2. 일반 기타인 경우: 배경 회색
        else:
            bg = 'grey'
            # 대표님 지정 조건: 기타 업종별 내부 점 색상
            t_colors = ['black', 'green']
            txt_c = t_colors[int(row['번호']) % 2]

        # [핵심 수정] icon_shape를 'circle'로 지정하여 물방울 꼬리 제거
        icon = plugins.BeautifyIcon(
            icon='circle',                # 내부 아이콘 모양 (점)
            icon_shape='circle',          # 마커 전체 외곽 형태 (물방울이 아닌 원형)
            border_color='lightgray',     # 외곽 테두리 색상
            background_color=bg,          # 마커 배경색 (흰색 또는 회색)
            text_color=txt_c,             # 내부 점(dot)의 컬러
            inner_icon_style='font-size:10px; padding-top:2px;' # 아이콘 크기 및 위치 상세 조정
        )
       
    else:
        # [방문 후] 물방울 마커 로직
        bg = visit_colors.get(v_cnt, 'gray')
        
        if not is_disaster:
            # 무사고: 하얀 원 바탕 + 배경색 숫자
            inner_style = 'background-color:white; border-radius:50%; width:16px; height:16px; line-height:16px;'
            txt_c = bg
            border_c = bg        
        else:
            # 사고발생: 마커 배경색 물방울 + 검은색 원 + 흰색 숫자
            # 1. 내부 원 스타일: 배경색을 검정(black)으로 변경하고, 내부 테두리는 삭제하여 깔끔하게 처리합니다.
            inner_style = 'background-color:black; border-radius:50%; width:16px; height:16px; line-height:16px;'
        
            # 2. 내부 글자 색상: 대표님 의견대로 흰색(white)을 유지합니다.
            txt_c = 'white'
            
            # 3. 물방울 외곽 테두리: 무사고 사업장 로직과 동일하게 마커 배경색(bg)으로 일치시킵니다.
            border_c = bg



        icon = plugins.BeautifyIcon(
            icon_shape='marker', number=v_cnt,
            background_color=bg, border_color=border_c,
            text_color=txt_c, inner_icon_style=inner_style
        )

    # 팝업 정보 및 마커 추가
    popup_info = f"<b>{row['사업장명_공사장명']}</b><br>차수: {v_cnt}회 / 재해: {row['재해여부']}건"
    folium.Marker(
        location=[row['위도'], row['경도']],
        popup=folium.Popup(popup_info, max_width=300),
        icon=icon
    ).add_to(agent_groups[row['담당자']])

# 6. 토글 메뉴 및 저장
folium.LayerControl(collapsed=True).add_to(m)
m.save('사업장_현황지도_최종.html')