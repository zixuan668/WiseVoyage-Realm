<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import {
  listStationAdmin,
  saveStationAdmin,
  stationError,
  type StationAdmin,
  type StationAdminData
} from '@/api/serviceStation'
import { locale, t } from '@/i18n'
const S = (zh: string, en: string) => (locale.value === 'en' ? en : zh)
const data = ref<StationAdminData | null>(null),
  draft = ref<StationAdmin | null>(null),
  selected = ref(''),
  newId = ref(''),
  error = ref(''),
  message = ref(''),
  loading = ref(false),
  saving = ref(false),
  locationChecked = ref(false)
const stationUrl = computed(() => (draft.value ? '/station/' + draft.value.station_id : ''))
type Tab = 'basic' | 'notices' | 'facilities' | 'more'
const activeTab = ref<Tab>('basic')
const editorBody = ref<HTMLElement | null>(null)
const showCreate = ref(false)
const newError = ref('')
const tabs = computed(() => [
  { key: 'basic' as Tab, label: S('基本信息', 'General') },
  { key: 'notices' as Tab, label: S('公告', 'Notices') },
  { key: 'facilities' as Tab, label: S('设施', 'Facilities') },
  { key: 'more' as Tab, label: S('更多设置', 'More settings') }
])
const needsLocationCheck = computed(() => {
  if (!draft.value || draft.value.demo) return false
  const original = data.value?.stations.find((row) => row.station_id === selected.value)
  return !original || original.demo || original.anchor_key !== draft.value.anchor_key
})
function selectTab(tab: Tab) {
  activeTab.value = tab
  void nextTick(() => {
    if (editorBody.value) editorBody.value.scrollTop = 0
  })
}
function openCreate() {
  newId.value = ''
  newError.value = ''
  showCreate.value = true
}
function choose(id: string, resetTab = true) {
  const row = data.value?.stations.find((s) => s.station_id === id)
  if (row) {
    draft.value = JSON.parse(JSON.stringify(row))
    selected.value = id
    if (resetTab) selectTab('basic')
    locationChecked.value = false
    error.value = ''
    message.value = ''
  }
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await listStationAdmin()
    choose(selected.value || data.value.stations[0]?.station_id || '', false)
  } catch (e) {
    error.value = stationError(e)
  } finally {
    loading.value = false
  }
}
function add() {
  newId.value = newId.value.trim()
  if (!/^[a-z0-9-]{1,60}$/.test(newId.value)) {
    newError.value = S(
      '编号仅支持小写字母、数字和短横线。',
      'Use lowercase letters, numbers and hyphens for the ID.'
    )
    return
  }
  if (data.value?.stations.some((s) => s.station_id === newId.value)) {
    choose(newId.value)
    showCreate.value = false
    return
  }
  draft.value = {
    station_id: newId.value,
    name: '新的数字人服务站',
    name_en: 'Digital Service Station',
    location: '',
    location_en: 'Configure the station location',
    anchor_key: 'gate:east',
    guide_id: 0,
    default_language: 'zh',
    welcome: '您好，我是本站数字接待员，可以为您咨询和规划游览。',
    welcome_en: 'Welcome. I can answer questions and plan a walk from this station.',
    idle_seconds: 120,
    volume: 0.7,
    enabled: true,
    demo: true,
    revision: 0,
    announcements: [],
    facilities: [],
    last_seen: null,
    updated_at: ''
  }
  selected.value = ''
  error.value = ''
  message.value = ''
  locationChecked.value = false
  newId.value = ''
  showCreate.value = false
  selectTab('basic')
}
async function save() {
  if (!draft.value || saving.value) return
  error.value = ''
  message.value = ''
  if (!validate()) return
  saving.value = true
  error.value = ''
  message.value = ''
  try {
    const saved = await saveStationAdmin(draft.value.station_id, {
      ...draft.value,
      location_checked: locationChecked.value
    })
    selected.value = saved.station_id
    await load()
    if (!error.value) message.value = S('配置已保存并发布。', 'Configuration saved and published.')
  } catch (e) {
    error.value = stationError(e)
  } finally {
    saving.value = false
  }
}
function addFacility() {
  if (draft.value)
    draft.value.facilities.push({
      key: 'facility-' + Date.now(),
      name: '',
      name_en: '',
      kind: 'service',
      anchor_key: draft.value.anchor_key,
      verified: false,
      status: 'unknown',
      source: ''
    })
}
function online(value: string | null) {
  return !!value && Date.now() - Date.parse(value + 'Z') < 90000
}
function invalid(tab: Tab, text: string) {
  error.value = text
  selectTab(tab)
  return false
}
function validate() {
  const value = draft.value
  if (!value) return false
  if (![value.name, value.location, value.welcome].every((text) => text.trim()))
    return invalid(
      'basic',
      S('请填写名称、位置和欢迎语。', 'Complete the name, location and welcome.')
    )
  if (needsLocationCheck.value && !locationChecked.value)
    return invalid(
      'basic',
      S('请先核实设备位置和步行起点。', 'Verify the device location and walking origin.')
    )
  if (![value.name_en, value.location_en, value.welcome_en].every((text) => text.trim()))
    return invalid(
      'more',
      S('请补全英文名称、位置和欢迎语。', 'Complete the English name, location and welcome.')
    )
  if (
    !Number.isFinite(value.idle_seconds) ||
    value.idle_seconds < 60 ||
    value.idle_seconds > 600 ||
    !Number.isFinite(value.volume) ||
    value.volume < 0 ||
    value.volume > 1
  )
    return invalid(
      'more',
      S('复位时间应为 60–600 秒，音量应为 0–1。', 'Idle timeout: 60–600 seconds. Volume: 0–1.')
    )
  if (value.announcements.some((notice) => !notice.text.trim() || !notice.text_en.trim()))
    return invalid(
      'notices',
      S('请补全公告的中文和英文内容。', 'Complete both languages for every notice.')
    )
  if (
    value.facilities.some(
      (facility) => !facility.name.trim() || !facility.name_en.trim() || !facility.source.trim()
    )
  )
    return invalid(
      'facilities',
      S('请补全设施名称和核实来源。', 'Complete facility names and verification sources.')
    )
  return true
}
function localExpiry(value: string) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? ''
    : new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
