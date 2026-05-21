# xhs-monitor — 项目记忆

小红书内容监控 + 拼豆工具的本地应用。FastAPI 后端 + Vue 3 前端，纯本地运行。

## 启动

- 双击 `start.bat`（已修好：必须 CRLF 行尾、全 ASCII、`setlocal enabledelayedexpansion`）。
  它会：选 `.venv` Python → 装依赖 → 装前端依赖 → **自动用调试端口启动 Chrome** → 起后端/前端。
- 端口：后端 `127.0.0.1:8765`、前端 `localhost:5173`、Chrome CDP `9222`。
- 爬虫依赖：Chrome 必须以 `--remote-debugging-port=9222 --user-data-dir="C:\chrome-debug"`
  启动**并已扫码登录小红书**——爬虫用 CDP 接管这个 Chrome 的登录态。

## 架构

- `app/` — FastAPI 后端。`app/api/*` 路由在 `app/main.py` 注册；`app/models/` 是
  SQLAlchemy 模型（SQLite `data/xhs_monitor.db`）；`app/adapters/mediacrawler.py`
  是 Playwright/CDP 爬虫适配器；`app/services/orchestrator.py` 是抓取流水线。
- `frontend/` — Vue 3 + TS + Vite。`views/` 页面、`composables/` 逻辑、
  `components/` 组件、`router/index.ts` 路由、`data/` 静态数据、`styles/theme.css` 主题。
- `lib/media_crawler_src/` — 上游 MediaCrawler 源码（参考用，别改）。

## 关键约定与坑

- **主题**：「樱花辑」kawaii 暗→亮风（`theme.css`）。配色用 CSS 变量
  `--sakura / --cream-* / --plum-* / --ok/--warn/--bad`、字体 `--font-display`
  (ZCOOL KuaiLe) / `--font-body` (Nunito) / `--font-mono`。旧变量名有 alias。
- **.bat 文件**：Write 工具默认写 LF，Windows cmd 必须 CRLF——写完用 PowerShell
  规范化：`(Get-Content) -replace ... ; WriteAllText(... UTF8 无BOM)`。`!` 在
  delayed-expansion 下要写 `^^!`。
- **DB 迁移**：`app/models/database.py` 的 `_add_column_if_missing()` 启动时幂等
  `ALTER TABLE`。加字段就往 `init_db()` 里加一行。
- **XHS 图片**：`<img>` 要 `referrerpolicy="no-referrer"`；浏览器 canvas 读不了
  XHS 远程图（跨域污染）——拼豆工具因此只支持本地上传。
- **XHS 反爬**：访问笔记必须带 `xsec_token`/`xsec_source`，否则弹「扫码查看」。
  详情抓取走三策略：`__INITIAL_STATE__` → FEED API → DOM。
- **校验**：`vue-tsc --noEmit` 会报一个**历史遗留**错误 `useWebSocket.ts(34)`
  —— 与新代码无关，忽略它。判断新文件是否有错就 grep 文件名。
  构建用 `npx vite build`。

## 拼豆工坊（Bead Studio）

入口：左侧导航「🧩 拼豆」，两个 tab —— 拼豆工坊(`/bead-studio`) / MARD 色卡(`/bead-studio/cards`)。

- `frontend/src/views/BeadStudio.vue` — 图片转拼豆图纸 + 编辑器（纯前端 Canvas）。
  被 `App.vue` 的 `<keep-alive :include="['BeadStudio']">` 缓存——切到 MARD 色卡
  再切回来画布/编辑不丢失；故全局监听必须用 `onActivated`/`onDeactivated`
  收发（不能用 `onMounted`/`onBeforeUnmount`），组件需显式 `name: 'BeadStudio'`。
- `frontend/src/views/MardCards.vue` — MARD 色卡浏览（8 档套装：24/48/72/96/120/144/216/264）。
- `frontend/src/components/BeadPalettePicker.vue` — 自定义色板选择弹窗
  （全部色号方块、按 A/B/C… 系列分类、可勾选）。
- `frontend/src/components/BeadExportDialog.vue` — 导出弹窗（只选格式，样式跟随画布）。
- `frontend/src/composables/usePerler.ts` — 转换逻辑：8 种生成算法
  (smooth/avg/sharp/slic/block/floyd/atkinson/bayer)、4 种平替算法
  (lab/weighted/hue/luma)。
  `sharp` 为边缘保留降采样（高分辨率重采样 + 暗簇优先，保轮廓）；
  `slic` 为 SLIC 超像素聚类（CIELAB+xy 空间，相似区域合并为扁平色块）；
  `block` 为色块归并（量化后 3×3 邻域多数表决迭代，相邻像素尽量同色）；
  `lab` 为默认平替：CIELAB ΔE94 感知匹配（渐变丝滑、惩罚去饱和避免混杂）。
