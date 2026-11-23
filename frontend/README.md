# 食合 · AI 饮食助手

电脑端 Web 原型，使用 Vue 3、Vite 和原生 CSS。首页将对话、餐单和打卡概览放在同一屏，侧栏可以切换日常打卡、健康统计、社区分享和个人档案。

## 本地运行

在当前目录打开 VS Code 的 PowerShell 终端。需要 Node.js 24 LTS。

```powershell
npm.cmd ci
npm.cmd run dev
```

打开终端打印的 `Local` 地址。首页点「拍照打卡 → 试用示例照片」，可以体验分析结果、保存打卡、查看统计和带图分享。

饮食助手默认调用后端。照片打卡上传 JPG、PNG 或 WebP 后会自动调用照片分析接口。已确认的打卡会更新能量、蛋白质、脂肪和碳水统计。社区支持独立发帖、上传一张配图，也可以从打卡记录带入照片。打卡照片保存在 IndexedDB。后端运行时，帖子和配图保存到共享社区。后端未启动时，社区显示本地演示并将新帖保存在当前浏览器。

## 生成网页文件

```powershell
npm.cmd run build
npm.cmd run preview
```

构建输出到 `dist/`。本地打开预览命令打印的地址。部署时由 Nginx 提供 `dist/` 中的文件，并将 `/api/` 转发给 FastAPI。

## 接入照片分析

先按 [后端启动说明](../backend/README.md) 启动 FastAPI。Vite 默认把 `/api` 代理到 `http://127.0.0.1:8000`，可通过 `DIET_API_PROXY_TARGET` 修改。照片以 `multipart/form-data` 的 `file` 字段提交到 `POST /api/meal-analysis`。后端设置 `DEEPSEEK_API_KEY` 后即可分析真实照片。正式运行时由 Nginx 提供同源反向代理。

## 饮食助手

按后端说明在 `8001` 启动 FastAPI 时，在前端的 `.env.local` 中设置 `DIET_API_PROXY_TARGET=http://127.0.0.1:8001`。如需离线演示，可设置 `VITE_ASSISTANT_MODE=demo`。

前端调用 `POST /api/assistant/chat`，提交本轮 `message`、档案 `profile`、可选的 `previous_meal` 和最近对话 `history`。档案保存在当前浏览器，随聊天发送的字段包括预算、口味、用餐场景和忌口。FastAPI 将这四项作为系统提示词的上下文交给 DeepSeek，称呼与打卡记录由浏览器保留。

返回值示例：

```json
{
  "reply": "这餐可以选择豆腐、时蔬和杂粮饭。",
  "meal": {
    "title": "清淡晚餐搭配",
    "reason": "结合这次的口味偏好来搭配。",
    "items": [
      { "name": "香煎豆腐", "portion": "1 份" },
      { "name": "杂粮饭", "portion": "半碗" }
    ]
  }
}
```

需要追问时返回 `{"reply":"你打算在家做还是在食堂吃？","meal":null}`。前端收到有效餐单后显示可保存的卡片，用户用餐后可以打开照片打卡入口。

## 源码入口

- `src/App.vue` · 页面和交互
- `src/style.css` · 桌面布局和响应式样式
- `src/diet.js` · 本地演示数据、记录存储和对话接口
- `src/MealPhotoForm.vue` · 上传、照片分析与确认打卡
- `src/PhotoPostForm.vue` · 编辑图文帖子
- `src/community.js` · 读取和发布共享社区帖子
- `src/photos.js` · 照片压缩、本地图片存储和照片分析接口
- `public/images/diet-bowl.webp` · 内置图像生成工具制作的餐食配图

<details>
<summary>餐食配图生成提示词</summary>

> Generate a single photorealistic editorial food photograph for the top-right of a polished Chinese nutrition-dashboard desktop web app. A shallow matte ivory ceramic bowl of a vibrant Chinese-inspired balanced lunch: glazed golden tofu cubes, short-grain brown rice, broccolini, napa greens, a few thin carrot ribbons and sesame as decoration. A dark moss-green linen tablecloth on a dark moss or forest green table, warm natural sidelight from upper-right, real fine food texture, sophisticated cookbook food photography. Medium-wide horizontal 3:2 crop, three-quarter overhead. Main plate centered-right, full bowl clearly seen, background fills whole frame, subtly darker shaded olive along the left edge for blending with the dashboard's deep forest green #23372b. Plate is hero, no people, props minimal, no lettering, no logos, no watermark, no frames or graphics. Restaurant-quality but approachable home cooking. Deep fern green and rich warm ivory tones, rich contrast.

</details>
