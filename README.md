<div align="center">

# xuanjqd · 宣讲会签到码

**知道编号，就能把整周的签到码一次性生成出来。**

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)
[![Stars](https://img.shields.io/github/stars/xkzm123/xuanjqd?style=social)](https://github.com/xkzm123/xuanjqd/stargazers)

<img src="xuanjqd-studio/docs/images/before-after.png" width="100%" alt="v1 与 v2 对比">

</div>

## 两个版本

| | 位置 | 说明 |
|---|---|---|
| **v1** | [`main.py`](main.py) | 最初的脚本：改两个变量，跑一下，`pic/` 里出现一堆裸二维码。 |
| **v2** | [`xuanjqd-studio/`](xuanjqd-studio/) | 重写版：卡片式渲染、6 套配色、A4 拼版、网页画廊、可视化设计器、扫码自检、日历导出。 |

**推荐直接用 v2。**

## 快速开始

```bash
git clone https://github.com/xkzm123/xuanjqd.git
cd xuanjqd/xuanjqd-studio
pip install -r requirements.txt

python -m xuanjqd demo                    # 先看效果（演示数据）
python -m xuanjqd gen --start 136991 -n 8 # 生成真实的 8 场
python -m xuanjqd preview                 # 打开可视化设计器
```

详细文档、效果图和全部参数见 👉 **[xuanjqd-studio/README.md](xuanjqd-studio/README.md)**

## 原理

签到二维码里的链接是：

```
http://job.hdu.edu.cn/teachin/qrcode?id={宣讲会编号}&id_code={md5(编号)}&signin=1
```

所以只要知道编号，就能离线把二维码画出来。本项目只做**本地图片生成**，不登录、不提交、不伪造任何签到记录。

## 说明

- 编号从哪里来：在[杭电 24365 就业数智平台](https://job.hdu.edu.cn/)的「校园宣讲会」里点开任意一场，地址栏的 `id=` 就是。
- 编号有空档是正常的，多生成几个，用不上的删掉即可。
- 请把它当**日程整理工具**用，是否参加、是否签到仍然是你自己的选择，也请遵守学校相关规定。

<div align="center">

如果这个项目帮你少跑了几趟教学楼，点个 ⭐ 就是最好的支持。

</div>
