<template>
  <div class="bead-studio">
    <BeadTabs />

    <!-- ===== Start panel: convert image / new canvas / import project ===== -->
    <div class="card setup-card">
      <div class="entry-grid">
        <!-- 转换图片 -->
        <div class="entry-card">
          <div class="entry-stage upload-zone"
               :class="{ dragging: isDragging, filled: !!sourcePreview }"
               @click="pickFile"
               @dragover.prevent="isDragging = true"
               @dragleave.prevent="isDragging = false"
               @drop.prevent="onDrop">
            <img v-if="sourcePreview" :src="sourcePreview" class="upload-preview" alt="原图" />
            <div v-else class="upload-hint">
              <div class="upload-emoji">🖼️</div>
              <div class="upload-text">点击或拖入图片</div>
              <div class="upload-sub">JPG / PNG / GIF</div>
            </div>
            <input ref="fileInput" type="file" accept="image/*" hidden @change="onFileChange" />
          </div>
          <button v-if="sourceImg" class="btn btn-primary entry-btn"
                  :disabled="converting" @click="convert(true)">
            {{ converting ? '转换中…' : '🔄 用当前图片重新转换' }}
          </button>
          <button v-if="sourceImg" class="btn btn-ghost entry-btn"
                  @click="showCropDialog = true">
            ✂️ 裁剪图片
          </button>
          <div class="entry-title">🖼️ 转换图片</div>
          <div class="entry-desc">选择或拖入一张图片，自动转换成拼豆图纸，导入后可在画布上继续编辑。</div>
        </div>

        <!-- 新建画布 -->
        <div class="entry-card">
          <div class="entry-stage blank-stage">
            <div class="blank-size">
              <label>宽
                <input type="number" min="8" max="220" v-model.number="gridWidth" class="input" />
              </label>
              <span class="blank-x">×</span>
              <label>高
                <input type="number" min="8" max="220" v-model.number="blankHeight" class="input" />
              </label>
            </div>
            <div class="blank-unit">单位：颗豆</div>
            <button class="btn btn-primary entry-btn" @click="newBlankGrid">✏️ 新建空白画布</button>
          </div>
          <div class="entry-title">✏️ 新建画布</div>
          <div class="entry-desc">设定宽 × 高，从一张空白画布开始自由手绘你的拼豆图。</div>
        </div>

        <!-- 导入工程 -->
        <div class="entry-card">
          <div class="entry-stage upload-zone proj-zone"
               @click="pickProjectFile"
               @dragover.prevent
               @drop.prevent="onProjectDrop">
            <div class="upload-hint">
              <div class="upload-emoji">📦</div>
              <div class="upload-text">点击或拖入工程文件</div>
              <div class="upload-sub">.beadproj</div>
            </div>
          </div>
          <div class="entry-title">📦 导入工程</div>
          <div class="entry-desc">打开之前保存的 .beadproj 工程文件，恢复画布与全部设置继续编辑。</div>
        </div>
      </div>

      <!-- collapsible advanced conversion settings -->
      <div class="conv-section">
        <div class="conv-toggle" @click="showConvSettings = !showConvSettings">
          <span class="conv-toggle-icon">{{ showConvSettings ? '▼' : '▶' }}</span>
          <span>转换设置 · 算法 / 平替 / 色板</span>
        </div>
        <div v-if="showConvSettings" class="conv-body">
          <div class="form-row">
            <label>生成算法</label>
            <select class="select" v-model="algo">
              <option v-for="a in ALGO_OPTIONS" :key="a.id" :value="a.id">{{ a.label }}</option>
            </select>
            <span class="form-hint">{{ algoDesc }}</span>
          </div>
          <div class="form-row">
            <label>平替算法</label>
            <select class="select" v-model="matchMetric">
              <option v-for="m in MATCH_OPTIONS" :key="m.id" :value="m.id">{{ m.label }}</option>
            </select>
            <span class="form-hint">{{ matchDesc }}</span>
          </div>
          <div class="form-row">
            <label>色板模式</label>
            <div class="mode-toggle">
              <button class="mode-btn" :class="{ on: palMode === 'tier' }" @click="palMode = 'tier'">套装色板</button>
              <button class="mode-btn" :class="{ on: palMode === 'custom' }" @click="palMode = 'custom'">我的色板</button>
            </div>
          </div>
          <div class="form-row" v-if="palMode === 'tier'">
            <label>工作色板</label>
            <select class="select" v-model="tier">
              <option v-for="t in TIER_ORDER" :key="t" :value="t">{{ TIER_LABELS[t] }}</option>
            </select>
            <span class="form-hint">转换与画笔都使用此色板（共 {{ workingPalette.length }} 色）</span>
          </div>
          <div class="form-row" v-else>
            <label>我的色板</label>
            <span class="form-hint">{{ workingPalette.length > 0 ? `已选 ${workingPalette.length} 色，可在右侧「我的色板」面板管理` : '⚠ 尚未添加任何颜色，请在右侧面板添加' }}</span>
          </div>
        </div>
      </div>

      <input ref="projInput" type="file" accept=".beadproj,.json,application/json"
             hidden @change="onProjectFileChange" />
    </div>

    <!-- ===== Workspace ===== -->
    <div v-if="grid" class="workspace">
      <!-- Canvas column — teleported to #app in fullscreen OR immersive so
           position:fixed escapes the transformed .bead-studio containing
           block, while staying in #app's stacking context so modal dialogs
           (z-index 100) stay above -->
      <Teleport to="#app" :disabled="!fullscreen && !immersive">
      <div class="canvas-col card" :class="{ fullscreen, immersive }">
       <!-- Floating status chip — only shown in immersive highlight mode,
            since the toolbar (where the normal status tag lives) is hidden.
            Draggable via grip; interactive controls (mode picker + W/H
            inputs) don't trigger drag thanks to startChipDrag's target check. -->
       <div v-if="immersive" class="immersive-status"
            :style="chipStyle"
            @mousedown="startChipDrag">
         <span class="im-grip" title="按住拖动整个面板">⠿</span>

         <!-- Mode switcher (compact dropdown) -->
         <div class="im-mode-wrap">
           <button class="im-mode-btn"
                   @click.stop="showHighlightMenu = !showHighlightMenu"
                   title="切换高亮模式">
             💡 {{ HIGHLIGHT_LABELS[highlightMode] }}
             <span class="im-caret">{{ showHighlightMenu ? '▴' : '▾' }}</span>
           </button>
           <div v-if="showHighlightMenu" class="im-menu"
                @click.stop @mousedown.stop>
             <button v-for="m in HIGHLIGHT_OPTIONS" :key="m.id"
                     class="im-menu-item" :class="{ on: highlightMode === m.id }"
                     @click="setHighlightMode(m.id); showHighlightMenu = false">
               <span class="im-menu-ico">{{ m.icon }}</span>
               <span>{{ m.label }}</span>
               <span v-if="highlightMode === m.id" class="im-menu-check">✓</span>
             </button>
           </div>
         </div>

         <!-- Mode-specific status / controls -->
         <span v-if="highlightMode === 'row'" class="im-tag mono">
           行 {{ highlightRow + 1 }} / {{ grid.height }}
         </span>
         <span v-else-if="highlightMode === 'col'" class="im-tag mono">
           列 {{ highlightCol + 1 }} / {{ grid.width }}
         </span>
         <span v-else-if="highlightMode === 'color'" class="im-color-wrap">
           <button class="im-color-btn"
                   :style="{ background: curColorHex,
                             color: chipTextOn(curColorHex),
                             borderColor: chipBorderOn(curColorHex) }"
                   @click.stop="showColorPickerInChip = !showColorPickerInChip"
                   title="点击换高亮的色号">
             <span class="mono">{{ currentCode || '请选色' }}</span>
             <span class="im-caret">{{ showColorPickerInChip ? '▴' : '▾' }}</span>
           </button>
           <div v-if="showColorPickerInChip" class="im-color-grid"
                @click.stop @mousedown.stop>
             <button v-for="c in usedColorsForPicker" :key="c.code"
                     class="im-color-cell"
                     :class="{ on: currentCode === c.code }"
                     :style="{ background: c.hex }"
                     :title="`${c.code} ${c.name} · 画布上 ${c.count} 颗`"
                     @click="selectColor(c.code); showColorPickerInChip = false">
               <span class="mono im-color-code"
                     :style="{ color: chipTextOn(c.hex) }">{{ c.code }}</span>
               <span class="mono im-color-count"
                     :style="{ color: chipTextOn(c.hex) }">{{ c.count }}</span>
             </button>
             <div v-if="usedColorsForPicker.length === 0" class="im-color-empty">
               画布上还没有任何颜色
             </div>
           </div>
         </span>
         <span v-else-if="highlightMode === 'rect'" class="im-rect-inline">
           <span class="im-lbl">宽</span>
           <input type="number" min="1" :max="grid.width" v-model.number="highlightRect.w"
                  class="im-num" @input="clampHighlightRect()"
                  @mousedown.stop @click.stop />
           <span class="im-lbl">高</span>
           <input type="number" min="1" :max="grid.height" v-model.number="highlightRect.h"
                  class="im-num" @input="clampHighlightRect()"
                  @mousedown.stop @click.stop />
           <span class="im-tag im-tag-pos mono">@({{ highlightRect.x + 1 }},{{ highlightRect.y + 1 }})</span>
         </span>

         <span class="im-hint">Esc 退出</span>
       </div>
       <div class="canvas-body">
        <!-- SAI-style tool rail -->
        <div class="tool-rail">
          <div class="rail-title">工具</div>
          <button v-for="t in tools" :key="t.id"
                  class="rail-btn" :class="{ on: tool === t.id }"
                  :title="`${t.label} (${t.key})`"
                  @click="tool = t.id">
            <svg class="tool-ico" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round"
                 v-html="t.svg"></svg>
          </button>
        </div>
        <div class="canvas-main">
        <!-- Toolbar -->
        <div class="toolbar">
          <!-- brush / eraser size — Shift + wheel -->
          <div class="size-tag" v-show="tool === 'paint' || tool === 'erase'"
               title="按住 Shift + 滚轮调整大小">
            {{ tool === 'paint' ? '画笔' : '橡皮' }}
            <b class="mono">{{ activeBrushSize }}×{{ activeBrushSize }}</b>
            <span class="size-hint">⇧滚轮</span>
          </div>
          <!-- mirror-copy config -->
          <div class="mirror-cfg" v-show="tool === 'mirror'">
            <button class="tool-btn mini-btn" :class="{ on: mirrorAxis === 'v' }"
                    title="竖直对称线（左右镜像）" @click="mirrorAxis = 'v'">竖轴</button>
            <button class="tool-btn mini-btn" :class="{ on: mirrorAxis === 'h' }"
                    title="水平对称线（上下镜像）" @click="mirrorAxis = 'h'">横轴</button>
            <button class="tool-btn mini-btn" :class="{ on: mirrorDir === 1 }"
                    @click="mirrorDir = 1">{{ mirrorAxis === 'v' ? '左→右' : '上→下' }}</button>
            <button class="tool-btn mini-btn" :class="{ on: mirrorDir === -1 }"
                    @click="mirrorDir = -1">{{ mirrorAxis === 'v' ? '右→左' : '下→上' }}</button>
          </div>
          <!-- selection tool hint -->
          <div class="size-tag sel-hint" v-show="tool === 'select'">
            ⬚ 拖拽框选 · 框内拖动移动 · Delete 删 · Esc 取消
          </div>
          <button class="btn btn-ghost btn-sm" v-show="tool === 'select'"
                  :disabled="!selection" @click="cropToSelection"
                  title="把画布裁剪到当前选区范围（区外丢弃）">
            ◳ 裁剪选区
          </button>
          <!-- shape tool options -->
          <div class="size-tag sel-hint" v-show="isShapeTool(tool)">
            <label class="shape-fill-opt" title="勾选则填充，否则只画轮廓">
              <input type="checkbox" v-model="shapeFill" />
              <span>填充</span>
            </label>
            <span class="size-hint">拖拽绘制 · Shift 约束正方/正圆/水平</span>
          </div>
          <div class="tool-divider"></div>
          <div class="tool-group">
            <button class="tool-btn" title="撤销 (Ctrl+Z)"
                    :disabled="!canUndo" @click="undo">↶</button>
            <button class="tool-btn" title="重做 (Ctrl+Shift+Z)"
                    :disabled="!canRedo" @click="redo">↷</button>
          </div>
          <div class="tool-divider"></div>
          <div class="tool-group">
            <button class="tool-btn" title="左右镜像" @click="flipH">⇄</button>
            <button class="tool-btn" title="上下翻转" @click="flipV">⇅</button>
            <button class="tool-btn" :class="{ on: transforming }"
                    title="自由变换（缩放 / 任意角度旋转）" @click="startTransform">⤢</button>
          </div>
          <div class="tool-divider"></div>
          <button type="button" class="cur-color" :class="{ active: showColorPanel }"
                  title="点击打开调色板（全屏时也能选色）" @click="toggleColorPanel">
            <span class="cur-swatch" :style="{ background: curColorHex }"></span>
            <span class="cur-label mono">{{ currentCode || '—' }}</span>
            <span class="cur-caret">{{ showColorPanel ? '▴' : '▾' }}</span>
          </button>
          <button class="btn btn-ghost btn-sm" @click="outlineShape"
                  title="一键描边：沿图案外缘描一圈「当前色」（先在调色板选好颜色）">
            🖍 描边
          </button>
          <button class="btn btn-ghost btn-sm" @click="removeBackground"
                  title="一键去背景：从图纸四边洪水填充，清除与边缘相连、接近背景色的格子">
            ✂️ 去背景
          </button>
          <button class="btn btn-ghost btn-sm" @click="openResizeDialog"
                  title="调整画布大小：同时改宽高，图案比例不变，多出的格子留空">
            📐 画布尺寸
          </button>
          <div class="tool-divider"></div>
          <!-- grid-lines popover: solid + dashed layers, each individually
               configurable (step / colour / on-off) -->
          <div class="gl-group">
            <button class="gl-btn" :class="{ on: gridConfig.solid.enabled || gridConfig.dashed.enabled }"
                    @click="showGridMenu = !showGridMenu"
                    title="参考线设置（实线 / 虚线，步长 + 颜色 + 开关）">
              📏 参考线
              <span class="gl-caret">{{ showGridMenu ? '▴' : '▾' }}</span>
            </button>
            <div v-if="showGridMenu" class="gl-menu" @click.stop @mousedown.stop>
              <div class="gl-row">
                <label class="gl-chk">
                  <input type="checkbox" v-model="gridConfig.solid.enabled" />
                  <span class="gl-row-title">实线</span>
                </label>
                <span class="gl-sub">每</span>
                <input type="number" min="1" :max="grid.width" class="gl-num"
                       v-model.number="gridConfig.solid.step"
                       :disabled="!gridConfig.solid.enabled" />
                <span class="gl-sub">格</span>
                <input type="color" class="gl-color"
                       :value="hexOf(gridConfig.solid.color)"
                       @input="gridConfig.solid.color = ($event.target as HTMLInputElement).value"
                       :disabled="!gridConfig.solid.enabled"
                       title="选颜色" />
                <input type="number" min="0.5" step="0.5" max="6" class="gl-num gl-num-sm"
                       v-model.number="gridConfig.solid.width"
                       :disabled="!gridConfig.solid.enabled"
                       title="线宽 (px)" />
              </div>
              <div class="gl-row">
                <label class="gl-chk">
                  <input type="checkbox" v-model="gridConfig.dashed.enabled" />
                  <span class="gl-row-title">虚线</span>
                </label>
                <span class="gl-sub">每</span>
                <input type="number" min="1" :max="grid.width" class="gl-num"
                       v-model.number="gridConfig.dashed.step"
                       :disabled="!gridConfig.dashed.enabled" />
                <span class="gl-sub">格</span>
                <input type="color" class="gl-color"
                       :value="hexOf(gridConfig.dashed.color)"
                       @input="gridConfig.dashed.color = ($event.target as HTMLInputElement).value"
                       :disabled="!gridConfig.dashed.enabled"
                       title="选颜色" />
                <input type="number" min="0.5" step="0.5" max="6" class="gl-num gl-num-sm"
                       v-model.number="gridConfig.dashed.width"
                       :disabled="!gridConfig.dashed.enabled"
                       title="线宽 (px)" />
              </div>
              <div class="gl-foot">
                <button class="btn btn-ghost btn-xs" @click="resetGridConfig">↺ 重置默认</button>
              </div>
            </div>
          </div>
          <div class="tool-divider"></div>
          <!-- highlight mode: one dropdown with all the highlight kinds -->
          <div class="hi-group">
            <button class="hi-btn" :class="{ on: highlightMode !== 'none' }"
                    @click="showHighlightMenu = !showHighlightMenu"
                    title="高亮模式（行 / 列 / 色号 / 矩形）—— 高亮中可按 ↑↓←→ 移动、Esc 退出">
              💡 高亮{{ highlightMode !== 'none' ? ` · ${HIGHLIGHT_LABELS[highlightMode]}` : '' }}
              <span class="hi-caret">{{ showHighlightMenu ? '▴' : '▾' }}</span>
            </button>
            <!-- popover menu -->
            <div v-if="showHighlightMenu" class="hi-menu" @click.stop>
              <button v-for="m in HIGHLIGHT_OPTIONS" :key="m.id"
                      class="hi-menu-item" :class="{ on: highlightMode === m.id }"
                      @click="setHighlightMode(m.id); showHighlightMenu = false">
                <span class="him-icon">{{ m.icon }}</span>
                <span class="him-text">{{ m.label }}</span>
                <span v-if="highlightMode === m.id" class="him-check">✓</span>
              </button>
            </div>
            <!-- live status / per-mode controls -->
            <span v-if="highlightMode === 'row'" class="hi-tag mono">
              行 {{ highlightRow + 1 }} / {{ grid.height }}
            </span>
            <span v-else-if="highlightMode === 'col'" class="hi-tag mono">
              列 {{ highlightCol + 1 }} / {{ grid.width }}
            </span>
            <span v-else-if="highlightMode === 'color'" class="hi-tag mono"
                  :style="{ background: curColorHex || '#fff' }">
              {{ currentCode || '请先选色' }}
            </span>
            <span v-else-if="highlightMode === 'rect'" class="hi-rect-ctl">
              <span class="hi-rect-lbl">宽</span>
              <input type="number" min="1" :max="grid.width" v-model.number="highlightRect.w"
                     class="hi-rect-num" @input="clampHighlightRect()" />
              <span class="hi-rect-lbl">高</span>
              <input type="number" min="1" :max="grid.height" v-model.number="highlightRect.h"
                     class="hi-rect-num" @input="clampHighlightRect()" />
              <span class="hi-rect-pos mono">@({{ highlightRect.x + 1 }},{{ highlightRect.y + 1 }})</span>
            </span>
          </div>
          <div class="tool-divider"></div>
          <div class="tool-group">
            <button class="tool-btn" title="缩小 (-)" @click="zoomBy(-1)">－</button>
            <span class="zoom-label mono">{{ Math.round(zoom * 100) }}%</span>
            <button class="tool-btn" title="放大 (+)" @click="zoomBy(1)">＋</button>
            <button class="tool-btn" title="适应窗口 (0)" @click="fitView">⊡</button>
            <button class="tool-btn" :class="{ on: fullscreen }"
                    :title="fullscreen ? '退出全屏 (F)' : '全屏画布 (F)'"
                    @click="fullscreen = !fullscreen">⛶</button>
          </div>
          <div class="tool-divider"></div>
          <span class="grid-size mono">{{ grid.width }} × {{ grid.height }}</span>
          <span class="grid-size mono" title="按豆径换算的成品尺寸">
            ≈ {{ finishedSize }}
          </span>
          <span class="kbd-hint" title="B 画笔 · E 橡皮 · G 魔棒画笔 · D 魔棒橡皮 · R 替换 · M 镜像复制 · S 选区 · I 取色 · H/空格 移动 · F 全屏 · ⇧+滚轮 笔刷大小 · +/- 缩放 · 0 适应 · Ctrl+Z 撤销 · 高亮模式下 ↑↓←→ 切换行列、Esc 退出">⌨ 快捷键</span>
          <label class="export-opt" style="margin-left:auto;" title="在画布每颗豆上显示 MARD 色号">
            <input type="checkbox" v-model="showLabels" />
            <span>标色号</span>
          </label>
          <button class="btn btn-ghost btn-sm" @click="saveProject"
                  title="保存为工程文件（.beadproj），下次可打开继续编辑">
            💾 存工程
          </button>
          <button class="btn btn-ghost btn-sm" @click="pickProjectFile"
                  title="打开已保存的工程文件继续编辑">
            📂 开工程
          </button>
          <button class="btn btn-ghost btn-sm" @click="openExportDialog">
            ⬇ 导出
          </button>
          <button class="btn btn-ghost btn-sm" @click="onPublishToGallery"
                  title="把当前画布生成带色号的图，发布到我的画廊">
            🎨 发布
          </button>
          <button class="btn btn-ghost btn-sm" @click="showShopDialog = true">
            🛒 购买
          </button>
          <button class="btn btn-ghost btn-sm" @click="showInventoryDialog = true"
                  title="我的库存：管理你拥有的拼豆数量">
            📦 库存
          </button>
          <button class="btn btn-ghost btn-sm" @click="onImportCanvasToInventory"
                  title="把当前画布上用到的所有色号 × 数量加进我的库存（可用来撤销「完工」的扣减）">
            ➕ 入库
          </button>
          <button class="btn btn-ghost btn-sm" @click="onFinishProject"
                  :class="{ 'finish-confirm': finishConfirm }"
                  :title="finishConfirm ? '再次点击确认扣减库存' : '把这张图用到的颜色从我的库存里扣掉'">
            {{ finishConfirm ? '确认扣库存？' : '➖ 完工' }}
          </button>
        </div>

        <!-- Live params — adjustable while editing -->
        <div class="param-bar">
          <label class="pb-cell pb-wide">
            <span class="pb-label">网格宽度 · {{ grid.width }}×{{ grid.height }}</span>
            <input type="range" min="16" max="180" step="1"
                   v-model.number="gridWidth" class="slider" />
          </label>
          <label class="pb-cell">
            <span class="pb-label">豆数</span>
            <input type="number" min="16" max="180"
                   v-model.number="gridWidth" class="input" />
          </label>
          <label class="pb-cell">
            <span class="pb-label">算法</span>
            <select class="select" v-model="algo">
              <option v-for="a in ALGO_OPTIONS" :key="a.id" :value="a.id">{{ a.label }}</option>
            </select>
          </label>
          <label class="pb-cell">
            <span class="pb-label">平替</span>
            <select class="select" v-model="matchMetric">
              <option v-for="m in MATCH_OPTIONS" :key="m.id" :value="m.id">{{ m.label }}</option>
            </select>
          </label>
          <label class="pb-cell">
            <span class="pb-label">颜色数</span>
            <input type="number" min="0" max="200" v-model.number="colorLimit"
                   class="input" title="限制图中最多用多少种颜色；0 = 不限制" />
          </label>
          <label class="pb-cell">
            <span class="pb-label">色板</span>
            <select class="select" v-model="tier" :disabled="palMode === 'custom'">
              <option v-for="t in TIER_ORDER" :key="t" :value="t">{{ t }} 色</option>
            </select>
          </label>
          <label class="pb-cell">
            <span class="pb-label">豆型</span>
            <select class="select" v-model="beadShape">
              <option value="circle">圆形</option>
              <option value="square">方形</option>
              <option value="fill">填满</option>
            </select>
          </label>
          <label class="pb-cell">
            <span class="pb-label">豆径</span>
            <div class="bead-size-toggle">
              <button class="pill-btn" :class="{ on: beadSize === 2.6 }" @click="beadSize = 2.6">2.6mm</button>
              <button class="pill-btn" :class="{ on: beadSize === 5 }" @click="beadSize = 5">5mm</button>
              <button class="pill-btn pill-sub" :class="{ on: beadSize === 3 }" @click="beadSize = 3" title="3mm（少量使用）">3</button>
            </div>
          </label>
          <span class="pb-hint" :class="{ busy: converting }">
            {{ converting ? '重新生成中…' : '改宽度/算法/色板会从原图重新生成 · 可 Ctrl+Z 撤销' }}
          </span>
        </div>

        <!-- Reference image overlay -->
        <div class="ref-section">
          <div class="ref-toggle" @click="showRefSection = !showRefSection">
            <span class="ref-toggle-icon">{{ showRefSection ? '▼' : '▶' }}</span>
            <span>参考图叠加</span>
            <span v-if="refImage" class="ref-badge">已加载</span>
          </div>
          <div v-if="showRefSection" class="ref-body">
            <div v-if="!refImage" class="ref-upload"
                 @click="refFileInput?.click()" @dragover.prevent
                 @drop.prevent="onRefDrop">
              <span>＋ 拖入或点击添加参考图</span>
              <input ref="refFileInput" type="file" accept="image/*" hidden @change="onRefFileChange" />
            </div>
            <div v-else class="ref-controls">
              <img :src="refPreview" class="ref-thumb" alt="参考图" />
              <label class="ref-slider-label">
                <span>透明度</span>
                <input type="range" min="0" max="1" step="0.05"
                       v-model.number="refOpacity" class="slider ref-slider" @input="render" />
                <span class="mono">{{ Math.round(refOpacity * 100) }}%</span>
              </label>
              <button class="ref-lock-btn" :class="{ locked: refLocked }"
                      @click="refLocked = !refLocked"
                      :title="refLocked ? '已锁定' : '点击锁定参考图'">
                {{ refLocked ? '🔒' : '🔓' }}
              </button>
              <button class="btn btn-ghost btn-xs" :disabled="refLocked" @click="removeRef">
                移除
              </button>
            </div>
          </div>
        </div>

        <!-- Canvas -->
        <div ref="wrapRef" class="canvas-wrap" :class="{ xforming: transforming }"
             @wheel.prevent="onWheel"
             @mousedown="onDown"
             @mousemove="onMove"
             @mouseup="onUp"
             @mouseleave="onLeave"
             @dragover.prevent
             @drop.prevent="onDrop">
          <canvas ref="canvasRef"></canvas>
          <div v-if="hoverTip && !transforming" class="hover-tip" :style="hoverTipStyle">
            {{ hoverTip }}
          </div>
          <transition name="fs-tip">
            <div v-if="showFsTip" class="fs-tip">
              <span class="fs-tip-key">F</span>
              <span class="fs-tip-text">键可全屏画布</span>
            </div>
          </transition>
          <!-- free-transform action bar -->
          <div v-if="transforming" class="xform-bar">
            <span class="xform-title">自由变换</span>
            <span class="xform-info mono">缩放 {{ xformScalePct }}% · 旋转 {{ xformAngleDeg }}°</span>
            <span class="xform-hint">角手柄按 Shift 等比</span>
            <button class="btn btn-sm btn-primary" @click="applyTransform">✓ 应用</button>
            <button class="btn btn-sm btn-ghost" @click="cancelTransform">✕ 取消</button>
          </div>
        </div>
        </div>
       </div>

        <!-- Floating palette — selectable even in fullscreen mode -->
        <div v-if="showColorPanel" class="color-panel" :style="{ top: colorPanelTop + 'px' }">
          <div class="color-panel-head">
            <span class="cp-swatch" :style="{ background: curColorHex }"></span>
            <span class="cp-title">调色板 · {{ currentCode || '—' }}</span>
            <button class="cp-close" title="关闭 (Esc)" @click="showColorPanel = false">✕</button>
          </div>
          <div class="color-panel-modes">
            <button class="mode-btn" :class="{ on: palMode === 'tier' }"
                    @click="palMode = 'tier'">套装色板</button>
            <button class="mode-btn" :class="{ on: palMode === 'custom' }"
                    @click="palMode = 'custom'">我的色板</button>
          </div>
          <div class="color-panel-body">
            <div v-if="paletteGroups.length === 0" class="cp-empty">
              「我的色板」还是空的 —— 退出全屏后在右侧「我的色板」面板添加色号
            </div>
            <div v-for="grp in paletteGroups" :key="grp.key" class="pal-group">
              <div class="pal-group-label">
                <span class="pal-group-key">{{ grp.key }}</span>
                <span>{{ grp.name }}</span>
                <span class="pal-group-n">{{ grp.colors.length }}</span>
              </div>
              <div class="palette-grid">
                <button v-for="c in grp.colors" :key="c.code"
                        class="pal-swatch"
                        :class="{ on: currentCode === c.code, used: usedCodes.has(c.code) }"
                        :style="{ background: c.hex }"
                        :title="`${c.code} ${c.name}`"
                        @click="selectColor(c.code)"></button>
              </div>
            </div>
          </div>
        </div>
      </div>
      </Teleport>

      <!-- Side column -->
      <div class="side-col">
        <!-- Palette — grouped by A/B/C… series, scrollable -->
        <div class="card side-card">
          <div class="side-head">
            调色板 · {{ palMode === 'custom' ? '我的色板' : TIER_LABELS[tier] }}
            <span class="side-count">{{ workingPalette.length }} 色</span>
          </div>
          <div class="palette-scroll">
            <div v-for="grp in paletteGroups" :key="grp.key" class="pal-group">
              <div class="pal-group-label">
                <span class="pal-group-key">{{ grp.key }}</span>
                <span>{{ grp.name }}</span>
                <span class="pal-group-n">{{ grp.colors.length }}</span>
              </div>
              <div class="palette-grid">
                <button v-for="c in grp.colors" :key="c.code"
                        class="pal-swatch"
                        :class="{ on: currentCode === c.code, used: usedCodes.has(c.code) }"
                        :style="{ background: c.hex }"
                        :title="`${c.code} ${c.name}`"
                        @click="selectColor(c.code)"></button>
              </div>
            </div>
          </div>
        </div>

        <!-- My palette management -->
        <div class="card side-card my-pal-card">
          <div class="side-head">
            我的色板
            <span class="side-count">{{ myPaletteCodes.length }} 色</span>
          </div>
          <div class="my-pal-mode">
            <button class="mode-btn" :class="{ on: palMode === 'tier' }" @click="palMode = 'tier'">套装模式</button>
            <button class="mode-btn" :class="{ on: palMode === 'custom' }" @click="palMode = 'custom'">自定义模式</button>
          </div>
          <button class="btn btn-primary btn-sm my-pal-pick-btn" @click="showPalettePicker = true">
            🎨 打开色卡选择
          </button>
          <div class="my-pal-add">
            <input class="input my-pal-input" v-model="myPaletteInput"
                   placeholder="或输入色号，如 A4"
                   @keydown.enter="addToMyPalette" />
            <button class="btn btn-sm btn-ghost" @click="addToMyPalette">添加</button>
          </div>
          <div class="my-pal-actions">
            <button class="btn btn-ghost btn-xs" @click="importFromUsed" title="把当前图纸用到的色号全导入">从图纸导入</button>
            <button class="btn btn-ghost btn-xs" @click="clearMyPalette" :disabled="myPaletteCodes.length === 0">清空</button>
          </div>
          <div v-if="myPaletteCodes.length === 0" class="side-empty">
            尚未添加色号，点击上方「打开色卡选择」挑选颜色
          </div>
          <div v-else class="my-pal-grid">
            <button v-for="code in myPaletteCodes" :key="code"
                    class="my-pal-chip"
                    :style="{ background: MARD_COLORS[code]?.hex || '#ccc',
                              color: textOn(MARD_COLORS[code]?.rgb || [200,200,200]) }"
                    :title="`${code} ${MARD_COLORS[code]?.name || ''} — 点击移除`"
                    @click="removeFromMyPalette(code)">
              <span class="chip-code">{{ code }}</span>
              <span class="chip-x">✕</span>
            </button>
          </div>
        </div>

        <!-- Color usage list -->
        <div class="card side-card">
          <div class="side-head">
            颜色用量
            <span class="side-count">{{ colorList.length }} 色 / {{ totalBeads }} 颗</span>
          </div>
          <div v-if="colorList.length === 0" class="side-empty">图纸还是空的</div>
          <div v-else class="color-list">
            <div v-for="row in colorList" :key="row.code" class="color-row"
                 @click="selectColor(row.code)">
              <span class="cl-swatch" :style="{ background: row.hex }"></span>
              <span class="cl-code mono">{{ row.code }}</span>
              <span class="cl-name">{{ row.name }}</span>
              <span class="cl-count mono">{{ row.count }}</span>
            </div>
          </div>
        </div>

        <!-- Gap analysis — missing colors + their 平替 substitute -->
        <div class="card side-card">
          <div class="side-head">MARD 套装缺色对比</div>
          <div class="side-sub">缺色 → 该套装内的平替色（按「{{ matchDesc }}」）</div>
          <div v-for="g in gapRows" :key="g.tier" class="gap-block">
            <div class="gap-head">
              <span class="gap-tier">{{ g.label }}</span>
              <span class="gap-stat" :class="{ ok: g.gaps.length === 0 }">
                {{ g.gaps.length === 0 ? '✓ 全部覆盖' : `缺 ${g.gaps.length} 色` }}
              </span>
            </div>
            <div v-if="g.gaps.length" class="gap-pairs">
              <div v-for="p in g.gaps" :key="p.color.code" class="gap-pair"
                   :title="`缺 ${p.color.code} ${p.color.name} → 平替 ${p.sub.code} ${p.sub.name}`">
                <span class="gap-swatch miss" :style="{ background: p.color.hex }"></span>
                <span class="gap-arrow">→</span>
                <span class="gap-swatch" :style="{ background: p.sub.hex }"></span>
                <span class="gap-sub-code mono">{{ p.sub.code }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Export Dialog (teleported above the fullscreen canvas in fullscreen mode) -->
  <Teleport to="#app" :disabled="!fullscreen">
  <BeadExportDialog v-if="showExportDialog && grid"
    :grid="grid!" :bead-shape="beadShape" :total-beads="totalBeads"
    :mard-colors="MARD_COLORS"
    :preview="exportPreview" :preview-plain="exportPreviewPlain"
    @close="showExportDialog = false"
    @export="handleExport" />
  </Teleport>

  <!-- Shop Dialog -->
  <Teleport to="#app" :disabled="!fullscreen">
  <BeadShopDialog v-if="showShopDialog && grid"
    :color-counts="colorCounts" :mard-colors="MARD_COLORS"
    @close="showShopDialog = false" />
  </Teleport>

  <!-- Inventory Dialog -->
  <Teleport to="#app" :disabled="!fullscreen">
  <BeadInventoryDialog v-if="showInventoryDialog"
    @close="showInventoryDialog = false" />
  </Teleport>

  <!-- Auth Dialog (login/signup) -->
  <Teleport to="#app" :disabled="!fullscreen">
  <AuthDialog v-if="showAuthDialog"
    @close="showAuthDialog = false" />
  </Teleport>

  <!-- Custom palette picker -->
  <BeadPalettePicker v-if="showPalettePicker"
    :codes="myPaletteCodes"
    @apply="onPaletteApply"
    @close="showPalettePicker = false" />

  <!-- Image-crop dialog -->
  <Teleport to="#app" :disabled="!fullscreen">
  <BeadImageCropDialog v-if="showCropDialog && sourcePreview"
    :src="sourcePreview"
    @close="showCropDialog = false"
    @apply="onCropApply" />
  </Teleport>

  <!-- Canvas-resize dialog -->
  <Teleport to="#app" :disabled="!fullscreen">
  <div v-if="showResizeDialog && grid" class="resize-overlay"
       @click.self="showResizeDialog = false">
    <div class="resize-modal card">
      <div class="resize-head">
        <span class="resize-title">📐 调整画布大小</span>
        <button class="resize-x" @click="showResizeDialog = false">✕</button>
      </div>
      <div class="resize-body">
        <div class="resize-cur">当前画布：{{ grid!.width }} × {{ grid!.height }} 颗豆</div>
        <div class="resize-fields">
          <label>宽
            <input type="number" min="1" max="400" v-model.number="resizeW" class="input" />
          </label>
          <span class="resize-x-sign">×</span>
          <label>高
            <input type="number" min="1" max="400" v-model.number="resizeH" class="input" />
          </label>
          <span class="resize-unit">颗豆</span>
        </div>
        <div class="resize-anchor-label">图案锚点 · 原图案放在新画布的哪个位置</div>
        <div class="resize-anchor">
          <button v-for="i in 9" :key="i" type="button"
                  class="anchor-cell" :class="{ on: resizeAnchor === i - 1 }"
                  @click="resizeAnchor = i - 1"></button>
        </div>
        <div class="resize-note">
          图案比例保持不变：放大时多出的格子留空，缩小时超出的部分会被裁掉。
        </div>
      </div>
      <div class="resize-foot">
        <button class="btn btn-ghost" @click="showResizeDialog = false">取消</button>
        <button class="btn btn-primary" @click="applyResize">应用</button>
      </div>
    </div>
  </div>
  </Teleport>
</template>

<script lang="ts">
// explicit name so <keep-alive :include="['BeadStudio']"> matches this view
export default { name: 'BeadStudio' }
</script>

<script setup lang="ts">
import { ref, computed, shallowRef, onBeforeUnmount, onActivated, onDeactivated, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  MARD_COLORS, MARD_TIERS, TIER_LABELS, TIER_ORDER, MARD_GROUPS,
  type Tier, type BeadColor,
} from '../data/mardPalettes'
import {
  imageToGrid, countColors, paletteGaps, substituteFor, textOn,
  ALGO_OPTIONS, MATCH_OPTIONS, type PerlerGrid, type ConvertAlgo, type MatchMetric,
} from '../composables/usePerler'
import BeadTabs from '../components/BeadTabs.vue'
import BeadExportDialog from '../components/BeadExportDialog.vue'
import BeadShopDialog from '../components/BeadShopDialog.vue'
import BeadInventoryDialog from '../components/BeadInventoryDialog.vue'
import BeadPalettePicker from '../components/BeadPalettePicker.vue'
import BeadImageCropDialog from '../components/BeadImageCropDialog.vue'
import { useInventory } from '../composables/useInventory'
import { useGallery } from '../composables/useGallery'
import { useAuth } from '../composables/useAuth'
import { useHeartTrail } from '../composables/useHeartTrail'
import AuthDialog from '../components/AuthDialog.vue'

type Tool = 'paint' | 'erase' | 'wand' | 'wanderase' | 'replace' | 'pick' | 'pan' | 'mirror'
          | 'select' | 'line' | 'rect' | 'ellipse'
type BeadShape = 'circle' | 'square' | 'fill'

// ---- state ----
const fileInput = ref<HTMLInputElement | null>(null)
const projInput = ref<HTMLInputElement | null>(null)   // .beadproj project file
const wrapRef = ref<HTMLDivElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)

