# 普通函数：一次性返回整个列表
def get_numbers():
    return [1, 2, 3, 4, 5]

# 生成器函数：按需产生值（惰性计算）
def counter():
    for i in range(5):
        yield i  # 每次只产生一个值

# 使用
for num in counter():
    print(num)
