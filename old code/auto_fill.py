import pandas as pd
from pyhwpx import Hwp
import os

# 1. 이제 'xlsx' 확장자를 가진 진짜 엑셀 파일을 불러옵니다.
excel_file = '배정명단.xlsx'
template_file = '사업장개요.hwpx'

# 엑셀을 읽기 위해 engine='openpyxl'을 명시하면 더 정확합니다.
# (터미널에서 pip install openpyxl 이 되어 있어야 합니다)
df = pd.read_excel(excel_file, engine='openpyxl')

# 열 이름의 줄바꿈 제거
df.columns = [col.replace('\n', '').strip() for col in df.columns]

hwp = Hwp()

for i, row in df.iterrows():
    hwp.open(os.path.join(os.getcwd(), template_file))
    
    # 누름틀 이름 매칭
    fields = ['주사업장명', '사업장명_공사장명', '사업장관리번호', '개시번호', '현장주소', '중업종']
    for f in fields:
        if f in df.columns:
            hwp.put_field_text(f, str(row[f]))
    
    # 저장 파일명 (사업장명으로 저장)
    save_name = f"{str(row['사업장명_공사장명']).strip()}.hwpx"
    hwp.save_as(os.path.join(os.getcwd(), save_name))
    print(f"[{i+1}/{len(df)}] {save_name} 생성 완료")

hwp.quit()
print("대표님, 모든 작업이 성공적으로 끝났습니다!")