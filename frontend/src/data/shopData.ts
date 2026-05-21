/* ================================================================
   拼豆购买链接数据 — 淘宝 / 天猫 / 拼多多 / 京东
   价格仅供参考，实际以店铺页面为准。
   ================================================================ */

export interface ShopItem {
  id: string
  platform: '淘宝' | '天猫' | '拼多多' | '京东'
  shopName: string
  productName: string
  type: 'refill' | 'fullset' | 'individual' | 'tool'
  price: number
  url: string
  applicableCodes: string[]
  description?: string
}

export const SHOP_ITEMS: ShopItem[] = [
  // ===== 天猫 / MARD 旗舰店 =====
  { id: 'tmall-01', platform: '天猫', shopName: 'MARD 旗舰店', productName: 'MARD 拼豆 221 色全套补充包', type: 'fullset', price: 128, url: 'https://detail.tmall.com/item.htm?id=10001', applicableCodes: [], description: '标准 221 色盒装，每色约 50 颗' },
  { id: 'tmall-02', platform: '天猫', shopName: 'MARD 旗舰店', productName: 'MARD 拼豆 72 色入门套装', type: 'fullset', price: 49.9, url: 'https://detail.tmall.com/item.htm?id=10002', applicableCodes: [], description: '72 色精选入门' },
  { id: 'tmall-03', platform: '天猫', shopName: 'MARD 旗舰店', productName: 'MARD 拼豆 A 系列补充包（26 色）', type: 'refill', price: 22.9, url: 'https://detail.tmall.com/item.htm?id=10003', applicableCodes: ['A1','A2','A3','A4','A5','A6','A7','A8','A9','A10','A11','A12','A13','A14','A15','A16','A17','A18','A19','A20','A21','A22','A23','A24','A25','A26'] },
  { id: 'tmall-04', platform: '天猫', shopName: 'MARD 旗舰店', productName: 'MARD 拼豆 B 系列补充包（32 色）', type: 'refill', price: 26.9, url: 'https://detail.tmall.com/item.htm?id=10004', applicableCodes: ['B1','B2','B3','B4','B5','B6','B7','B8','B9','B10','B11','B12','B13','B14','B15','B16','B17','B18','B19','B20','B21','B22','B23','B24','B25','B26','B27','B28','B29','B30','B31','B32'] },
  { id: 'tmall-05', platform: '天猫', shopName: 'MARD 旗舰店', productName: 'MARD 拼豆 291 色大全套', type: 'fullset', price: 259, url: 'https://detail.tmall.com/item.htm?id=10005', applicableCodes: [], description: '全 291 色豪华盒装，含所有扩充色号' },

  // ===== 淘宝店铺 =====
  { id: 'tb-01', platform: '淘宝', shopName: '豆豆工坊', productName: 'MARD 拼豆散珠自选色', type: 'individual', price: 3.5, url: 'https://item.taobao.com/item.htm?id=20001', applicableCodes: [], description: '可按色号选购，100 颗/袋' },
  { id: 'tb-02', platform: '淘宝', shopName: '豆豆工坊', productName: 'MARD 拼豆 72 色塑料收纳盒套装', type: 'fullset', price: 68, url: 'https://item.taobao.com/item.htm?id=20002', applicableCodes: [], description: '含收纳盒、镊子、模板' },
  { id: 'tb-03', platform: '淘宝', shopName: '拼豆乐园', productName: 'MARD 拼豆补充包 C 系列（29 色）', type: 'refill', price: 24.9, url: 'https://item.taobao.com/item.htm?id=20003', applicableCodes: ['C1','C2','C3','C4','C5','C6','C7','C8','C9','C10','C11','C12','C13','C14','C15','C16','C17','C18','C19','C20','C21','C22','C23','C24','C25','C26','C27','C28','C29'] },
  { id: 'tb-04', platform: '淘宝', shopName: '拼豆乐园', productName: 'MARD 拼豆补充包 D 系列（26 色）', type: 'refill', price: 22.9, url: 'https://item.taobao.com/item.htm?id=20004', applicableCodes: ['D1','D2','D3','D4','D5','D6','D7','D8','D9','D10','D11','D12','D13','D14','D15','D16','D17','D18','D19','D20','D21','D22','D23','D24','D25','D26'] },
  { id: 'tb-05', platform: '淘宝', shopName: '拼豆乐园', productName: 'MARD 拼豆 E/F/G 系列补充包', type: 'refill', price: 59.9, url: 'https://item.taobao.com/item.htm?id=20005', applicableCodes: [], description: '含 E 系 24 色 + F 系 25 色 + G 系 21 色，共 70 色' },
  { id: 'tb-06', platform: '淘宝', shopName: 'DIY 手作屋', productName: 'MARD 拼豆 H/M 莫兰迪补充包', type: 'refill', price: 35.9, url: 'https://item.taobao.com/item.htm?id=20006', applicableCodes: [], description: 'H 系 23 色（黑白灰）+ M 系 15 色（莫兰迪）' },

  // ===== 拼多多 =====
  { id: 'pdd-01', platform: '拼多多', shopName: '豆豆家拼豆', productName: 'MARD 拼豆 72 色入门套装', type: 'fullset', price: 39.9, url: 'https://mobile.yangkeduo.com/goods1.html', applicableCodes: [], description: '超高性价比入门套装' },
  { id: 'pdd-02', platform: '拼多多', shopName: '豆豆家拼豆', productName: 'MARD 拼豆 221 色标准补充包', type: 'fullset', price: 99, url: 'https://mobile.yangkeduo.com/goods2.html', applicableCodes: [], description: '标准 221 色，量大实惠' },
  { id: 'pdd-03', platform: '拼多多', shopName: '豆豆家拼豆', productName: 'MARD 拼豆单色补充（50 颗/袋）', type: 'individual', price: 1.99, url: 'https://mobile.yangkeduo.com/goods3.html', applicableCodes: [], description: '单色 50 颗装，任选色号' },
  { id: 'pdd-04', platform: '拼多多', shopName: '手作拼豆坊', productName: 'MARD 拼豆 P/Q/R 扩充系列（56 色）', type: 'refill', price: 49.9, url: 'https://mobile.yangkeduo.com/goods4.html', applicableCodes: [], description: '扩充系列补充包' },

  // ===== 京东 =====
  { id: 'jd-01', platform: '京东', shopName: 'MARD 官方旗舰店', productName: 'MARD 拼豆 221 色标准盒装', type: 'fullset', price: 139, url: 'https://item.jd.com/30001.html', applicableCodes: [], description: '京东自营，次日达' },
  { id: 'jd-02', platform: '京东', shopName: 'MARD 官方旗舰店', productName: 'MARD 拼豆工具套装（镊子+模板+熨斗纸）', type: 'tool', price: 29.9, url: 'https://item.jd.com/30002.html', applicableCodes: [] },
  { id: 'jd-03', platform: '京东', shopName: 'MARD 官方旗舰店', productName: 'MARD 拼豆 264 色大全套', type: 'fullset', price: 189, url: 'https://item.jd.com/30003.html', applicableCodes: [], description: '264 色，含扩充系列' },
]

export function filterByUsedColors(items: ShopItem[], usedColors: Set<string>): ShopItem[] {
  return items.filter(item =>
    item.applicableCodes.length === 0 ||
    item.applicableCodes.some(c => usedColors.has(c)),
  )
}

export const PLATFORMS: { id: string; label: string; icon: string }[] = [
  { id: '淘宝', label: '淘宝', icon: '🛒' },
  { id: '天猫', label: '天猫', icon: '🏪' },
  { id: '拼多多', label: '拼多多', icon: '🛍' },
  { id: '京东', label: '京东', icon: '📦' },
]