const sourceImg = shallowRef<HTMLImageElement | null>(null)
const sourcePreview = ref('')
const isDragging = ref(false)
const showConvSettings = ref(false)   // collapsible advanced conversion settings
const showCropDialog = ref(false)     // PS-style source-image crop dialog

// ---- canvas-resize dialog (resize without scaling the pattern) ----
const showResizeDialog = ref(false)
const resizeW = ref(0)
const resizeH = ref(0)
const resizeAnchor = ref(4)           // 0-8, row-major 3x3 grid; 4 = center

const gridWidth = ref(56)
const blankHeight = ref(56)                // height for "new blank canvas"
const tier = ref<Tier>('264')
const algo = ref<ConvertAlgo>('smooth')
const matchMetric = ref<MatchMetric>('lab')
const colorLimit = ref(0)       // cap on distinct colors in the result; 0 = unlimited
const showLabels = ref(false)   // show MARD codes on every bead (canvas + export)
const beadShape = ref<BeadShape>('fill')
const beadSize = ref(2.6)                 // physical bead diameter, mm

// --- configurable grid / reference lines (one solid layer + one dashed) ---
interface GridLayer {
  enabled: boolean
  step: number    // every N cells
  color: string   // CSS colour
  width: number   // line width in px
}
const GRID_STORAGE_KEY = 'bead-grid-lines-v1'
function loadGridConfig(): { solid: GridLayer; dashed: GridLayer } {
  try {
    const raw = localStorage.getItem(GRID_STORAGE_KEY)
    if (raw) {
      const v = JSON.parse(raw)
      if (v?.solid && v?.dashed) return v
    }
  } catch { /* malformed — fall through */ }
  return {
    solid:  { enabled: true, step: 10, color: '#e8462a', width: 1.6 },
    dashed: { enabled: true, step: 5,  color: '#7c5cff', width: 1   },
  }
}
const gridConfig = ref(loadGridConfig())
const showGridMenu = ref(false)
watch(gridConfig, (v) => {
  try { localStorage.setItem(GRID_STORAGE_KEY, JSON.stringify(v)) } catch {}
  render()
}, { deep: true })

/** Normalise any CSS-colour string down to a #RRGGBB the <input type="color">
 *  control can accept (it doesn't accept rgba / named colours). */
function hexOf(c: string): string {
  if (!c) return '#000000'
  const t = c.trim()
  if (/^#[0-9a-f]{6}$/i.test(t)) return t.toLowerCase()
  if (/^#[0-9a-f]{3}$/i.test(t)) {
    return ('#' + t.slice(1).split('').map(ch => ch + ch).join('')).toLowerCase()
  }
  const m = t.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i)
  if (m) {
    const h = (n: number) => n.toString(16).padStart(2, '0')
    return ('#' + h(+m[1]) + h(+m[2]) + h(+m[3])).toLowerCase()
  }
  return '#000000'
}
function resetGridConfig() {
  gridConfig.value = {
    solid:  { enabled: true, step: 10, color: '#e8462a', width: 1.6 },
    dashed: { enabled: true, step: 5,  color: '#7c5cff', width: 1   },
  }
}
// close grid popover on click-outside
watch(showGridMenu, (open) => {
  if (!open) return
  const onDocClick = (ev: MouseEvent) => {
    const target = ev.target as HTMLElement | null
    if (target && target.closest('.gl-group')) return
    showGridMenu.value = false
  }
  setTimeout(() => document.addEventListener('click', onDocClick, { once: true }), 0)
})
const brushSize = ref(1)                  // paint brush diameter in cells (Shift+wheel)
const eraserSize = ref(1)                 // eraser diameter in cells (Shift+wheel)

// ---- custom palette (persisted to localStorage) ----
const palMode = ref<'tier' | 'custom'>('tier')
const myPaletteCodes = ref<string[]>(
  JSON.parse(localStorage.getItem('bead-my-palette') || '[]'),
)
const myPaletteInput = ref('')

const grid = shallowRef<PerlerGrid | null>(null)
const gridVersion = ref(0)
const converting = ref(false)

// reference image overlay
const refImage = shallowRef<HTMLImageElement | null>(null)
const refPreview = ref('')
const refOpacity = ref(0.35)
const refLocked = ref(false)
const showRefSection = ref(false)
const refFileInput = ref<HTMLInputElement | null>(null)

// dialogs
const showExportDialog = ref(false)
const showShopDialog = ref(false)
const showInventoryDialog = ref(false)
const finishConfirm = ref(false)
let finishConfirmTimer: number | null = null
const inventory = useInventory()
const gallery = useGallery()
const auth = useAuth()
const showAuthDialog = ref(false)

/**
 * "此作品已拼完" — two-click confirm to avoid accidental inventory edits.
 * First click flips the button to "确认扣库存？"; second click within 5s deducts.
 */
function onFinishProject() {
  if (!grid.value) { ElMessage.warning('画布是空的，没什么可以扣的~'); return }
  if (totalBeads.value === 0) { ElMessage.warning('当前画布没画上任何豆子'); return }
  if (!finishConfirm.value) {
    finishConfirm.value = true
    if (finishConfirmTimer != null) clearTimeout(finishConfirmTimer)
    finishConfirmTimer = window.setTimeout(() => { finishConfirm.value = false; finishConfirmTimer = null }, 5000)
    return
  }
  // confirmed — do the deduction
  finishConfirm.value = false
  if (finishConfirmTimer != null) { clearTimeout(finishConfirmTimer); finishConfirmTimer = null }
  const result = inventory.deductByCounts(colorCounts.value)
  ElMessage.success(`已从库存中扣减 ${result.totalDeducted} 颗豆子`)
  if (result.insufficient.length > 0) {
    const list = result.insufficient.slice(0, 4)
      .map(i => `${i.code}(差${i.needed - i.had})`).join('、')
    ElMessage.warning(
      `这些色号实际库存不够：${list}${result.insufficient.length > 4 ? ` 等 ${result.insufficient.length} 色` : ''}`
    )
  }
  if (result.lowStock.length > 0) {
    const list = result.lowStock.slice(0, 5)
      .map(l => `${l.code}(剩${l.remaining})`).join('、')
    ElMessage({
      type: 'warning',
      duration: 3000,
      message: `⚠ 库存补货提醒：${list}${result.lowStock.length > 5 ? ` 等 ${result.lowStock.length} 色` : ''} 已低于 ${inventory.state.value.threshold} 颗`,
    })
  }
}

/**
 * "➕ 入库" — add the canvas's current colour counts into inventory. Inverse of
 * "完工"; mainly serves as a one-click safety net to undo an accidental
 * deduction (re-import puts the exact same amounts back).
 */
function onImportCanvasToInventory() {
  if (!grid.value) { ElMessage.warning('画布是空的，没什么可以入库的~'); return }
  const counts = colorCounts.value
  if (counts.size === 0) { ElMessage.warning('当前画布没画上任何豆子'); return }
  let total = 0
  for (const [code, n] of counts) {
    inventory.setCount(code, inventory.getCount(code) + n)
    total += n
  }
  ElMessage.success(
    `已把画布的 ${counts.size} 个色号 · 共 ${total.toLocaleString()} 颗豆子加入库存`,
  )
}

/**
 * "🎨 发布" — render the current canvas as a labelled-pattern PNG and store
 * the work in the local gallery (localStorage). Prompts for a title first;
 * the PNG always shows colour-code labels so the gallery image is usable as
 * a printable / shareable pattern even if the live canvas had labels off.
 */
