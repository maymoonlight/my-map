import win32com.client as win32
import pandas as pd
import os
import re

# 1. 제공받은 데이터 로드
csv_file = "배정명단.xlsx - 명단1차.csv"
df = pd.read_csv(csv_file)

# 2. 한글 프로그램 실행 및 보안 모듈 등록
hwp = win32.gencache.EnsureDispatch("HWPFrame.HwpObject")
# 보안 승인 팝업 방지 (FilePathCheckerModule.dll 설치 필요)
hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
hwp.XHwpWindows.Item(0).Visible = True

# 3. 문서 생성 프로세스
for index, row in df.iterrows():
    # 양식 파일 열기 (template.hwp 파일이 같은 폴더에 있어야 합니다)
    template_path = os.path.join(os.getcwd(), "template.hwp")
    hwp.Open(template_path)
    
    # 엑셀의 모든 컬럼을 순회하며 누름틀에 값 입력
    for column in df.columns:
        # 데이터가 비어있는 경우를 대비해 문자열로 변환 후 입력
        field_content = str(row[column]) if pd.notnull(row[column]) else ""
        hwp.PutFieldText(column, field_content)
    
    # 4. 파일명 생성: '사업장명_공사장명' 헤더 활용
    raw_name = str(row['사업장명_공사장명']).strip()
    # 파일명으로 사용할 수 없는 특수문자 제거 (예방 대책)
    clean_name = re.sub(r'[\\/:*?"<>|]', '_', raw_name)
    
    # 5. HWPX 확장자로 저장
    output_filename = f"{clean_name}.hwpx"
    save_path = os.path.join(os.getcwd(), output_filename)
    
    hwp.SaveAs(save_path)
    
# 작업 완료 후 종료
hwp.Quit()
print(f"대표님, {len(df)}개의 현장에 대한 HWPX 문서 생성이 완료되었습니다.")