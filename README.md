# 颐居慧视 – AI 适老家评助手  

让爸妈住得更安全，一张照片就够了！

---

## 🏠 项目简介  
「颐居慧视」是一款基于 **Gradio** 的轻量级 Web 小工具。用户只需 **拍照上传**，即可：  
1. 自动上传到图床（picgo.net）生成 https 直链；  
2. 获得 AI 给出的**适老化 / 安全改造建议**；  
3. 实时查看**带风险标注的改造后示意图**；  
4. 继续与**内置小助手**对话，获取低成本改造灵感；  
5. 浏览本地 PDF 参考书籍（可扩展）。  

> 代码纯 Python，≈70 行核心，本地 / Colab / 服务器一键运行。

---

## 🚀 30 秒快速启动

### ① 安装依赖  
```bash
pip install gradio pillow requests
```

### ② 获取图床 key（可选）  
- 注册 [picgo.net](https://www.picgo.net) → 后台生成 **API v1 Key** → 替换代码里 `PICGO_KEY`  
- 若跳过，上传步骤将报错，其余功能正常

### ③ 运行  
```bash
python app.py
```
浏览器自动打开 `http://localhost:7860`

---

## 📸 核心功能一览
| Tab | 功能 | 说明 |
|-----|------|------|
| 📸 环境评估 | 上传照片 → 图床直链 → AI 建议 + 风险标注图 | 红框标出隐患，文字给出改造方案 |
| 💬 进一步咨询 | 多轮对话 Chatbot | 随机回复适老干货，可替换成大模型 |
| 📖 参考书籍 | PDF 预览 Gallery | 把本地 PDF 转图片展示，供用户查阅 |

---

## 🧠 代码结构（已精简）
```
app.py
 ├─ upload_to_picgo()      # PIL → 图床 → https 直链
 ├─ fake_caption()         # 随机返回一条适老建议（可接大模型）
 ├─ fake_annotated()       # 画红框 + 文字生成“改造后示意图”
 ├─ ai_advise()            # Tab1 主逻辑：上传→建议→示意图
 ├─ fake_chat()            # Tab2 多轮对话
 └─ gr.Blocks()            # 三栏界面 + CSS 美化
```

---

## 🔧 低成本二次开发
- **接入真·大模型**：把 `fake_caption()` 换成调用 **ChatGLM / GPT-4V** 等 vision 接口即可  
- **接入真·目标检测**：用 YOLOv8 检测跌倒隐患，再画框 → 秒变专业评估工具  
- **多语言 / 主题**：改 `CSS` 变量即可切换风格  
- **部署到公网**：`gradio deploy` / Docker / Hugging Face Spaces 一键上线

---

## 📄 License  
MIT – 随意商用，请保留作者信息。

---

## 💬 反馈 & PR  
有改进想法请直接提 Issue / Pull Request，一起让长辈的家更安全！
