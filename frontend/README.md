# 食合 · AI 饮食助手

电脑端 Web 原型，使用 Vue 3、Vite 和原生 CSS。首页将对话、餐单和打卡概览放在同一屏，侧栏可以切换日常打卡、健康统计、社区分享和个人档案。

## 本地运行

在当前目录打开 VS Code 的 PowerShell 终端。需要 Node.js 24 LTS。

```powershell
npm.cmd ci
npm.cmd run dev
```

打开终端打印的 `Local` 地址。首页点「试用示例餐单」，再点「记入打卡」，即可走完打卡、查看统计和分享的演示流程。

默认使用本地演示模式。餐单示例用于展示交互。档案、手动打卡、保存的餐单和社区分享保存在当前浏览器。演示统计提供能量和打卡频率。

## 生成网页文件

```powershell
npm.cmd run build
npm.cmd run preview
```

构建输出到 `dist/`。本地打开预览命令打印的地址。部署时由 Nginx 提供 `dist/` 中的文件，并将 `/api/` 转发给 FastAPI。

## 接入 FastAPI 和 MaaS

复制 `.env.example` 为 `.env.local`，把 `VITE_ASSISTANT_MODE` 改为 `api`，再重启 Vite。开发服务器默认把 `/api` 代理到 `http://127.0.0.1:8000`，可通过 `DIET_API_PROXY_TARGET` 修改。正式运行时使用同源反向代理。

前端调用 `POST /api/assistant/chat`，提交本轮 `message`、可选的 `previous_meal` 和最近对话 `history`。后端按登录身份读取相关档案，再让 MaaS 实时生成结果。服务端需实现账号鉴权、档案读取和真正的模型调用。这个原型中的档案、打卡、分享继续保存在浏览器，跨账号和跨设备同步属于后端联调。

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

需要追问时返回 `{"reply":"你打算在家做还是在食堂吃？","meal":null}`。MaaS 密钥只由 FastAPI 读取。前端收到有效餐单后显示可保存和可确认打卡的卡片。

## 源码入口

- `src/App.vue` · 页面和交互
- `src/style.css` · 桌面布局和响应式样式
- `src/diet.js` · 本地演示数据、记录存储和对话接口
- `public/images/diet-bowl.webp` · 内置图像生成工具制作的餐食配图

<details>
<summary>餐食配图生成提示词</summary>

> Generate a single photorealistic editorial food photograph for the top-right of a polished Chinese nutrition-dashboard desktop web app. A shallow matte ivory ceramic bowl of a vibrant Chinese-inspired balanced lunch: glazed golden tofu cubes, short-grain brown rice, broccolini, napa greens, a few thin carrot ribbons and sesame as decoration. A dark moss-green linen tablecloth on a dark moss or forest green table, warm natural sidelight from upper-right, real fine food texture, sophisticated cookbook food photography. Medium-wide horizontal 3:2 crop, three-quarter overhead. Main plate centered-right, full bowl clearly seen, background fills whole frame, subtly darker shaded olive along the left edge for blending with the dashboard's deep forest green #23372b. Plate is hero, no people, props minimal, no lettering, no logos, no watermark, no frames or graphics. Restaurant-quality but approachable home cooking. Deep fern green and rich warm ivory tones, rich contrast.

</details>