function isoExpiry(value: string) {
  return value ? new Date(value).toISOString() : ''
}
onMounted(load)
</script>
<template>
  <main class="station-admin">
    <header class="station-admin-heading">
      <h1>{{ S('服务站管理', 'Service stations') }}</h1>
      <div class="heading-actions">
        <button type="button" @click="load" :disabled="loading || saving">
          {{ S('刷新', 'Refresh') }}
        </button>
        <button type="button" class="primary" @click="openCreate" :disabled="saving">
          ＋ {{ S('新增服务站', 'Add station') }}
        </button>
      </div>
    </header>
    <p v-if="error" class="admin-error" role="alert">{{ t(error) }}</p>
    <p v-if="message" class="admin-success" role="status">{{ message }}</p>
    <div class="station-admin-grid">
      <aside class="station-list-panel" :aria-label="S('服务站列表', 'Station list')">
        <h2>{{ S('服务站', 'Stations') }}</h2>
        <div class="station-list">
          <button
            v-for="row in data?.stations"
            :key="row.station_id"
            type="button"
            class="station-choice"
            :aria-pressed="draft?.station_id === row.station_id"
            :disabled="saving"
            @click="choose(row.station_id)"
          >
            <strong>{{ locale === 'en' ? row.name_en : row.name }}</strong>
            <span
              ><i :class="{ online: online(row.last_seen) }"></i
              >{{ online(row.last_seen) ? S('在线', 'Online') : S('离线', 'Offline') }} ·
              {{ row.enabled ? S('已启用', 'Enabled') : S('已停用', 'Disabled') }}</span
            >
          </button>
          <p v-if="!data?.stations.length" class="empty-state">
            {{ loading ? S('正在读取…', 'Loading…') : S('暂无服务站', 'No stations') }}
          </p>
        </div>
      </aside>
      <form v-if="draft" class="station-form" @submit.prevent="save">
        <div class="editor-heading">
          <h2>
            {{
              selected
                ? locale === 'en'
                  ? draft.name_en
                  : draft.name
                : S('新增服务站', 'New station')
            }}
          </h2>
          <a v-if="selected" :href="stationUrl" target="_blank" rel="noopener noreferrer"
            >{{ S('查看页面', 'View station') }} ↗</a
          >
        </div>
        <div class="station-tabs" role="tablist" :aria-label="S('配置分类', 'Settings categories')">
          <button
            v-for="tab in tabs"
            :id="'station-tab-' + tab.key"
            :key="tab.key"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.key"
            :aria-controls="'station-panel-' + tab.key"
            @click="selectTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>
        <div
          :id="'station-panel-' + activeTab"
          ref="editorBody"
          class="station-form-body"
          role="tabpanel"
          :aria-labelledby="'station-tab-' + activeTab"
        >
          <section v-if="activeTab === 'basic'" class="admin-fields">
            <label
              >{{ S('服务站名称', 'Station name')
              }}<input v-model="draft.name" required maxlength="80"
            /></label>
            <label
              >{{ S('设备位置', 'Device location')
              }}<input v-model="draft.location" required maxlength="160"
            /></label>
            <label
              >{{ S('步行起点', 'Walking origin')
              }}<select v-model="draft.anchor_key">
                <option v-for="anchor in data?.anchors" :key="anchor.key" :value="anchor.key">
                  {{ t(anchor.label) }}
                </option>
              </select></label
            >
            <label
              >{{ S('数字接待员', 'Digital receptionist')
              }}<select v-model.number="draft.guide_id">
                <option :value="0">{{ S('自动选择', 'Automatic') }}</option>
                <option v-for="guide in data?.guides" :key="guide.guide_id" :value="guide.guide_id">
                  {{ t(guide.name) }}
                </option>
              </select></label
            >
            <label class="full-width"
              >{{ S('欢迎语', 'Welcome message')
              }}<textarea v-model="draft.welcome" required maxlength="500" rows="3" />
            </label>
            <div class="admin-checks full-width">
              <label
                ><input v-model="draft.enabled" type="checkbox" />{{
                  S('启用服务站', 'Enable station')
                }}</label
              >
              <label
                ><input v-model="draft.demo" type="checkbox" />{{
                  S('示范点位', 'Demonstration')
                }}</label
              >
              <label v-if="needsLocationCheck"
                ><input v-model="locationChecked" type="checkbox" />{{
                  S('已核实设备位置和步行起点', 'Location and walking access verified')
                }}</label
              >
            </div>
          </section>
          <section v-else-if="activeTab === 'notices'">
            <div class="admin-section-heading">
              <h3>{{ S('服务公告', 'Station notices') }}</h3>
              <button
                type="button"
                :disabled="draft.announcements.length >= 8"
                @click="draft.announcements.push({ text: '', text_en: '', expires_at: '' })"
              >
                ＋ {{ S('添加公告', 'Add notice') }}
              </button>
            </div>
            <p v-if="!draft.announcements.length" class="empty-state">
              {{ S('暂无公告', 'No notices') }}
            </p>
            <article
              v-for="(notice, index) in draft.announcements"
              :key="index"
              class="admin-entry"
            >
              <div class="admin-section-heading">
                <h3>{{ S('公告', 'Notice') }} {{ index + 1 }}</h3>
                <button
                  type="button"
                  class="remove-entry"
                  @click="draft.announcements.splice(index, 1)"
                >
                  {{ S('删除', 'Remove') }}
                </button>
              </div>
              <div class="admin-fields">
                <label
                  >{{ S('中文内容', 'Chinese text')
                  }}<textarea v-model="notice.text" required maxlength="500" rows="3" />
                </label>
                <label
                  >{{ S('英文内容', 'English text')
                  }}<textarea v-model="notice.text_en" required maxlength="800" rows="3" />
                </label>
                <label
                  >{{ S('截止时间（可选）', 'Expiry (optional)')
                  }}<input
                    type="datetime-local"
                    :value="localExpiry(notice.expires_at)"
                    @input="
                      notice.expires_at = isoExpiry(($event.target as HTMLInputElement).value)
                    "
                /></label>
              </div>
            </article>
          </section>
          <section v-else-if="activeTab === 'facilities'">
            <div class="admin-section-heading">
              <h3>{{ S('设施位置', 'Facility locations') }}</h3>
              <button type="button" :disabled="draft.facilities.length >= 40" @click="addFacility">
                ＋ {{ S('添加设施', 'Add facility') }}
              </button>
            </div>
            <p v-if="!draft.facilities.length" class="empty-state">
              {{ S('暂无设施', 'No facilities') }}
            </p>
            <article
              v-for="(facility, index) in draft.facilities"
              :key="facility.key"
              class="admin-entry"
            >
              <div class="admin-section-heading">
                <h3>{{ S('设施', 'Facility') }} {{ index + 1 }}</h3>
                <button
                  type="button"
                  class="remove-entry"
                  @click="draft.facilities.splice(index, 1)"
                >
                  {{ S('删除', 'Remove') }}
                </button>
              </div>
              <div class="admin-fields">
                <label
                  >{{ S('中文名称', 'Chinese name')
                  }}<input v-model="facility.name" required maxlength="80"
                /></label>
                <label
                  >{{ S('英文名称', 'English name')
                  }}<input v-model="facility.name_en" required maxlength="120"
                /></label>
                <label
                  >{{ S('类别', 'Type')
                  }}<select v-model="facility.kind">
                    <option value="toilet">{{ S('卫生间', 'Restroom') }}</option>
                    <option value="water">{{ S('饮水', 'Drinking water') }}</option>
                    <option value="service">{{ S('服务台', 'Service desk') }}</option>
                    <option value="rest">{{ S('休息点', 'Rest area') }}</option>
                  </select></label
                >
                <label
                  >{{ S('步行接入点', 'Walking access')
                  }}<select v-model="facility.anchor_key">
                    <option v-for="anchor in data?.anchors" :key="anchor.key" :value="anchor.key">
                      {{ t(anchor.label) }}
                    </option>
                  </select></label
                >
                <label
                  >{{ S('开放状态', 'Availability')
                  }}<select v-model="facility.status">
                    <option value="unknown">{{ S('待确认', 'Unconfirmed') }}</option>
                    <option value="open">{{ S('开放', 'Open') }}</option>
                    <option value="closed">{{ S('暂不可用', 'Unavailable') }}</option>
                  </select></label
                >
                <label
                  >{{ S('核实来源', 'Verification source')
                  }}<input v-model="facility.source" required maxlength="200"
                /></label>
              </div>
              <label class="admin-checkbox"
                ><input v-model="facility.verified" type="checkbox" />{{
                  S('位置已核实，允许展示', 'Verified and ready to display')
                }}</label
              >
            </article>
          </section>
          <section v-else class="admin-fields">
            <label
              >{{ S('默认语言', 'Default language')
              }}<select v-model="draft.default_language">
                <option value="zh">中文</option>
                <option value="en">English</option>
              </select></label
            >
            <label
              >{{ S('无人操作复位（秒）', 'Idle reset (seconds)')
              }}<input
                v-model.number="draft.idle_seconds"
                type="number"
                min="60"
                max="600"
                required
            /></label>
            <label
              >{{ S('音量（0–1）', 'Volume (0–1)')
              }}<input
                v-model.number="draft.volume"
                type="number"
                min="0"
                max="1"
                step=".1"
                required
            /></label>
            <label
              >{{ S('服务站编号', 'Station ID') }}<input :value="draft.station_id" readonly
            /></label>
            <label
              >{{ S('英文名称', 'English name')
              }}<input v-model="draft.name_en" required maxlength="120"
            /></label>
            <label
              >{{ S('英文位置', 'English location')
              }}<input v-model="draft.location_en" required maxlength="240"
            /></label>
            <label class="full-width"
              >{{ S('英文欢迎语', 'English welcome')
              }}<textarea v-model="draft.welcome_en" required maxlength="800" rows="3" />
            </label>
          </section>
        </div>
        <footer class="admin-save">
          <button class="primary" type="submit" :disabled="saving">
            {{ saving ? S('正在保存…', 'Saving…') : S('保存配置', 'Save settings') }}
          </button>
        </footer>
      </form>
      <div v-else class="station-form empty-state">
        {{ S('请选择或新增服务站', 'Select or add a station') }}
      </div>
    </div>
    <el-dialog
      v-model="showCreate"
      :title="S('新增服务站', 'Add station')"
      width="min(480px, 94vw)"
      append-to-body
      align-center
      destroy-on-close
    >
      <form class="station-create-form" @submit.prevent="add">
        <label
          >{{ S('服务站编号', 'Station ID')
          }}<input
            v-model="newId"
            required
            maxlength="60"
            placeholder="east-gate"
            autocomplete="off"
        /></label>
        <p>{{ S('使用小写字母、数字或短横线。', 'Use lowercase letters, numbers or hyphens.') }}</p>
        <p v-if="newError" class="admin-error" role="alert">{{ newError }}</p>
        <div class="heading-actions">
          <button type="button" @click="showCreate = false">{{ S('取消', 'Cancel') }}</button
          ><button type="submit" class="primary">{{ S('开始配置', 'Configure') }}</button>
        </div>
      </form>
    </el-dialog>
  </main>
