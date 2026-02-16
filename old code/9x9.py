while True:
    num_str = input(" ~~~ ? : ")
    num = int(num_str)

    if num == 0: 
        break

    for i in range (1, 10, 1):          
        print(f"{num} x {i} = {num * i}")
        
print("bye~")