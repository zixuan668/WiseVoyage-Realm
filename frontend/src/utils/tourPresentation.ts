import { t } from '@/i18n'
const knowledgeFooter = /\s*以上内容来自景区知识档案[，,]你还可以继续询问更具体的问题[。.]?\s*$/

export function isKnowledgeSourceUrl(value: string) {
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && ['gygl.beijing.gov.cn', 'wwj.beijing.gov.cn',
      'yllhj.beijing.gov.cn', 'www.beijing.gov.cn', 'www.summerpalace.net.cn',
      'www.visitbeijing.com.cn', 'jr.visitbeijing.com.cn', 'mp.visitbeijing.com.cn',
      's.visitbeijing.com.cn', 'www.dpm.org.cn', 'whc.unesco.org'].includes(url.hostname)
  } catch { return false }
}

export function formatTourMessage(message: string, guideReply = false, names: string[] = []) {
  let content = message || ''
  if (guideReply) {
    content = content.replace(knowledgeFooter, '')
    for (const name of names.filter(Boolean)) {
      const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      content = content.replace(new RegExp(t("(^|\\n)\\s*{p0}(?:先生|女士|老师|小朋友)?\\s*[，,：:、]\\s*", {p0: escaped}), 'gm'), '$1')
    }
  }
  return content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;')
    .replace(/\*\*([^\n]+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>')
}
