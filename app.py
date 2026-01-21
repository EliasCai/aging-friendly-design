# -*- coding: utf-8 -*-
"""
适老化设计师 – 精简三栏版（ModelScope + DashScope 图像编辑）
"""
import os, io, hashlib, requests, gradio as gr
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI
import fitz  # PyMuPDF
import random
from typing import Iterator
from gradio import ChatMessage
from io import BytesIO



# ------------------ 配置 ------------------
Z_TOKEN    = os.getenv('Z_TOKEN') or 'hellocgc@qq.com'
Z_API      = "https://playground.z.wiki/img/api/upload"
MS_TOKEN   = os.getenv('MS_TOKEN') or "ms-1934ce73-e690-4a6a-b31c-2d0cb71cc6a9"
MS_API_URL = "https://api-inference.modelscope.cn/v1"
DS_KEY     = os.getenv('DASHSCOPE_API_KEY') or "sk-55180135971c4d909f780892f2c8f8e1"
PDF_PATH = r"./P020240613034653.pdf"  # 请换成真实路径

PROMPT = """
你是一位专业的适老化改造与居家安全顾问，专注于通过视觉分析识别居住环境中的潜在风险与适老改造机会。你的任务是通过分析用户上传的家庭环境照片，结合老年人居家安全与生活便利性需求，提供清晰、具体、可操作的改造建议。

---

**身份与任务说明**
1. 你是一名居家适老化改造专家，具备老年人安全防护、无障碍设计、居家风险预防的专业知识。
2. 请分析用户上传的图片，从以下角度评估：
   - **跌倒预防**：地面高低差、地面材质、杂物堆积、通道宽度、扶手缺失、照明不足、地毯/地垫固定情况等；
   - **火灾与用电安全**：电线裸露、插座过载、易燃物靠近热源、烟雾报警器缺失、厨房用火隐患等；
   - **便利性提升**：常用物品取放高度、家具边角防护、开关位置、门把手形式、座椅高度等；
   - **卫生间与浴室安全**：防滑措施、淋浴坐浴设施、扶手安装位置、紧急呼叫设备等。
3. 所有建议必须基于图片中可见的内容，不得虚构图中不存在的物品或结构。

**输出格式与要求**
1. 输出建议数量为1–5条，按优先级排序（最危险或最易改进的排前面）。
2. 每条建议格式为：“序号. 一句话的改造建议（改进措施+问题定位，50个字左右）”，建议内容需包含：
   - **改进措施**：提供低成本、易实施的解决方法（可包含物品推荐，如防滑垫、感应灯）；
   - **问题定位**：使用相对位置描述（如“床左侧的过道”“厨房灶台旁边的插线板”）；
"""

