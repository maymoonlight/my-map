import time

print("3초 뒤에 카운트다운을 시작합니다...")
time.sleep(3)

for i in range(5, 0, -1):
    print(f"{i}...")
    time.sleep(1)

print("🚀 파이썬 고속도로 진입 성공!")