- `frontend/src/data/mardPalettes.ts` — **MARD 官方色卡数据（263 色）**。
  A~M 九系为标准盒、P/Q/R/T/Y 五系为追加色（共 14 系）。
  来源：pixel-beads.com + bitbead + maxcleme/beadcolors 三方交叉核对。
  套装档位 `MARD_TIERS` 为 8 档累进套装（24/48/72/96/120/144/216/264），
  逐盘录入官方分盘色卡表 ①-⑪ / Ⓐ-Ⓔ：24/48/72/96=①②③④ 累进、
  120=ⒶⒷⒸⒹⒺ、144=120+⑥、216=120+⑥⑨⑩⑪、264=120+⑥⑦⑧⑨⑩⑪。
  更新色卡只需整体替换本文件，其余功能按色号工作。
- `frontend/src/data/pixelPalettes.ts` — **已废弃**（像素风格色板，已无引用，可删）。
- 已实现：
  - 转换：8 生成算法 + 4 平替算法（默认 `lab` 丝滑匹配）。拖入/选择图片
    （上传区或画布上拖放皆可）会**自动转换**；改宽度/算法/色板从原图重新
    量化生成（防抖）；自动重生成前会 `pushHistory`，故 **可 Ctrl+Z 撤销回
    上一次设置**（撤销会同步宽度滑块，`suppressReconv` 防其再触发转换）。
    「🔄 重新转换」按钮则是不可撤销的全新转换。
  - 空白画布：不导入图片，按宽×高「新建空白画布」直接手绘；无源图时改
    网格宽度＝对当前画布做最近邻重采样缩放（`resampleGrid`，可撤销）。
  - 一键描边：沿图案外缘补一圈「当前色」（空格中与图案相邻的格变描边色）。
  - 抠图/去背景：边缘洪水填充识别背景（`detectBackgroundCells`，从四边
    连通 + RGB 容差）。「✂️ 去背景」按钮手动去除；设置区「自动抠图」勾选
    后每次转换自动识别主体、只转主体。适合背景较干净的图。
  - 色板模式：套装色板（8 档）/ 我的色板（自定义，`localStorage` 持久化，
    可从色卡弹窗勾选或从图纸导入）。
  - 编辑工具：画笔 / 橡皮 / 魔棒画笔 / 魔棒橡皮 / 同色替换 / 镜像复制 / 取色 / 移动。
    画笔与橡皮为**圆形**，按 **Shift+滚轮**调大小。
    魔棒画笔/橡皮 = 洪水填充点击处相连同色区域为当前色 / 清空。
    镜像复制 = 选竖/横对称轴 + 方向，点击即把一侧镜像到另一侧。
  - 变换：左右镜像 / 上下翻转 / **自由变换**（PS 式 Ctrl+T，8 手柄缩放 +
    任意角度旋转 + 平移，确认后重采样；撤销系统为完整快照支持尺寸变化）。
  - 豆型(圆/方/填满)、豆径(2.6/3/5mm)成品尺寸、撤销重做。
  - 快捷键：B 画笔 / E 橡皮 / G 魔棒画笔 / D 魔棒橡皮 / R 替换 / M 镜像 /
    I 取色 / H·空格 移动 / Shift+滚轮 笔刷大小 / +- 缩放 / 0 适应 /
    Ctrl+Z 撤销 / 变换中 Enter 应用·Esc 取消。
  - 「标色号」勾选后**实时**在画布每颗豆上显示色号。
  - 导出 PNG/JPG/SVG/CSV —— 所见即所得，跟随画布当前豆型与标色号，无镜像选项。
  - 缺色对比(缺色→平替)。

## 其它功能区

- 任务监控：`/tasks` 列表、详情（三栏可拖拽 splitter、状态指示灯、批量抓取）。
- 评论收藏：`/favorites`，评论可 ♥ 收藏 + 自定义分类。
- B 站搜索：`/bilibili`，走 B 站公开 API。

## 验证

```
cd frontend && npx vite build          # 前端构建
python -c "import py_compile; ..."     # 后端语法
```
后端冒烟测试：起 `run.py` 后打 `GET /api/system/health`。