async function onPublishToGallery() {
  if (!grid.value) { ElMessage.warning('画布是空的~'); return }
  if (totalBeads.value === 0) { ElMessage.warning('画布上还没画任何豆子'); return }
  // Require sign-in for remote-mode gallery (Supabase backed)
  if (gallery.REMOTE_ENABLED && !auth.user.value) {
    ElMessage({
      type: 'warning',
      duration: 4000,
      showClose: true,
      dangerouslyUseHTMLString: true,
      message: '发布到画廊需要先登录 · <a href="#" id="open-auth-now" style="color:#e84a85;font-weight:700;margin-left:6px">点这里登录/注册 →</a>',
    })
    // wire the link inside the toast (next tick)
    setTimeout(() => {
      const a = document.getElementById('open-auth-now')
      if (a) a.onclick = (e) => { e.preventDefault(); showAuthDialog.value = true }
    }, 50)
    return
  }
  // ask for a title
  let title = ''
  try {
    const r = await ElMessageBox.prompt('给作品起个名字（也可以不写）', '发布到画廊', {
      confirmButtonText: '发布', cancelButtonText: '取消',
      inputPlaceholder: '比如：粉色草莓',
      inputValue: `拼豆图 ${grid.value.width}×${grid.value.height}`,
      inputValidator: (v: string) => v.length <= 40 || '标题最多 40 字',
    })
    title = (r.value || '').trim() || `拼豆图 ${grid.value.width}×${grid.value.height}`
  } catch { return /* cancelled */ }

  // Render a clean pattern — no colour-code labels, no grid lines, no ruler,
  // and empty cells stay transparent. Force showLabels off regardless of the
  // user's UI setting; pass withGrid=false + transparentEmpty=true.
  const prevLabels = showLabels.value
  showLabels.value = false
  let fullCv: HTMLCanvasElement
  try {
    fullCv = buildPatternCanvas(24, false, true)   // 24 px/cell, beads only, transparent bg
  } finally {
    showLabels.value = prevLabels
  }
  // Cap the long edge at 1800 px — typical patterns stay near-native; very
  // wide ones downscale to keep upload size sensible.
  const maxDim = 1800
  const longEdge = Math.max(fullCv.width, fullCv.height)
  let outCv: HTMLCanvasElement
  if (longEdge <= maxDim) {
    outCv = fullCv
  } else {
    const scale = maxDim / longEdge
    outCv = document.createElement('canvas')
    outCv.width = Math.max(1, Math.round(fullCv.width * scale))
    outCv.height = Math.max(1, Math.round(fullCv.height * scale))
    const tctx = outCv.getContext('2d')!
    // intentionally NO white fill — preserve alpha when downscaling
    tctx.imageSmoothingEnabled = true
    tctx.imageSmoothingQuality = 'high'
    tctx.drawImage(fullCv, 0, 0, outCv.width, outCv.height)
  }
  // PNG keeps the alpha channel so transparent cells stay transparent;
  // JPEG would have to flatten them onto a background. Bead patterns have
  // few distinct colours so PNG compresses very well even at full size.
  const dataUrl = outCv.toDataURL('image/png')

  // upload to the gallery (Supabase if configured, else local localStorage)
  const uploading = ElMessage({
    type: 'info', duration: 0, showClose: false, message: '🎨 上传中…',
  })
  let entry: Awaited<ReturnType<typeof gallery.publish>>
  try {
    entry = await gallery.publish({
      title,
      width: grid.value.width,
      height: grid.value.height,
      totalBeads: totalBeads.value,
      uniqueColors: colorCounts.value.size,
      beadShape: beadShape.value,
      thumbnailDataUrl: dataUrl,
    })
  } catch (e: any) {
    uploading.close()
    ElMessage.error(`发布失败：${e?.message || e}`)
    return
  } finally {
    uploading.close()
  }

  ElMessage({
    type: 'success',
    duration: 4000,
    showClose: true,
    dangerouslyUseHTMLString: true,
    message: `🎉 已发布「${entry.title}」到画廊 <a href="#/bead-studio/gallery" style="color:#e84a85;font-weight:700;margin-left:6px">去看看 →</a>`,
  })
}
const showPalettePicker = ref(false)
const exportPreview = ref('')        // export-dialog preview — with grid lines
const exportPreviewPlain = ref('')   // export-dialog preview — without grid lines

// ---- undo / redo history ----
interface GridSnap { width: number; height: number; cells: (string | null)[] }
const undoStack: GridSnap[] = []
const redoStack: GridSnap[] = []
const histVer = ref(0)
const canUndo = computed(() => { void histVer.value; return undoStack.length > 0 })
const canRedo = computed(() => { void histVer.value; return redoStack.length > 0 })

const algoDesc = computed(() =>
  ALGO_OPTIONS.find(a => a.id === algo.value)?.desc || '',
)
const matchDesc = computed(() =>
  MATCH_OPTIONS.find(m => m.id === matchMetric.value)?.desc || '',
)

const tool = ref<Tool>('paint')
const currentCode = ref('')

// ---- highlight mode -------------------------------------------------------
// "row" / "col": single row/col (arrow keys to navigate).
// "color":       every cell whose code matches currentCode.
// "rect":        a configurable W×H rectangle (arrow keys move it, the W/H
//                inputs in the toolbar resize it).
type HighlightMode = 'none' | 'row' | 'col' | 'color' | 'rect'
const highlightMode = ref<HighlightMode>('none')
const highlightRow = ref(0)
const highlightCol = ref(0)
const highlightRect = ref<{ x: number; y: number; w: number; h: number }>({
  x: 0, y: 0, w: 8, h: 8,
})
const showHighlightMenu = ref(false)
/** Pure canvas mode — chrome (toolbars, palette, ruler chrome) hidden so the
 *  grid + dim overlay fill the entire viewport. Active whenever any highlight
 *  mode is on, since the toolbar status chip is hidden too. */
const immersive = computed(() => highlightMode.value !== 'none')

// chip-internal colour picker (only used in colour-highlight mode)
const showColorPickerInChip = ref(false)
// close the picker when leaving immersive / colour mode
watch([immersive, highlightMode], () => { showColorPickerInChip.value = false })

/** Colours currently used on the canvas — what the chip's picker offers, so
 *  the user is only choosing among codes that actually appear in their work
 *  (and the highlight will always have at least one matching bead).
 *  Sorted by usage so the most common code comes first. */
const usedColorsForPicker = computed(() => {
  const counts = colorCounts.value
  return [...counts.entries()]
    .map(([code, n]) => ({ code, count: n, hex: MARD_COLORS[code]?.hex || '#000', name: MARD_COLORS[code]?.name || '' }))
    .sort((a, b) => b.count - a.count)
})

/** Pick a readable foreground colour for text drawn on the given bead hex. */
function chipTextOn(hex: string): string {
  if (!hex || hex.length < 7) return '#000'
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return (r * 299 + g * 587 + b * 114) / 1000 > 145 ? '#000' : '#fff'
}
function chipBorderOn(hex: string): string {
  // pale colours need a darker border so the chip reads on the cream backdrop
  return chipTextOn(hex) === '#000' ? '#c87b1f' : '#ffd76b'
}

// --- draggable immersive status chip ----------------------------------------
// `chipPos` is null until the user moves the chip; while null the CSS default
// (top-centre) applies. After the first drag the chip stays where the user
// dropped it for the rest of the immersive session.
const chipPos = ref<{ x: number; y: number } | null>(null)
const chipStyle = computed(() => {
  if (!chipPos.value) return {}
  return {
    left: chipPos.value.x + 'px',
    top: chipPos.value.y + 'px',
    transform: 'none',   // override the default `translateX(-50%)` centering
  }
})
let chipDragOffset: { dx: number; dy: number } | null = null

function startChipDrag(e: MouseEvent) {
  // Don't start a drag when the click landed on an interactive control —
  // the buttons / inputs need their own clicks/focus to work.
  const t = e.target as HTMLElement | null
  if (t && t.closest('button, input, select, textarea, a')) return
  const el = e.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  // remember pointer offset within the chip so dragging doesn't jump
  chipDragOffset = { dx: e.clientX - rect.left, dy: e.clientY - rect.top }
  document.addEventListener('mousemove', onChipDragMove)
  document.addEventListener('mouseup', onChipDragEnd)
  e.preventDefault()
}
function onChipDragMove(e: MouseEvent) {
  if (!chipDragOffset) return
  // clamp inside the viewport, leaving some padding so the chip stays grabbable
  const w = window.innerWidth, h = window.innerHeight
  const pad = 8
  const x = Math.max(pad, Math.min(w - 60 - pad, e.clientX - chipDragOffset.dx))
  const y = Math.max(pad, Math.min(h - 30 - pad, e.clientY - chipDragOffset.dy))
  chipPos.value = { x, y }
}
function onChipDragEnd() {
  chipDragOffset = null
  document.removeEventListener('mousemove', onChipDragMove)
  document.removeEventListener('mouseup', onChipDragEnd)
}

// Reset chip position when leaving immersive so the next entry starts centred.
watch(immersive, (now) => {
  if (!now) chipPos.value = null
})

const HIGHLIGHT_LABELS: Record<HighlightMode, string> = {
  none: '关闭', row: '行', col: '列', color: '色号', rect: '矩形',
}
const HIGHLIGHT_OPTIONS = [
  { id: 'none' as const,  icon: '⊘', label: '关闭高亮' },
  { id: 'row' as const,   icon: '▤', label: '高亮某一行（↑↓ 切换）' },
  { id: 'col' as const,   icon: '▥', label: '高亮某一列（←→ 切换）' },
  { id: 'color' as const, icon: '◉', label: '高亮当前色号' },
  { id: 'rect' as const,  icon: '▢', label: '高亮自定义矩形（↑↓←→ 移动）' },
]

/** Clamp the rect's position/size into the current grid bounds. */
function clampHighlightRect() {
  const g = grid.value
  if (!g) return
  const r = highlightRect.value
  r.w = Math.max(1, Math.min(g.width,  Math.floor(r.w || 1)))
  r.h = Math.max(1, Math.min(g.height, Math.floor(r.h || 1)))
  r.x = Math.max(0, Math.min(g.width  - r.w, r.x))
  r.y = Math.max(0, Math.min(g.height - r.h, r.y))
}

function setHighlightMode(m: HighlightMode) {
  // exit path: clicking "关闭高亮" or the same mode again
  if (m === 'none' || highlightMode.value === m) {
    highlightMode.value = 'none'
    showHighlightMenu.value = false
    render()
    return
  }
  const isFreshEntry = highlightMode.value === 'none'
  highlightMode.value = m
  const g = grid.value
  if (g) {
    if (m === 'row') highlightRow.value = Math.min(highlightRow.value, g.height - 1)
    if (m === 'col') highlightCol.value = Math.min(highlightCol.value, g.width - 1)
    if (m === 'rect') {
      // re-centre the rect when freshly entering rect mode
      const r = highlightRect.value
      if (r.x + r.w > g.width || r.y + r.h > g.height || (r.x === 0 && r.y === 0)) {
        r.w = Math.min(r.w, g.width)
        r.h = Math.min(r.h, g.height)
        r.x = Math.floor((g.width - r.w) / 2)
        r.y = Math.floor((g.height - r.h) / 2)
      }
      clampHighlightRect()
    }
  }
  // On first entry into ANY highlight mode, the immersive CSS class (driven
  // by the `immersive` computed) puts canvas-col full-viewport on its own
  // and hides every bit of chrome. Show a 3 s hint toast with the keybindings.
  if (isFreshEntry) {
    ElMessage({
      type: 'info',
      duration: 3000,
      showClose: true,
      message: `💡 高亮 · ${HIGHLIGHT_LABELS[m]}  ${highlightHintText(m)} · Esc 退出`,
    })
  }
  render()
}

function highlightHintText(m: HighlightMode): string {
  switch (m) {
    case 'row':   return '↑↓ 切换行'
    case 'col':   return '←→ 切换列'
    case 'color': return '在调色板换色即可换高亮色号'
    case 'rect':  return '↑↓←→ 移动矩形 · 工具栏改宽高'
    default:      return ''
  }
}
const zoom = ref(1)
const offset = ref({ x: 28, y: 28 })
const hover = ref<{ x: number; y: number } | null>(null)
const fullscreen = ref(false)   // canvas fills the whole viewport
// "press F for fullscreen" hint — shown whenever a canvas is open and we're not already fullscreen
const showFsTip = computed(() => !!grid.value && !fullscreen.value)

// cursor heart trail — shared composable; keep the canvas wrap heart-free
useHeartTrail({ skipWhenInside: () => wrapRef.value })
const showColorPanel = ref(false)   // floating palette — usable while fullscreen
const colorPanelTop = ref(56)       // panel top offset (below the toolbars)

// SAI / Photoshop-style monochrome glyphs (24×24 viewBox, currentColor).
const tools: { id: Tool; svg: string; label: string; key: string }[] = [
  { id: 'paint', label: '画笔', key: 'B', svg:
    '<path d="M18.37 2.63 14 7l-1.59-1.59a2 2 0 0 0-2.82 0L8 7l9 9 1.59-1.59a2 2 0 0 0 0-2.82L17 10l4.37-4.37a2.12 2.12 0 1 0-3-3Z"/>' +
    '<path d="M9 8c-2 3-4 3.5-7 4l8 10c2-1 6-5 6-7"/>' +
    '<path d="M14.5 17.5 4.5 15"/>' },
  { id: 'erase', label: '橡皮', key: 'E', svg:
    '<path d="m7 21-4.3-4.3c-1-1-1-2.5 0-3.4l9.6-9.6c1-1 2.5-1 3.4 0l5.6 5.6c1 1 1 2.5 0 3.4L13 21"/>' +
    '<path d="M22 21H7"/><path d="m5 11 9 9"/>' },
  { id: 'wand', label: '魔棒画笔', key: 'G', svg:
    '<path d="M3.5 20.5 13 11" stroke-width="2.6"/>' +
    '<path d="M17 2.8 18.5 6.5 22.2 8 18.5 9.5 17 13.2 15.5 9.5 11.8 8 15.5 6.5Z" fill="currentColor" stroke="none"/>' +
    '<circle cx="6.6" cy="6" r="1.1" fill="currentColor" stroke="none"/>' },
  { id: 'wanderase', label: '魔棒橡皮', key: 'D', svg:
    '<path d="M3.5 20.5 14.5 9.5" stroke-width="2.6"/>' +
    '<circle cx="15.8" cy="8.2" r="1.4" fill="currentColor" stroke="none"/>' +
    '<circle cx="17.6" cy="18" r="5.2" fill="currentColor" stroke="none"/>' +
    '<path d="M15 18h5.2" stroke="#fff" stroke-width="2.3"/>' },
  { id: 'replace', label: '同色替换', key: 'R', svg:
    '<path d="M14 4a2 2 0 0 1 2-2"/><path d="M16 10a2 2 0 0 1-2-2"/>' +
    '<path d="M20 2a2 2 0 0 1 2 2"/><path d="M22 8a2 2 0 0 1-2 2"/>' +
    '<path d="m3 7 3 3 3-3"/><path d="M6 10V5a3 3 0 0 1 3-3h1"/>' +
    '<rect x="2.5" y="14" width="8" height="8" rx="2"/>' },
  { id: 'line', label: '直线', key: 'L', svg:
    '<path d="M5 19 19 5"/>' +
    '<circle cx="5" cy="19" r="2.3" fill="currentColor" stroke="none"/>' +
    '<circle cx="19" cy="5" r="2.3" fill="currentColor" stroke="none"/>' },
  { id: 'rect', label: '矩形', key: 'U', svg:
    '<rect x="3.5" y="5.5" width="17" height="13" rx="1"/>' },
  { id: 'ellipse', label: '椭圆 / 圆', key: 'O', svg:
    '<ellipse cx="12" cy="12" rx="9.2" ry="7"/>' },
  { id: 'mirror', label: '镜像复制', key: 'M', svg:
    '<path d="m3 7 5 5-5 5V7"/><path d="m21 7-5 5 5 5V7"/>' +
    '<path d="M12 20v2"/><path d="M12 14v2"/><path d="M12 8v2"/><path d="M12 2v2"/>' },
  { id: 'select', label: '选区移动', key: 'S', svg:
    '<rect x="3.5" y="3.5" width="17" height="17" rx="1" stroke-dasharray="3.2 3"/>' },
  { id: 'pick', label: '取色', key: 'I', svg:
    '<rect x="14" y="2.6" width="7.2" height="7.2" rx="2.2" transform="rotate(45 17.6 6.2)" fill="currentColor" stroke="none"/>' +
    '<path d="M15.6 8.4 3.6 20.4" stroke-width="2.6"/>' },
  { id: 'pan', label: '移动', key: 'H', svg:
    '<path d="M18 11V6a2 2 0 0 0-4 0"/>' +
    '<path d="M14 10V4a2 2 0 0 0-4 0v2"/>' +
    '<path d="M10 10.5V6a2 2 0 0 0-4 0v8"/>' +
    '<path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>' },
]

// ---- shape tools (line / rect / ellipse) ----
const shapeFill = ref(false)            // shape tools: filled vs outline
let shapeDragging = false
let shapeStart: { x: number; y: number } | null = null
let shapeEnd: { x: number; y: number } | null = null
let shapeShift = false                  // Shift held during the current drag
const SHAPE_TOOLS = ['line', 'rect', 'ellipse']
const isShapeTool = (t: Tool) => SHAPE_TOOLS.includes(t)

// ---- rectangular selection (marquee + move) ----
const selection = ref<{ x: number; y: number; w: number; h: number } | null>(null)
let selMode: 'none' | 'create' | 'move' = 'none'
let selAnchor: { x: number; y: number } | null = null    // create-drag start cell
let selMoveStart: { x: number; y: number } | null = null // move-drag start cell (raw)
let selBufOrigin: { x: number; y: number } | null = null // selection pos when lifted
let selBuf: (string | null)[] | null = null              // lifted (floating) cells
let selBufW = 0
let selBufH = 0

// mirror-copy axis configuration
const mirrorAxis = ref<'v' | 'h'>('v')   // vertical or horizontal symmetry line
const mirrorDir = ref<1 | -1>(1)         // v: 1=左→右 -1=右→左 ; h: 1=上→下 -1=下→上

// active brush/eraser size shown in the toolbar
const activeBrushSize = computed(() =>
  tool.value === 'paint' ? brushSize.value : eraserSize.value,
)

const BASE_CELL = 18
const RULER = 26

// ---- derived ----
const estHeight = computed(() => {
  const img = sourceImg.value
  if (!img) return 0
  const ratio = (img.naturalHeight || 1) / (img.naturalWidth || 1)
  return Math.max(1, Math.round(gridWidth.value * ratio))
})
const workingPalette = computed<BeadColor[]>(() => {
  if (palMode.value === 'custom') {
    return myPaletteCodes.value.map(c => MARD_COLORS[c]).filter(Boolean)
  }
  return MARD_TIERS[tier.value].map(c => MARD_COLORS[c]).filter(Boolean)
})
// Palette grouped by A/B/C… series for the scrollable picker.
const paletteGroups = computed(() => {
  const byKey = new Map<string, BeadColor[]>()
  for (const c of workingPalette.value) {
    const k = c.code.match(/^[A-Z]+/)?.[0] || c.code
    if (!byKey.has(k)) byKey.set(k, [])
    byKey.get(k)!.push(c)
  }
  return MARD_GROUPS
    .map(g => ({ key: g.key, name: g.name, colors: byKey.get(g.key) || [] }))
    .filter(g => g.colors.length > 0)
})
const curColorHex = computed(() => MARD_COLORS[currentCode.value]?.hex || '#ffffff')

// Physical finished dimensions from bead diameter (mm → cm).
const finishedSize = computed(() => {
  const g = grid.value
  if (!g) return ''
  const w = (g.width * beadSize.value / 10)
  const h = (g.height * beadSize.value / 10)
  return `${w.toFixed(1)} × ${h.toFixed(1)} cm`
})

const colorCounts = computed(() => {
  gridVersion.value  // dependency
  return grid.value ? countColors(grid.value) : new Map<string, number>()
})
const usedCodes = computed(() => new Set(colorCounts.value.keys()))
const totalBeads = computed(() => {
  let n = 0
  for (const v of colorCounts.value.values()) n += v
  return n
})
const colorList = computed(() => {
  return [...colorCounts.value.entries()]
    .map(([code, count]) => ({
      code, count,
      name: MARD_COLORS[code]?.name || code,
      hex: MARD_COLORS[code]?.hex || '#ccc',
    }))
    .sort((a, b) => b.count - a.count)
})
const gapRows = computed(() => {
  const used = usedCodes.value
  return (['72', '96', '216', '264'] as Tier[]).map(t => {
    const tierPal = MARD_TIERS[t].map(c => MARD_COLORS[c]).filter(Boolean)
    // each missing color paired with its 平替 (substitute) in this kit
    const gaps = paletteGaps(used, MARD_TIERS[t]).map(color => ({
      color,
      sub: substituteFor(color, tierPal, matchMetric.value),
    }))
    return { tier: t, label: TIER_LABELS[t], gaps }
  })
})

// ---- hover tooltip ----
const hoverTip = computed(() => {
  if (!hover.value || !grid.value) return ''
  const { x, y } = hover.value
  const code = grid.value.cells[y * grid.value.width + x]
  if (!code) return `(${x + 1}, ${y + 1}) 空`
  const c = MARD_COLORS[code]
  return `(${x + 1}, ${y + 1}) ${code} ${c?.name || ''}`
})
const hoverTipStyle = ref<Record<string, string>>({})

// ---- file loading ----
function pickFile() { fileInput.value?.click() }
function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) loadFile(f)
}
function onDrop(e: DragEvent) {
  isDragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) loadFile(f)
}
function loadFile(file: File) {
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    const img = new Image()
    img.onload = () => {
      sourceImg.value = img
      sourcePreview.value = String(reader.result)
      // 拖入 / 选择图片后立即转换成拼豆图纸（无论当前是空白画布还是已有图纸）
      convert(true)
    }
    img.onerror = () => ElMessage.error('图片解码失败')
    img.src = String(reader.result)
  }
  reader.readAsDataURL(file)
}

// ---- project file (.beadproj) ----
function pickProjectFile() { projInput.value?.click() }
function onProjectFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (f) openProjectFile(f)
  input.value = ''   // allow re-opening the same file
}
function onProjectDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f) openProjectFile(f)
}

// ---- image crop (PS-style) ----
function onCropApply(payload: { dataUrl: string }) {
  showCropDialog.value = false
  const img = new Image()
  img.onload = () => {
    sourceImg.value = img
    sourcePreview.value = payload.dataUrl
    convert(true)   // re-convert from the cropped image
  }
  img.onerror = () => ElMessage.error('裁剪结果加载失败')
  img.src = payload.dataUrl
}

