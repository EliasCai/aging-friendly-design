# -*- coding: utf-8 -*-
"""
颐居慧视 – 精简三栏版
Tab1: 上传照片 → 图床 → AI 评估 + 改造示意
Tab2: Chatbot
Tab3: PDF 预览（保留空壳，可自行补路径）
"""

import os
import random
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import gradio as gr

# ----------- 配置 -----------
PICGO_KEY = "chv_SvuPk_278ac4f8bd16991a45b2a0cb2b710f18f8f34c26e87f1354b40042178fb673f8a1a9074d5a93728b5fe50db32b8b4b0eaf6035c2df47f8797f70e4cd28faa413"
PICGO_API = "https://www.picgo.net/api/1/upload"

# ----------- 工具 -----------
def upload_to_picgo(pil_img: Image.Image) -> str:
    """PIL 图 → 上传 picgo → 返回 https 直链"""
    # 先转存为内存 jpeg
    from io import BytesIO
    buf = BytesIO()
    pil_img = pil_img.convert("RGB")
    pil_img.save(buf, format="JPEG", quality=90)
    buf.seek(0)

    files = {"source": ("upload.jpg", buf, "image/jpeg")}
    headers = {"X-API-Key": PICGO_KEY}
    resp = requests.post(PICGO_API, files=files, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status_code") != 200:
        raise RuntimeError(data.get("error", {}).get("message", "上传失败"))
    return data["image"]["url"]   # https 直链

# ----------- Tab1 逻辑 -----------
def fake_caption(_: Image.Image) -> str:
    return random.choice([
        "检测到浴室地垫无防滑底，建议更换为防滑垫或铺设防滑贴；同时加装一字型扶手。",
        "卧室过道宽度<900 mm，建议将储物箱移至床底，保持≥1 m 通道，方便轮椅通行。",
        "插线板超负荷使用，建议拔掉不常用电器，并更换为带独立开关的新国标插线板。",
        "客厅灯光照度不足，建议更换 6500 K 高显色 LED 灯泡，并在动线增加感应夜灯。",
        "厨房地面有油渍，建议铺设防油地贴，随手放置“防滑提醒”标识。",
    ])

def fake_annotated(pil_img: Image.Image) -> Image.Image:
    W, H = pil_img.size
    img = pil_img.copy()
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    for _ in range(random.randint(1, 3)):
        x1 = random.randint(0, W // 2)
        y1 = random.randint(0, H // 2)
        x2 = x1 + random.randint(80, 200)
        y2 = y1 + random.randint(80, 200)
        draw.rectangle([x1, y1, x2, y2], outline="red", width=6)
    draw.rectangle([0, H - 80, W, H], fill="black")
    draw.text((20, H - 60), "AI 改造示意：已标注风险点", fill="white", font=font)
    return img

def ai_advise(image):
    if image is None:
        return "请先上传一张照片", None
    # 1. 上图床
    url = upload_to_picgo(image)
    # 2. 生成建议 & 示意图
    advise = fake_caption(image)
    after = fake_annotated(image)
    return advise, after

# ----------- Tab2 逻辑 -----------
def fake_chat(history, user_msg):
    history = history or []
    replies = [
        "您可以考虑安装感应夜灯，减少起夜跌倒风险。",
        "家具圆角处理或加装防撞条，也是低成本的好方法。",
        "如需进一步帮助，可咨询本地社区养老服务中心。",
    ]
    history.append([user_msg, random.choice(replies)])
    return history

# ----------- Gradio 界面 -----------
css = """
body{background:#fafafa;}
.gr-button-primary{font-size:20px!important;padding:12px 24px!important;background:#d60000!important;color:white!important;}
.gr-text-output,.gr-chatbot{font-size:22px!important;line-height:1.8!important;color:#222!important;}
.gr-markdown{font-size:26px!important;font-weight:bold!important;text-align:center!important;margin-bottom:10px!important;}
"""

with gr.Blocks(css=css, title="颐居慧视") as demo:
    gr.Markdown("🏠 颐居慧视 · 让 AI 帮爸妈把家变得更安全")

    with gr.Tab("📸 环境评估"):
        with gr.Row():
            with gr.Column():
                img_in = gr.Image(label="1. 拍摄或上传照片", type="pil")
                btn = gr.Button("一键评估", elem_classes="gr-button-primary")
            with gr.Column():
                advise_out = gr.Textbox(label="2. AI 评估建议", lines=4, elem_classes="gr-text-output")
                img_out = gr.Image(label="3. AI 改造后示意图", type="pil")
        btn.click(ai_advise, inputs=img_in, outputs=[advise_out, img_out])

    with gr.Tab("💬 进一步咨询"):
        chatbot = gr.Chatbot(label="适老改造小助手", elem_classes="gr-chatbot", height=400)
        msg = gr.Textbox(label="输入您的问题", placeholder="例如：浴室防滑还有哪些便宜方案？")
        send = gr.Button("发送", elem_classes="gr-button-primary")
        send.click(fake_chat, inputs=[chatbot, msg], outputs=chatbot)
        msg.submit(fake_chat, inputs=[chatbot, msg], outputs=chatbot)

    with gr.Tab("📖 参考书籍"):
        gallery = gr.Gallery(label="PDF 预览", columns=2, height=700)
        # 如需展示 PDF，请把真实路径填进 pdf_to_images 再 bind 即可
        # demo.load(...)

demo.launch(server_name="0.0.0.0", debug=True, show_api=False)
