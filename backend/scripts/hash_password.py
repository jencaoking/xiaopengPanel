import bcrypt

# 要哈希的密码
password = "admin123"

# 生成哈希密码
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# 打印哈希密码
print(f"原始密码: {password}")
print(f"哈希密码: {hashed_password.decode('utf-8')}")
