import pandas as pd
import requests
import re
import time

# 1. 설정 (API 키와 파일명)
KAKAO_API_KEY = '642110cf68ce91c87607598112158673'
input_file = '배정명단.xlsx'
output_file = '배정명단_GPS.xlsx'

def get_coordinates(addr):
    """카카오 API를 사용하여 주소를 좌표(경도, 위도)로 변환"""
    if not addr or pd.isna(addr): return None, None
    
    # [전처리] 괄호 제거 및 상세주소(층, 호) 제거 로직
    clean_addr = addr.split('(')[0].strip()
    clean_addr = re.sub(r'\s\d+층.*$', '', clean_addr)
    clean_addr = re.sub(r'\s\d+호.*$', '', clean_addr)
    
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    url = 'https://dapi.kakao.com/v2/local/search/address.json'
    
    try:
        response = requests.get(url, headers=headers, params={'query': clean_addr})
        result = response.json()
        if result.get('documents'):
            # x는 경도(127.x), y는 위도(37.x)
            return float(result['documents'][0]['x']), float(result['documents'][0]['y'])
        else:
            # '번지' 글자 제거 후 2차 시도
            retry_addr = clean_addr.replace('번지', '').strip()
            response = requests.get(url, headers=headers, params={'query': retry_addr})
            result = response.json()
            if result.get('documents'):
                return float(result['documents'][0]['x']), float(result['documents'][0]['y'])
    except Exception as e:
        print(f"Error: {e}")
    
    return None, None

# 2. 데이터 불러오기
print(f"📂 '{input_file}' 파일을 읽어오는 중...")
df = pd.read_excel(input_file)

# 좌표를 담을 리스트
lons = [] # 경도 (15열용)
lats = [] # 위도 (16열용)

# 3. 반복문을 통한 좌표 추출
print(f"🚀 총 {len(df)}건의 주소 변환을 시작합니다.")
for i, row in df.iterrows():
    # '현장주소' 열 이름을 확인하세요. 엑셀 제목과 일치해야 합니다.
    lon, lat = get_coordinates(row['현장주소'])
    lons.append(lon)
    lats.append(lat)
    
    if (i + 1) % 10 == 0:
        print(f"━━━━━━━━━━ {i + 1}/{len(df)} 건 완료 ━━━━━━━━━━")
    
    # API 과부하 방지를 위한 아주 짧은 휴식 (선택사항)
    time.sleep(0.05)

# 4. 15열(O), 16열(P) 위치에 데이터 삽입
# 기존에 동일한 이름의 열이 있다면 제거 (중복 방지)
if '경도' in df.columns: df.drop('경도', axis=1, inplace=True)
if '위도' in df.columns: df.drop('위도', axis=1, inplace=True)

# Pandas insert는 0부터 시작하므로 14번 인덱스가 15열입니다.
df.insert(14, '경도', lons)
df.insert(15, '위도', lats)

# 5. 새로운 엑셀 파일로 저장
try:
    df.to_excel(output_file, index=False)
    print("\n" + "="*40)
    print(f"✅ 작업 완료! '{output_file}' 파일이 생성되었습니다.")
    print(f"📍 15열(경도)와 16열(위도)를 확인해 보세요.")
    print("="*40)
except Exception as e:
    print(f"❌ 파일 저장 중 오류 발생: {e}")
    print("팁: 엑셀 파일이 이미 열려있다면 닫고 다시 실행해 보세요.")