/** Save the whole editable state as a .beadproj (JSON) project file. */
function saveProject() {
  const g = grid.value
  if (!g) { ElMessage.info('画布还是空的，没有可保存的工程'); return }
  const proj = {
    format: 'bead-studio-project',
    version: 1,
    savedAt: new Date().toISOString(),
    grid: { width: g.width, height: g.height, cells: g.cells },
    beadShape: beadShape.value,
    beadSize: beadSize.value,
    showLabels: showLabels.value,
    tier: tier.value,
    palMode: palMode.value,
    myPalette: myPaletteCodes.value,
    algo: algo.value,
    matchMetric: matchMetric.value,
    colorLimit: colorLimit.value,
    currentCode: currentCode.value,
    gridWidth: gridWidth.value,
    blankHeight: blankHeight.value,
    source: sourcePreview.value || null,   // keeps width / algorithm re-convert working
  }
  const blob = new Blob([JSON.stringify(proj)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.download = `拼豆工程_${g.width}x${g.height}.beadproj`
  a.href = url
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('工程已保存')
}

/** Load a .beadproj file and restore the full editable state. */
function openProjectFile(file: File) {
  const reader = new FileReader()
  reader.onload = () => {
    let proj: any
    try { proj = JSON.parse(String(reader.result)) }
    catch { ElMessage.error('工程文件无法解析'); return }
    if (!proj || proj.format !== 'bead-studio-project' || !proj.grid) {
      ElMessage.error('这不是有效的拼豆工程文件')
      return
    }
    const pg = proj.grid
    if (typeof pg.width !== 'number' || typeof pg.height !== 'number'
        || !Array.isArray(pg.cells) || pg.cells.length !== pg.width * pg.height) {
      ElMessage.error('工程文件的画布数据已损坏')
      return
    }
    // restore settings — suppressReconv blocks the watch from re-converting
    suppressReconv = true
    if (['circle', 'square', 'fill'].includes(proj.beadShape)) beadShape.value = proj.beadShape
    if ([2.6, 3, 5].includes(proj.beadSize)) beadSize.value = proj.beadSize
    if (typeof proj.showLabels === 'boolean') showLabels.value = proj.showLabels
    if (proj.tier && TIER_ORDER.includes(proj.tier)) tier.value = proj.tier
    if (proj.palMode === 'tier' || proj.palMode === 'custom') palMode.value = proj.palMode
    if (Array.isArray(proj.myPalette)) myPaletteCodes.value = proj.myPalette
    if (proj.algo && ALGO_OPTIONS.some(a => a.id === proj.algo)) algo.value = proj.algo
    if (proj.matchMetric && MATCH_OPTIONS.some(m => m.id === proj.matchMetric)) {
      matchMetric.value = proj.matchMetric
    }
    if (typeof proj.colorLimit === 'number') colorLimit.value = proj.colorLimit
    if (typeof proj.blankHeight === 'number') blankHeight.value = proj.blankHeight
    gridWidth.value = pg.width
    // restore the grid
    grid.value = { width: pg.width, height: pg.height, cells: pg.cells.slice() }
    gridVersion.value++
    undoStack.length = 0
    redoStack.length = 0
    histVer.value++
    // restore the source image so width / algorithm re-convert still works
    if (typeof proj.source === 'string' && proj.source) {
      const img = new Image()
      img.onload = () => { sourceImg.value = img }
      img.src = proj.source
      sourcePreview.value = proj.source
    } else {
      sourceImg.value = null
      sourcePreview.value = ''
    }
    // pick a valid current paint color
    if (proj.currentCode && MARD_COLORS[proj.currentCode]) {
      currentCode.value = proj.currentCode
    } else {
      const first = [...countColors(grid.value).entries()].sort((a, b) => b[1] - a[1])[0]
      currentCode.value = first?.[0] || workingPalette.value[0]?.code || ''
    }
    nextTick(() => {
      suppressReconv = false
      syncCanvasSize()
      fitView()
    })
    ElMessage.success('工程已载入，可继续编辑')
  }
  reader.onerror = () => ElMessage.error('工程文件读取失败')
  reader.readAsText(file)
}

// ---- reference image ----
function onRefFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) loadRefFile(f)
}
function onRefDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f) loadRefFile(f)
}
function loadRefFile(file: File) {
  if (!file.type.startsWith('image/')) return
  const reader = new FileReader()
  reader.onload = () => {
    const img = new Image()
    img.onload = () => {
      refImage.value = img
      refPreview.value = String(reader.result)
      render()
    }
    img.src = String(reader.result)
  }
  reader.readAsDataURL(file)
}
function removeRef() {
  if (refLocked.value) return
  refImage.value = null
  refPreview.value = ''
  render()
}

// Reduce the grid to at most `n` distinct colors: keep the n most-used,
// remap every other color to its nearest kept color (by the 平替 metric).
function limitColors(g: PerlerGrid, n: number) {
  if (n <= 0) return
  const counts = countColors(g)
  if (counts.size <= n) return
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1])
  const kept = sorted.slice(0, n).map(e => e[0])
  const keptColors = kept.map(c => MARD_COLORS[c]).filter(Boolean)
  if (keptColors.length === 0) return
  const keptSet = new Set(kept)
  const remap = new Map<string, string>()
  for (const [code] of counts) {
    if (keptSet.has(code)) continue
    const col = MARD_COLORS[code]
    if (col) remap.set(code, substituteFor(col, keptColors, matchMetric.value).code)
  }
  for (let i = 0; i < g.cells.length; i++) {
    const c = g.cells[i]
    if (c) { const r = remap.get(c); if (r) g.cells[i] = r }
  }
}

// ---- conversion ----
async function convert(refit = true) {
  if (!sourceImg.value) return
  if (workingPalette.value.length === 0) {
    if (refit) ElMessage.warning('当前色板为空，请先添加颜色或切换到套装色板')
    return
  }
  // A live re-convert (width / algorithm / palette tweak) snapshots the
  // current grid so Ctrl+Z returns to the previous setting.
  // A button conversion (refit) starts fresh, discarding edit history.
  if (!refit && grid.value) pushHistory()
  converting.value = true
  await nextTick()
  try {
    grid.value = imageToGrid(
      sourceImg.value, gridWidth.value, workingPalette.value,
      algo.value, matchMetric.value,
    )
    // 限制颜色数量：保留最常用的 N 色，其余就近平替
    if (colorLimit.value > 0) limitColors(grid.value, colorLimit.value)
    gridVersion.value++
    // 「像素图智能修正」尺寸由检测决定 —— 把宽度滑块同步过去
    syncWidthFromGrid()
    if (refit) {
      // a fresh conversion from the button invalidates the edit history
      undoStack.length = 0
      redoStack.length = 0
    }
    histVer.value++
    // default paint color = most-used color
    const first = [...countColors(grid.value).entries()].sort((a, b) => b[1] - a[1])[0]
    if (!currentCode.value || !workingPalette.value.some(c => c.code === currentCode.value)) {
      currentCode.value = first?.[0] || workingPalette.value[0]?.code || ''
    }
    await nextTick()
    syncCanvasSize()
    if (refit) fitView()
    else render()
  } catch (e: any) {
    ElMessage.error('转换失败：' + (e?.message || e))
  } finally {
    converting.value = false
  }
}

// ---- new blank canvas (draw from scratch, no image) ----
function newBlankGrid() {
  if (workingPalette.value.length === 0) {
    ElMessage.warning('当前色板为空，请先切换到套装色板或添加颜色')
    return
  }
  const w = Math.max(8, Math.min(220, Math.round(gridWidth.value)))
  const h = Math.max(8, Math.min(220, Math.round(blankHeight.value)))
  sourceImg.value = null
  sourcePreview.value = ''
  grid.value = { width: w, height: h, cells: new Array(w * h).fill(null) }
  gridVersion.value++
  undoStack.length = 0
  redoStack.length = 0
  histVer.value++
  if (!currentCode.value || !workingPalette.value.some(c => c.code === currentCode.value)) {
    currentCode.value = workingPalette.value[0]?.code || ''
  }
  tool.value = 'paint'
  nextTick(() => { syncCanvasSize(); fitView() })
}

/** Nearest-neighbour resample of the current grid to a new size. */
function resampleGrid(newW: number, newH: number) {
  const g = grid.value
  if (!g) return
  newW = Math.max(1, Math.round(newW))
  newH = Math.max(1, Math.round(newH))
  if (newW === g.width && newH === g.height) return
  const cells: (string | null)[] = new Array(newW * newH)
  for (let y = 0; y < newH; y++) {
    const sy = Math.min(g.height - 1, Math.floor(y * g.height / newH))
    for (let x = 0; x < newW; x++) {
      const sx = Math.min(g.width - 1, Math.floor(x * g.width / newW))
      cells[y * newW + x] = g.cells[sy * g.width + sx]
    }
  }
  grid.value = { width: newW, height: newH, cells }
  gridVersion.value++
}

// Tweaking width / algorithm / palette re-converts from the source image
// (debounced, undoable — convert() snapshots the previous grid first).
// For a blank / hand-drawn canvas (no source image) a width change instead
// resizes the current grid by resampling it.
// `suppressReconv` blocks the watch while undo/redo syncs the width slider.
let suppressReconv = false
let reconvTimer: number | undefined
watch([gridWidth, algo, tier, matchMetric, palMode, myPaletteCodes, colorLimit], (nv, ov) => {
  if (suppressReconv || !grid.value || transforming.value) return
  if (reconvTimer) clearTimeout(reconvTimer)
  const widthChanged = nv[0] !== ov[0]
  // anything other than the width — algorithm / palette / colour-limit …
  const otherChanged = nv[1] !== ov[1] || nv[2] !== ov[2] || nv[3] !== ov[3]
                    || nv[4] !== ov[4] || nv[5] !== ov[5] || nv[6] !== ov[6]
  // resample the current grid to the new width (keeps the pattern, nearest-neighbour)
  const doResample = () => {
    const g = grid.value
    if (!g) return
    const nw = Math.max(1, Math.round(gridWidth.value))
    if (nw === g.width) return
    pushHistory()
    resampleGrid(nw, Math.max(1, Math.round(nw * g.height / g.width)))
    render()
  }
  if (sourceImg.value) {
    // pixelfit auto-detects the size — a width-only tweak just resamples the
    // detected grid; anything else re-converts from the source image
    if (algo.value === 'pixelfit' && widthChanged && !otherChanged) {
      reconvTimer = window.setTimeout(doResample, 240)
    } else {
      reconvTimer = window.setTimeout(() => convert(false), 240)
    }
  } else if (nv[6] !== ov[6] && colorLimit.value > 0) {
    // no source image → colour-limit reduces the current grid in place
    reconvTimer = window.setTimeout(() => {
      if (!grid.value) return
      pushHistory()
      limitColors(grid.value, colorLimit.value)
      gridVersion.value++
      render()
    }, 240)
  } else if (widthChanged) {
    // blank / hand-drawn canvas → width change resamples the grid
    reconvTimer = window.setTimeout(doResample, 240)
  }
})

// Persist custom palette to localStorage
watch(myPaletteCodes, (codes) => {
  localStorage.setItem('bead-my-palette', JSON.stringify(codes))
}, { deep: true })

function selectColor(code: string) {
  currentCode.value = code
  if (tool.value === 'erase' || tool.value === 'pan' || tool.value === 'mirror') {
    tool.value = 'paint'
  }
}

// Floating palette — lets the side-panel colors be picked while fullscreen.
function toggleColorPanel() {
  showColorPanel.value = !showColorPanel.value
  if (showColorPanel.value) {
    nextTick(() => { colorPanelTop.value = wrapRef.value?.offsetTop ?? 56 })
  }
}

// ---- custom palette management ----
function addToMyPalette() {
  const code = myPaletteInput.value.trim().toUpperCase()
  if (!code) return
  if (!MARD_COLORS[code]) {
    ElMessage.warning(`色号 ${code} 不在 MARD 色卡中`)
    return
  }
  if (myPaletteCodes.value.includes(code)) {
    ElMessage.info(`${code} 已在色板中`)
    return
  }
  myPaletteCodes.value = [...myPaletteCodes.value, code]
  myPaletteInput.value = ''
}
function removeFromMyPalette(code: string) {
  myPaletteCodes.value = myPaletteCodes.value.filter(c => c !== code)
}
function clearMyPalette() {
  myPaletteCodes.value = []
}
function importFromUsed() {
  if (!grid.value) { ElMessage.info('请先生成图纸'); return }
  const existing = new Set(myPaletteCodes.value)
  const newCodes = [...usedCodes.value].filter(c => !existing.has(c))
  if (newCodes.length === 0) { ElMessage.info('当前图纸的颜色已全在色板中'); return }
  myPaletteCodes.value = [...myPaletteCodes.value, ...newCodes]
  ElMessage.success(`已从图纸导入 ${newCodes.length} 个色号`)
}
function onPaletteApply(codes: string[]) {
  myPaletteCodes.value = codes
  ElMessage.success(`我的色板已更新：${codes.length} 色`)
}

// ---- canvas sizing ----
function syncCanvasSize() {
  const cv = canvasRef.value, wrap = wrapRef.value
  if (!cv || !wrap) return
  const dpr = window.devicePixelRatio || 1
  const w = wrap.clientWidth, h = wrap.clientHeight
  cv.width = Math.round(w * dpr)
  cv.height = Math.round(h * dpr)
  cv.style.width = w + 'px'
  cv.style.height = h + 'px'
  const ctx = cv.getContext('2d')!
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  render()
}

function fitView() {
  const g = grid.value, wrap = wrapRef.value
  if (!g || !wrap) return
  const availW = wrap.clientWidth - RULER - 24
  const availH = wrap.clientHeight - RULER - 24
  const z = Math.min(availW / (g.width * BASE_CELL), availH / (g.height * BASE_CELL))
  zoom.value = Math.max(0.15, Math.min(z, 4))
  const cell = BASE_CELL * zoom.value
  offset.value = {
    x: Math.max(8, (wrap.clientWidth - RULER - g.width * cell) / 2),
    y: Math.max(8, (wrap.clientHeight - RULER - g.height * cell) / 2),
  }
  render()
}

function zoomBy(dir: number) {
  const wrap = wrapRef.value
  if (!wrap) return
  zoomAt(wrap.clientWidth / 2, wrap.clientHeight / 2, dir > 0 ? 1.25 : 1 / 1.25)
}
function zoomAt(cx: number, cy: number, factor: number) {
  const oldZoom = zoom.value
  const newZoom = Math.max(0.15, Math.min(oldZoom * factor, 8))
  if (newZoom === oldZoom) return
  // keep the grid point under the cursor stable
  const gx = (cx - RULER - offset.value.x) / (BASE_CELL * oldZoom)
  const gy = (cy - RULER - offset.value.y) / (BASE_CELL * oldZoom)
  zoom.value = newZoom
  offset.value = {
    x: cx - RULER - gx * BASE_CELL * newZoom,
    y: cy - RULER - gy * BASE_CELL * newZoom,
  }
  render()
}
function onWheel(e: WheelEvent) {
  const d = e.deltaY !== 0 ? e.deltaY : e.deltaX
  // Shift + wheel adjusts brush / eraser size
  if (e.shiftKey && (tool.value === 'paint' || tool.value === 'erase')) {
    const step = d < 0 ? 1 : -1
    const size = tool.value === 'paint' ? brushSize : eraserSize
    size.value = Math.min(20, Math.max(1, size.value + step))
    render()
    return
  }
  const rect = wrapRef.value!.getBoundingClientRect()
  zoomAt(e.clientX - rect.left, e.clientY - rect.top, d < 0 ? 1.15 : 1 / 1.15)
}

// ---- pointer → cell ----
function cellAt(e: MouseEvent): { x: number; y: number } | null {
  const g = grid.value, wrap = wrapRef.value
  if (!g || !wrap) return null
  const rect = wrap.getBoundingClientRect()
  const cell = BASE_CELL * zoom.value
  const x = Math.floor((e.clientX - rect.left - RULER - offset.value.x) / cell)
  const y = Math.floor((e.clientY - rect.top - RULER - offset.value.y) / cell)
  if (x < 0 || y < 0 || x >= g.width || y >= g.height) return null
  return { x, y }
}

/** Pointer → cell coordinate, unclamped (may be negative / beyond the grid). */
function cellAtRaw(e: MouseEvent): { x: number; y: number } {
  const rect = wrapRef.value!.getBoundingClientRect()
  const cell = BASE_CELL * zoom.value
  return {
    x: Math.floor((e.clientX - rect.left - RULER - offset.value.x) / cell),
    y: Math.floor((e.clientY - rect.top - RULER - offset.value.y) / cell),
  }
}

// ---- undo / redo ----
function snapGrid(): GridSnap {
  const g = grid.value!
  return { width: g.width, height: g.height, cells: g.cells.slice() }
}
function pushHistory() {
  if (!grid.value) return
  undoStack.push(snapGrid())
  if (undoStack.length > 60) undoStack.shift()
  redoStack.length = 0
  histVer.value++
}
// keep the width slider in sync with a restored snapshot, without the
// change re-triggering an image re-conversion
function syncWidthFromGrid() {
  const g = grid.value
  if (g && gridWidth.value !== g.width) {
    suppressReconv = true
    gridWidth.value = g.width
    nextTick(() => { suppressReconv = false })
  }
}
function undo() {
  if (!grid.value || !undoStack.length) return
  redoStack.push(snapGrid())
  grid.value = undoStack.pop()!
  syncWidthFromGrid()
  gridVersion.value++
  histVer.value++
  nextTick(() => { syncCanvasSize(); render() })
}
function redo() {
  if (!grid.value || !redoStack.length) return
  undoStack.push(snapGrid())
  grid.value = redoStack.pop()!
  syncWidthFromGrid()
  gridVersion.value++
  histVer.value++
  nextTick(() => { syncCanvasSize(); render() })
}

// ---- flip / rotate ----
function flipH() {
  const g = grid.value
  if (!g) return
  pushHistory()
  const w = g.width, h = g.height
  const n = g.cells.slice()
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++)
      n[y * w + (w - 1 - x)] = g.cells[y * w + x]
  grid.value = { ...g, cells: n }
  gridVersion.value++
  render()
}
function flipV() {
  const g = grid.value
  if (!g) return
  pushHistory()
  const w = g.width, h = g.height
  const n = g.cells.slice()
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++)
      n[(h - 1 - y) * w + x] = g.cells[y * w + x]
  grid.value = { ...g, cells: n }
  gridVersion.value++
  render()
}

// ---- one-click outline ----
// Wrap the drawn shape in a 1-cell border of the currently-selected color:
// every empty cell touching a filled cell (8-neighbourhood) becomes outline.
function outlineShape() {
  const g = grid.value
  if (!g) return
  if (!currentCode.value) {
    ElMessage.warning('请先在右侧调色板选择描边颜色')
    return
  }
  const w = g.width, h = g.height
  const mark: number[] = []
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const idx = y * w + x
      if (g.cells[idx] !== null) continue        // only empty cells become outline
      let adj = false
      for (let dy = -1; dy <= 1 && !adj; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          if (!dx && !dy) continue
          const nx = x + dx, ny = y + dy
          if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue
          if (g.cells[ny * w + nx] !== null) { adj = true; break }
        }
      }
      if (adj) mark.push(idx)
    }
  }
  if (!mark.length) {
    ElMessage.info('没有可描边的边缘（图纸为空或已填满）')
    return
  }
  pushHistory()
  for (const idx of mark) g.cells[idx] = currentCode.value
  gridVersion.value++
  render()
  ElMessage.success(`已描边 ${mark.length} 颗豆`)
}

// ---- one-click background removal ----
// Flood-fill inward from all four edges, clearing cells whose color is close
// to the dominant border color. Identifies the subject by what's left.
// Works best on photos / stickers with a relatively uniform background.
/**
 * Detect edge-connected background cells: flood-fill inward from the four
 * borders, collecting cells whose color is close to the dominant border
 * color. Returns the indices of background cells (the rest = the subject).
 */
function detectBackgroundCells(g: PerlerGrid): number[] {
  const w = g.width, h = g.height
  // dominant border code = the background color
  const borderCount = new Map<string, number>()
  const tally = (code: string | null) => {
    if (code) borderCount.set(code, (borderCount.get(code) || 0) + 1)
  }
  for (let x = 0; x < w; x++) { tally(g.cells[x]); tally(g.cells[(h - 1) * w + x]) }
  for (let y = 0; y < h; y++) { tally(g.cells[y * w]); tally(g.cells[y * w + w - 1]) }
  let bgCode = '', bgN = 0
  for (const [code, n] of borderCount) if (n > bgN) { bgN = n; bgCode = code }
  const bg = bgCode ? MARD_COLORS[bgCode] : null
  if (!bg) return []
  // a cell is "background" if its color is close enough to the border color
  const TOL = 11000   // ≈ 60 / channel, sum of squared RGB difference
  const isBg = (i: number): boolean => {
    const code = g.cells[i]
    if (!code) return false
    const c = MARD_COLORS[code]
    if (!c) return false
    const dr = c.rgb[0] - bg.rgb[0], dgr = c.rgb[1] - bg.rgb[1], db = c.rgb[2] - bg.rgb[2]
    return dr * dr + dgr * dgr + db * db <= TOL
  }
  // flood inward from every border cell — only edge-connected background goes
  const visited = new Uint8Array(w * h)
  const stack: number[] = []
  const seed = (i: number) => { if (!visited[i]) { visited[i] = 1; stack.push(i) } }
  for (let x = 0; x < w; x++) { seed(x); seed((h - 1) * w + x) }
  for (let y = 0; y < h; y++) { seed(y * w); seed(y * w + w - 1) }
  const removed: number[] = []
  while (stack.length) {
    const i = stack.pop()!
    if (!isBg(i)) continue
    removed.push(i)
    const x = i % w, y = (i / w) | 0
    if (x + 1 < w) seed(i + 1)
    if (x - 1 >= 0) seed(i - 1)
    if (y + 1 < h) seed(i + w)
    if (y - 1 >= 0) seed(i - w)
  }
  return removed
}

function removeBackground() {
  const g = grid.value
  if (!g) return
  const removed = detectBackgroundCells(g)
  if (!removed.length) { ElMessage.info('未检测到可去除的背景'); return }
  pushHistory()
  for (const i of removed) g.cells[i] = null
  gridVersion.value++
  render()
  ElMessage.success(`已去除背景 ${removed.length} 颗豆`)
}

// ---- free transform (PS-style Ctrl+T) ----
interface XBox { cx: number; cy: number; halfW: number; halfH: number; angle: number }
const transforming = ref(false)
const xbox = ref<XBox>({ cx: 0, cy: 0, halfW: 0, halfH: 0, angle: 0 })
let xW0 = 0, xH0 = 0                              // original grid dimensions
let xCanvas: HTMLCanvasElement | null = null      // 1px-per-cell content snapshot
let xDrag: {
  mode: 'scale' | 'rotate' | 'move'
  handle: number
  anchor: { x: number; y: number }
  anchorLocal: { x: number; y: number }
  start: XBox
  startMouse: { x: number; y: number }
  startPointerAngle: number
} | null = null

const OPP_HANDLE = [2, 3, 0, 1, 6, 7, 4, 5]   // opposite scale handle

const xformScalePct = computed(() => {
  if (!xW0) return 100
  const sx = (xbox.value.halfW * 2) / xW0
  const sy = (xbox.value.halfH * 2) / xH0
  return Math.round((sx + sy) / 2 * 100)
})
const xformAngleDeg = computed(() => {
  const d = Math.round(xbox.value.angle * 180 / Math.PI)
  return ((d % 360) + 360) % 360
})

/** continuous cell-space coordinate of a pointer event */
function clientToCell(e: MouseEvent): { x: number; y: number } {
  const rect = wrapRef.value!.getBoundingClientRect()
  const cellPx = BASE_CELL * zoom.value
  return {
    x: (e.clientX - rect.left - RULER - offset.value.x) / cellPx,
    y: (e.clientY - rect.top - RULER - offset.value.y) / cellPx,
  }
}
/** local (pre-rotation) offset of scale-handle i from the box center */
function handleLocal(i: number, b: XBox): { x: number; y: number } {
  return {
    x: (i === 0 || i === 3 || i === 7) ? -b.halfW
     : (i === 1 || i === 2 || i === 5) ?  b.halfW : 0,
    y: (i === 0 || i === 1 || i === 4) ? -b.halfH
     : (i === 2 || i === 3 || i === 6) ?  b.halfH : 0,
  }
}
/** world (cell-space) position of scale-handle i (0-3 corners, 4-7 edges) */
function handleWorld(i: number, b: XBox): { x: number; y: number } {
  const l = handleLocal(i, b)
  const c = Math.cos(b.angle), s = Math.sin(b.angle)
  return { x: b.cx + l.x * c - l.y * s, y: b.cy + l.x * s + l.y * c }
}
/** world position of the rotation handle (floats above the top edge) */
function rotHandleWorld(b: XBox): { x: number; y: number } {
  const d = b.halfH + Math.max(1.4, 26 / (BASE_CELL * zoom.value))
  return { x: b.cx + d * Math.sin(b.angle), y: b.cy - d * Math.cos(b.angle) }
}
/** is a cell-space point inside the rotated box? */
function pointInXBox(p: { x: number; y: number }, b: XBox): boolean {
  const dx = p.x - b.cx, dy = p.y - b.cy
  const c = Math.cos(-b.angle), s = Math.sin(-b.angle)
  return Math.abs(dx * c - dy * s) <= b.halfW
      && Math.abs(dx * s + dy * c) <= b.halfH
}

