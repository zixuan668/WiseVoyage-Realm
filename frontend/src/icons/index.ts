import { defineComponent, h } from 'vue'
import catalog from '../../../shared/ui-icons.json'

type IconNode = [string, Record<string, string>]
const icons = catalog.icons as unknown as Record<string, IconNode[]>
function createIcon(icon: string, name: string) {
  return defineComponent({
    name,
    inheritAttrs: false,
    props: { size: { type: [Number, String], default: '1em' }, title: { type: String, default: '' } },
    setup(props, { attrs }) {
      return () => h('svg', {
        xmlns: 'http://www.w3.org/2000/svg', width: props.size, height: props.size,
        viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.5,
        'stroke-linecap': 'round', 'stroke-linejoin': 'round', focusable: 'false',
        'aria-hidden': props.title || attrs['aria-label'] ? undefined : 'true',
        role: props.title || attrs['aria-label'] ? 'img' : undefined,
        ...attrs, class: ['ui-icon', attrs.class], 'data-icon': icon,
      }, [
        ...(props.title ? [h('title', props.title)] : []),
        ...icons[icon].map(([tag, attributes]) => h(tag, { ...attributes, 'vector-effect': 'non-scaling-stroke' })),
      ])
    },
  })
}

export const ArrowDown = createIcon('chevron-down', 'ArrowDown')
export const ArrowLeft = createIcon('arrow-left', 'ArrowLeft')
export const ArrowRight = createIcon('arrow-right', 'ArrowRight')
export const ArrowUp = createIcon('chevron-up', 'ArrowUp')
export const Bell = createIcon('bell', 'Bell')
export const Bottom = createIcon('arrow-down', 'Bottom')
export const ChatDotRound = createIcon('message-circle', 'ChatDotRound')
export const Check = createIcon('check', 'Check')
export const CircleCheck = createIcon('circle-check', 'CircleCheck')
export const Clock = createIcon('clock', 'Clock')
export const Cloudy = createIcon('cloud', 'Cloudy')
export const Collection = createIcon('bookmark', 'Collection')
export const DataAnalysis = createIcon('chart-no-axes-combined', 'DataAnalysis')
export const Delete = createIcon('trash-2', 'Delete')
export const Document = createIcon('file-text', 'Document')
export const Drizzling = createIcon('cloud-drizzle', 'Drizzling')
export const Edit = createIcon('pencil', 'Edit')
export const Expand = createIcon('panel-left-open', 'Expand')
export const FirstAidKit = createIcon('briefcase-medical', 'FirstAidKit')
export const Fold = createIcon('panel-left-close', 'Fold')
export const Guide = createIcon('compass', 'Guide')
export const House = createIcon('house', 'House')
export const InfoFilled = createIcon('info', 'InfoFilled')
export const Iphone = createIcon('smartphone', 'Iphone')
export const Lightning = createIcon('cloud-lightning', 'Lightning')
export const Loading = createIcon('loader-circle', 'Loading')
export const Location = createIcon('map-pin', 'Location')
export const Lock = createIcon('lock-keyhole', 'Lock')
export const MapLocation = createIcon('map', 'MapLocation')
export const Microphone = createIcon('mic', 'Microphone')
export const Moon = createIcon('moon', 'Moon')
export const Notebook = createIcon('notebook-text', 'Notebook')
export const Picture = createIcon('image', 'Picture')
export const Plus = createIcon('plus', 'Plus')
export const Position = createIcon('navigation', 'Position')
export const QuestionFilled = createIcon('circle-help', 'QuestionFilled')
export const Reading = createIcon('book-open', 'Reading')
export const Refresh = createIcon('refresh-cw', 'Refresh')
export const RefreshRight = createIcon('rotate-cw', 'RefreshRight')
export const Search = createIcon('search', 'Search')
export const Ship = createIcon('ship', 'Ship')
export const Sunny = createIcon('sun', 'Sunny')
export const Top = createIcon('arrow-up', 'Top')
export const Upload = createIcon('upload', 'Upload')
export const User = createIcon('user-round', 'User')
export const UserFilled = createIcon('user-round', 'UserFilled')
export const VideoPlay = createIcon('play', 'VideoPlay')
export const Warning = createIcon('triangle-alert', 'Warning')
export const WarningFilled = createIcon('triangle-alert', 'WarningFilled')
export const ServiceStation = createIcon('map-pin-house', 'ServiceStation')
export const RouteIcon = createIcon('route', 'RouteIcon')
export const Walk = createIcon('footprints', 'Walk')
export const ArrowUpRight = createIcon('arrow-up-right', 'ArrowUpRight')
export const Close = createIcon('x', 'Close')

// Leaflet markers use the same safe, local vector primitives as Vue controls.
export function iconMarkup(icon: string) {
  const escape = (value: string) => value.replace(/&/g, '&amp;').replace(/"/g, '&quot;')
  const body = (icons[icon] || icons['map-pin']).map(([tag, attrs]) =>
    '<' + tag + ' ' + Object.entries(attrs).map(([key, value]) => key + '="' + escape(value) + '"').join(' ') + '/>'
  ).join('')
  return '<svg class="ui-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + body + '</svg>'
}
