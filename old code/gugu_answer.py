def gugu_answer(x):
    print(f"{x} 단의 답은....")
    for i in range(1, 10):
        print(f"{x} x {i} = {x * i}")
        
x_str = input("몇 단을 알려줄까? ")
x = int(x_str)

gugu_answer(x)