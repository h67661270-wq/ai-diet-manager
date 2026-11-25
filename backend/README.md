# 食合 · FastAPI 饮食管理

提供饮食助手、照片打卡和共享社区接口。

## Windows 本地启动

在 `backend/` 目录打开 VS Code 的 PowerShell 终端。使用 uv 和 Python 3.11 或更新版本。

饮食推荐和真实照片分析共用 `DEEPSEEK_API_KEY`。在同一个 PowerShell 窗口配置密钥并启动后端。若后端已启动，先按 `Ctrl+C` 停止。

```powershell
$deepseekKeyInput = Read-Host "输入 DeepSeek 官方 API Key" -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $deepseekKeyInput).Password
uv run --with-requirements requirements.txt -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

在另一个终端启动 [前端](../frontend/README.md)，将 Vite 的代理目标也设为 `http://127.0.0.1:8001`。`/docs` 可测试接口，`/api/health` 中的 `assistant_configured` 和 `vision_configured` 表示后端是否读取到了密钥。

## 饮食助手

`POST /api/assistant/chat` 接收本轮消息、档案中的预算、口味、用餐场景和忌口，以及最近最多六条对话和可选的上一份餐单。后端将档案和餐单作为 JSON 数据加入系统提示词，通过 DeepSeek 官方 API 请求 `deepseek-flash` 生成答案。接口返回文本 `reply` 和可选的结构化 `meal`。服务端不保存档案和对话。

## 照片打卡与营养知识库

`POST /api/meal-analysis` 接收图片字段 `file` 和可选的 `meal_hint`（最多 240 字）。后端清理图片元数据并缩放，由 `deepseek-flash` 返回识别到的菜品和营养估算。照片识别和营养资料补充的单次输出上限为 10,000 tokens。

[本地营养知识库](data/README.md) 包含 6,280 条记录。检索到资料时，后端把相关条目和初步结果一起交给模型。模型可补充来源、修正个别营养值，也可保留初步估算。每 100 克数据可帮助按克数估算，整菜的配方每份值在界面单独展示。检索无结果或资料补充失败时，接口继续返回初步分析。

食物、烹饪方式或份量不能确定时，界面允许补充后重新分析。无法识别食物时，接口返回空菜品列表和下一步提示。单项营养缺失时，可以使用模型给出的整餐估算。没有合理估算的字段保留为 `null`。

照片和用户补充会发给 DeepSeek，后端不保存上传文件。点击确认后，浏览器保存记录和压缩图。

## 社区

`GET /api/posts` 读取最近 50 条帖子，`POST /api/posts` 保存正文和可选照片，`GET /api/posts/{post_id}/photo` 返回已发布的配图。默认数据库在 `backend/var/community.sqlite3`，可用 `DIET_COMMUNITY_DB` 改为持久化文件的位置。演示昵称来自浏览器档案。

公开上线时，应对接账号鉴权、内容管理和模型调用额度管理。

[DeepSeek 图像理解](https://api-docs.deepseek.com/zh-cn/guides/vision/)
