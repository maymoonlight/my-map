import pandas as pd
import requests
import folium
from folium import plugins
import re

# 1. 설정 및 API 키
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
excel_file = '현황.xlsx'

# 2. 데이터 로드
try:
    df = pd.read_excel(
        excel_file, 
        sheet_name='맵핑', 
        dtype={'사업장관리번호': str, '개시번호': str}
    )
except Exception as e:
    print(f"파일 로딩 실패: {e}")

# 3. 주소 분석 함수
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

# 4. 지도 생성 및 레이어 그룹화
valid_df = df.dropna(subset=['위도', '경도'])
m = folium.Map(location=[valid_df['위도'].mean(), valid_df['경도'].mean()], zoom_start=11)

# 방문 차수별 색상 매핑
visit_colors = {1: 'red', 2: 'orange', 3: 'yellow', 4: 'green', 5: 'blue'}

# 담당자별 토글 그룹
agent_groups = {}
for agent in valid_df['담당자'].unique():
    agent_groups[agent] = folium.FeatureGroup(name=f"담당자: {agent}").add_to(m)

# 5. 마커 생성 로직
for _, row in valid_df.iterrows():
    v_cnt = int(row['방문회차'])
    is_disaster = int(row['재해여부']) > 0
    industry = str(row['업종'])
      
    # [A] 미방문 사업장 (v_cnt == 0)
    
    if v_cnt == 0:
        special_field = str(row['특화분야'])
        
        # 1. 스타일 및 배경색 결정
        if '제조' in special_field:
            # 제조: 테두리 없이 배경색만 (보더 두께 0)
            bg = 'red' if '자동차' in industry else 'blue' if '화학' in industry else 'green' if '섬유' in industry else 'black' if '기계' in industry else 'grey'
            border_c = bg 
            border_w = '0px'
        else:
            # 일반 및 기타: 파란 테두리 + 업종별 배경색
            bg = 'black' if '서비스' in industry else 'green' if '판매' in industry else 'red' if '창고' in industry else 'grey'
            border_c = 'blue' 
            border_w = '2px'

        # 2. 아이콘 생성 (내부 점 제거 핵심 설정)
        icon = plugins.BeautifyIcon(
            icon=' ',                # 빈칸 한 개를 넣어 기본 점(dot) 생성을 방지합니다.
            icon_shape='marker',
            icon_size=[22, 22],
            border_color=border_c,
            background_color=bg,
            # display:none을 추가하여 내부의 모든 요소를 강제로 숨깁니다.
            inner_icon_style=f'border:{border_w} solid {border_c}; display:none;' 
        )
       

    # [B] 방문 완료 사업장 (v_cnt > 0)
    else:
        bg = visit_colors.get(v_cnt, 'gray')
        if not is_disaster:
            # 무사고: padding-left로 위치 미세 조정
            inner_style = f'background-color:white; border-radius:50%; width:16px; height:16px; line-height:16px; margin-top:2px; text-align:center; padding-left:1px;'
            txt_c, border_c = bg, bg
        else:
            # 사고발생: 검정 원 바탕
            inner_style = f'background-color:black; border-radius:50%; width:16px; height:16px; line-height:16px; margin-top:2px; text-align:center; padding-left:1px;'
            txt_c, border_c = 'white', bg

        icon = plugins.BeautifyIcon(
            icon_shape='marker',
            icon_size=[40, 40],
            number=v_cnt,
            background_color=bg,
            border_color=border_c,
            text_color=txt_c,
            inner_icon_style=inner_style
        )
    # 6. 마커 배치
    # 6. 마커 배치 (팝업 폭 확대 및 가독성 개선)
    popup_html = f"""
    <div style="width:250px;">
        <h4 style="margin-bottom:5px;"><b>{row['사업장명_공사장명']}</b></h4>
        <hr style="margin:5px 0;">
        <b>업종:</b> {industry}<br>
        <b>방문회차:</b> {v_cnt}회
    </div>
    """
    
    folium.Marker(
        location=[row['위도'], row['경도']],
        # max_width를 지정하여 팝업이 옆으로 넓게 펼쳐지게 합니다.
        popup=folium.Popup(popup_html, max_width=300),
        icon=icon
    ).add_to(agent_groups[row['담당자']])


# 7. 제어 도구 추가 및 파일 저장
folium.LayerControl(collapsed=True).add_to(m)
m.save('사업장_현황지도_최종.html')
print("지도가 성공적으로 생성되었습니다.")