PROMPT_ASK = \
"""
# 适老宜居设计指南

随着年龄增长，老年人居家生活中面临诸多安全隐患，如地面湿滑、光线不足、操作复杂等。本指南基于《家居产品适老化设计指南》核心内容，提炼出适用于普通家庭的适老化改造原则与低成本、可动手的实施建议，帮助提升居家安全性与便利性。

## 一、安全优先：预防跌倒与误操作
- **防滑防绊**：在地面铺设防滑垫，尤其浴室、厨房等湿滑区域；固定地毯边缘，避免卷边绊倒；整理电线，防止缠绕或绊脚。
- **避免尖锐设计**：家具边角做倒圆处理，或使用防撞角保护；移除或遮盖尖锐突出物。
- **稳定支撑**：为家具添加防滑脚垫，确保站立时稳定；常用物品放置于易取位置，减少登高或弯腰。

## 二、感官友好：强化视觉、听觉与触觉提示
- **视觉增强**：采用大号无衬线字体标注开关、标签；提高照明亮度，避免眩光；关键信息（如应急电话）置于醒目位置。
- **听觉辅助**：降低家电噪音，设置清晰操作提示音；必要时以振动或灯光补充提醒。
- **触觉优化**：选择表面温暖、材质柔软的家居用品；控制按键间距适中，避免误触。

## 三、体能支持：减少身体负担
- **简化操作**：选择单手可操作的物品，避免复杂流程；常用工具（如遥控器、水龙头）应轻便省力。
- **空间适配**：确保通道宽敞，便于轮椅或助行器通过；减少转身、弯腰动作，如使用可调节高度的家具。

## 四、认知简化：提升易用性与理解度
- **流程直观化**：家电操作步骤控制在三步以内；使用图示代替文字说明。
- **反馈明确**：操作成功后提供声音或灯光反馈，帮助确认；设置异常警报（如燃气泄漏监测）。

## 五、低成本改造建议
- **DIY调整**：用防滑贴改造地板；安装感应小夜灯；用标签机标注药品和开关。
- **优先改造区**：聚焦浴室、厨房、卧室等高频区域，通过小投入实现大改善。

适老宜居改造的核心是“以人为中心”，通过细微调整显著提升生活品质。定期检查家居环境，结合老年人实际需求灵活优化，让家成为安全、舒适、温暖的港湾。

---
*本指南基于《家居产品适老化设计指南》提炼，重点聚焦低成本、可动手的解决方案，助力实现居家适老化。*

# 任务要求

你需要根据"家居产品适老化设计指南"回答用户的问题，
如果用户的问题与指南不相关，则拒绝回答并提醒用户，
用户的问题是：
"""

markdown_text = \
"""
# 🏠 适老宜居设计师

欢迎使用！本工具帮助您（或您的父母）主动发现家中潜在的安全隐患（如地毯卷边、浴室湿滑、电线杂乱），并提供**低成本、可动手**的适老化改造建议。
"""