function startTransform() {
  const g = grid.value
  if (!g || transforming.value) return
  clearSelection()
  xW0 = g.width; xH0 = g.height
  xbox.value = {
    cx: g.width / 2, cy: g.height / 2,
    halfW: g.width / 2, halfH: g.height / 2, angle: 0,
  }
  // 1px-per-cell offscreen snapshot of the current beads
  const cv = document.createElement('canvas')
  cv.width = g.width; cv.height = g.height
  const c = cv.getContext('2d')!
  for (let y = 0; y < g.height; y++) {
    for (let x = 0; x < g.width; x++) {
      const code = g.cells[y * g.width + x]
      if (!code) continue
      c.fillStyle = MARD_COLORS[code]?.hex || '#000'
      c.fillRect(x, y, 1, 1)
    }
  }
  xCanvas = cv
  xDrag = null
  hover.value = null
  transforming.value = true
  render()
}
function cancelTransform() {
  transforming.value = false
  xCanvas = null
  xDrag = null
  render()
}
function applyTransform() {
  const g = grid.value
  if (!g || !transforming.value) return
  const b = xbox.value
  // axis-aligned bounding box of the transformed quad (cell space)
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (let i = 0; i < 4; i++) {
    const p = handleWorld(i, b)
    minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x)
    minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y)
  }
  const newW = Math.max(1, Math.min(400, Math.round(maxX - minX)))
  const newH = Math.max(1, Math.min(400, Math.round(maxY - minY)))
  const sx = (b.halfW * 2) / xW0 || 1e-6
  const sy = (b.halfH * 2) / xH0 || 1e-6
  const c = Math.cos(-b.angle), s = Math.sin(-b.angle)
  const cells: (string | null)[] = new Array(newW * newH).fill(null)
  for (let ny = 0; ny < newH; ny++) {
    for (let nx = 0; nx < newW; nx++) {
      const wx = minX + nx + 0.5 - b.cx
      const wy = minY + ny + 0.5 - b.cy
      const bx = wx * c - wy * s        // inverse-rotate
      const by = wx * s + wy * c
      const gx = Math.floor(bx / sx + xW0 / 2)
      const gy = Math.floor(by / sy + xH0 / 2)
      if (gx >= 0 && gx < xW0 && gy >= 0 && gy < xH0) {
        cells[ny * newW + nx] = g.cells[gy * xW0 + gx]
      }
    }
  }
  pushHistory()
  grid.value = { width: newW, height: newH, cells }
  gridVersion.value++
  transforming.value = false
  xCanvas = null
  xDrag = null
  nextTick(() => { syncCanvasSize(); fitView() })
}

function transformOnDown(e: MouseEvent) {
  const m = clientToCell(e)
  const b = xbox.value
  const thr = 12 / (BASE_CELL * zoom.value)   // hit radius, cell units
  // rotation handle
  const rh = rotHandleWorld(b)
  if (Math.hypot(m.x - rh.x, m.y - rh.y) <= thr) {
    xDrag = { mode: 'rotate', handle: -1, start: { ...b }, startMouse: m,
              anchor: { x: b.cx, y: b.cy }, anchorLocal: { x: 0, y: 0 },
              startPointerAngle: Math.atan2(m.y - b.cy, m.x - b.cx) }
    return
  }
  // 8 scale handles
  for (let i = 0; i < 8; i++) {
    const hp = handleWorld(i, b)
    if (Math.hypot(m.x - hp.x, m.y - hp.y) <= thr) {
      const opp = OPP_HANDLE[i]
      xDrag = { mode: 'scale', handle: i, start: { ...b }, startMouse: m,
                anchor: handleWorld(opp, b), anchorLocal: handleLocal(opp, b),
                startPointerAngle: 0 }
      return
    }
  }
  // inside the box → move
  if (pointInXBox(m, b)) {
    xDrag = { mode: 'move', handle: -1, start: { ...b }, startMouse: m,
              anchor: { x: 0, y: 0 }, anchorLocal: { x: 0, y: 0 }, startPointerAngle: 0 }
  }
}
function transformOnMove(e: MouseEvent) {
  if (!xDrag) return
  const m = clientToCell(e)
  const b0 = xDrag.start
  if (xDrag.mode === 'move') {
    xbox.value = { ...b0,
      cx: b0.cx + (m.x - xDrag.startMouse.x),
      cy: b0.cy + (m.y - xDrag.startMouse.y) }
  } else if (xDrag.mode === 'rotate') {
    const ang = Math.atan2(m.y - b0.cy, m.x - b0.cx)
    xbox.value = { ...b0, angle: b0.angle + (ang - xDrag.startPointerAngle) }
  } else {
    // opposite-anchor scaling (rotation stays fixed)
    const a = b0.angle
    const ux = Math.cos(a), uy = Math.sin(a)
    const vx = -Math.sin(a), vy = Math.cos(a)
    const dx = m.x - xDrag.anchor.x, dy = m.y - xDrag.anchor.y
    const du = dx * ux + dy * uy
    const dv = dx * vx + dy * vy
    const i = xDrag.handle
    const xActive = i <= 3 || i === 5 || i === 7
    const yActive = i <= 3 || i === 4 || i === 6
    let halfW = xActive ? Math.max(0.5, Math.abs(du) / 2) : b0.halfW
    let halfH = yActive ? Math.max(0.5, Math.abs(dv) / 2) : b0.halfH
    // Shift on a corner handle → uniform (proportional) scaling
    if (e.shiftKey && i <= 3 && b0.halfW > 1e-4 && b0.halfH > 1e-4) {
      const s = Math.max(halfW / b0.halfW, halfH / b0.halfH)
      halfW = b0.halfW * s
      halfH = b0.halfH * s
    }
    const uComp = xActive ? (du >= 0 ? halfW : -halfW) : -xDrag.anchorLocal.x
    const vComp = yActive ? (dv >= 0 ? halfH : -halfH) : -xDrag.anchorLocal.y
    xbox.value = {
      cx: xDrag.anchor.x + uComp * ux + vComp * vx,
      cy: xDrag.anchor.y + uComp * uy + vComp * vy,
      halfW, halfH, angle: a,
    }
  }
  render()
}

function drawTransformPreview(ctx: CanvasRenderingContext2D,
                              cell: number, ox: number, oy: number) {
  if (!xCanvas) return
  const b = xbox.value
  ctx.save()
  ctx.translate(ox + b.cx * cell, oy + b.cy * cell)
  ctx.rotate(b.angle)
  const sw = b.halfW * 2 * cell, sh = b.halfH * 2 * cell
  ctx.imageSmoothingEnabled = false
  ctx.drawImage(xCanvas, -sw / 2, -sh / 2, sw, sh)
  ctx.restore()
}
function drawTransformBox(ctx: CanvasRenderingContext2D,
                          cell: number, ox: number, oy: number) {
  const b = xbox.value
  const toScreen = (p: { x: number; y: number }) =>
    ({ x: ox + p.x * cell, y: oy + p.y * cell })
  const corners = [0, 1, 2, 3].map(i => toScreen(handleWorld(i, b)))
  ctx.strokeStyle = '#7c5cff'
  ctx.lineWidth = 1.8
  ctx.beginPath()
  ctx.moveTo(corners[0].x, corners[0].y)
  for (let i = 1; i < 4; i++) ctx.lineTo(corners[i].x, corners[i].y)
  ctx.closePath()
  ctx.stroke()
  // rotation handle stem + knob
  const top = toScreen(handleWorld(4, b))
  const rh = toScreen(rotHandleWorld(b))
  ctx.beginPath()
  ctx.moveTo(top.x, top.y); ctx.lineTo(rh.x, rh.y)
  ctx.stroke()
  ctx.fillStyle = '#fff'
  ctx.beginPath(); ctx.arc(rh.x, rh.y, 6, 0, Math.PI * 2); ctx.fill(); ctx.stroke()
  // 8 scale handles
  for (let i = 0; i < 8; i++) {
    const hp = toScreen(handleWorld(i, b))
    ctx.fillStyle = '#fff'
    ctx.fillRect(hp.x - 5, hp.y - 5, 10, 10)
    ctx.strokeRect(hp.x - 5, hp.y - 5, 10, 10)
  }
}

/** Draw the floating (lifted) selection content while it is being moved. */
function drawSelFloat(ctx: CanvasRenderingContext2D,
                      cell: number, ox: number, oy: number) {
  const s = selection.value
  if (!s || !selBuf) return
  for (let dy = 0; dy < selBufH; dy++) {
    for (let dx = 0; dx < selBufW; dx++) {
      const code = selBuf[dy * selBufW + dx]
      if (!code) continue
      drawBead(ctx, ox + (s.x + dx) * cell, oy + (s.y + dy) * cell, cell,
               MARD_COLORS[code]?.hex || '#000', beadShape.value, '#fdf6f0')
    }
  }
}

/** Draw the selection marquee rectangle + a size badge. */
function drawMarquee(ctx: CanvasRenderingContext2D,
                     cell: number, ox: number, oy: number) {
  const s = selection.value
  if (!s) return
  const rx = ox + s.x * cell, ry = oy + s.y * cell
  const rw = s.w * cell, rh = s.h * cell
  ctx.save()
  ctx.fillStyle = 'rgba(124,92,255,0.10)'
  ctx.fillRect(rx, ry, rw, rh)
  // two-tone dashed border ("marching ants" look)
  ctx.lineWidth = 1.6
  ctx.setLineDash([5, 3])
  ctx.strokeStyle = '#ffffff'
  ctx.lineDashOffset = 0
  ctx.strokeRect(rx, ry, rw, rh)
  ctx.strokeStyle = '#7c5cff'
  ctx.lineDashOffset = 4
  ctx.strokeRect(rx, ry, rw, rh)
  ctx.restore()
  // size badge inside the top-left corner
  ctx.save()
  ctx.font = 'bold 11px "JetBrains Mono", monospace'
  const tag = `${s.w}×${s.h}`
  const tw = ctx.measureText(tag).width + 12
  ctx.fillStyle = 'rgba(124,92,255,0.92)'
  ctx.fillRect(rx + 1, ry + 1, tw, 15)
  ctx.fillStyle = '#fff'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText(tag, rx + 7, ry + 9)
  ctx.restore()
}

// ---- editing / interaction ----
let painting = false
let panning = false
let panStart = { x: 0, y: 0, ox: 0, oy: 0 }

/** Stamp a circular brush of diameter `size` centered on (cx, cy). */
function stampBlock(g: PerlerGrid, cx: number, cy: number,
                    size: number, value: string | null) {
  const lo = -Math.floor((size - 1) / 2)
  const hi = Math.floor(size / 2)
  const cen = (lo + hi) / 2            // circle center offset within the span
  const r2 = (size / 2) * (size / 2)
  for (let dy = lo; dy <= hi; dy++) {
    for (let dx = lo; dx <= hi; dx++) {
      const ddx = dx - cen, ddy = dy - cen
      if (ddx * ddx + ddy * ddy > r2) continue   // outside the brush circle
      const ex = cx + dx, ey = cy + dy
      if (ex >= 0 && ex < g.width && ey >= 0 && ey < g.height) {
        g.cells[ey * g.width + ex] = value
      }
    }
  }
}

/** Mirror-copy one half of the grid onto the other across a line. */
function mirrorCopy(cell: { x: number; y: number }) {
  const g = grid.value
  if (!g) return
  pushHistory()
  const w = g.width, h = g.height
  const n = g.cells.slice()
  if (mirrorAxis.value === 'v') {
    // axis = column cell.x ; copy one side onto the other
    const ax = cell.x
    for (let k = 1; ax - k >= 0 || ax + k < w; k++) {
      const left = ax - k, right = ax + k
      if (left < 0 || right >= w) continue
      for (let y = 0; y < h; y++) {
        if (mirrorDir.value === 1) n[y * w + right] = g.cells[y * w + left]
        else                      n[y * w + left]  = g.cells[y * w + right]
      }
    }
  } else {
    // axis = row cell.y
    const ax = cell.y
    for (let k = 1; ax - k >= 0 || ax + k < h; k++) {
      const top = ax - k, bot = ax + k
      if (top < 0 || bot >= h) continue
      for (let x = 0; x < w; x++) {
        if (mirrorDir.value === 1) n[bot * w + x] = g.cells[top * w + x]
        else                      n[top * w + x] = g.cells[bot * w + x]
      }
    }
  }
  grid.value = { ...g, cells: n }
  gridVersion.value++
  render()
}

/** Flood-fill the contiguous same-value region starting at (sx, sy). */
function floodFill(g: PerlerGrid, sx: number, sy: number,
                   target: string | null, repl: string | null) {
  if (target === repl) return
  const w = g.width, h = g.height
  const stack = [sy * w + sx]
  while (stack.length) {
    const i = stack.pop()!
    if (g.cells[i] !== target) continue
    g.cells[i] = repl
    const x = i % w, y = (i / w) | 0
    if (x + 1 < w) stack.push(i + 1)
    if (x - 1 >= 0) stack.push(i - 1)
    if (y + 1 < h) stack.push(i + w)
    if (y - 1 >= 0) stack.push(i - w)
  }
}

function applyTool(cell: { x: number; y: number }) {
  const g = grid.value
  if (!g) return
  const idx = cell.y * g.width + cell.x
  if (tool.value === 'paint') {
    if (!currentCode.value) return
    stampBlock(g, cell.x, cell.y, brushSize.value, currentCode.value)
    gridVersion.value++
    render()
  } else if (tool.value === 'erase') {
    stampBlock(g, cell.x, cell.y, eraserSize.value, null)
    gridVersion.value++
    render()
  } else if (tool.value === 'wand') {
    // 魔棒画笔：把点击处相连的同色区域整片填成当前色
    if (!currentCode.value) return
    const target = g.cells[idx]
    if (target === currentCode.value) return
    floodFill(g, cell.x, cell.y, target, currentCode.value)
    gridVersion.value++
    render()
  } else if (tool.value === 'wanderase') {
    // 魔棒橡皮：把点击处相连的同色区域整片擦除
    const target = g.cells[idx]
    if (target === null) return
    floodFill(g, cell.x, cell.y, target, null)
    gridVersion.value++
    render()
  } else if (tool.value === 'replace') {
    // 同色替换：把整张图里该颜色全部换成当前色
    if (!currentCode.value) return
    const target = g.cells[idx]
    if (target === currentCode.value) return
    for (let i = 0; i < g.cells.length; i++) {
      if (g.cells[i] === target) g.cells[i] = currentCode.value
    }
    gridVersion.value++
    render()
  } else if (tool.value === 'mirror') {
    mirrorCopy(cell)
  } else if (tool.value === 'pick') {
    const code = g.cells[idx]
    if (code) { currentCode.value = code; tool.value = 'paint' }
  }
}

// ---- rectangular selection tool ----
/** Is cell (x, y) inside the current selection rectangle? */
function inSelection(x: number, y: number): boolean {
  const s = selection.value
  return !!s && x >= s.x && x < s.x + s.w && y >= s.y && y < s.y + s.h
}

/** Reset all selection state (does not repaint — callers render). */
function clearSelection() {
  if (selMode === 'move') commitSelMove()   // don't lose an in-progress move
  selection.value = null
  selMode = 'none'
  selAnchor = null
  selMoveStart = null
  selBuf = null
  selBufOrigin = null
}

function selectOnDown(e: MouseEvent) {
  const g = grid.value
  if (!g) return
  const raw = cellAtRaw(e)
  const cx = Math.max(0, Math.min(g.width - 1, raw.x))
  const cy = Math.max(0, Math.min(g.height - 1, raw.y))
  hover.value = null
  if (selection.value && inSelection(cx, cy)) {
    // press inside an existing selection → lift its cells to move them
    const s = selection.value
    selBufW = s.w
    selBufH = s.h
    selBuf = new Array(s.w * s.h)
    for (let dy = 0; dy < s.h; dy++) {
      for (let dx = 0; dx < s.w; dx++) {
        const gx = s.x + dx, gy = s.y + dy
        selBuf[dy * s.w + dx] =
          (gx >= 0 && gx < g.width && gy >= 0 && gy < g.height)
            ? g.cells[gy * g.width + gx] : null
      }
    }
    selBufOrigin = { x: s.x, y: s.y }
    selMoveStart = { x: raw.x, y: raw.y }
    selMode = 'move'
  } else {
    // press elsewhere → start a fresh marquee
    selAnchor = { x: cx, y: cy }
    selection.value = { x: cx, y: cy, w: 1, h: 1 }
    selBuf = null
    selMode = 'create'
  }
  render()
}

function selectOnMove(e: MouseEvent) {
  const g = grid.value
  if (!g) return
  const raw = cellAtRaw(e)
  if (selMode === 'create' && selAnchor) {
    const cx = Math.max(0, Math.min(g.width - 1, raw.x))
    const cy = Math.max(0, Math.min(g.height - 1, raw.y))
    selection.value = {
      x: Math.min(selAnchor.x, cx),
      y: Math.min(selAnchor.y, cy),
      w: Math.abs(cx - selAnchor.x) + 1,
      h: Math.abs(cy - selAnchor.y) + 1,
    }
    render()
  } else if (selMode === 'move' && selMoveStart && selBufOrigin) {
    selection.value = {
      x: selBufOrigin.x + (raw.x - selMoveStart.x),
      y: selBufOrigin.y + (raw.y - selMoveStart.y),
      w: selBufW, h: selBufH,
    }
    render()
  }
}

/** Stamp the lifted region into the grid at its new position. */
function commitSelMove() {
  const g = grid.value, s = selection.value
  if (!g || !s || !selBuf || !selBufOrigin) return
  if (s.x !== selBufOrigin.x || s.y !== selBufOrigin.y) {
    pushHistory()
    // clear the cells the region was lifted from
    for (let dy = 0; dy < selBufH; dy++) {
      for (let dx = 0; dx < selBufW; dx++) {
        const ox = selBufOrigin.x + dx, oy = selBufOrigin.y + dy
        if (ox >= 0 && ox < g.width && oy >= 0 && oy < g.height)
          g.cells[oy * g.width + ox] = null
      }
    }
    // drop the lifted block at the new position
    for (let dy = 0; dy < selBufH; dy++) {
      for (let dx = 0; dx < selBufW; dx++) {
        const nx = s.x + dx, ny = s.y + dy
        if (nx >= 0 && nx < g.width && ny >= 0 && ny < g.height)
          g.cells[ny * g.width + nx] = selBuf[dy * selBufW + dx] ?? null
      }
    }
    gridVersion.value++
  }
  selBuf = null
  selBufOrigin = null
  selMoveStart = null
}

/** Finish a select-tool drag (mouseup / leave). */
function finishSelDrag() {
  if (selMode === 'create') {
    // a 1×1 marquee from a plain click acts as "deselect"
    if (selection.value && selection.value.w === 1 && selection.value.h === 1)
      selection.value = null
  } else if (selMode === 'move') {
    commitSelMove()
  }
  selMode = 'none'
  selAnchor = null
  render()
}

/** Clear the beads inside the current selection. */
function deleteSelection() {
  const g = grid.value, s = selection.value
  if (!g || !s) return
  pushHistory()
  for (let dy = 0; dy < s.h; dy++) {
    for (let dx = 0; dx < s.w; dx++) {
      const x = s.x + dx, y = s.y + dy
      if (x >= 0 && x < g.width && y >= 0 && y < g.height)
        g.cells[y * g.width + x] = null
    }
  }
  gridVersion.value++
  render()
}

/** Crop the grid down to the current selection rectangle (region outside is discarded). */
function cropToSelection() {
  const g = grid.value, s = selection.value
  if (!g) return
  if (!s) { ElMessage.info('请先用「选区」工具框选要保留的范围'); return }
  // clamp the selection to the grid
  const x0 = Math.max(0, s.x), y0 = Math.max(0, s.y)
  const x1 = Math.min(g.width, s.x + s.w), y1 = Math.min(g.height, s.y + s.h)
  const nw = x1 - x0, nh = y1 - y0
  if (nw < 1 || nh < 1) { ElMessage.warning('选区不在画布范围内'); return }
  if (nw === g.width && nh === g.height) { ElMessage.info('选区已是整张画布，无需裁剪'); return }
  pushHistory()
  const cells: (string | null)[] = new Array(nw * nh)
  for (let y = 0; y < nh; y++)
    for (let x = 0; x < nw; x++)
      cells[y * nw + x] = g.cells[(y0 + y) * g.width + (x0 + x)]
  grid.value = { width: nw, height: nh, cells }
  gridVersion.value++
  syncWidthFromGrid()
  // grid was reassigned → watch(grid) clears the selection & repaints
  nextTick(() => { syncCanvasSize(); fitView() })
  ElMessage.success(`已裁剪到 ${nw} × ${nh}`)
}

// ---- canvas resize (change W & H without scaling — pad with empty cells) ----
function openResizeDialog() {
  const g = grid.value
  if (!g) return
  resizeW.value = g.width
  resizeH.value = g.height
  resizeAnchor.value = 4
  showResizeDialog.value = true
}
/**
 * Resize the canvas to resizeW × resizeH WITHOUT scaling the pattern: each
 * existing bead keeps its size, the pattern is placed at the chosen anchor,
 * extra room is filled with empty cells, and any overflow is cropped.
 */
function applyResize() {
  const g = grid.value
  if (!g) return
  const nw = Math.max(1, Math.min(400, Math.round(resizeW.value || 0)))
  const nh = Math.max(1, Math.min(400, Math.round(resizeH.value || 0)))
  if (nw === g.width && nh === g.height) { showResizeDialog.value = false; return }
  // anchor: column 0/1/2 = left/center/right, row 0/1/2 = top/middle/bottom
  const ac = resizeAnchor.value % 3, ar = (resizeAnchor.value / 3) | 0
  const ox = ac === 0 ? 0 : ac === 2 ? nw - g.width : Math.round((nw - g.width) / 2)
  const oy = ar === 0 ? 0 : ar === 2 ? nh - g.height : Math.round((nh - g.height) / 2)
  pushHistory()
  const cells: (string | null)[] = new Array(nw * nh).fill(null)
  for (let y = 0; y < g.height; y++) {
    for (let x = 0; x < g.width; x++) {
      const nx = x + ox, ny = y + oy
      if (nx >= 0 && nx < nw && ny >= 0 && ny < nh)
        cells[ny * nw + nx] = g.cells[y * g.width + x]
    }
  }
  grid.value = { width: nw, height: nh, cells }
  gridVersion.value++
  syncWidthFromGrid()
  showResizeDialog.value = false
  nextTick(() => { syncCanvasSize(); fitView() })
  ElMessage.success(`画布已调整为 ${nw} × ${nh}`)
}

