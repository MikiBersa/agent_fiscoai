sum_val = 0
for i in range(1, 1000001):
    if (i % 3 == 0) ^ (i % 5 == 0):
        sum_val += i

print(sum_val)