markdown_about = \
"""
### ✨ 功能特色
* **智能排查隐患：** AI 自动识别照片中的跌倒、火灾等风险。
* **专业改造建议：** 提供 1-3 条最关键、最实用的文字建议。
* **直观效果预览：** 生成一张“改造后”的示意图，让您一看就懂。

### 📝 如何使用
1.  **拍摄照片：** 点击下方的“拍摄或上传照片”框，拍一张您家中的（如 **浴室、厨房、卧室**）的照片。
2.  **一键评估：** 点击 **“一键评估”** 按钮。
3.  **获取报告：** AI 将首先生成“评估建议”（文字），稍等片刻后，将生成“改造后示意图”（图片）。
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

def create_report_image(text: str, image: Image.Image) -> Image.Image:
    """将文本和图片合并成一张报告图片"""
    if image is None:
        return None
    
    img_width, img_height = image.size
    
    header_height = 80
    text_height = 200
    total_height = header_height + text_height + img_height + 40
    
    report = Image.new('RGB', (img_width, total_height), color='white')
    draw = ImageDraw.Draw(report)
    
    try:
        title_font = ImageFont.truetype("fonts/msyh.ttf", 36)
        text_font = ImageFont.truetype("fonts/msyh.ttf", 20)
    except:
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    draw.rectangle([(0, 0), (img_width, header_height)], fill='#A855F7')
    draw.text((20, 25), '适老化改造评估报告', fill='white', font=title_font)
    
    y_offset = header_height + 20
    draw.text((20, y_offset), '评估建议：', fill='#333333', font=text_font)
    y_offset += 35
    
    lines = text.split('\n')
    for line in lines:
        if line.strip():
            draw.text((20, y_offset), line, fill='#555555', font=text_font)
            y_offset += 25
    
    report.paste(image, (0, header_height + text_height + 20))
    
    return report

# ------------------ 流式建议 ------------------
def stream_advise(image_url: str):
    client = OpenAI(base_url=MS_API_URL, api_key=MS_TOKEN)
    for chk in client.chat.completions.create(
            model='Qwen/Qwen3-VL-30B-A3B-Instruct', # Qwen3-VL-235B-A22B-Instruct',
            messages=[{"role": "user",
                       "content": [{"type": "text", "text": PROMPT},
                                   {"type": "image_url", "image_url": {"url": image_url}}]}],
            stream=True):
        if chk.choices[0].delta.content:
            yield chk.choices[0].delta.content

# ----------- Tab2 逻辑 -----------
client = OpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    api_key = MS_TOKEN,
)

def stream_qwen_response(user_message: str, messages: list) -> Iterator[list]:
    extra_body = {"enable_thinking": True}
    resp = client.chat.completions.create(
        model='Qwen/Qwen3-32B',
        messages=[{"role": "user", "content": PROMPT_ASK + user_message}],
        stream=True,
        extra_body=extra_body
    )

    thought_buffer = ""
    response_buffer = ""
    thinking_complete = False

    # 初始“思考中”占位
    messages.append(
        ChatMessage(
            role="assistant",
            content="",
            metadata={"title": "⏳Thinking: *The thoughts produced by the Qwen3 model are experimental"}
        )
    )
    yield messages

    for chunk in resp:
        delta = chunk.choices[0].delta
        thinking_chunk = delta.reasoning_content
        answer_chunk = delta.content

        # 1. 还在思考
        if thinking_chunk is not None and thinking_chunk != "":
            thought_buffer += thinking_chunk
            messages[-1] = ChatMessage(
                role="assistant",
                content=thought_buffer,
                metadata={"title": "⏳Thinking: *The thoughts produced by the Qwen3 model are experimental"}
            )
            yield messages
            continue

        # 2. 开始/继续回答
        if answer_chunk is not None and answer_chunk != "":
            if not thinking_complete:
                # 标记思考结束，同时把第一个 answer_chunk 也收进 buffer
                thinking_complete = True
                response_buffer += answer_chunk
                messages[-1] = ChatMessage(
                    role="assistant",
                    content=thought_buffer,
                    metadata={"title": "✅ Thinking Complete"}
                )
                # 新建一条消息专门展示回答
                messages.append(
                    ChatMessage(role="assistant", content=response_buffer)
                )
            else:
                # 继续累加回答
                response_buffer += answer_chunk
                messages[-1] = ChatMessage(role="assistant", content=response_buffer)
            yield messages


def user_message(user_msg: str, messages: list):
    messages.append(ChatMessage(role="user", content=user_msg))
    return "", messages


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
examples = [
    "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/DnUK/1000X750/03.jpg",
    "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/5Aiu/780X438/01.jpg",
    "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/9UDn/710X400/08.jpg",
    "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/Vhu7/1000X750/02.jpg",
    "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/7CEm/780X438/04.jpg",
    "https://pic7.fukit.cn/autoupload/Rw6YVAKeYl4ryDjv52L9NA/20251103/YXz8/780X438/05.jpg"
]

_cache = {}

for url in examples:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        image = Image.open(BytesIO(resp.content))
        key = hashlib.md5(image.tobytes()).hexdigest()
        _cache[key] = url
    except Exception as e:
        print(f"skip {url}  -> {e}")

print("_cache 初始化完成，共缓存 {} 张图".format(len(_cache)))

def ai_advise(image):
    if image is None:
        yield '请先上传一张照片', None, gr.update(interactive=False)
        return

    # 1. 先上传原图，拿到 url 备用
    key = hashlib.md5(image.tobytes()).hexdigest()
    url = _cache.get(key)
    if not url:
        try:
            url = upload_image2z(image)
            print(url)
            _cache[key] = url
        except Exception as e:
            yield f'（图片上传失败：{e}）', None, gr.update(interactive=False)
            return

    # 2. 流式输出文字建议
    buffer = ''
    for piece in stream_advise(url):
        buffer += piece
        yield buffer, None, gr.update(interactive=False)

    # 3. 流结束，用最终文字生成改造图
    try:
        after = edit_image(url, edit_prompt=buffer)
    except Exception as e:
        yield f'{buffer}\n\n（改造图生成失败：{e}）', None, gr.update(interactive=False)
        return

    # 4. 一次性把最终文字+改造图推出去，启用下载按钮
    yield buffer, after, gr.update(interactive=True)

def download_report(text, image):
    print(f"download_report 被调用，text={text is not None}, image={image is not None}")
    
    if text is None or image is None:
        print("下载报告失败：text 或 image 为 None")
        return None
    
    try:
        print("开始生成报告图片...")
        report_img = create_report_image(text, image)
        if report_img is None:
            print("报告图片生成失败：返回 None")
            return None
        
        print("报告图片生成成功，开始保存到本地...")
        local_path = "./report_output.jpg"
        report_img.save(local_path, format='JPEG', quality=90)
        print(f"报告图片已保存到本地: {local_path}")
        
        print("开始上传到图床...")
        url = upload_image2z(report_img)
        print(f"图床上传成功，URL: {url}")
        return url
    except Exception as e:
        print(f"下载报告失败: {e}")
        import traceback
        traceback.print_exc()
        return None

# ------------------ Gradio UI ------------------
# 定义产品卡片边框样式
product_card_css = """
.product-card {
    border: 2px solid #e0e0e0 !important;
    border-radius: 12px !important;
    padding: 12px !important;
    background-color: #ffffff !important;
    margin: 8px !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
    transition: all 0.3s ease !important;
}
.product-card:hover {
    border-color: #4CAF50 !important;
    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.15) !important;
    transform: translateY(-2px) !important;
}
.gr-button-primary {
    background-color: #A855F7 !important;
    color: #FFFFFF !important;
}
.download-btn {
    background-color: #A855F7 !important;
    color: #FFFFFF !important;
}
.download-btn:disabled {
    background-color: #cccccc !important;
    color: #666666 !important;
    cursor: not-allowed !important;
}
"""

with gr.Blocks(title='颐居慧视', css=product_card_css) as demo:
    gr.Markdown(markdown_text) # '🏠 适老宜居设计师 · 让 AI 帮爸妈把家变得更安全')
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
                btn_download = gr.Button('下载报告', elem_classes='download-btn', interactive=False)
                report_url = gr.Textbox(label='报告链接', visible=False, interactive=False)
                download_link = gr.HTML(visible=False)
        btn.click(ai_advise, inputs=img_in, outputs=[adv_out, img_out, btn_download])
        btn_download.click(download_report, inputs=[adv_out, img_out], outputs=report_url).then(
            lambda url: (gr.update(visible=True, value=url), gr.update(visible=True, value=f'<a href="{url}" target="_blank" style="color:#A855F7;font-size:16px;font-weight:bold;">点击此处打开报告图片</a>')) if url else (gr.update(visible=False), gr.update(visible=False)),
            inputs=report_url,
            outputs=[report_url, download_link]
        )

    with gr.Tab("💬 进一步咨询"):

        chatbot = gr.Chatbot(type="messages", label="适老设计问答助手", render_markdown=True)
        input_box = gr.Textbox(lines=1, label="请输入问题并按回车键", placeholder="例如：厕所的装修需要注意什么")
        msg_store = gr.State("")

        input_box.submit(
            lambda msg: (msg, msg, ""),
            inputs=[input_box],
            outputs=[msg_store, input_box, input_box],
            queue=False
        ).then(
            user_message,
            inputs=[msg_store, chatbot],
            outputs=[input_box, chatbot],
            queue=False
        ).then(
            stream_qwen_response,
            inputs=[msg_store, chatbot],
            outputs=chatbot
        )

        examples = gr.Examples(
        examples=[
            "厕所的装修需要注意什么",
            "厨房有哪些危险需要注意",
            "如何增加家具稳定性"
        ],
        inputs=input_box,
        label="快速提问"
        )
    
    


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

demo.queue().launch(server_name='0.0.0.0', debug=True, show_api=False, share=False)