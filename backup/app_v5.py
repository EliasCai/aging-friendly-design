# -*- coding: utf-8 -*-
"""
颐居慧视 – 精简三栏版（ModelScope + DashScope 图像编辑）
"""
import os, io, hashlib, requests, gradio as gr
from PIL import Image
from openai import OpenAI
import fitz  # PyMuPDF
import random



# ------------------ 配置 ------------------
Z_TOKEN    = os.getenv('Z_TOKEN') or 'hellocgc@qq.com'
Z_API      = "https://playground.z.wiki/img/api/upload"
MS_TOKEN   = os.getenv('MS_TOKEN') or "ms-da2c260d-9d0a-48c7-9624-53cd424d8108"
MS_API_URL = "https://api-inference.modelscope.cn/v1"
DS_KEY     = os.getenv('DASHSCOPE_API_KEY') or "sk-55180135971c4d909f780892f2c8f8e1"
PDF_PATH = r"./P020240613034653.pdf"  # 请换成真实路径

PROMPT = (
    "你需要从适老化改造的角度出发，提出1-5个最重要的合理建议，\n"
    "要求：\n1. 仅限定你看到的画面；\n"
    "2. 使用相对位置描述，勿给出绝对尺寸；\n"
    "3. 格式为“序号.改造建议”。"
    "参考输出："
    "1. 在马桶左侧墙面加装L型扶手"
    "2. 在淋浴喷头下方的墙面加装垂直扶手，提供淋浴时的支撑点"
    "3. 在地面可见区域铺设防滑贴，防止滑倒"
    "4. 在马桶后方墙面安装紧急呼救拉绳装置，便于突发情况求助"
    "5. 更换淋浴的杆件为可上下滑动的经济型杆件，位置在淋浴喷头的杆件处。"
)

markdown_text = \
"""
# 🏠 适老宜居设计师

欢迎使用！本工具旨在帮助您（或您的父母）主动发现家中潜在的安全隐患（如地毯卷边、浴室湿滑、电线杂乱），并提供**低成本、可动手**的适老化改造建议。
"""

markdown_about = \
"""
### ✨ 功能特色
* **智能排查隐患：** AI 自动识别照片中的跌倒、火灾等风险。
* **专业改造建议：** 提供 1-3 条最关键、最实用的文字建议。
* **直观效果预览：** 生成一张“改造后”的示意图，让您一看就懂。

### 📝 如何使用
1.  **拍摄照片：** 点击下方的“拍摄或上传照片”框，拍一张您家中的（如 **浴室、厨房、卧室、走廊**）的照片。
2.  **一键评估：** 点击 **“一键评估”** 按钮。
3.  **获取报告：** AI 将在右侧首先生成“评估建议”（文字），稍等片刻后，将生成“改造后示意图”（图片）。
"""

# ------------------ 工具 ------------------
def upload_image2z(pil_img: Image.Image) -> str:
    buf = io.BytesIO()
    pil_img.convert('RGB').save(buf, format='JPEG', quality=90)
    buf.seek(0)
    rsp = requests.post(Z_API, files={'file': ('u.jpg', buf, 'image/jpeg')},
                        data={'uid': Z_TOKEN, 'fileName': 'u.jpg'}, timeout=30)
    rsp.raise_for_status()
    return rsp.json()['url']

def edit_image(url: str, *, edit_prompt: str) -> Image.Image:
    """PIL + 编辑提示词 → DashScope qwen-image-edit-plus → PIL"""
    # url = upload_image2z(pil_img)   # 原图公网 url
    rsp = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
        headers={"Authorization": f"Bearer {DS_KEY}", "Content-Type": "application/json"},
        json={
            "model": "qwen-image-edit-plus",
            "input": {
                "messages": [{
                    "role": "user",
                    "content": [{"image": url},
                                {"text": edit_prompt}]
                }]
            },
            "parameters": {"n": 1, "watermark": False}
        },
        timeout=60)
    rsp.raise_for_status()
    new_url = rsp.json()['output']['choices'][0]['message']['content'][0]['image']
    return Image.open(io.BytesIO(requests.get(new_url, timeout=30).content))