// ---- shape tools: rasterization ----
function lineCells(x0: number, y0: number, x1: number, y1: number): number[][] {
  const pts: number[][] = []
  const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0)
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1
  let err = dx - dy, x = x0, y = y0
  for (;;) {
    pts.push([x, y])
    if (x === x1 && y === y1) break
    const e2 = 2 * err
    if (e2 > -dy) { err -= dy; x += sx }
    if (e2 < dx) { err += dx; y += sy }
  }
  return pts
}
function rectCells(x0: number, y0: number, x1: number, y1: number, filled: boolean): number[][] {
  const lx = Math.min(x0, x1), rx = Math.max(x0, x1)
  const ty = Math.min(y0, y1), by = Math.max(y0, y1)
  const pts: number[][] = []
  if (filled) {
    for (let y = ty; y <= by; y++) for (let x = lx; x <= rx; x++) pts.push([x, y])
  } else {
    for (let x = lx; x <= rx; x++) { pts.push([x, ty]); pts.push([x, by]) }
    for (let y = ty + 1; y < by; y++) { pts.push([lx, y]); pts.push([rx, y]) }
  }
  return pts
}
function ellipseCells(x0: number, y0: number, x1: number, y1: number, filled: boolean): number[][] {
  const lx = Math.min(x0, x1), rx = Math.max(x0, x1)
  const ty = Math.min(y0, y1), by = Math.max(y0, y1)
  const cx = (lx + rx) / 2, cy = (ty + by) / 2
  const a = Math.max(0.5, (rx - lx) / 2), b = Math.max(0.5, (by - ty) / 2)
  const inside = (x: number, y: number) => {
    const u = (x - cx) / a, v = (y - cy) / b
    return u * u + v * v <= 1
  }
  const pts: number[][] = []
  for (let y = ty; y <= by; y++) {
    for (let x = lx; x <= rx; x++) {
      if (!inside(x, y)) continue
      if (filled || !inside(x - 1, y) || !inside(x + 1, y)
          || !inside(x, y - 1) || !inside(x, y + 1)) pts.push([x, y])
    }
  }
  return pts
}
/** Apply the Shift constraint to the current shape end point. */
function constrainedShapeEnd(): { x: number; y: number } {
  const s = shapeStart!, e = shapeEnd!
  if (!shapeShift) return e
  const dx = e.x - s.x, dy = e.y - s.y
  if (tool.value === 'line') {
    const ax = Math.abs(dx), ay = Math.abs(dy)
    if (ax > ay * 2) return { x: e.x, y: s.y }            // horizontal
    if (ay > ax * 2) return { x: s.x, y: e.y }            // vertical
    const d = Math.max(ax, ay)                            // 45°
    return { x: s.x + Math.sign(dx) * d, y: s.y + Math.sign(dy) * d }
  }
  const d = Math.max(Math.abs(dx), Math.abs(dy))          // square bbox
  return { x: s.x + (dx < 0 ? -d : d), y: s.y + (dy < 0 ? -d : d) }
}
function currentShapeCells(): number[][] {
  if (!shapeStart || !shapeEnd) return []
  const e = constrainedShapeEnd()
  if (tool.value === 'line') return lineCells(shapeStart.x, shapeStart.y, e.x, e.y)
  if (tool.value === 'rect') return rectCells(shapeStart.x, shapeStart.y, e.x, e.y, shapeFill.value)
  return ellipseCells(shapeStart.x, shapeStart.y, e.x, e.y, shapeFill.value)
}
function clampCell(raw: { x: number; y: number }): { x: number; y: number } {
  const g = grid.value!
  return {
    x: Math.max(0, Math.min(g.width - 1, raw.x)),
    y: Math.max(0, Math.min(g.height - 1, raw.y)),
  }
}
function shapeOnDown(e: MouseEvent) {
  if (!grid.value) return
  const c = clampCell(cellAtRaw(e))
  shapeStart = c
  shapeEnd = c
  shapeShift = e.shiftKey
  shapeDragging = true
  hover.value = null
  render()
}
function shapeOnMove(e: MouseEvent) {
  if (!grid.value || !shapeDragging) return
  shapeEnd = clampCell(cellAtRaw(e))
  shapeShift = e.shiftKey
  render()
}
function shapeOnUp(e: MouseEvent) {
  const g = grid.value
  if (!g || !shapeDragging) { shapeDragging = false; return }
  shapeShift = e.shiftKey
  const cells = currentShapeCells()
  shapeDragging = false
  shapeStart = null
  shapeEnd = null
  if (cells.length === 0 || !currentCode.value) { render(); return }
  pushHistory()
  for (const [x, y] of cells) {
    if (x >= 0 && x < g.width && y >= 0 && y < g.height) g.cells[y * g.width + x] = currentCode.value
  }
  gridVersion.value++
  render()
}

function onDown(e: MouseEvent) {
  if (transforming.value) { transformOnDown(e); return }
  if (tool.value === 'pan' || e.button === 1) {
    panning = true
    panStart = { x: e.clientX, y: e.clientY, ox: offset.value.x, oy: offset.value.y }
    return
  }
  if (tool.value === 'select') { selectOnDown(e); return }
  if (isShapeTool(tool.value)) { shapeOnDown(e); return }
  const cell = cellAt(e)
  if (cell) {
    // snapshot once per action so Ctrl+Z reverts the whole stroke
    // (mirror does its own pushHistory inside mirrorCopy)
    if (['paint', 'erase', 'wand', 'wanderase', 'replace'].includes(tool.value)) pushHistory()
    painting = true
    applyTool(cell)
  }
}
function onMove(e: MouseEvent) {
  if (transforming.value) { if (xDrag) transformOnMove(e); return }
  if (panning) {
    offset.value = {
      x: panStart.ox + (e.clientX - panStart.x),
      y: panStart.oy + (e.clientY - panStart.y),
    }
    render()
    return
  }
  if (selMode !== 'none') { selectOnMove(e); return }
  if (shapeDragging) { shapeOnMove(e); return }
  const cell = cellAt(e)
  hover.value = cell
  if (cell) {
    const rect = wrapRef.value!.getBoundingClientRect()
    hoverTipStyle.value = {
      left: (e.clientX - rect.left + 14) + 'px',
      top: (e.clientY - rect.top + 14) + 'px',
    }
  }
  if (painting && cell && (tool.value === 'paint' || tool.value === 'erase')) {
    applyTool(cell)
  } else {
    render()
  }
}
function onUp(e: MouseEvent) {
  if (transforming.value) { xDrag = null; return }
  if (selMode !== 'none') { finishSelDrag(); return }
  if (shapeDragging) { shapeOnUp(e); return }
  painting = false; panning = false
}
function onLeave(e: MouseEvent) {
  if (transforming.value) { xDrag = null; return }
  if (selMode !== 'none') { finishSelDrag(); return }
  if (shapeDragging) { shapeOnUp(e); return }
  painting = false; panning = false; hover.value = null; render()
}

// ---- rendering ----
function render() {
  const cv = canvasRef.value, g = grid.value
  if (!cv || !g) return
  const ctx = cv.getContext('2d')!
  const dpr = window.devicePixelRatio || 1
  const W = cv.width / dpr, H = cv.height / dpr
  const cell = BASE_CELL * zoom.value
  const emptyMargin = cell * 0.3            // empty-cell marker inset
  const emptySize = cell - emptyMargin * 2  // empty-cell marker side
  const ox = RULER + offset.value.x
  const oy = RULER + offset.value.y

  ctx.clearRect(0, 0, W, H)
  ctx.fillStyle = '#fdf6f0'
  ctx.fillRect(0, 0, W, H)

  // visible cell range (cull)
  const cx0 = Math.max(0, Math.floor((-offset.value.x) / cell))
  const cy0 = Math.max(0, Math.floor((-offset.value.y) / cell))
  const cx1 = Math.min(g.width, Math.ceil((W - ox) / cell) + 1)
  const cy1 = Math.min(g.height, Math.ceil((H - oy) / cell) + 1)

  // beads (hidden while a free-transform preview is active)
  if (!transforming.value) for (let y = cy0; y < cy1; y++) {
    for (let x = cx0; x < cx1; x++) {
      const code = g.cells[y * g.width + x]
      const px = ox + x * cell, py = oy + y * cell
      // while a selection is being moved, its source region reads as empty
      const inHole = selMode === 'move' && selBufOrigin !== null
        && x >= selBufOrigin.x && x < selBufOrigin.x + selBufW
        && y >= selBufOrigin.y && y < selBufOrigin.y + selBufH
      if (!code || inHole) {
        // empty / erased cell: a small centered marker — clearly smaller than
        // the cell, so empty cells stand apart from filled beads at a glance
        if (emptySize >= 1.2) {
          ctx.fillStyle = ((x + y) & 1) ? '#ddd6e0' : '#bfb6c6'
          ctx.fillRect(px + emptyMargin, py + emptyMargin, emptySize, emptySize)
        }
        continue
      }
      drawBead(ctx, px, py, cell, MARD_COLORS[code]?.hex || '#000', beadShape.value, '#fdf6f0')
      // color-code label
      if (showLabels.value && cell >= 13) {
        const bc = MARD_COLORS[code]
        if (bc) {
          ctx.fillStyle = textOn(bc.rgb)
          ctx.font = `bold ${Math.max(7, Math.round(cell * 0.32))}px "JetBrains Mono", monospace`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(code, px + cell / 2, py + cell / 2)
        }
      }
    }
  }

  // ---- reference image overlay (on top of beads so it stays visible) ----
  const refImg = refImage.value
  if (refImg && !transforming.value) {
    ctx.save()
    ctx.globalAlpha = refOpacity.value
    ctx.drawImage(refImg, ox, oy, g.width * cell, g.height * cell)
    ctx.restore()
  }

  // selection: floating move preview + marquee rectangle
  if (selection.value && !transforming.value) {
    if (selMode === 'move' && selBuf) drawSelFloat(ctx, cell, ox, oy)
    drawMarquee(ctx, cell, ox, oy)
  }

  // shape-tool drag preview
  if (shapeDragging && !transforming.value) {
    const hex = curColorHex.value
    for (const [sx, sy] of currentShapeCells()) {
      drawBead(ctx, ox + sx * cell, oy + sy * cell, cell, hex, beadShape.value, '#fdf6f0')
    }
  }

  // free-transform preview
  if (transforming.value && xCanvas) drawTransformPreview(ctx, cell, ox, oy)

  // hover highlight
  if (hover.value && !transforming.value) {
    ctx.strokeStyle = '#ff6b9d'
    ctx.lineWidth = 2
    if (tool.value === 'paint' || tool.value === 'erase') {
      // circular brush / eraser footprint
      const s = tool.value === 'paint' ? brushSize.value : eraserSize.value
      const lo = -Math.floor((s - 1) / 2)
      const hi = Math.floor(s / 2)
      const cen = (lo + hi + 1) / 2
      ctx.beginPath()
      ctx.arc(
        ox + (hover.value.x + cen) * cell,
        oy + (hover.value.y + cen) * cell,
        (s / 2) * cell, 0, Math.PI * 2,
      )
      ctx.stroke()
    } else if (tool.value === 'mirror') {
      // show the symmetry line through the hovered cell
      ctx.strokeRect(ox + hover.value.x * cell, oy + hover.value.y * cell, cell, cell)
      ctx.strokeStyle = '#7c5cff'
      ctx.lineWidth = 2.5
      ctx.setLineDash([6, 4])
      ctx.beginPath()
      if (mirrorAxis.value === 'v') {
        const lx = ox + (hover.value.x + 0.5) * cell
        ctx.moveTo(lx, oy)
        ctx.lineTo(lx, oy + g.height * cell)
      } else {
        const ly = oy + (hover.value.y + 0.5) * cell
        ctx.moveTo(ox, ly)
        ctx.lineTo(ox + g.width * cell, ly)
      }
      ctx.stroke()
      ctx.setLineDash([])
    } else {
      ctx.strokeRect(ox + hover.value.x * cell, oy + hover.value.y * cell, cell, cell)
    }
  }

  // highlight overlay: dim every cell that's NOT in the highlighted row /
  // column / colour, then draw a bright outline on the focused band.
  if (highlightMode.value !== 'none' && !transforming.value) {
    drawHighlightOverlay(ctx, cell, ox, oy)
  }

  // grid lines (drawn AFTER the highlight overlay so they stay at full
  // colour — the dim mask shouldn't fade the reference lines)
  if (cell >= 5 && !transforming.value) {
    drawGridLayer(ctx, gridConfig.value.dashed, [6, 4], g, ox, oy, cell)
    drawGridLayer(ctx, gridConfig.value.solid,  [],     g, ox, oy, cell)
  }

  // ruler
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, W, RULER)
  ctx.fillRect(0, 0, RULER, H)
  ctx.font = '10px "JetBrains Mono", monospace'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  const step = cell < 16 ? 10 : cell < 30 ? 5 : 1
  for (let x = cx0; x < cx1; x++) {
    if (x % step) continue
    ctx.fillStyle = (x % 10 === 0) ? '#e8462a' : '#a896a3'
    ctx.fillText(String(x + 1), ox + x * cell + cell / 2, RULER / 2)
  }
  ctx.textAlign = 'right'
  for (let y = cy0; y < cy1; y++) {
    if (y % step) continue
    ctx.fillStyle = (y % 10 === 0) ? '#e8462a' : '#a896a3'
    ctx.fillText(String(y + 1), RULER - 4, oy + y * cell + cell / 2)
  }
  // corner mask
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, RULER, RULER)

  // free-transform box + handles (drawn on top of the ruler)
  if (transforming.value) drawTransformBox(ctx, cell, ox, oy)
}

/**
 * Draw one configurable grid layer: vertical + horizontal lines at every
 * `cfg.step` cells, in the given colour / width / dash pattern. No-op when
 * the layer is disabled or the step is < 1.
 */
function drawGridLayer(
  ctx: CanvasRenderingContext2D,
  cfg: GridLayer,
  dash: number[],
  g: { width: number; height: number },
  ox: number, oy: number, cell: number,
) {
  if (!cfg.enabled || !cfg.step || cfg.step < 1) return
  ctx.save()
  ctx.strokeStyle = cfg.color
  ctx.lineWidth = Math.max(0.5, cfg.width || 1)
  ctx.setLineDash(dash)
  ctx.beginPath()
  for (let x = 0; x <= g.width; x++) {
    if (x % cfg.step !== 0) continue
    const px = ox + x * cell
    ctx.moveTo(px, oy); ctx.lineTo(px, oy + g.height * cell)
  }
  for (let y = 0; y <= g.height; y++) {
    if (y % cfg.step !== 0) continue
    const py = oy + y * cell
    ctx.moveTo(ox, py); ctx.lineTo(ox + g.width * cell, py)
  }
  ctx.stroke()
  ctx.restore()
}

/**
 * Dim every cell not in the highlighted row / column / colour band by
 * painting a translucent black rectangle over it, then draw a bright outline
 * around the lit area so the focus is unmistakable.
 */
function drawHighlightOverlay(
  ctx: CanvasRenderingContext2D, cell: number, ox: number, oy: number,
) {
  const g = grid.value!
  const W = g.width * cell, H = g.height * cell
  const dim = 'rgba(20, 14, 30, 0.55)'

  ctx.save()
  ctx.fillStyle = dim
  if (highlightMode.value === 'row') {
    const r = Math.max(0, Math.min(g.height - 1, highlightRow.value))
    // dim above and below the highlighted row
    if (r > 0) ctx.fillRect(ox, oy, W, r * cell)
    if (r < g.height - 1) ctx.fillRect(ox, oy + (r + 1) * cell, W, (g.height - r - 1) * cell)
    // bright outline on the row
    ctx.strokeStyle = '#ffd76b'
    ctx.lineWidth = 2
    ctx.strokeRect(ox + 0.5, oy + r * cell + 0.5, W - 1, cell - 1)
  } else if (highlightMode.value === 'col') {
    const c = Math.max(0, Math.min(g.width - 1, highlightCol.value))
    if (c > 0) ctx.fillRect(ox, oy, c * cell, H)
    if (c < g.width - 1) ctx.fillRect(ox + (c + 1) * cell, oy, (g.width - c - 1) * cell, H)
    ctx.strokeStyle = '#ffd76b'
    ctx.lineWidth = 2
    ctx.strokeRect(ox + c * cell + 0.5, oy + 0.5, cell - 1, H - 1)
  } else if (highlightMode.value === 'rect') {
    clampHighlightRect()
    const r = highlightRect.value
    // dim the four bands around the rect
    if (r.y > 0)                 ctx.fillRect(ox, oy, W, r.y * cell)
    if (r.y + r.h < g.height)    ctx.fillRect(ox, oy + (r.y + r.h) * cell, W, (g.height - r.y - r.h) * cell)
    if (r.x > 0)                 ctx.fillRect(ox, oy + r.y * cell, r.x * cell, r.h * cell)
    if (r.x + r.w < g.width)     ctx.fillRect(ox + (r.x + r.w) * cell, oy + r.y * cell, (g.width - r.x - r.w) * cell, r.h * cell)
    // bright outline on the rect
    ctx.strokeStyle = '#ffd76b'
    ctx.lineWidth = 2
    ctx.strokeRect(ox + r.x * cell + 0.5, oy + r.y * cell + 0.5, r.w * cell - 1, r.h * cell - 1)
  } else if (highlightMode.value === 'color') {
    const target = currentCode.value
    if (!target) {
      // no colour picked — dim everything as a hint
      ctx.fillRect(ox, oy, W, H)
    } else {
      // dim all non-matching cells; leave matching cells bright
      for (let y = 0; y < g.height; y++) {
        for (let x = 0; x < g.width; x++) {
          if (g.cells[y * g.width + x] !== target) {
            ctx.fillRect(ox + x * cell, oy + y * cell, cell, cell)
          }
        }
      }
      // draw a bright outline around each matching cell
      ctx.strokeStyle = '#ffd76b'
      ctx.lineWidth = Math.max(1.5, cell * 0.06)
      for (let y = 0; y < g.height; y++) {
        for (let x = 0; x < g.width; x++) {
          if (g.cells[y * g.width + x] === target) {
            ctx.strokeRect(ox + x * cell + 1, oy + y * cell + 1, cell - 2, cell - 2)
          }
        }
      }
    }
  }
  ctx.restore()
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number,
) {
  if (r <= 0.5) { ctx.beginPath(); ctx.rect(x, y, w, h); return }
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

/** Mix a #RRGGBB colour toward black by amount (0..1). Used for the bead hole. */
function darken(hex: string, amount: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const m = 1 - amount
  const to = (v: number) => Math.round(v * m).toString(16).padStart(2, '0')
  return `#${to(r)}${to(g)}${to(b)}`
}

/** Draw one bead in a cell according to the chosen shape. */
function drawBead(
  ctx: CanvasRenderingContext2D,
  px: number, py: number, cell: number, hex: string, shape: BeadShape,
  cellBg: string = '#ffffff',
) {
  ctx.fillStyle = hex
  if (shape === 'fill') {
    // edge-to-edge, tiny overlap to avoid hairline seams
    ctx.fillRect(px, py, cell + 0.6, cell + 0.6)
  } else if (shape === 'circle') {
    // Top-down view of a real perler bead — a hollow ring: outer disc in the
    // bead colour, with a smaller central disc filled with the cell's
    // background to read as the cylinder's hole. Use evenodd fill on a single
    // path so the two arcs share the same colour, no sub-pixel seam between
    // the rim and the hole boundary.
    const pad = cell > 7 ? cell * 0.06 : 0
    const cx = px + cell / 2, cy = py + cell / 2
    const rOuter = (cell - pad * 2) / 2
    const rInner = rOuter * 0.42
    if (rOuter >= 3) {
      // ring: outer arc minus inner arc, drawn as one path with evenodd rule
      ctx.beginPath()
      ctx.arc(cx, cy, rOuter, 0, Math.PI * 2)
      ctx.arc(cx, cy, rInner, 0, Math.PI * 2, true)
      ctx.fill('evenodd')
      // a faint inner-edge stroke so the hole reads cleanly against a similar bg
      ctx.strokeStyle = darken(hex, 0.35)
      ctx.lineWidth = Math.max(0.5, cell * 0.025)
      ctx.beginPath()
      ctx.arc(cx, cy, rInner, 0, Math.PI * 2)
      ctx.stroke()
    } else {
      // too small for a visible hole — draw as a solid disc
      ctx.beginPath()
      ctx.arc(cx, cy, rOuter, 0, Math.PI * 2)
      ctx.fill()
    }
  } else {
    // rounded square
    const pad = cell > 7 ? Math.max(0.5, cell * 0.07) : 0
    const r = cell > 12 ? Math.min(cell * 0.22, 4) : 1
    roundRect(ctx, px + pad, py + pad, cell - pad * 2, cell - pad * 2, r)
    ctx.fill()
  }
}

// ---- export ----
/**
 * Build the export-style pattern canvas at a given cell size.
 *
 * - `withGrid`: when true, paints grid lines + every-10 ticks + the numbered
 *   ruler around the pattern. Off gives a clean beads-only image.
 * - `transparentEmpty`: when true, leaves empty cells fully transparent and
 *   omits the white canvas background — useful for publishing/exporting PNGs
 *   that should let the cell background show through (e.g. against a dark
 *   page or pasted onto another image).
 *
 * Shared by export & preview.
 */
function buildPatternCanvas(
  cell: number,
  withGrid = true,
  transparentEmpty = false,
): HTMLCanvasElement {
  const g = grid.value!
  const labels = showLabels.value
  const pad = withGrid ? RULER : 0
  const cv = document.createElement('canvas')
  cv.width = pad + g.width * cell
  cv.height = pad + g.height * cell
  const ctx = cv.getContext('2d')!
  // Only paint a white background when the caller wants opaque output —
  // skipping this leaves the canvas fully transparent where no beads draw.
  if (!transparentEmpty) {
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, cv.width, cv.height)
  }

  const emptyMargin = cell * 0.3            // empty-cell marker inset
  const emptySize = cell - emptyMargin * 2  // empty-cell marker side
  // bead-hole background used to "punch" the inner ring of the circle shape:
  // white in opaque mode, but in transparent mode we want the actual hole to
  // be empty too — so we let drawBead's evenodd ring leave it alone.
  const beadCellBg = transparentEmpty ? 'transparent' : '#ffffff'
  for (let y = 0; y < g.height; y++) {
    for (let x = 0; x < g.width; x++) {
      const code = g.cells[y * g.width + x]
      const px = pad + x * cell, py = pad + y * cell
      if (!code) {
        // empty cell: in opaque mode draw a small centered marker so it reads
        // distinctly from a real bead; in transparent mode just skip it.
        if (!transparentEmpty && emptySize >= 1) {
          ctx.fillStyle = ((x + y) & 1) ? '#ddd6e0' : '#bfb6c6'
          ctx.fillRect(px + emptyMargin, py + emptyMargin, emptySize, emptySize)
        }
        continue
      }
      const bc = MARD_COLORS[code]
      drawBead(ctx, px, py, cell, bc?.hex || '#000', beadShape.value, beadCellBg)
      if (labels && bc && cell >= 12) {
        ctx.fillStyle = textOn(bc.rgb)
        ctx.font = `bold ${Math.round(cell * 0.30)}px "JetBrains Mono", monospace`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(code, px + cell / 2, py + cell / 2)
      }
    }
  }
  if (withGrid) {
    // grid lines: same configurable layers as the live canvas
    drawGridLayer(ctx, gridConfig.value.dashed, [6, 4], g, pad, pad, cell)
    drawGridLayer(ctx, gridConfig.value.solid,  [],     g, pad, pad, cell)
    // ruler numbers — stepped so small (preview) cells stay legible
    const rstep = cell < 14 ? 10 : cell < 22 ? 5 : 1
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, cv.width, RULER)
    ctx.fillRect(0, 0, RULER, cv.height)
    ctx.font = '11px monospace'
    ctx.textBaseline = 'middle'
    for (let x = 0; x < g.width; x++) {
      if (x % rstep) continue
      ctx.fillStyle = (x % 10 === 0) ? '#e8462a' : '#aaa'
      ctx.textAlign = 'center'
      ctx.fillText(String(x + 1), RULER + x * cell + cell / 2, RULER / 2)
    }
    for (let y = 0; y < g.height; y++) {
      if (y % rstep) continue
      ctx.fillStyle = (y % 10 === 0) ? '#e8462a' : '#aaa'
      ctx.textAlign = 'right'
      ctx.fillText(String(y + 1), RULER - 4, RULER + y * cell + cell / 2)
    }
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, RULER, RULER)
  }
  return cv
}

