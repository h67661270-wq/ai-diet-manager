# 食合 · FastAPI 饮食管理

提供 `POST /api/meal-analysis`。上传一张餐食照片后，后端清理图片元数据、缩放并调用 DeepSeek 官方 API。响应包含识别出的食物类型、估计份量及整餐的能量、蛋白质、脂肪和碳水。缺失的数值用 `null` 表示。

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

后端将照片发送到 `https://api.deepseek.com/chat/completions`，使用支持图片的 `deepseek-flash`。密钥从 [DeepSeek 开放平台](https://platform.deepseek.com/api_keys) 获取，只用于后端。照片分析服务本身不保存上传文件。用户点击确认后，前端把记录和压缩图保存在本浏览器。

## 社区

`GET /api/posts` 读取最近 50 条帖子，`POST /api/posts` 保存正文和可选照片，`GET /api/posts/{post_id}/photo` 返回已发布的配图。默认数据库在 `backend/var/community.sqlite3`，可用 `DIET_COMMUNITY_DB` 改为持久化文件的位置。演示昵称来自浏览器档案。

公开上线时，应对接账号鉴权、内容管理和模型调用额度管理。

[DeepSeek 图像理解](https://api-docs.deepseek.com/zh-cn/guides/vision/)