# ------------------ 流式建议 ------------------
def stream_advise(image_url: str):
    client = OpenAI(base_url=MS_API_URL, api_key=MS_TOKEN)
    for chk in client.chat.completions.create(
            model='Qwen/Qwen3-VL-235B-A22B-Instruct',
            messages=[{"role": "user",
                       "content": [{"type": "text", "text": PROMPT},
                                   {"type": "image_url", "image_url": {"url": image_url}}]}],
            stream=True):
        if chk.choices[0].delta.content:
            yield chk.choices[0].delta.content

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

# ------------------------------------------------------------------
# Tab3 逻辑：PDF 展示
# ------------------------------------------------------------------

def pdf_to_images(pdf_path=PDF_PATH, dpi=120):
    """将 PDF 逐页转 PIL 图片，供 Gradio Gallery 展示"""
    if not os.path.isfile(pdf_path):
        return [Image.new("RGB", (400, 600), color="gray")]
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images if images else [Image.new("RGB", (400, 600), color="gray")]

# ------------------ 主逻辑 ------------------
_cache = {}

def ai_advise(image):
    if image is None:
        yield '请先上传一张照片', None
        return

    # 1. 先上传原图，拿到 url 备用
    key = hashlib.md5(image.tobytes()).hexdigest()
    url = _cache.get(key)
    if not url:
        try:
            url = upload_image2z(image)
            _cache[key] = url
        except Exception as e:
            yield f'（图片上传失败：{e}）', None
            return

    # 2. 流式输出文字建议
    buffer = ''
    for piece in stream_advise(url):
        buffer += piece
        yield buffer, None          # 图暂时给 None，前端只更新文字

    # 3. 流结束，用最终文字生成改造图
    try:
        after = edit_image(url, edit_prompt=buffer)
    except Exception as e:
        yield f'{buffer}\n\n（改造图生成失败：{e}）', None
        return

    # 4. 一次性把最终文字+改造图推出去
    yield buffer, after

# ------------------ Gradio UI ------------------
with gr.Blocks(title='颐居慧视') as demo:
    gr.Markdown(markdown_text) # '🏠 颐居慧视 · 让 AI 帮爸妈把家变得更安全')
    with gr.Tab('📸 环境评估'):
        with gr.Row():
            with gr.Column():
                img_in = gr.Image(label='1. 拍摄或上传照片', type='pil')
                btn    = gr.Button('一键评估', elem_classes='gr-button-primary')
                # ① 新增示例图，支持任意可公开访问的 URL
                gr.Examples(
                    examples=[
                        "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/DnUK/1000X750/03.jpg",
                        "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/5Aiu/780X438/01.jpg",
                        "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/9UDn/710X400/08.jpg",
                        "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/Vhu7/1000X750/02.jpg",
                        "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/7CEm/780X438/04.jpg",
                        "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/YXz8/780X438/05.jpg"
                        # 需要再加别的图，继续往列表里填 URL 即可
                    ],
                    inputs=img_in,
                    label="📷 快速体验（点击即可加载）"
                )
            with gr.Column():
                adv_out = gr.Textbox(label='2. AI 评估建议', lines=4, interactive=False)
                img_out = gr.Image(label='3. AI 改造后示意图', type='pil')
        btn.click(ai_advise, inputs=img_in, outputs=[adv_out, img_out])

    with gr.Tab("💬 进一步咨询"):
        chatbot = gr.Chatbot(label="适老改造小助手", elem_classes="gr-chatbot", height=400)
        msg = gr.Textbox(label="输入您的问题", placeholder="例如：浴室防滑还有哪些便宜方案？")
        send = gr.Button("发送", elem_classes="gr-button-primary")
        send.click(fake_chat, inputs=[chatbot, msg], outputs=chatbot)
        msg.submit(fake_chat, inputs=[chatbot, msg], outputs=chatbot)

    with gr.Tab("📖 参考书籍"):
        gallery = gr.Gallery(label="PDF 预览", columns=2, height=700)
        demo.load(fn=pdf_to_images, inputs=None, outputs=gallery)

    with gr.Tab("⚙️ 应用说明"):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Image("./show.png",label="技术实现流程")
            with gr.Column(scale=2):
                gr.Markdown(markdown_about)
                gr.Image("./compare.png",label="实现效果")

demo.queue().launch(server_name='0.0.0.0', debug=True, show_api=False)
