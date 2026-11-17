export type ScenicGalleryPhoto = {
  id: string
  src: string
  caption: string
  /** 拍摄位置/角度说明，显示在大图查看器的辅助行 */
  note: string
}

export type ScenicFact = {
  label: string
  value: string
}

export type ScenicDetail = {
  spotId: string
  name: string
  /** 英文名用于大字副标题的排版装饰 */
  nameEn: string
  tagline: string
  intro: string[]
  facts: ScenicFact[]
  tip: string
  hero: { src: string; position: string }
  gallery: ScenicGalleryPhoto[]
  audio: { title: string; seconds: number; script: string }
}

const seventeenArchBridge: ScenicDetail = {
  spotId: 'seventeen-arch-bridge',
  name: '十七孔桥',
  nameEn: 'Seventeen-Arch Bridge',
  tagline: '连接东堤与南湖岛的一段水上风景。',
  intro: [
    '十七孔桥坐落在昆明湖东南水域，东接东堤，西连南湖岛，是颐和园里最长的一座石桥。桥身由十七个桥洞组成，正中的桥洞最高，向两侧依次降低，远远看过去像一条落在湖面上的弧线。',
    '桥栏上共有五百多只石狮子，姿态各不相同，靠近中心的一侧雕刻更精细。站在桥上看，湖面开阔，万寿山和佛香阁就在西北方向；走到南湖岛上回头，桥和昆明湖又能排出另一种构图。',
    '每年冬至前后，落日会穿过十七个桥洞，在湖面留下金色的光柱，人们把它叫作“金光穿洞”。傍晚顺光的时候，桥身和湖水会一起变成暖金色。'
  ],
  facts: [
    { label: '始建', value: '1750 年' },
    { label: '桥孔', value: '17 孔' },
    { label: '石狮', value: '544 只' },
    { label: '全长', value: '约 150 米' }
  ],
  tip: '想看“金光穿洞”，冬至前后下午来，站到东堤一侧的湖边，桥洞和落日会对成一条线。',
  hero: { src: '/scenic/enhanced/seventeen-arch-bridge.jpg', position: 'center 62%' },
  gallery: [
    { id: 'bridge-dusk', src: '/scenic/enhanced/seventeen-arch-bridge.jpg', caption: '十七孔桥 · 落日把桥洞染成金色', note: '东堤一侧，傍晚顺光' },
    { id: 'kunming-lake', src: '/scenic/enhanced/kunming-lake.jpg', caption: '昆明湖 · 从万寿山南望', note: '万寿山前山' },
    { id: 'bronze-ox', src: '/scenic/enhanced/bronze-ox.jpg', caption: '铜牛 · 雪后望向西山', note: '东堤北端' },
    { id: 'south-lake-island', src: '/scenic/enhanced/south-lake-island.jpg', caption: '南湖岛 · 涵虚堂的雪', note: '湖心岛上' },
    { id: 'long-corridor', src: '/scenic/enhanced/long-corridor.jpg', caption: '长廊 · 彩画与红灯笼', note: '长廊中段' },
    { id: 'jade-belt-bridge', src: '/scenic/enhanced/jade-belt-bridge.jpg', caption: '玉带桥 · 水面上的圆', note: '昆明湖西侧' },
    { id: 'wenchang-pavilion', src: '/scenic/enhanced/wenchang-pavilion.jpg', caption: '文昌阁 · 东堤边的楼阁', note: '东堤与文昌阁之间' },
    { id: 'marble-boat', src: '/scenic/enhanced/marble-boat.jpg', caption: '石舫 · 昆明湖畔', note: '万寿山西侧' }
  ],
  audio: {
    title: '十七孔桥讲解',
    seconds: 96,
    script:
      '这里是十七孔桥。它东接东堤，西连南湖岛，是颐和园里最长的一座石桥。桥身有十七个桥洞，正中的桥洞最高，向两侧依次降低。桥栏上有五百多只石狮子，姿态各不相同。每年冬至前后，落日会穿过桥洞，湖面上会出现“金光穿洞”。'
  }
}

export const scenicDetails: Record<string, ScenicDetail> = {
  'seventeen-arch-bridge': seventeenArchBridge
}

export function getScenicDetail(spotId?: string): ScenicDetail {
  return (spotId && scenicDetails[spotId]) || seventeenArchBridge
}
