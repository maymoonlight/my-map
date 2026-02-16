num_str = input(" ~~~ ? : ")
num = int(num_str)
if num % 2 == 0:
    print(" 2's friend!")
else:
    print(f"num : {num} is 1's friends!")
    print("and " +  str(num) + " 3's friends, too")