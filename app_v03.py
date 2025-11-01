# -*- coding: utf-8 -*-
"""
颐居慧视 – 精简三栏版（接入 ModelScope 多模态大模型）
图床已迁移至 playground.z.wiki
"""
import os, io, hashlib, random, requests, gradio as gr
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# ----------- 配置 -----------
Z_TOKEN     = os.getenv('Z_TOKEN') or 'hellocgc@qq.com'   # 缺省方便调试
Z_API       = "https://playground.z.wiki/img/api/upload"
MS_TOKEN    = os.getenv('MS_TOKEN')
MS_API_URL  = "https://api-inference.modelscope.cn/v1"
PROMPT      = (
    "你需要从适老化改造的角度出发，提出1-3个最重要的合理建议，\n"
    "要求：\n1. 仅限定你看到的画面；\n"
    "2. 使用相对位置描述，勿给出绝对尺寸；\n"
    "3. 格式为“序号.改造建议”。\n"
)

# ----------- 工具 -----------
def upload_image2z(pil_img: Image.Image) -> str:
    """PIL → playground.z.wiki → URL"""
    buf = io.BytesIO()
    pil_img.convert('RGB').save(buf, format='JPEG', quality=90)
    buf.seek(0)
    files = {'file': ('upload.jpg', buf, 'image/jpeg')}
    data  = {'uid': Z_TOKEN, 'fileName': 'upload.jpg'}
    rsp = requests.post(Z_API, files=files, data=data, timeout=30)
    rsp.raise_for_status()
    return rsp.json()['url']

def fake_annotated(pil_img: Image.Image) -> Image.Image:
    """随手画红框示意"""
    W, H = pil_img.size
    img = pil_img.copy()
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    for _ in range(random.randint(1, 3)):
        x1 = random.randint(0, W//2)
        y1 = random.randint(0, H//2)
        x2 = x1 + random.randint(80, 200)
        y2 = y1 + random.randint(80, 200)
        draw.rectangle([x1, y1, x2, y2], outline='red', width=6)
    draw.rectangle([0, H-80, W, H], fill='black')
    draw.text((20, H-60), 'AI 改造示意：已标注风险点', fill='white', font=font)
    return img

# ----------- 流式调用 -----------
def stream_advise(image_url: str):
    client = OpenAI(base_url=MS_API_URL, api_key=MS_TOKEN)
    response = client.chat.completions.create(
        model='Qwen/Qwen3-VL-235B-A22B-Instruct',
        messages=[{
            'role': 'user',
            'content': [{'type': 'text', 'text': PROMPT},
                        {'type': 'image_url', 'image_url': {'url': image_url}}]
        }],
        stream=True)
    for chk in response:
        if chk.choices[0].delta.content:
            yield chk.choices[0].delta.content

# ----------- 缓存 -----------
_cache = {}   # md5 → url

def ai_advise(image):
    if image is None:
        yield '请先上传一张照片', None
        return
    after = fake_annotated(image)
    yield '', after

    key = hashlib.md5(image.tobytes()).hexdigest()
    url = _cache.get(key)
    if not url:
        try:
            url = upload_image2z(image)
            _cache[key] = url
        except Exception as e:
            yield f'（图片上传失败：{e}）', after
            return

    buffer = ''
    for piece in stream_advise(url):
        buffer += piece
        yield buffer, after

# ----------- Chatbot -----------
def fake_chat(history, msg):
    history = history or []
    ans = random.choice([
        '您可以考虑安装感应夜灯，减少起夜跌倒风险。',
        '家具圆角处理或加装防撞条，也是低成本的好方法。',
        '如需进一步帮助，可咨询本地社区养老服务中心。'])
    history.append([msg, ans])
    return history

# ----------- Gradio UI -----------
css = """
body{background:#fafafa;}
.gr-button-primary{font-size:20px!important;padding:12px 24px!important;background:#d60000!important;color:white!important;}
.gr-text-output,.gr-chatbot{font-size:22px!important;line-height:1.8!important;color:#222!important;}
.gr-markdown{font-size:26px!important;font-weight:bold!important;text-align:center!important;margin-bottom:10px!important;}
"""

with gr.Blocks(css=css, title='颐居慧视') as demo:
    gr.Markdown('🏠 颐居慧视 · 让 AI 帮爸妈把家变得更安全')

    with gr.Tab('📸 环境评估'):
        with gr.Row():
            with gr.Column():
                img_in  = gr.Image(label='1. 拍摄或上传照片', type='pil')
                btn     = gr.Button('一键评估', elem_classes='gr-button-primary')
            with gr.Column():
                adv_out = gr.Textbox(label='2. AI 评估建议', lines=4, elem_classes='gr-text-output', interactive=False)
                img_out = gr.Image(label='3. AI 改造后示意图', type='pil')
        btn.click(ai_advise, inputs=img_in, outputs=[adv_out, img_out])

    with gr.Tab('💬 进一步咨询'):
        chat = gr.Chatbot(label='适老改造小助手', elem_classes='gr-chatbot', height=400)
        msg  = gr.Textbox(label='输入您的问题', placeholder='例如：浴室防滑还有哪些便宜方案？')
        send = gr.Button('发送', elem_classes='gr-button-primary')
        send.click(fake_chat, inputs=[chat, msg], outputs=chat)
        msg.submit(fake_chat, inputs=[chat, msg], outputs=chat)

    with gr.Tab('📖 参考书籍'):
        gallery = gr.Gallery(label='PDF 预览', columns=2, height=700)

demo.queue().launch(server_name='0.0.0.0', debug=True, show_api=False)
