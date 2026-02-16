import pandas as pd
import requests
import folium
from folium import plugins
import re

# 1. 설정 및 API 키
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
excel_file = '현황.xlsx'

# 2. 데이터 로드 (시트명 '맵핑' 지정 및 데이터 타입 왜곡 방지)
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

# 좌표 추출 및 업데이트 (출력1)
print("위경도 좌표 분석 중...")
df['경도'], df['위도'] = zip(*df['현장주소'].apply(get_coords))
df.to_excel('현황_좌표업데이트.xlsx', index=False)

# 4. 지도 생성 및 레이어 그룹화
valid_df = df.dropna(subset=['위도', '경도'])
m = folium.Map(location=[valid_df['위도'].mean(), valid_df['경도'].mean()], zoom_start=11)

# 방문 차수별 색상 매핑
visit_colors = {1: 'red', 2: 'orange', 3: 'yellow', 4: 'green', 5: 'blue'}

# 담당자별 토글 그룹
agent_groups = {}
for agent in valid_df['담당자'].unique():
    agent_groups[agent] = folium.FeatureGroup(name=f"담당자: {agent}").add_to(m)

# 5. 마커 생성 로직 (수정된 조건 반영)
for _, row in valid_df.iterrows():
    v_cnt = int(row['방문회차'])
    is_disaster = int(row['재해여부']) > 0
    industry = str(row['중업종']) # I열 업종 구분 데이터

    if v_cnt == 0:
        # [미방문 사업장] - 업종별 컬러 및 테두리 굵기 설정
        border_w = '1px' # 대표님, 여기서 보더 굵기를 자유롭게 조절하시면 됩니다.

        icon = plugins.BeautifyIcon(
        icon_shape='marker',
        icon_size=[22, 22],  # 여기서 마커의 전체 크기를 조절합니다 (기본값은 보통 22, 22 내외)
        #border_color=border_c,
        #background_color=bg,
        inner_icon_style=f'font-size:15px; border:1px solid {border_c};'
        )

        if '제조' in str(row['특화분야']):
            # 일반 제조: 물방울 형태, 보라색 테두리
            shape, border_c = 'marker', 'purple'
            bg = 'grey' # 기본값
            if '자동차' in industry: bg = 'red'
            elif '화학' in industry: bg = 'blue'
            elif '섬유' in industry: bg = 'green'
            elif '기계' in industry: bg = 'black'
        else:
            # 일반 기타: 원형 깃발, 파란색 테두리
            shape, border_c = 'marker', 'blue'
            bg = 'grey' # 기본값
            if '서비스' in industry: bg = 'black'
            elif '판매' in industry: bg = 'green'
            elif '창고' in industry: bg = 'red'

        icon = plugins.BeautifyIcon(
            icon='', # 내부 아이콘 없음
            icon_shape=shape,
            border_color=border_c,
            background_color=bg,
            # border_width를 추가하여 두께를 명시적으로 제어합니다.
            inner_icon_style=f'font-size:15px; margin-top:2px; border:1px solid {border_c};' 
        )
    else:
        
        # [방문 완료 사업장] - 기존 사고 강조 로직 유지

        bg = visit_colors.get(v_cnt, 'gray')
        if not is_disaster:
            # 무사고: 하얀 원 바탕 + 배경색 숫자
            inner_style = 'background-color:white; border-radius:50%; width:16px; height:16px; line-height:16px;'
            txt_c, border_c = bg, bg
        else:
            # 사고발생: 검정 원 바탕 + 흰색 숫자
            inner_style = 'background-color:black; border-radius:50%; width:16px; height:16px; line-height:16px;'
            txt_c, border_c = 'white', bg

            # 마커 전체 크기를 [40, 40]으로 확대
        icon = plugins.BeautifyIcon(
            icon_shape='marker',
            icon_size=[40, 40],   # <--- 방문한 곳은 더 크게 표시
            number=v_cnt,
            background_color=bg,
            border_color=border_c,
            text_color=txt_c,
            inner_icon_style=inner_style  # 내부 원 크기도 함께 조정됨
        )


    # 마커 배치
    folium.Marker(
        location=[row['위도'], row['경도']],
        popup=f"<b>{row['사업장명_공사장명']}</b><br>업종: {industry}",
        icon=icon
    ).add_to(agent_groups[row['담당자']])

# 6. 제어 도구 추가 및 파일 저장
folium.LayerControl(collapsed=True).add_to(m)
m.save('사업장_현황지도_최종.html')
print("지도가 성공적으로 생성되었습니다.")