/* ================================================================
   像素艺术风格调色板 — 转换前量化用
   ================================================================ */

export interface PixelPalette {
  id: string
  name: string
  description: string
  colors: string[]
}

export type StylePaletteId = 'none' | 'minecraft' | 'stardew' | 'pico8' | 'gameboy' | 'nes' | 'db16' | 'db32'

export const STYLE_PALETTES: Record<StylePaletteId, PixelPalette | null> = {
  none: null,
  minecraft: {
    id: 'minecraft',
    name: 'Minecraft',
    description: 'Minecraft 混凝土/羊毛色板',
    colors: [
      '#FFFFFF','#DBD4C8','#B8A894','#6B5434','#3C2F1C',
      '#A0A0A0','#707070','#404040','#202020','#000000',
      '#7FB238','#4C7F2A','#2E5218','#547F7F','#3F5E5E',
      '#7F7FBF','#5454A0','#000060','#BF6E3F','#8F4A1F',
      '#5F2E00','#FF6F00','#BF5400','#7F3F00','#FFA87F',
      '#FF7F3F','#BF5420','#7F3F20','#FF7FA0','#FF4070',
      '#BF1F3F','#7F1030','#BFA0FF','#8060D0','#4020A0',
      '#FFC0FF','#FF80D0','#BF40A0','#7F2060','#FFF5E0',
    ],
  },
  stardew: {
    id: 'stardew',
    name: 'Stardew Valley',
    description: '星露谷物语代表性色板',
    colors: [
      '#000000','#38211D','#5B2E24','#8B4A35','#B66B47',
      '#DA8C5A','#F5B572','#FFDCA8','#CBE6B0','#8DC36C',
      '#589A3D','#327126','#1D4A1A','#B5D2E8','#6EA8D4',
      '#3579A8','#1B457A','#FFF9AE','#F5D742','#D6A02B',
      '#AB641A','#5C3310','#F09F9F','#D06A6A','#A83C3C',
      '#6E1C1C','#D8A0D8','#AC70B8','#7C4890','#542C60',
      '#E8D8C8','#C0ACA0','#908070','#605048','#403830',
      '#F0E8D8',
    ],
  },
  pico8: {
    id: 'pico8',
    name: 'PICO-8',
    description: 'PICO-8 Fantasy Console 16 色调色板',
    colors: [
      '#000000','#1D2B53','#7E2553','#008751','#AB5236',
      '#5F574F','#C2C3C7','#FFF1E8','#FF004D','#FFA300',
      '#FFEC27','#00E436','#29ADFF','#83769C','#FF77A8',
      '#FFCCAA',
    ],
  },
  gameboy: {
    id: 'gameboy',
    name: 'Game Boy',
    description: 'Game Boy 4 阶灰度绿',
    colors: ['#0F380F','#306230','#8BAC0F','#9BBC0F'],
  },
  nes: {
    id: 'nes',
    name: 'NES',
    description: 'NES / FC 8-bit 标准色板',
    colors: [
      '#585858','#0022A0','#1A3EB0','#3A2EB0','#5A1AA0','#6E0070',
      '#680040','#50001A','#3C0800','#301800','#282800','#003400',
      '#003A1A','#003A38','#000048','#000000',
      '#A8A8A8','#1050D0','#3070E0','#5050E0','#7830D0','#9000A0',
      '#900060','#781840','#603800','#485000','#386000','#006C00',
      '#007040','#00706A','#202078','#202020',
      '#F8F8F8','#6090F8','#78A8FF','#8888FF','#B068F8','#D060F8',
      '#D060A0','#C06858','#A07840','#888800','#689800','#40A828',
      '#28B060','#28B088','#4860A0','#686868',
      '#F8F8F8','#B8D8F8','#C8D8FF','#D0C8FF','#E0B8FF','#F0B0F8',
      '#F0B0C8','#F0B8A0','#F0C090','#D0D060','#B8D858','#A0E060',
      '#90E0A0','#90E0C8','#A0B0D0','#C0C0C0',
    ],
  },
  db16: {
    id: 'db16',
    name: 'DawnBringer 16',
    description: 'DawnBringer 经典 16 色像素画色板',
    colors: [
      '#140C1C','#442434','#30346D','#4E4A4E','#854C30',
      '#346524','#D04648','#757161','#597DCE','#D27D2C',
      '#8595A1','#6DAA2C','#D2AA99','#6DC2CA','#DAD45E',
      '#DEEED6',
    ],
  },
  db32: {
    id: 'db32',
    name: 'DawnBringer 32',
    description: 'DawnBringer 32 色扩展像素画色板',
    colors: [
      '#280B2B','#442434','#653854','#7B3E5C','#A54864',
      '#CD5D6D','#E0826F','#F5C17A','#FDEDA0','#C1D98C',
      '#7BB274','#42633B','#233D27','#2D5A5C','#38837A',
      '#50A88C','#70CBB4','#9AE1CA','#BDF0DA','#68A7D8',
      '#3F7EB3','#2B5580','#1C334F','#1B213E','#20206A',
      '#38388C','#564E9E','#826DAE','#9E91C0','#A5A5C4',
      '#B5B5C4','#C0C0C0',
    ],
  },
}

export const STYLE_OPTIONS: { id: StylePaletteId; label: string; colors: number }[] = [
  { id: 'none',      label: '无（原始颜色）', colors: 0 },
  { id: 'minecraft', label: 'Minecraft',       colors: 40 },
  { id: 'stardew',   label: 'Stardew Valley',  colors: 36 },
  { id: 'pico8',     label: 'PICO-8',          colors: 16 },
  { id: 'gameboy',   label: 'Game Boy',        colors: 4 },
  { id: 'nes',       label: 'NES 8-bit',       colors: 56 },
  { id: 'db16',      label: 'DB16',            colors: 16 },
  { id: 'db32',      label: 'DB32',            colors: 32 },
]
