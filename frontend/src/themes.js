export const DEFAULT_THEME_ID = 'atelier'

export const THEMES = [
  {
    id: 'atelier',
    name: '工坊',
    desc: '暖米轻奢',
    swatch: ['#f7f4ef', '#c45c4a', '#9a6b52'],
    stageBg: '#ffffff',
    thumbBg: '#ffffff',
    boardSolid: '#f7f4ef',
  },
  {
    id: 'noir',
    name: '夜宴',
    desc: '黑金时装',
    swatch: ['#161412', '#d4af67', '#f3eadc'],
    stageBg: '#1c1a17',
    thumbBg: '#1c1a17',
    boardSolid: '#100e0c',
  },
  {
    id: 'studio',
    name: '白场',
    desc: '极简展陈',
    swatch: ['#f5f5f3', '#111111', '#d8d8d4'],
    stageBg: '#ffffff',
    thumbBg: '#ffffff',
    boardSolid: '#f7f7f5',
  },
  {
    id: 'ink',
    name: '宣纸',
    desc: '东方水墨',
    swatch: ['#f3ead9', '#8c2f24', '#1c1a17'],
    stageBg: '#faf6ee',
    thumbBg: '#faf6ee',
    boardSolid: '#f6efe3',
  },
  {
    id: 'live',
    name: '热卖',
    desc: '直播主推',
    swatch: ['#fff4ee', '#e23c2f', '#1a1a1a'],
    stageBg: '#ffffff',
    thumbBg: '#ffffff',
    boardSolid: '#fff8f4',
  },
  {
    id: 'folio',
    name: '刊页',
    desc: '杂志对开',
    swatch: ['#efe8dc', '#2c241c', '#c4a574'],
    stageBg: '#f7f3ec',
    thumbBg: '#ffffff',
    boardSolid: '#ffffff',
  },
]

export const THEME_MAP = Object.fromEntries(THEMES.map((item) => [item.id, item]))

export function resolveThemeId(id) {
  return THEME_MAP[id] ? id : DEFAULT_THEME_ID
}