/** Generic canvas export (PNG / JPEG). `withGrid` = include grid lines & ruler. */
function exportImage(mime: 'png' | 'jpeg', quality: number | undefined, withGrid: boolean) {
  const g = grid.value
  if (!g) return
  // PNG supports alpha — preserve empty-cell transparency in the exported file.
  // JPEG has no alpha so we keep the current opaque rendering (empty cells get
  // their checker-marker on a white background).
  const transparentEmpty = mime === 'png'
  const cv = buildPatternCanvas(showLabels.value ? 42 : 26, withGrid, transparentEmpty)
  const ext = mime === 'jpeg' ? 'jpg' : 'png'
  const mimeType = mime === 'jpeg' ? 'image/jpeg' : 'image/png'
  const a = document.createElement('a')
  a.download = `拼豆图纸_${g.width}x${g.height}.${ext}`
  a.href = cv.toDataURL(mimeType, quality)
  a.click()
}

/** Render a scaled-down data-URL preview of the exported pattern. */
function buildPreview(withGrid: boolean): string {
  const g = grid.value
  if (!g) return ''
  const pc = Math.max(4, Math.min(30, Math.round(900 / Math.max(g.width, g.height))))
  return buildPatternCanvas(pc, withGrid).toDataURL('image/png')
}

/** Open the export dialog, generating both grid / no-grid previews first. */
function openExportDialog() {
  if (!grid.value) return
  exportPreview.value = buildPreview(true)
  exportPreviewPlain.value = buildPreview(false)
  showExportDialog.value = true
}