</template>
<style scoped>
.station-admin {
  display: flex;
  flex-direction: column;
  gap: 18px;
  height: calc(100dvh - 116px);
  min-height: 0;
  font: 18px/1.6 var(--app-font-family);
  color: var(--text);
}
.station-admin-heading,
.heading-actions,
.editor-heading,
.admin-section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.station-admin-heading {
  flex-shrink: 0;
  min-height: 44px;
}
.station-admin h1 {
  margin: 0;
  font-size: 26px;
  line-height: 1.5;
}
.station-admin h2 {
  margin: 0;
  font-size: 21px;
  line-height: 1.5;
}
.station-admin h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.5;
}
.heading-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
}
.station-admin button,
.station-admin input,
.station-admin textarea,
.station-admin select {
  font: inherit;
}
.station-admin button {
  min-height: 42px;
  padding: 8px 16px;
  border: 1px solid var(--glass-line);
  border-radius: 10px;
  background: #f8fafc;
  color: var(--text-secondary);
  cursor: pointer;
}
.station-admin button:disabled {
  opacity: 0.5;
  cursor: default;
}
.station-admin .primary {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #fff;
}
.station-admin-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 20px;
  min-height: 0;
}
.station-list-panel,
.station-form {
  min-width: 0;
  min-height: 0;
  border: 1px solid var(--glass-line);
  border-radius: 18px;
  background: #fff;
  overflow: hidden;
}
.station-list-panel {
  display: flex;
  flex-direction: column;
  padding: 20px;
  gap: 16px;
}
.station-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.station-choice {
  display: block;
  width: 100%;
  margin-bottom: 10px;
  padding: 14px !important;
  text-align: left;
}
.station-choice[aria-pressed='true'] {
  background: #eef2ff;
  border-color: #c7d2fe;
}
.station-choice strong {
  display: block;
  font-size: 18px;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.station-choice span {
  display: block;
  margin-top: 7px;
  color: var(--text-muted);
  font-size: 18px;
}
.station-choice i {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 7px;
  border-radius: 50%;
  background: #94a3b8;
}
.station-choice i.online {
  background: #10b981;
}
.station-form {
  display: flex;
  flex-direction: column;
}
.editor-heading {
  padding: 18px 24px 10px;
  flex-shrink: 0;
}
.editor-heading h2 {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.editor-heading a {
  flex-shrink: 0;
  color: #4f46e5;
  font-size: 18px;
  text-decoration: none;
}
.station-tabs {
  display: flex;
  gap: 6px;
  padding: 0 24px;
  border-bottom: 1px solid var(--glass-line);
  flex-shrink: 0;
}
.station-tabs button {
  padding: 10px 14px;
  border: 0;
  border-bottom: 3px solid transparent;
  border-radius: 0;
  background: transparent;
  white-space: nowrap;
}
.station-tabs button[aria-selected='true'] {
  color: #4f46e5;
  border-bottom-color: #4f46e5;
  font-weight: 600;
}
.station-form-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  padding: 22px 24px;
}
.admin-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 22px;
}
.full-width {
  grid-column: 1/-1;
}
.station-admin label {
  display: block;
  min-width: 0;
  font-size: 18px;
  color: var(--text-secondary);
}
.station-admin label > input:not([type='checkbox']),
.station-admin label > select,
.station-admin textarea {
  display: block;
  width: 100%;
  min-width: 0;
  min-height: 44px;
  margin-top: 7px;
  padding: 10px 12px;
  border: 1px solid var(--glass-line);
  border-radius: 10px;
  background: #fff;
  color: var(--text);
  font-size: 18px;
}
.station-admin input[readonly] {
  background: #f8fafc;
}
.station-admin textarea {
  resize: vertical;
  line-height: 1.6;
}
.station-admin :is(input:not([type='checkbox']), textarea, select):focus-visible {
  outline: none;
  border-color: #818cf8;
  box-shadow: 0 0 0 3px #6366f11a;
}
.admin-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
}
.admin-checks label,
.admin-checkbox {
  display: flex !important;
  align-items: center;
  gap: 9px;
}
.station-admin input[type='checkbox'] {
  flex-shrink: 0;
  width: 19px;
  height: 19px;
  margin: 0;
  accent-color: #4f46e5;
}
.admin-save {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
  padding: 15px 24px;
  border-top: 1px solid var(--glass-line);
  background: #fff;
}
.admin-save button {
  min-width: 136px;
}
.admin-section-heading {
  margin-bottom: 18px;
}
.admin-entry {
  margin-top: 16px;
  padding: 18px;
  border: 1px solid var(--glass-line);
  border-radius: 12px;
}
.admin-entry .admin-checkbox {
  margin-top: 18px;
}
.station-admin .remove-entry {
  color: #be123c;
  background: #fff1f2;
  border-color: transparent;
}
.empty-state {
  padding: 30px 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 18px;
}
.admin-error,
.admin-success {
  flex-shrink: 0;
  margin: 0;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 18px;
}
.admin-error {
  color: #be123c;
  background: #fff1f2;
}
.admin-success {
  color: #047857;
  background: #ecfdf5;
}
.station-create-form p {
  font-size: 18px;
  color: var(--text-muted);
}
.station-create-form .heading-actions {
  margin-top: 22px;
}
@media (max-width: 1100px) {
  .station-admin-grid {
    grid-template-columns: 210px minmax(0, 1fr);
    gap: 14px;
  }
  .admin-fields {
    grid-template-columns: minmax(0, 1fr);
  }
  .station-list-panel {
    padding: 16px;
  }
  .station-form-body {
    padding: 20px;
  }
  .station-tabs {
    padding: 0 12px;
    gap: 0;
  }
  .station-tabs button {
    padding: 10px;
  }
}
@media (max-width: 900px) {
  .station-admin {
    gap: 12px;
  }
  .station-admin-heading {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .station-admin-grid {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
    gap: 12px;
  }
  .station-list-panel {
    padding: 12px;
  }
  .station-list-panel > h2 {
    display: none;
  }
  .station-list {
    display: flex;
    gap: 10px;
    overflow-x: auto;
  }
  .station-choice {
    flex: 0 0 210px;
    margin: 0;
    padding: 10px !important;
  }
  .station-choice span {
    margin-top: 3px;
  }
  .editor-heading {
    padding: 14px 16px 8px;
  }
  .editor-heading h2 {
    font-size: 19px;
  }
  .station-form-body {
    padding: 16px;
  }
  .station-tabs button {
    font-size: 18px;
    padding: 9px;
  }
  .admin-save {
    padding: 12px 16px;
  }
}
.station-create-form {
  font: 18px/1.6 var(--app-font-family);
  color: var(--text);
}
.station-create-form label {
  display: block;
  font-size: 18px;
}
.station-create-form input {
  display: block;
  width: 100%;
  min-height: 44px;
  margin-top: 8px;
  padding: 10px 12px;
  border: 1px solid var(--glass-line);
  border-radius: 10px;
  font: inherit;
  color: var(--text);
}
.station-create-form button {
  min-height: 42px;
  padding: 8px 16px;
  border: 1px solid var(--glass-line);
  border-radius: 10px;
  background: #f8fafc;
  font: inherit;
  color: var(--text);
  cursor: pointer;
}
.station-create-form .primary {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #fff;
}
.station-create-form input:focus-visible {
  outline: none;
  border-color: #818cf8;
  box-shadow: 0 0 0 3px #6366f11a;
}
</style>
