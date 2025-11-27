import os
import shutil
import hashlib
import qrcode

start_id = 136991
count = 5  # 生成多少个

pic_dir = "pic"

# 准备目录：若存在则删除再创建，保证为空
if os.path.exists(pic_dir):
    print(f"清除目录：{pic_dir}")
    shutil.rmtree(pic_dir)
os.makedirs(pic_dir, exist_ok=True)
print(f"已创建空目录：{pic_dir}")

urls = []
for i in range(start_id, start_id + count):
    id_code = hashlib.md5(str(i).encode()).hexdigest()
    url = f"http://job.hdu.edu.cn/teachin/qrcode?id={i}&id_code={id_code}&signin=1"
    print(f"[DEBUG] id={i} md5={id_code} url={url}")
    urls.append((i, url))

# 生成并保存二维码
for i, url in urls:
    try:
        img = qrcode.make(url)
        path = os.path.join(pic_dir, f"{i}.png")
        img.save(path)
        print(f"[OK] 保存 {path}")
    except Exception as e:
        print(f"[ERR] id={i} 保存失败：{e}")

print("全部完成。")