/** Export as SVG vector. `withGrid` = include grid lines. */
function downloadSVG(shape: 'circle' | 'rect', withGrid: boolean) {
  const g = grid.value
  if (!g) return
  const labels = showLabels.value
  const cell = labels ? 42 : 26
  const pad = withGrid ? RULER : 0
  const W = pad + g.width * cell
  const H = pad + g.height * cell

  let beads = ''
  for (let y = 0; y < g.height; y++) {
    for (let x = 0; x < g.width; x++) {
      const code = g.cells[y * g.width + x]
      const px = pad + x * cell, py = pad + y * cell
      if (!code) continue
      const bc = MARD_COLORS[code]
      if (!bc) continue
      const d = cell - 1
      if (shape === 'circle') {
        const r = d / 2
        beads += `<circle cx="${px + d / 2}" cy="${py + d / 2}" r="${r}" fill="${bc.hex}" />\n`
      } else {
        beads += `<rect x="${px}" y="${py}" width="${d}" height="${d}" rx="${Math.min(3, d * 0.15)}" fill="${bc.hex}" />\n`
      }
      if (labels) {
        beads += `<text x="${px + d / 2}" y="${py + d / 2 + 1}" text-anchor="middle" dominant-baseline="middle" font-size="${Math.round(cell * 0.28)}" font-family="monospace" fill="${textOn(bc.rgb)}">${code}</text>\n`
      }
    }
  }

  let gridLines = ''
  if (withGrid) {
    for (let x = 0; x <= g.width; x++) {
      const lx = pad + x * cell
      gridLines += `<line x1="${lx}" y1="${pad}" x2="${lx}" y2="${H}" ${x % 10 === 0 ? 'class="tick"' : ''} />\n`
    }
    for (let y = 0; y <= g.height; y++) {
      const ly = pad + y * cell
      gridLines += `<line x1="${pad}" y1="${ly}" x2="${W}" y2="${ly}" ${y % 10 === 0 ? 'class="tick"' : ''} />\n`
    }
  }

  // No background rect — leave the SVG transparent so empty cells stay empty
  // (matches the live canvas behaviour). Viewers that need an opaque
  // backdrop can lay this over their own colour.
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<style>.tick{stroke:#e8462a;stroke-width:2}line{stroke:rgba(120,90,90,0.25);stroke-width:1}</style>
${gridLines}${beads}</svg>`

  const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.download = `拼豆图纸_${g.width}x${g.height}.svg`
  a.href = url
  a.click()
  URL.revokeObjectURL(url)
}

/** Export material list as CSV */
function downloadCSV() {
  const g = grid.value
  if (!g) return
  const sorted = [...colorCounts.value.entries()].sort((a, b) => b[1] - a[1])
  const rows = ['﻿色号,颜色名,Hex,数量']
  for (const [code, count] of sorted) {
    const c = MARD_COLORS[code]
    rows.push(`${code},${c?.name ?? ''},${c?.hex ?? ''},${count}`)
  }
  const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.download = `拼豆材料单_${g.width}x${g.height}.csv`
  a.href = url
  a.click()
  URL.revokeObjectURL(url)
}

// ---- export dialog handler — exports every chosen format in one go ----
function handleExport(opts: {
  formats: ('png' | 'jpg' | 'svg' | 'csv')[]
  gridLines: boolean
  jpgQuality: number
  svgShape: 'circle' | 'rect'
}) {
  showExportDialog.value = false
  if (!grid.value || opts.formats.length === 0) return
  // stagger the downloads so the browser doesn't drop rapid successive ones
  opts.formats.forEach((f, i) => {
    setTimeout(() => {
      if (f === 'png') exportImage('png', undefined, opts.gridLines)
      else if (f === 'jpg') exportImage('jpeg', opts.jpgQuality / 100, opts.gridLines)
      else if (f === 'svg') downloadSVG(opts.svgShape, opts.gridLines)
      else if (f === 'csv') downloadCSV()
    }, i * 300)
  })
  ElMessage.success(`已导出 ${opts.formats.length} 个文件`)
}

// Bead shape & code labels only affect display — just repaint, no re-convert.
watch([beadShape, showLabels], () => render())
// re-render when the highlight target changes (mode toggle, row/col index, or
// the current paint colour while in colour-highlight mode)
watch([highlightMode, highlightRow, highlightCol, currentCode], () => render())
watch(highlightRect, () => render(), { deep: true })

// close the highlight popover when clicking outside it
watch(showHighlightMenu, (open) => {
  if (!open) return
  const onDocClick = (ev: MouseEvent) => {
    const target = ev.target as HTMLElement | null
    if (!target) return
    // clicks inside the toolbar group or the immersive chip menu shouldn't close
    if (target.closest('.hi-group') || target.closest('.immersive-status')) return
    showHighlightMenu.value = false
  }
  // attach on next tick so the very click that opened the menu doesn't close it
  setTimeout(() => document.addEventListener('click', onDocClick, { once: true }), 0)
})

// ---- keyboard shortcuts ----
let panBeforeSpace: Tool | null = null
function onKeyDown(e: KeyboardEvent) {
  // ignore while typing in a form field
  const tag = (e.target as HTMLElement)?.tagName
  if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return
  if (!grid.value) return

  // free-transform: Enter applies, Esc cancels
  if (transforming.value) {
    if (e.key === 'Enter') { e.preventDefault(); applyTransform() }
    else if (e.key === 'Escape') { e.preventDefault(); cancelTransform() }
    return
  }

  // selection: Delete clears the region, Escape deselects
  if ((e.key === 'Delete' || e.key === 'Backspace')
      && tool.value === 'select' && selection.value) {
    e.preventDefault(); deleteSelection(); return
  }
  if (e.key === 'Escape') {
    if (showHighlightMenu.value) { e.preventDefault(); showHighlightMenu.value = false; return }
    if (showColorPanel.value) { e.preventDefault(); showColorPanel.value = false; return }
    if (highlightMode.value !== 'none') {
      e.preventDefault(); setHighlightMode('none'); return
    }
    if (selection.value) { e.preventDefault(); clearSelection(); render(); return }
    if (fullscreen.value) { e.preventDefault(); fullscreen.value = false; return }
  }

  // arrow keys cycle / move the highlight band while in highlight mode
  if (highlightMode.value !== 'none') {
    const g = grid.value
    if (g) {
      let consumed = true
      const m = highlightMode.value
      if (m === 'row' && e.key === 'ArrowUp') {
        highlightRow.value = (highlightRow.value - 1 + g.height) % g.height
      } else if (m === 'row' && e.key === 'ArrowDown') {
        highlightRow.value = (highlightRow.value + 1) % g.height
      } else if (m === 'col' && e.key === 'ArrowLeft') {
        highlightCol.value = (highlightCol.value - 1 + g.width) % g.width
      } else if (m === 'col' && e.key === 'ArrowRight') {
        highlightCol.value = (highlightCol.value + 1) % g.width
      } else if (m === 'rect' && (e.key === 'ArrowUp' || e.key === 'ArrowDown'
                                 || e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
        // Step the rect by its own dimensions so successive presses tile
        // across the grid (no overlap), then clamp at the edges.
        const r = highlightRect.value
        if (e.key === 'ArrowUp')    r.y = Math.max(0, r.y - r.h)
        if (e.key === 'ArrowDown')  r.y = Math.min(g.height - r.h, r.y + r.h)
        if (e.key === 'ArrowLeft')  r.x = Math.max(0, r.x - r.w)
        if (e.key === 'ArrowRight') r.x = Math.min(g.width - r.w, r.x + r.w)
      } else {
        consumed = false
      }
      if (consumed) { e.preventDefault(); render(); return }
    }
  }

  // undo / redo
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
    e.preventDefault()
    if (e.shiftKey) redo(); else undo()
    return
  }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
    e.preventDefault(); redo(); return
  }
  if (e.ctrlKey || e.metaKey || e.altKey) return

  switch (e.key.toLowerCase()) {
    case 'b': tool.value = 'paint'; break
    case 'e': tool.value = 'erase'; break
    case 'g': tool.value = 'wand'; break
    case 'd': tool.value = 'wanderase'; break
    case 'r': tool.value = 'replace'; break
    case 'l': tool.value = 'line'; break
    case 'u': tool.value = 'rect'; break
    case 'o': tool.value = 'ellipse'; break
    case 'm': tool.value = 'mirror'; break
    case 's': tool.value = 'select'; break
    case 'i': tool.value = 'pick'; break
    case 'h': tool.value = 'pan'; break
    case 'f': fullscreen.value = !fullscreen.value; break
    case ' ':
      e.preventDefault()
      if (tool.value !== 'pan') { panBeforeSpace = tool.value; tool.value = 'pan' }
      break
    case '+': case '=': zoomBy(1); break
    case '-': case '_': zoomBy(-1); break
    case '0': fitView(); break
    default: return
  }
}
function onKeyUp(e: KeyboardEvent) {
  if (e.key === ' ' && panBeforeSpace) {
    tool.value = panBeforeSpace
    panBeforeSpace = null
  }
}

// ---- lifecycle ----
// This view is wrapped in <keep-alive>, so the canvas & all edits survive
// navigating to the MARD palette tab and back. Global listeners are bound on
// activate / unbound on deactivate so shortcuts don't fire on other pages.
function onResize() { syncCanvasSize() }
function bindGlobalEvents() {
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
}
function unbindGlobalEvents() {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
}
onActivated(() => {
  bindGlobalEvents()
  // container size may have changed while the view was inactive
  if (grid.value) nextTick(() => syncCanvasSize())
})
onDeactivated(unbindGlobalEvents)
onBeforeUnmount(unbindGlobalEvents)
watch(tier, () => {
  // keep currentCode valid for the new tier's picker
  if (currentCode.value && !MARD_TIERS[tier.value].includes(currentCode.value)) {
    currentCode.value = workingPalette.value[0]?.code || ''
  }
})

// Toggling fullscreen resizes the canvas container — re-fit after the DOM updates.
watch(fullscreen, () => {
  showColorPanel.value = false   // toolbar height changes → panel offset stale
  nextTick(() => { syncCanvasSize(); fitView() })
})

// Same handling when toggling immersive (highlight): chrome hides/shows, so
// the canvas-wrap available height changes — resync + refit.
watch(immersive, () => {
  showColorPanel.value = false
  nextTick(() => { syncCanvasSize(); fitView() })
})

// Leaving the selection tool drops any active selection.
watch(tool, (nv, ov) => {
  if (ov === 'select' && nv !== 'select') { clearSelection(); render() }
})


// Any structural grid change (convert / undo / flip / transform …) invalidates
// the selection, since its coordinates may no longer be in bounds.
watch(grid, () => { clearSelection(); render() })
</script>

<style scoped>
.bead-studio { display: flex; flex-direction: column; gap: 1rem; }

/* ===== setup — start panel (3 evenly-distributed entry cards) ===== */
.setup-card { padding: 1.25rem 1.4rem; }
.entry-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.1rem;
}
@media (max-width: 760px) { .entry-grid { grid-template-columns: 1fr; } }

.entry-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.entry-stage { height: 150px; flex-shrink: 0; }
.entry-title {
  font-family: var(--font-display);
  font-size: 1rem;
  color: var(--plum-1);
  text-align: center;
  margin-top: 0.1rem;
}
.entry-desc {
  font-size: 0.74rem;
  color: var(--plum-3);
  line-height: 1.65;
  text-align: center;
}
.entry-btn { width: 100%; }

.upload-zone {
  border: 2.5px dashed var(--sakura-light);
  border-radius: var(--radius-md);
  background: var(--cream-2);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  transition: all var(--transition-fast);
}
.upload-zone:hover, .upload-zone.dragging {
  border-color: var(--sakura);
  background: var(--sakura-glow);
}
.upload-zone.filled { border-style: solid; padding: 4px; }
.upload-preview { max-width: 100%; max-height: 100%; border-radius: var(--radius-sm); object-fit: contain; }
.upload-hint { text-align: center; color: var(--plum-2); }
.upload-emoji { font-size: 2rem; }
.upload-text { font-family: var(--font-display); font-size: 1rem; margin-top: 0.3rem; }
.upload-sub { font-size: 0.7rem; color: var(--plum-3); margin-top: 0.15rem; }
.proj-zone:hover { border-color: var(--plum-2); background: var(--cream-3, var(--cream-2)); }

/* new-canvas stage */
.blank-stage {
  border: 2.5px dashed var(--sakura-light);
  border-radius: var(--radius-md);
  background: var(--cream-2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
}
.blank-size { display: flex; align-items: center; gap: 0.45rem; }
.blank-size label {
  display: flex; align-items: center; gap: 0.3rem;
  font-size: 0.82rem; color: var(--plum-2);
}
.blank-size .input { width: 66px; text-align: center; }
.blank-x { color: var(--plum-3); font-weight: 700; }
.blank-unit { font-size: 0.68rem; color: var(--plum-3); }

/* collapsible advanced conversion settings */
.conv-section { margin-top: 1rem; border-top: 2px dashed var(--line-strong); padding-top: 0.7rem; }
.conv-toggle {
  display: flex; align-items: center; gap: 0.4rem;
  cursor: pointer; user-select: none;
  font-size: 0.82rem; font-weight: 700; color: var(--plum-2);
}
.conv-toggle-icon { font-size: 0.65rem; }
.conv-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem 1.25rem;
  margin-top: 0.7rem;
}
@media (max-width: 720px) { .conv-body { grid-template-columns: 1fr; } }

.slider { flex: 1; accent-color: var(--sakura); cursor: pointer; }

/* ===== workspace ===== */
.workspace {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 1rem;
  align-items: start;
}
@media (max-width: 1000px) { .workspace { grid-template-columns: 1fr; } }

.canvas-col { padding: 0; overflow: hidden; position: relative; }
.canvas-body { display: flex; align-items: stretch; }
.canvas-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }

/* SAI-style tool rail — single-column vertical tool panel on the left */
.tool-rail {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  background: var(--cream-2);
  border-right: 2px solid var(--line-strong);
}
.rail-title {
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--plum-3);
  text-align: center;
  padding: 1px 0 2px;
}
.rail-btn {
  width: 34px; height: 34px;
  border: 1.5px solid var(--cream-4);
  background: #fff;
  color: var(--plum-2);
  border-radius: 5px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background var(--transition-fast), border-color var(--transition-fast),
              color var(--transition-fast);
}
.rail-btn:hover { border-color: var(--sakura); }
.rail-btn.on {
  background: var(--sakura);
  border-color: var(--sakura-deep);
  color: var(--plum-1);
  box-shadow: inset 0 1px 5px rgba(74,54,69,0.28);
}
.tool-ico {
  width: 21px; height: 21px;
  display: block;
  pointer-events: none;
}

/* fullscreen canvas — teleported to #app, covers the whole viewport */
.canvas-col.fullscreen {
  position: fixed;
  inset: 0;
  z-index: 80;
  margin: 0;
  border-radius: 0;
  transform: none;
  display: flex;
  flex-direction: column;
}
.canvas-col.fullscreen .canvas-body { flex: 1 1 auto; min-height: 0; }
.canvas-col.fullscreen .canvas-wrap {
  flex: 1 1 auto;
  height: auto;
  min-height: 0;
}

/* immersive mode — when a highlight is active, hide ALL chrome (tool rail,
   toolbar, param-bar, ref overlay, etc.) so the dim overlay + lit band fill
   the whole viewport. The floating status chip below shows mode + index. */
.canvas-col.immersive {
  position: fixed;
  inset: 0;
  z-index: 80;
  margin: 0;
  border-radius: 0;
  background: #fdf6f0;
  display: flex;
  flex-direction: column;
}
.canvas-col.immersive .tool-rail,
.canvas-col.immersive .toolbar,
.canvas-col.immersive .param-bar,
.canvas-col.immersive .ref-section,
.canvas-col.immersive .color-panel { display: none; }
.canvas-col.immersive .canvas-body { flex: 1 1 auto; min-height: 0; }
.canvas-col.immersive .canvas-main { display: flex; flex-direction: column; flex: 1 1 auto; min-height: 0; }
.canvas-col.immersive .canvas-wrap {
  flex: 1 1 auto;
  height: auto;
  min-height: 0;
}

/* floating status chip in immersive mode — draggable */
.immersive-status {
  position: fixed;
  top: 16px; left: 50%;
  transform: translateX(-50%);
  z-index: 90;
  display: flex; align-items: center; gap: 0.55rem;
  padding: 0.45rem 0.9rem 0.45rem 0.55rem;
  background: rgba(255, 255, 255, 0.96);
  border: 2px solid #ffd76b;
  border-radius: 999px;
  box-shadow: 0 6px 24px rgba(255, 184, 74, 0.35);
  font-family: var(--font-body);
  font-weight: 700; font-size: 0.84rem;
  color: var(--plum-1);
  cursor: move;
  user-select: none;
}
.immersive-status:active { cursor: grabbing; }
.im-grip {
  color: #c87b1f; font-size: 1.05rem;
  padding: 0 0.15rem;
  line-height: 1;
}
.im-mode-wrap { position: relative; }
.im-mode-btn {
  background: linear-gradient(180deg, #ffd76b, #ffb84a);
  color: #6b3a06;
  padding: 0.18rem 0.7rem;
  border: none;
  border-radius: 999px;
  font-family: inherit;
  font-weight: 800;
  font-size: 0.82rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  box-shadow: 0 2px 0 #c87b1f;
}
.im-mode-btn:hover { filter: brightness(1.04); }
.im-caret { font-size: 0.7rem; opacity: 0.85; }
.im-menu {
  position: absolute; top: calc(100% + 0.4rem); left: 0;
  min-width: 220px;
  background: #fff;
  border: 2px solid #ffd76b;
  border-radius: var(--radius-md);
  box-shadow: 0 6px 24px rgba(255, 184, 74, 0.45);
  padding: 0.35rem;
  display: flex; flex-direction: column; gap: 0.15rem;
  z-index: 100;
}
.im-menu-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  border: none; background: transparent;
  border-radius: var(--radius-sm);
  font-family: inherit; font-size: 0.8rem; font-weight: 600;
  color: var(--plum-1);
  cursor: pointer; text-align: left;
}
.im-menu-item:hover { background: var(--cream-2); }
.im-menu-item.on {
  background: linear-gradient(180deg, #fff5d0, #ffe6a3);
  color: #6b3a06; font-weight: 800;
}
.im-menu-ico { font-size: 1rem; }
.im-menu-item > span:nth-child(2) { flex: 1; }
.im-menu-check { color: #c87b1f; font-weight: 800; }

/* colour picker inside the chip */
.im-color-wrap { position: relative; display: inline-flex; }
.im-color-btn {
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.18rem 0.7rem;
  border: 2px solid #ffd76b;
  border-radius: 999px;
  font-family: inherit;
  font-weight: 800; font-size: 0.78rem;
  cursor: pointer;
  box-shadow: 0 2px 0 rgba(0, 0, 0, 0.1);
}
.im-color-btn:hover { filter: brightness(1.04); }
.im-color-grid {
  position: absolute; top: calc(100% + 0.4rem); left: 0;
  min-width: 280px; max-width: 360px;
  max-height: 280px; overflow-y: auto;
  background: #fff;
  border: 2px solid #ffd76b;
  border-radius: var(--radius-md);
  box-shadow: 0 6px 24px rgba(255, 184, 74, 0.45);
  padding: 0.45rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(38px, 1fr));
  gap: 4px;
  z-index: 100;
}
.im-color-cell {
  width: 100%; aspect-ratio: 1;
  border: 1.5px solid rgba(0, 0, 0, 0.15);
  border-radius: var(--radius-sm);
  padding: 0;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: transform var(--transition-fast);
}
.im-color-cell:hover { transform: scale(1.1); z-index: 2; }
.im-color-cell.on {
  border-width: 3px; border-color: #c87b1f;
  box-shadow: 0 0 0 2px #ffd76b, 0 2px 6px rgba(255, 184, 74, 0.6);
}
.im-color-cell {
  flex-direction: column;
  gap: 1px;
}
.im-color-code { font-size: 0.6rem; font-weight: 800; line-height: 1; }
.im-color-count { font-size: 0.48rem; font-weight: 700; line-height: 1; opacity: 0.85; }
.im-color-empty {
  grid-column: 1 / -1;
  text-align: center; padding: 1rem 0.5rem;
  font-size: 0.78rem; color: var(--plum-3);
}

/* rect controls inline inside the chip */
.im-rect-inline {
  display: inline-flex; align-items: center; gap: 0.3rem;
  padding: 0.1rem 0.5rem;
  background: var(--cream-2);
  border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-sm);
}
.im-lbl { font-size: 0.7rem; color: var(--plum-3); font-weight: 700; }
.im-num {
  width: 46px; padding: 0.05rem 0.35rem;
  border: 1.5px solid var(--cream-4); border-radius: 4px;
  font-family: var(--font-mono); font-weight: 700; font-size: 0.78rem;
  text-align: right; background: #fff; outline: none;
}
.im-num:focus { border-color: var(--sakura); }
.im-tag-pos { background: transparent; border: none; font-size: 0.72rem; padding: 0; }
.im-tag {
  padding: 0.15rem 0.55rem;
  background: var(--cream-2);
  border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-sm);
  font-weight: 800;
}
.im-hint {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--plum-3);
  font-weight: 700;
}

/* shape-tool fill option */
.shape-fill-opt {
  display: inline-flex; align-items: center; gap: 0.25rem;
  cursor: pointer; font-weight: 700; color: var(--plum-1);
}
.shape-fill-opt input { cursor: pointer; }
.xform-hint {
  font-size: 0.66rem; color: var(--plum-3);
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius-pill);
  padding: 0 0.4rem;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 0.8rem;
  border-bottom: 2px dashed var(--line-strong);
  flex-wrap: wrap;
}
.tool-group { display: flex; align-items: center; gap: 0.25rem; }
/* "此作品已拼完" button — pulsing pink when waiting for confirmation click */
.btn.finish-confirm {
  background: var(--sakura) !important;
  color: #fff !important;
  border-color: var(--sakura-deep) !important;
  animation: finish-pulse 1.1s ease-in-out infinite;
}
@keyframes finish-pulse {
  0%, 100% { box-shadow: 0 0 0 0 var(--sakura-ring); }
  50%      { box-shadow: 0 0 0 6px rgba(255, 107, 157, 0); }
}
.tool-btn {
  width: 32px; height: 32px;
  border: 2px solid var(--cream-4);
  background: #fff;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.95rem;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition-fast);
}
.tool-btn:hover { border-color: var(--sakura); transform: translateY(-1px); }
.tool-btn.on {
  background: var(--sakura);
  border-color: var(--sakura);
  box-shadow: 0 3px 10px var(--sakura-glow);
}
.tool-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  transform: none;
}
.tool-btn:disabled:hover { border-color: var(--cream-4); }

/* brush / eraser size indicator */
.size-tag {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.74rem;
  color: var(--plum-2);
  background: var(--cream-2);
  border-radius: var(--radius-pill);
  padding: 0.18rem 0.6rem;
  white-space: nowrap;
}
.size-tag b { color: var(--plum-1); }
.size-hint {
  font-size: 0.62rem;
  color: var(--plum-3);
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius-pill);
  padding: 0 0.35rem;
}

/* mirror-copy config */
.mirror-cfg {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 0.25rem;
}
.mini-btn {
  width: auto !important;
  font-size: 0.68rem !important;
  font-weight: 700;
  font-family: var(--font-round);
  padding: 0 0.45rem;
  min-width: 30px;
}
.mini-btn.on {
  background: var(--plum-1) !important;
  border-color: var(--plum-1) !important;
  color: #fff !important;
}

.kbd-hint {
  font-size: 0.72rem;
  color: var(--plum-3);
  border: 1.5px dashed var(--line-strong);
  border-radius: var(--radius-pill);
  padding: 0.12rem 0.6rem;
  cursor: help;
  white-space: nowrap;
}
.tool-divider { width: 1px; height: 22px; background: var(--line-strong); }

/* grid-lines settings popover */
.gl-group { position: relative; display: inline-flex; }
.gl-btn {
  padding: 0.3rem 0.6rem;
  border: 1.5px solid var(--cream-4);
  background: #fff; color: var(--plum-2);
  border-radius: var(--radius-pill);
  font-size: 0.74rem; font-weight: 700;
  cursor: pointer; transition: all var(--transition-fast);
  white-space: nowrap;
  display: inline-flex; align-items: center; gap: 0.3rem;
}
.gl-btn:hover { border-color: var(--sakura-light); color: var(--plum-1); }
.gl-btn.on { background: var(--sakura-glow); border-color: var(--sakura); color: var(--sakura-deep); }
.gl-caret { font-size: 0.7rem; opacity: 0.7; }
.gl-menu {
  position: absolute; top: calc(100% + 0.4rem); left: 0;
  z-index: 80; min-width: 320px;
  background: #fff;
  border: 2px solid var(--sakura-light);
  border-radius: var(--radius-md);
  box-shadow: 0 6px 24px var(--sakura-glow);
  padding: 0.55rem 0.65rem;
  display: flex; flex-direction: column; gap: 0.45rem;
}
.gl-row {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.35rem 0.45rem;
  background: var(--cream-2);
  border-radius: var(--radius-sm);
  font-size: 0.78rem; color: var(--plum-2);
}
.gl-chk {
  display: inline-flex; align-items: center; gap: 0.3rem;
  cursor: pointer; font-weight: 700; color: var(--plum-1);
}
.gl-row-title { font-size: 0.84rem; min-width: 2.5em; }
.gl-sub { font-size: 0.74rem; color: var(--plum-3); }
.gl-num {
  width: 56px; padding: 0.18rem 0.4rem;
  border: 1.5px solid var(--cream-4); border-radius: var(--radius-sm);
  font-family: var(--font-mono); font-weight: 700; text-align: right;
  background: #fff; outline: none; font-size: 0.78rem;
}
.gl-num:focus { border-color: var(--sakura); }
.gl-num:disabled { opacity: 0.4; cursor: not-allowed; }
.gl-num-sm { width: 50px; margin-left: auto; }
.gl-color {
  width: 30px; height: 26px; padding: 0; cursor: pointer;
  border: 1.5px solid var(--cream-4); border-radius: var(--radius-sm);
  background: #fff;
}
.gl-color:disabled { opacity: 0.4; cursor: not-allowed; }
.gl-foot { display: flex; justify-content: flex-end; padding-top: 0.15rem; }

/* highlight-mode dropdown + status / per-mode controls */
.hi-group {
  display: flex; align-items: center; gap: 0.35rem;
  flex-wrap: nowrap; position: relative;
}
.hi-btn {
  padding: 0.3rem 0.6rem;
  border: 1.5px solid var(--cream-4);
  background: #fff; color: var(--plum-2);
  border-radius: var(--radius-pill);
  font-size: 0.74rem; font-weight: 700;
  cursor: pointer; transition: all var(--transition-fast);
  white-space: nowrap;
  display: inline-flex; align-items: center; gap: 0.3rem;
}
.hi-btn:hover { border-color: var(--sakura-light); color: var(--plum-1); }
.hi-btn.on {
  background: linear-gradient(180deg, #ffd76b, #ffb84a);
  border-color: #c87b1f;
  color: #6b3a06;
  box-shadow: 0 2px 0 #c87b1f;
}
.hi-caret { font-size: 0.7rem; opacity: 0.7; }
.hi-menu {
  position: absolute; top: calc(100% + 0.35rem); left: 0;
  z-index: 60; min-width: 240px;
  background: #fff;
  border: 2px solid var(--sakura-light);
  border-radius: var(--radius-md);
  box-shadow: 0 6px 24px var(--sakura-glow);
  padding: 0.35rem;
  display: flex; flex-direction: column; gap: 0.15rem;
}
.hi-menu-item {
  display: flex; align-items: center; gap: 0.55rem;
  padding: 0.45rem 0.6rem;
  border: none; background: transparent;
  border-radius: var(--radius-sm);
  font-size: 0.82rem; font-weight: 600; color: var(--plum-1);
  cursor: pointer; text-align: left;
  transition: all var(--transition-fast);
}
.hi-menu-item:hover { background: var(--cream-2); }
.hi-menu-item.on {
  background: linear-gradient(180deg, #fff5d0, #ffe6a3);
  color: #6b3a06; font-weight: 800;
}
.him-icon { font-size: 1rem; }
.him-text { flex: 1; }
.him-check { color: #c87b1f; font-weight: 800; }
.hi-tag {
  padding: 0.15rem 0.55rem;
  font-size: 0.72rem; font-weight: 800;
  background: var(--cream-2);
  border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-sm);
  color: var(--plum-1);
}
.hi-rect-ctl {
  display: inline-flex; align-items: center; gap: 0.3rem;
  padding: 0.1rem 0.5rem;
  background: var(--cream-2);
  border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-sm);
}
.hi-rect-lbl { font-size: 0.7rem; color: var(--plum-3); font-weight: 700; }
.hi-rect-num {
  width: 48px; padding: 0.1rem 0.35rem;
  border: 1.5px solid var(--cream-4); border-radius: 4px;
  font-family: var(--font-mono); font-weight: 700; font-size: 0.78rem;
  text-align: right; background: #fff; outline: none;
}
.hi-rect-num:focus { border-color: var(--sakura); }
.hi-rect-pos { font-size: 0.7rem; color: var(--plum-2); margin-left: 0.15rem; }
.export-opt {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--plum-2);
  cursor: pointer;
  user-select: none;
}

/* live param row */
.param-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.8rem;
  background: var(--cream-2);
  border-bottom: 2px dashed var(--line-strong);
  flex-wrap: wrap;
}
.pb-cell {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.pb-cell.pb-wide { flex: 1; min-width: 160px; }
.pb-label {
  font-size: 0.66rem;
  font-weight: 700;
  color: var(--plum-3);
}
.pb-cell .input { padding: 0.25rem 0.4rem; font-size: 0.78rem; width: 72px; }
.pb-cell .select {
  padding: 0.25rem 1.7rem 0.25rem 0.5rem;
  font-size: 0.78rem;
  background-position: right 0.55rem center;
}
.pb-cell .slider { accent-color: var(--sakura); cursor: pointer; }
.pb-hint {
  font-size: 0.7rem;
  color: var(--plum-3);
  margin-left: auto;
}
.pb-hint.busy { color: var(--sakura-deep); font-weight: 700; }
.cur-color {
  display: flex; align-items: center; gap: 0.35rem;
  background: #fff;
  border: 2px solid var(--cream-4);
  border-radius: var(--radius-sm);
  padding: 0.1rem 0.4rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.cur-color:hover { border-color: var(--sakura); }
.cur-color.active {
  border-color: var(--sakura);
  background: var(--sakura-glow);
}
.cur-swatch {
  width: 22px; height: 22px; border-radius: 6px;
  border: 2px solid var(--cream-4);
}
.cur-label { font-size: 0.78rem; color: var(--plum-2); }
.cur-caret { font-size: 0.6rem; color: var(--plum-3); }

/* floating palette panel — works inside fullscreen too */
.color-panel {
  position: absolute;
  right: 10px;
  bottom: 10px;
  width: 250px;
  background: #fff;
  border: 2px solid var(--sakura);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-pop, 0 10px 30px rgba(74,54,69,0.25));
  z-index: 9;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.color-panel-head {
  display: flex; align-items: center; gap: 0.4rem;
  padding: 0.4rem 0.55rem;
  border-bottom: 2px dashed var(--line-strong);
  background: var(--cream-2);
}
.cp-swatch {
  width: 20px; height: 20px; border-radius: 5px;
  border: 2px solid var(--cream-4); flex-shrink: 0;
}
.cp-title {
  flex: 1; font-family: var(--font-display);
  font-size: 0.82rem; color: var(--plum-1);
}
.cp-close {
  background: none; border: none; cursor: pointer;
  font-size: 0.9rem; color: var(--plum-3); line-height: 1;
}
.cp-close:hover { color: var(--plum-1); }
.color-panel-modes {
  display: flex;
  gap: 2px;
  margin: 0.45rem 0.55rem 0;
  background: var(--cream-2);
  border-radius: var(--radius-pill);
  padding: 2px;
}
.color-panel-modes .mode-btn { flex: 1; padding: 0.25rem 0; font-size: 0.74rem; }
.color-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0.55rem;
}
.cp-empty {
  font-size: 0.74rem;
  color: var(--plum-3);
  line-height: 1.6;
  padding: 0.6rem 0.3rem;
  text-align: center;
}

/* canvas-resize dialog */
.resize-overlay {
  position: fixed; inset: 0;
  background: rgba(74,54,69,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; backdrop-filter: blur(4px);
}
.resize-modal {
  width: min(380px, 92vw);
  padding: 1.1rem 1.3rem;
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.resize-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.9rem;
}
.resize-title { font-family: var(--font-display); font-size: 1.05rem; color: var(--plum-1); }
.resize-x { background: none; border: none; font-size: 1.1rem; cursor: pointer; color: var(--plum-3); }
.resize-x:hover { color: var(--plum-1); }
.resize-body { display: flex; flex-direction: column; gap: 0.7rem; }
.resize-cur { font-size: 0.78rem; color: var(--plum-3); }
.resize-fields { display: flex; align-items: center; gap: 0.5rem; }
.resize-fields label {
  display: flex; align-items: center; gap: 0.35rem;
  font-size: 0.85rem; color: var(--plum-2); font-weight: 700;
}
.resize-fields .input { width: 78px; text-align: center; }
.resize-x-sign { color: var(--plum-3); font-weight: 700; }
.resize-unit { font-size: 0.72rem; color: var(--plum-3); }
.resize-anchor-label {
  font-size: 0.74rem; color: var(--plum-2); font-weight: 700; margin-top: 0.2rem;
}
.resize-anchor {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  width: 96px;
}
.anchor-cell {
  aspect-ratio: 1;
  border: 2px solid var(--cream-4);
  background: #fff;
  border-radius: 5px;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.anchor-cell:hover { border-color: var(--sakura-light); }
.anchor-cell.on {
  background: var(--sakura);
  border-color: var(--sakura);
  box-shadow: 0 2px 8px var(--sakura-glow);
}
.resize-note {
  font-size: 0.72rem; color: var(--plum-3); line-height: 1.6;
  background: var(--cream-2); border-radius: var(--radius-sm); padding: 0.45rem 0.6rem;
}
.resize-foot {
  display: flex; justify-content: flex-end; gap: 0.6rem;
  margin-top: 1rem; padding-top: 0.8rem;
  border-top: 2px dashed var(--line-strong);
}
.zoom-label { font-size: 0.76rem; color: var(--plum-2); min-width: 42px; text-align: center; }
.grid-size { font-size: 0.76rem; color: var(--plum-3); }

.canvas-wrap {
  position: relative;
  height: 64vh;
  min-height: 360px;
  background: #fdf6f0;
  overflow: hidden;
  cursor: crosshair;
}
.canvas-wrap canvas { display: block; }
.hover-tip {
  position: absolute;
  background: var(--plum-1);
  color: #fff;
  font-size: 0.72rem;
  font-family: var(--font-mono);
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  pointer-events: none;
  white-space: nowrap;
  z-index: 5;
}

/* free-transform action bar */
.canvas-wrap.xforming { cursor: default; }
.xform-bar {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: rgba(255, 255, 255, 0.96);
  border: 2px solid var(--plum-1);
  border-radius: var(--radius-pill);
  padding: 0.35rem 0.45rem 0.35rem 0.85rem;
  box-shadow: var(--shadow-soft);
  z-index: 8;
}
.xform-title {
  font-family: var(--font-display);
  font-size: 0.86rem;
  color: var(--plum-1);
}
.xform-info {
  font-size: 0.74rem;
  color: var(--plum-2);
}

/* ===== side ===== */
.side-col { display: flex; flex-direction: column; gap: 1rem; }
.side-card { padding: 0.8rem 0.9rem; }
.side-head {
  font-family: var(--font-display);
  font-size: 0.95rem;
  color: var(--plum-1);
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.6rem;
}
.side-count { font-size: 0.7rem; font-family: var(--font-mono); color: var(--plum-3); }
.side-sub { font-size: 0.72rem; color: var(--plum-3); margin: -0.35rem 0 0.55rem; }
.side-empty { font-size: 0.78rem; color: var(--plum-3); padding: 0.5rem 0; }

.palette-scroll {
  max-height: 320px;
  overflow-y: auto;
  padding-right: 2px;
}
.pal-group { margin-bottom: 0.55rem; }
.pal-group:last-child { margin-bottom: 0; }
.pal-group-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem;
  color: var(--plum-2);
  margin-bottom: 0.25rem;
  position: sticky;
  top: 0;
  background: #fff;
  padding: 0.1rem 0;
  z-index: 1;
}
.pal-group-key {
  font-family: var(--font-mono);
  font-weight: 800;
  color: var(--sakura-deep);
  background: var(--sakura-glow);
  border-radius: 4px;
  padding: 0 0.3rem;
}
.pal-group-n { margin-left: auto; color: var(--plum-3); font-family: var(--font-mono); }
.palette-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(20px, 1fr));
  gap: 3px;
}
.pal-swatch {
  aspect-ratio: 1;
  border: 1.5px solid rgba(0,0,0,0.08);
  border-radius: 4px;
  cursor: pointer;
  padding: 0;
  transition: transform var(--transition-fast);
  position: relative;
}
.pal-swatch:hover { transform: scale(1.25); z-index: 2; }
.pal-swatch.used::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 3px;
  box-shadow: inset 0 0 0 1.5px rgba(255,255,255,0.85);
}
.pal-swatch.on {
  box-shadow: 0 0 0 2.5px var(--sakura);
  transform: scale(1.2);
  z-index: 3;
}

.color-list { max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 1px; }
.color-row {
  display: grid;
  grid-template-columns: 18px 42px 1fr auto;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.3rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}
.color-row:hover { background: var(--sakura-glow); }
.cl-swatch { width: 16px; height: 16px; border-radius: 4px; border: 1px solid rgba(0,0,0,0.1); }
.cl-code { font-size: 0.72rem; color: var(--plum-2); }
.cl-name { font-size: 0.76rem; color: var(--plum-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cl-count { font-size: 0.74rem; color: var(--sakura-deep); font-weight: 700; }

.gap-block { margin-bottom: 0.6rem; }
.gap-block:last-child { margin-bottom: 0; }
.gap-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.3rem; }
.gap-tier { font-size: 0.8rem; font-weight: 700; color: var(--plum-1); font-family: var(--font-round); }
.gap-stat { font-size: 0.72rem; font-weight: 700; color: var(--bad); }
.gap-stat.ok { color: var(--ok); }
.gap-pairs {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 150px;
  overflow-y: auto;
}
.gap-pair {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 1px 0;
}
.gap-swatch {
  width: 15px; height: 15px;
  border-radius: 4px;
  border: 1px solid rgba(0,0,0,0.12);
  flex-shrink: 0;
}
.gap-swatch.miss {
  border-style: dashed;
  border-color: var(--bad);
}
.gap-arrow { font-size: 0.7rem; color: var(--plum-3); }
.gap-sub-code { font-size: 0.66rem; color: var(--plum-2); }

/* ===== bead-size toggle ===== */
.bead-size-toggle {
  display: inline-flex;
  gap: 2px;
  background: var(--cream-2);
  border-radius: var(--radius-pill);
  padding: 2px;
}
.pill-btn {
  padding: 0.25rem 0.65rem;
  border: 2px solid transparent;
  background: transparent;
  border-radius: var(--radius-pill);
  font-family: var(--font-round);
  font-weight: 700;
  font-size: 0.78rem;
  color: var(--plum-3);
  cursor: pointer;
  transition: all var(--transition-fast);
  line-height: 1.3;
}
.pill-btn.on {
  background: #fff;
  border-color: var(--sakura);
  color: var(--sakura-deep);
  box-shadow: 0 2px 6px var(--sakura-glow);
}
.pill-btn:hover:not(.on) { color: var(--plum-1); }
.pill-sub {
  font-size: 0.62rem;
  padding: 0.25rem 0.4rem;
  opacity: 0.5;
  min-width: 20px;
}
.pill-sub:hover { opacity: 1; }

/* ===== reference image overlay ===== */
.ref-section {
  padding: 0.35rem 0.75rem;
  border-top: 2px dashed var(--line-strong);
  background: var(--cream-2);
}
.ref-toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--plum-2);
  user-select: none;
}
.ref-toggle-icon { font-size: 0.65rem; }
.ref-badge {
  font-size: 0.65rem;
  background: var(--sakura-glow);
  color: var(--sakura-deep);
  padding: 0.05rem 0.5rem;
  border-radius: var(--radius-pill);
}
.ref-body {
  margin-top: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.ref-upload {
  border: 2px dashed var(--cream-4);
  border-radius: var(--radius-md);
  padding: 0.4rem 0.85rem;
  cursor: pointer;
  font-size: 0.78rem;
  color: var(--plum-3);
  text-align: center;
  transition: border var(--transition-fast);
}
.ref-upload:hover { border-color: var(--sakura-light); }
.ref-thumb {
  width: 42px; height: 42px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--cream-4);
}
.ref-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.ref-slider-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.72rem;
  color: var(--plum-3);
}
.ref-slider { width: 80px; }
.ref-lock-btn {
  background: none;
  border: 1.5px solid var(--cream-4);
  border-radius: var(--radius-sm);
  padding: 0.1rem 0.35rem;
  cursor: pointer;
  font-size: 0.9rem;
  line-height: 1;
  transition: all var(--transition-fast);
}
.ref-lock-btn.locked { border-color: var(--sakura); background: var(--sakura-glow); }

/* ===== palette mode toggle ===== */
.mode-toggle {
  display: inline-flex;
  gap: 2px;
  background: var(--cream-2);
  border-radius: var(--radius-pill);
  padding: 2px;
}

/* auto-subject checkbox */
.subj-check {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
  color: var(--plum-2);
  cursor: pointer;
  user-select: none;
}
.subj-check input { cursor: pointer; }
.mode-btn {
  padding: 0.28rem 0.75rem;
  border: 2px solid transparent;
  background: transparent;
  border-radius: var(--radius-pill);
  font-family: var(--font-round);
  font-weight: 700;
  font-size: 0.8rem;
  color: var(--plum-3);
  cursor: pointer;
  transition: all var(--transition-fast);
  line-height: 1.3;
}
.mode-btn.on {
  background: #fff;
  border-color: var(--sakura);
  color: var(--sakura-deep);
  box-shadow: 0 2px 6px var(--sakura-glow);
}
.mode-btn:hover:not(.on) { color: var(--plum-1); }

/* ===== my palette side card ===== */
.my-pal-card .my-pal-mode {
  margin-bottom: 0.6rem;
}
.my-pal-pick-btn {
  width: 100%;
  margin-bottom: 0.5rem;
}
.my-pal-add {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.4rem;
}
.my-pal-input { flex: 1; min-width: 0; font-family: var(--font-mono); text-transform: uppercase; }
.my-pal-actions {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}
.my-pal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(42px, 1fr));
  gap: 4px;
  max-height: 240px;
  overflow-y: auto;
  padding-right: 2px;
}
.my-pal-chip {
  aspect-ratio: 1;
  border: 1.5px solid rgba(0,0,0,0.12);
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  font-family: var(--font-mono);
  font-weight: 800;
  padding: 0;
  transition: transform var(--transition-fast);
}
.my-pal-chip:hover { transform: scale(1.1); z-index: 2; }
.chip-code { font-size: 0.62rem; line-height: 1; }
.chip-x {
  font-size: 0.5rem;
  line-height: 1;
  opacity: 0;
  transition: opacity var(--transition-fast);
}
.my-pal-chip:hover .chip-x { opacity: 0.85; }

/* "press F for fullscreen" tip — top-right of canvas */
.fs-tip {
  position: absolute;
  top: 12px;
  right: 14px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.8rem 0.45rem 0.55rem;
  background: linear-gradient(135deg, #fff 0%, var(--cream-2) 100%);
  border: 2px solid var(--sakura);
  border-radius: 999px;
  box-shadow: 0 4px 14px rgba(255, 107, 157, 0.25);
  font-family: var(--font-body);
  font-weight: 700;
  font-size: 0.78rem;
  color: var(--plum-1);
  pointer-events: none;
  z-index: 20;
}
.fs-tip-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.4rem;
  height: 1.4rem;
  padding: 0 0.4rem;
  background: var(--sakura);
  color: #fff;
  border-radius: 6px;
  font-family: var(--font-mono);
  font-weight: 800;
  font-size: 0.8rem;
  box-shadow: 0 2px 0 #d75d8a;
}
.fs-tip-text { white-space: nowrap; }
.fs-tip-enter-active, .fs-tip-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fs-tip-enter-from { opacity: 0; transform: translateY(-6px) scale(0.92); }
.fs-tip-leave-to   { opacity: 0; transform: translateY(-4px) scale(0.96); }
</style>
