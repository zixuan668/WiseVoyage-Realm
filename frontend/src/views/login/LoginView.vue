<script lang="ts" setup>
import LanguageSwitch from '@/components/LanguageSwitch.vue'
import { gsap } from 'gsap'
import { t } from '@/i18n'

import BrandLogo from '@/components/BrandLogo.vue'
import { nextTick, onBeforeUnmount, onMounted, reactive, ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  User,
  Lock,
  Guide,
  ArrowRight,
  Location,
  ChatDotRound,
  MapLocation
} from '@/icons'
import { ElMessage, ElNotification, type FormInstance, type FormRules } from 'element-plus'
import { loginRequest } from '@/api/user'
import { useTokenStore, type TokenItem } from '@/stores/userToken'
import { AxiosError } from 'axios'
import { request_handler } from '@/api/base'

const router = useRouter()
const route = useRoute()
type EntryMode = 'visitor' | 'admin'
const entryMode = ref<EntryMode>('admin')
const isLogining = ref(false)
const serviceState = ref<'checking' | 'ready' | 'offline'>('checking')
const rememberAccount = ref(true)
const tokenStore = useTokenStore()
const formRef = ref<FormInstance>()
const rememberedAccountKey = 'zhiyou.remembered-account'
const entryPage = ref<HTMLElement>()
let pointerFrame = 0
let motionPreference: MediaQueryList | undefined
let motionMedia: gsap.MatchMedia | undefined
let motionContext: gsap.Context | undefined
let contentMotion: gsap.Context | undefined
let sceneryMotion: gsap.core.Timeline | undefined
let arrivalMotion: gsap.core.Timeline | undefined
const motionPaused = ref(false)

function animateEntryContent(element: Element) {
  contentMotion?.revert()
  if (motionPreference?.matches || document.hidden) return
  contentMotion = gsap.context(() => {
    const timeline = gsap.timeline({
      defaults: { duration: 0.45, ease: 'power2.out', clearProps: 'transform,opacity' }
    })
    timeline.from('.entry-heading', { opacity: 0, y: 12 }, 0)
    const visitorScene = element.querySelector('.visitor-scene')
    if (visitorScene) {
      timeline.from(visitorScene, { opacity: 0, y: 14, scale: 0.96, ease: 'back.out(1.2)' }, 0.08)
    }
    timeline
      .from('.entry-features > span, .el-form-item', { opacity: 0, y: 10, stagger: 0.075 }, 0.14)
      .from('.entry-options, .entry-primary', { opacity: 0, y: 8, stagger: 0.07 }, 0.23)
  }, element)
}

function syncMotionVisibility() {
  motionPaused.value = document.hidden
  sceneryMotion?.paused(document.hidden)
  // Finish an entrance when leaving the tab so returning never shows a half-hidden form.
  if (document.hidden) {
    arrivalMotion?.progress(1)
    contentMotion?.revert()
    resetAtmosphere()
  }
}

function resetReducedMotion() {
  if (motionPreference?.matches) resetAtmosphere()
}

function startLoginMotion() {
  if (!entryPage.value) return
  motionContext = gsap.context(() => {
    motionMedia = gsap.matchMedia()
    motionMedia.add('(prefers-reduced-motion: no-preference)', () => {
      // Parallel scenic layers share a timeline; the form is never part of this ambient loop.
      sceneryMotion = gsap
        .timeline({ repeat: -1, yoyo: true, defaults: { ease: 'sine.inOut' } })
        .to('.scenery-far', { x: 26, y: -10, duration: 9 }, 0)
        .to('.scenery-near', { x: -20, y: 8, duration: 9 }, 0)
        .to('.scenery-reflection', { x: 38, opacity: 0.65, duration: 9 }, 0)
        .to('.scenery-cloud', { x: 48, duration: 9 }, 0)
      arrivalMotion = gsap
        .timeline({ defaults: { ease: 'power3.out', clearProps: 'transform,opacity' } })
        .from('.entry-header', { opacity: 0, y: -12, duration: 0.6 }, 0.08)
        .from('.entry-card', { opacity: 0, y: 22, scale: 0.985, duration: 0.7 }, 0.12)
        .from('.entry-scenery', { opacity: 0, y: 24, duration: 1.2, ease: 'sine.out' }, 0.1)
      const panel = entryPage.value?.querySelector('.entry-content')
      if (panel) animateEntryContent(panel)
      syncMotionVisibility()
      return () => {
        contentMotion?.revert()
        sceneryMotion = undefined
        arrivalMotion = undefined
      }
    })
  }, entryPage.value)
}
function moveAtmosphere(event: PointerEvent) {
  if (event.pointerType !== 'mouse' || motionPreference?.matches || document.hidden) return
  const bounds =
    event.currentTarget instanceof HTMLElement ? event.currentTarget.getBoundingClientRect() : null
  if (!bounds) return
  const x = (event.clientX - bounds.left) / bounds.width - 0.5
  const y = (event.clientY - bounds.top) / bounds.height - 0.5
  cancelAnimationFrame(pointerFrame)
  pointerFrame = requestAnimationFrame(() => {
    entryPage.value?.style.setProperty('--pointer-x', x * 48 + 'px')
    entryPage.value?.style.setProperty('--pointer-y', y * 32 + 'px')
  })
}
function resetAtmosphere() {
  cancelAnimationFrame(pointerFrame)
  entryPage.value?.style.setProperty('--pointer-x', '0px')
  entryPage.value?.style.setProperty('--pointer-y', '0px')
}
interface FormType {
  username: string
  password: string
}
const loginForm = reactive<FormType>({ username: '', password: '' })
const rules = computed<FormRules<FormType>>(() => ({
  username: [{ required: true, message: t('请输入账号'), trigger: 'blur' }],
  password: [
    { required: true, message: t('请输入密码'), trigger: 'blur' },
    { min: 6, max: 18, message: t('密码长度必须为 6 至 18 位'), trigger: 'blur' }
  ]
}))
async function selectEntry(mode: EntryMode, focus = false) {
  if (isLogining.value) return
  entryMode.value = mode
  if (focus) {
    await nextTick()
    document.getElementById('entry-tab-' + mode)?.focus()
  }
}
const onSubmit = async () => {
  if (isLogining.value || !formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  isLogining.value = true
  try {
    const response = await loginRequest({
      username: loginForm.username,
      password: loginForm.password
    })
    if (response.status !== 200) {
      ElMessage.error(t('账号或密码错误'))
      return
    }
    tokenStore.saveToken(response.data as TokenItem)
    tokenStore.saveUserInfo({ username: loginForm.username, role: 'admin' })
    try {
      if (rememberAccount.value) localStorage.setItem(rememberedAccountKey, loginForm.username)
      else localStorage.removeItem(rememberedAccountKey)
    } catch {
      /* Account recall is optional when browser storage is restricted. */
    }
    ElNotification({ title: t('登录成功'), message: t('已进入后台'), type: 'success' })
    router.push((route.query.redirect as string) || '/home')
  } catch (error) {
    if (error instanceof AxiosError && error.response?.status === 401)
      ElMessage.error(t('账号或密码错误'))
    else ElMessage.error(t('登录失败，请稍后重试'))
  } finally {
    isLogining.value = false
  }
}
const enterAsVisitor = () => router.push('/station/summer-palace-east')
const handleForgotPassword = () => ElMessage.info(t('请联系系统管理员重置密码'))
onMounted(() => {
  motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)')
  motionPreference.addEventListener('change', resetReducedMotion)
  document.addEventListener('visibilitychange', syncMotionVisibility)
  startLoginMotion()
  try {
    loginForm.username = localStorage.getItem(rememberedAccountKey) || ''
  } catch {
    /* Optional account recall. */
  }
  request_handler
    .get('/tour-session/guides', { timeout: 5000 })
    .then(() => {
      serviceState.value = 'ready'
    })
    .catch(() => {
      serviceState.value = 'offline'
    })
  document.documentElement.classList.add('login-viewport')
  document.body.classList.add('login-viewport')
})
onBeforeUnmount(() => {
  cancelAnimationFrame(pointerFrame)
  document.removeEventListener('visibilitychange', syncMotionVisibility)
  motionPreference?.removeEventListener('change', resetReducedMotion)
  contentMotion?.revert()
  motionMedia?.revert()
  motionContext?.revert()
  document.documentElement.classList.remove('login-viewport')
  document.body.classList.remove('login-viewport')
})
</script>

<template>
  <main
    ref="entryPage"
    class="entry-page"
    :class="{ 'motion-paused': motionPaused }"
    @pointermove="moveAtmosphere"
    @pointerleave="resetAtmosphere"
  >
    <div class="entry-atmosphere" aria-hidden="true">
      <i class="entry-glow glow-purple"></i><i class="entry-glow glow-blue"></i
      ><i class="entry-glow glow-mint"></i>
      <div class="entry-contour contour-left"></div>
      <div class="entry-contour contour-right"></div>
      <div class="entry-aurora"></div>
      <svg class="entry-scenery" viewBox="0 0 1440 620" preserveAspectRatio="xMidYMax slice">
        <defs>
          <linearGradient id="scenery-violet" x1="0" y1="0" x2="0" y2="1">
            <stop stop-color="#b6afe5" stop-opacity=".38" />
            <stop offset="1" stop-color="#d9d7ed" stop-opacity=".08" />
          </linearGradient>
          <linearGradient id="scenery-jade" x1="0" y1="0" x2="0" y2="1">
            <stop stop-color="#96c5c9" stop-opacity=".36" />
            <stop offset="1" stop-color="#c8e0de" stop-opacity=".12" />
          </linearGradient>
        </defs>
        <g class="scenery-cloud" fill="none" stroke="#a5b1cc" stroke-opacity=".24">
          <path d="M36 214Q75 196 119 214T205 212M70 226H167" />
          <path d="M1170 130Q1215 112 1260 129T1378 131M1220 146H1351" />
        </g>
        <g class="scenery-far" fill="url(#scenery-violet)">
          <path
            d="M-80 445Q0 415 78 330Q116 286 147 326L216 402Q249 433 276 390L336 283Q366 225 397 274L477 419Q507 475 566 457L660 530H-80Z"
          />
          <path
            d="M925 465L1056 335Q1081 311 1104 339L1146 387L1237 251Q1261 215 1291 251L1380 377L1495 323V550H925Z"
          />
        </g>
        <g class="scenery-near" fill="url(#scenery-jade)">
          <path d="M-60 501Q33 447 115 453T257 426T455 469T618 503V610H-60Z" />
          <path d="M854 541Q964 478 1062 483T1240 441T1490 468V620H854Z" />
        </g>
        <g
          class="scenery-landmarks"
          fill="none"
          stroke="#8e98ba"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <g class="scenery-bridge">
            <path
              d="M42 476Q170 395 298 476M42 486Q170 408 298 486M57 466V476M82 451V461M111 439V449M141 432V442M170 429V439M199 432V442M229 439V449M258 451V461M283 466V476"
            />
            <path d="M75 488V509M265 488V509M88 479Q170 431 252 479" />
          </g>
          <g class="scenery-pavilion">
            <path
              d="M1200 448H1320M1214 448V420H1306V448M1228 418V394H1292V418M1242 392V371H1278V392M1260 332V344"
            />
            <path
              d="M1200 418Q1230 417 1260 397Q1290 417 1320 418ZM1215 393Q1240 390 1260 375Q1280 390 1305 393ZM1230 371Q1250 368 1260 344Q1270 368 1290 371Z"
            />
            <path d="M1243 448V429H1254V448M1266 448V429H1277V448M1245 415V400M1275 415V400" />
          </g>
        </g>
        <g
          class="scenery-reflection"
          fill="none"
          stroke="#8fb8c2"
          stroke-width="1.4"
          stroke-linecap="round"
          opacity=".35"
        >
          <path
            d="M24 532H90M120 544H240M62 559H186M266 534H342M1136 493H1280M1200 508H1350M1164 526H1254M1040 570H1150"
          />
        </g>
      </svg>
      <svg class="entry-flow-map" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice">
        <g fill="none" stroke-linecap="round">
          <path class="flow-track" d="M-60 660C100 650 370 520 315 310S70 110 210 25" />
          <path class="flow-track" d="M1480 170C1190 120 1000 260 1160 485S1460 735 1100 920" />
          <path
            class="flow-stream stream-purple"
            pathLength="1200"
            d="M-60 660C100 650 370 520 315 310S70 110 210 25"
          />
          <path
            class="flow-stream stream-blue"
            pathLength="1200"
            d="M1480 170C1190 120 1000 260 1160 485S1460 735 1100 920"
          />
        </g>
        <g class="flow-waypoints" fill="#f7f8fc" stroke="#9a92d8" stroke-width="1.5">
          <g class="flow-waypoint waypoint-one">
            <circle class="waypoint-wave" cx="280" cy="427" r="8" />
            <circle cx="280" cy="427" r="5" />
            <circle cx="280" cy="427" r="2" fill="#9485d5" stroke="none" />
          </g>
          <g class="flow-waypoint waypoint-two">
            <circle class="waypoint-wave" cx="1190" cy="526" r="8" />
            <circle cx="1190" cy="526" r="5" />
            <circle cx="1190" cy="526" r="2" fill="#79b8cb" stroke="none" />
          </g>
        </g>
      </svg>
      <div class="entry-motes">
        <i
          v-for="n in 9"
          :key="n"
          :style="{
            left: ((n * 31) % 96) + '%',
            top: ((n * 23) % 88) + '%',
            '--mote-delay': -n * 1.3 + 's',
            '--mote-duration': 7 + (n % 4) + 's'
          }"
        ></i>
      </div>
      <svg class="entry-lake" viewBox="0 0 1440 360" preserveAspectRatio="xMidYMax slice">
        <defs>
          <linearGradient id="entry-lake-fill" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#c6d8f0" stop-opacity=".18" />
            <stop offset="1" stop-color="#b9dcd8" stop-opacity=".35" />
          </linearGradient>
        </defs>
        <path
          d="M0 210 Q160 135 310 220 T630 235 T960 195 T1260 230 T1440 215 V360 H0Z"
          fill="url(#entry-lake-fill)"
        />
        <g class="lake-ripples" fill="none" stroke="#97b5ca" stroke-width="1.3">
          <path d="M-80 230 Q140 195 350 250 T820 260 T1240 228 T1530 250" />
          <path d="M-120 264 Q150 230 370 282 T830 292 T1260 264 T1560 284" />
          <path d="M-60 304 Q200 280 460 320 T960 328 T1500 304" />
        </g>
      </svg>
      <span class="entry-orbit orbit-one"></span><span class="entry-orbit orbit-two"></span
      ><span class="entry-orbit orbit-three"></span>
    </div>
    <header class="entry-header"><BrandLogo /><LanguageSwitch class="entry-language" /></header>
    <section class="entry-center" :aria-label="$t('选择访问入口')">
      <div class="entry-card">
        <div class="entry-tabs" role="tablist" :aria-label="$t('访问方式')">
          <span
            class="entry-tab-indicator"
            :class="{ admin: entryMode === 'admin' }"
            aria-hidden="true"
          ></span>
          <button
            id="entry-tab-visitor"
            type="button"
            role="tab"
            :aria-selected="entryMode === 'visitor'"
            aria-controls="entry-panel-visitor"
            :tabindex="entryMode === 'visitor' ? 0 : -1"
            :disabled="isLogining"
            @click="selectEntry('visitor')"
            @keydown.right.prevent="selectEntry('admin', true)"
            @keydown.end.prevent="selectEntry('admin', true)"
          >
            <el-icon><Guide /></el-icon><span>{{ $t('景区服务站') }}</span>
          </button>
          <button
            id="entry-tab-admin"
            type="button"
            role="tab"
            :aria-selected="entryMode === 'admin'"
            aria-controls="entry-panel-admin"
            :tabindex="entryMode === 'admin' ? 0 : -1"
            :disabled="isLogining"
            @click="selectEntry('admin')"
            @keydown.left.prevent="selectEntry('visitor', true)"
            @keydown.home.prevent="selectEntry('visitor', true)"
          >
            <el-icon><User /></el-icon><span>{{ $t('后台登录') }}</span>
          </button>
        </div>
        <Transition name="entry-switch" mode="out-in" @enter="animateEntryContent">
          <section
            v-if="entryMode === 'visitor'"
            id="entry-panel-visitor"
            key="visitor"
            class="entry-content"
            role="tabpanel"
            aria-labelledby="entry-tab-visitor"
            tabindex="0"
          >
            <div class="entry-visitor-body">
            <div class="entry-heading">
              <h1>{{ $t('景区数字人服务站') }}</h1>
              <p>{{ $t('在本站咨询规划，扫码带走游览方案。') }}</p>
            </div>
            <div class="visitor-scene" aria-hidden="true">
              <svg viewBox="0 0 400 170" fill="none">
                <defs>
                  <linearGradient
                    id="entry-mountain"
                    x1="80"
                    y1="50"
                    x2="300"
                    y2="160"
                    gradientUnits="userSpaceOnUse"
                  >
                    <stop stop-color="#a5a6f7" />
                    <stop offset="1" stop-color="#a6d8e6" />
                  </linearGradient>
                </defs>
                <ellipse class="scene-shadow" cx="200" cy="147" rx="145" ry="15" fill="#e9edf8" />
                <path
                  class="scene-mountain-back"
                  d="M50 128L112 54Q118 47 125 54L164 97L204 37Q209 29 217 37L300 128Z"
                  fill="url(#entry-mountain)"
                  opacity=".65"
                />
                <path
                  class="scene-mountain-front"
                  d="M142 129L216 72Q221 68 225 73L271 129Z"
                  fill="#c9d7f3"
                />
                <ellipse
                  class="scene-pin-wave"
                  cx="294"
                  cy="133"
                  rx="21"
                  ry="5"
                  stroke="#9c96ed"
                  stroke-width="2"
                />
                <path
                  d="M75 132Q136 110 191 140T323 130"
                  stroke="#7abacc"
                  stroke-width="3"
                  stroke-linecap="round"
                />
                <path
                  class="scene-trail"
                  d="M95 124Q140 137 197 120T312 124"
                  stroke="#7775df"
                  stroke-width="2"
                  stroke-dasharray="4 7"
                  stroke-linecap="round"
                />
                <g class="scene-pin">
                  <circle cx="294" cy="70" r="31" fill="#fff" />
                  <path
                    d="M310 66C310 79 294 94 294 94S278 79 278 66A16 16 0 11310 66Z"
                    fill="#5750e9"
                  />
                  <circle cx="294" cy="66" r="5" fill="#fff" />
                </g>
                <path
                  class="scene-star"
                  d="M104 36L108 47L119 51L108 55L104 66L100 55L89 51L100 47Z"
                  fill="#9c96ed"
                />
              </svg>
            </div>
            <div class="entry-features">
              <span
                ><el-icon><MapLocation /></el-icon><span class="entry-feature-label">{{ $t('景区地图') }}</span></span
              ><span
                ><el-icon><Location /></el-icon><span class="entry-feature-label">{{ $t('路线规划') }}</span></span
              >
              <span
                ><el-icon><ChatDotRound /></el-icon><span class="entry-feature-label">{{ $t('数字人导览') }}</span></span
              >
            </div>
            </div>
            <el-button type="primary" class="entry-primary" @click="enterAsVisitor"
              >{{ $t('进入景区服务站') }}<el-icon><ArrowRight /></el-icon
            ></el-button>
          </section>
          <section
            v-else
            id="entry-panel-admin"
            key="admin"
            class="entry-content"
            role="tabpanel"
            aria-labelledby="entry-tab-admin"
            tabindex="0"
          >
            <div class="entry-heading">
              <h1>{{ $t('后台登录') }}</h1>
              <p>{{ $t('管理景点、路线与数字人。') }}</p>
            </div>
            <el-form
              ref="formRef"
              :model="loginForm"
              :rules="rules"
              label-position="top"
              size="large"
              class="entry-form"
              @submit.prevent="onSubmit"
            >
              <el-form-item :label="$t('账号')" prop="username"
                ><el-input
                  v-model="loginForm.username"
                  :prefix-icon="User"
                  :placeholder="$t('输入账号')"
                  autocomplete="username"
                  :disabled="isLogining"
              /></el-form-item>
              <el-form-item :label="$t('密码')" prop="password"
                ><el-input
                  v-model="loginForm.password"
                  :prefix-icon="Lock"
                  type="password"
                  :placeholder="$t('请输入密码')"
                  autocomplete="current-password"
                  show-password
                  :disabled="isLogining"
              /></el-form-item>
              <div class="entry-options">
                <el-checkbox v-model="rememberAccount">{{ $t('记住账号') }}</el-checkbox
                ><button type="button" @click="handleForgotPassword">{{ $t('忘记密码？') }}</button>
              </div>
              <el-button
                type="primary"
                native-type="submit"
                :loading="isLogining"
                class="entry-primary"
                >{{ $t('登录后台') }}<el-icon v-if="!isLogining"><ArrowRight /></el-icon
              ></el-button>
            </el-form>
          </section>
        </Transition>
        <div class="entry-status" :class="serviceState" role="status">
          <i aria-hidden="true"></i>
          <span>{{
            $t(
              serviceState === 'ready'
                ? '服务可用'
                : serviceState === 'offline'
                  ? '服务暂不可用，请稍后重试'
                  : '正在连接服务'
            )
          }}</span>
        </div>
      </div>
    </section>
  </main>
</template>

<style lang="scss" scoped>
:global(html.login-viewport),
:global(body.login-viewport),
:global(html.login-viewport #app) {
  min-width: 0;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
:global(html.login-viewport::-webkit-scrollbar),
:global(body.login-viewport::-webkit-scrollbar),
:global(html.login-viewport #app::-webkit-scrollbar),
.entry-page::-webkit-scrollbar,
.entry-page ::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}
.entry-page,
.entry-page * {
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.entry-page,
.entry-page *,
.entry-page *::before,
.entry-page *::after {
  box-sizing: border-box;
}
.entry-page {
  position: relative;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  overflow: hidden;
  padding: 24px 40px;
  color: #243248;
  background: #f5f7fb;
}
.entry-atmosphere {
  position: absolute;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  pointer-events: none;
}
.entry-glow {
  position: absolute;
  display: block;
  width: min(60vw, 780px);
  aspect-ratio: 1;
  border-radius: 50%;
  filter: blur(65px);
}
.glow-purple {
  left: -18%;
  top: -35%;
  background: radial-gradient(circle, #ccc9f7 0, #e3e4fc 38%, transparent 70%);
  animation: entry-light-drift 18s ease-in-out infinite alternate;
}
.glow-blue {
  right: -18%;
  top: 10%;
  background: radial-gradient(circle, #c0dcf1 0, #dbe9f5 40%, transparent 70%);
  animation: entry-light-drift 22s -8s ease-in-out infinite alternate-reverse;
}
.glow-mint {
  left: 15%;
  bottom: -65%;
  width: 75vw;
  background: radial-gradient(circle, #c6e3dc 0, #e0ece8 40%, transparent 70%);
  animation: entry-light-drift 26s -12s ease-in-out infinite alternate;
}
.entry-contour {
  position: absolute;
  width: 720px;
  height: 470px;
  opacity: 0.16;
  background: url('/images/tour-landscape-outline.svg') center / contain no-repeat;
  animation: entry-landscape-drift 22s ease-in-out infinite alternate;
}
.contour-left {
  left: -170px;
  bottom: 16px;
}
.contour-right {
  right: -240px;
  top: 100px;
  transform: scaleX(-1);
  animation-direction: alternate-reverse;
}
.entry-lake {
  position: absolute;
  bottom: 0;
  left: -6%;
  width: 112%;
  height: 34vh;
  min-height: 180px;
}
.lake-ripples {
  opacity: 0.28;
  animation: entry-ripple-drift 12s ease-in-out infinite alternate;
}
.entry-orbit {
  position: absolute;
  border: 1px solid rgba(131, 145, 203, 0.14);
  border-radius: 50%;
}
.orbit-one {
  left: -220px;
  top: 18%;
  width: 550px;
  height: 550px;
  animation: entry-orbit-breathe 16s ease-in-out infinite;
}
.orbit-two {
  right: -150px;
  bottom: 12%;
  width: 380px;
  height: 380px;
  animation: entry-orbit-breathe 18s -5s ease-in-out infinite;
}
.orbit-three {
  right: 9%;
  top: 8%;
  width: 14px;
  height: 14px;
  background: #c9c5f7;
  border: none;
  animation: entry-pin-float 5s ease-in-out infinite;
}
.entry-language {
  margin-left: auto;
}
.entry-header {
  display: flex;
  align-items: center;
  width: 100%;
  max-width: 1560px;
  margin: 0 auto;
  min-height: 44px;
}
.entry-header :deep(.brand-logo) {
  mix-blend-mode: multiply;
}
.entry-center {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  min-width: 0;
  place-items: center;
  flex: 1;
  padding: 24px 0;
}
.entry-card {
  min-width: 0;
  max-width: 100%;
  width: min(100%, 500px);
  height: min(700px, calc(100dvh - 140px));
  min-height: 560px;
  display: flex;
  flex-direction: column;
  padding: 26px 32px 20px;
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow:
    0 22px 70px -28px rgba(82, 99, 135, 0.22),
    0 2px 6px rgba(255, 255, 255, 0.8);
}
.entry-tabs {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  height: 70px;
  flex: none;
  gap: 6px;
  padding: 6px;
  border-radius: 18px;
  background: #f1f3f9;
  box-shadow:
    inset 2px 2px 6px rgba(151, 162, 186, 0.12),
    inset -2px -2px 6px #fff;
}
.entry-tab-indicator {
  position: absolute;
  top: 6px;
  left: 6px;
  width: calc(50% - 9px);
  height: calc(100% - 12px);
  background: #fff;
  border: 1px solid #e9e8fc;
  border-radius: 13px;
  box-shadow: 0 4px 10px rgba(96, 93, 174, 0.1);
  transition: transform 0.34s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.entry-tab-indicator.admin {
  transform: translateX(calc(100% + 6px));
}
.entry-tabs button {
  min-width: 0;
  padding: 4px 8px;
  overflow-wrap: anywhere;
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 9px;
  min-height: 0;
  line-height: 1.3;
  border: 0;
  border-radius: 13px;
  background: transparent;
  color: #6b7790;
  font-size: 18px;
  cursor: pointer;
  transition: color 0.25s;
}
.entry-tabs button[aria-selected='true'] {
  color: #5147df;
  font-weight: 600;
}
.entry-tabs button:disabled {
  cursor: wait;
}
.entry-page button:focus-visible,
.entry-content:focus-visible {
  outline: 2px solid #8178ed;
  outline-offset: 4px;
}
.entry-content {
  min-width: 0;
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-top: 24px;
  outline: none;
}
.entry-visitor-body {
  display: grid;
  grid-template-rows: 140px minmax(72px, 1fr) 116px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
}
.entry-visitor-body .visitor-scene { min-height: 0; height: 100%; margin: 0; overflow: hidden; }
.entry-visitor-body .visitor-scene svg { height: 100%; max-height: 158px; overflow: hidden; }
.entry-content > .entry-primary { height: 52px; }
.entry-heading h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 500;
  line-height: 1.35;
}
.entry-heading p {
  margin: 10px 0 0;
  color: #728096;
  font-size: 18px;
  line-height: 1.5;
}
.visitor-scene {
  display: grid;
  place-items: center;
  flex: 1;
  min-height: 170px;
  margin: 8px 0;
}
.visitor-scene svg {
  width: 100%;
  max-width: 360px;
  height: 158px;
  overflow: visible;
}
.scene-pin {
  animation: entry-pin-float 4.8s ease-in-out infinite;
}
.scene-star {
  transform-origin: 104px 51px;
  animation: entry-star-breathe 5s ease-in-out infinite;
}
.scene-trail {
  animation: entry-trail-flow 9s linear infinite;
}
.entry-features {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 12px 0 24px;
  color: #69788c;
}
.entry-features > span {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  gap: 8px;
  font-size: 18px;
  line-height: 1.5;
  white-space: normal;
  text-align: center;
}
.entry-feature-label { display: block; max-width: 100%; overflow-wrap: anywhere; }
.entry-features .el-icon {
  color: #7a73df;
  font-size: 18px;
}
.entry-primary.el-button {
  width: 100%;
  min-height: 52px;
  height: auto;
  white-space: normal;
  flex: none;
  border-radius: 15px;
  font-size: 18px;
  letter-spacing: 1px;
  transition:
    transform 0.25s,
    box-shadow 0.25s;
}
.entry-primary :deep(.el-icon) {
  margin-left: 12px;
  transition: transform 0.25s;
}
.entry-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px -8px rgba(79, 70, 229, 0.4);
}
.entry-primary:hover :deep(.el-icon) {
  transform: translateX(3px);
}
.entry-primary:active {
  transform: translateY(0);
}
.entry-form {
  min-height: 0;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-top: 18px;
}
.entry-form :deep(.el-form-item) {
  margin-bottom: 16px;
}
.entry-form :deep(.el-form-item__content) {
  flex-direction: column;
  align-items: stretch;
}
.entry-form :deep(.el-form-item__error) {
  position: static;
  width: 100%;
  margin-top: 8px;
  padding-top: 0;
  font-size: 18px;
  line-height: 1.5;
}
.entry-form :deep(.el-form-item__label) {
  font-size: 18px;
  height: auto;
  line-height: 22px;
  padding: 0;
  margin-bottom: 8px;
}
.entry-form :deep(.el-input__wrapper) {
  min-height: 48px;
  border-radius: 12px;
}
.entry-form :deep(.el-input__inner) {
  font-size: 18px;
}
.entry-form :deep(.el-input__inner:focus-visible) {
  // 焦点边框由带图标的外层统一绘制，避免内部文字区出现错位方框。
  outline: none;
}
.entry-options {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: -1px 0 16px;
}
.entry-options :deep(.el-checkbox) {
  height: 32px;
}
.entry-options :deep(.el-checkbox__label) {
  font-size: 18px;
}
.entry-options button {
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: #6962d7;
  font-size: 18px;
  cursor: pointer;
}
.entry-form .entry-primary {
  margin-top: auto;
}
.entry-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 36px;
  flex: none;
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid #edf0f6;
  color: #7c889b;
  font-size: 18px;
}
.entry-status i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #a4aab7;
}
.entry-status.ready i {
  background: #6cac9c;
}
.entry-status.offline {
  color: #a96d54;
}
.entry-status.offline i {
  background: #dba37a;
}
.entry-status.checking i {
  animation: entry-star-breathe 1.4s ease-in-out infinite;
}
.entry-switch-enter-active,
.entry-switch-leave-active {
  transition:
    opacity 0.18s,
    transform 0.18s;
}
.entry-switch-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.entry-switch-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
@keyframes entry-light-drift {
  from {
    transform: translate3d(-10%, -8%, 0) scale(0.88);
  }
  to {
    transform: translate3d(24%, 18%, 0) scale(1.2);
  }
}
@keyframes entry-landscape-drift {
  from {
    translate: 0 0;
  }
  to {
    translate: 34px -22px;
  }
}
@keyframes entry-ripple-drift {
  from {
    transform: translateX(-45px);
  }
  to {
    transform: translateX(45px);
  }
}
@keyframes entry-orbit-breathe {
  0%,
  100% {
    transform: scale(0.98);
    opacity: 0.6;
  }
  50% {
    transform: scale(1.04);
    opacity: 1;
  }
}
@keyframes entry-pin-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-12px);
  }
}
@keyframes entry-star-breathe {
  0%,
  100% {
    opacity: 0.6;
    scale: 0.94;
  }
  50% {
    opacity: 1;
    scale: 1.08;
  }
}
@keyframes entry-trail-flow {
  to {
    stroke-dashoffset: -66;
  }
}
/* Decorative motion stays behind the stable, readable access panel. */
.entry-atmosphere {
  inset: -32px;
  transform: translate(var(--pointer-x, 0px), var(--pointer-y, 0px));
  transition: transform 0.7s cubic-bezier(0.2, 0.7, 0.2, 1);
}
.glow-purple {
  animation-duration: 8s;
  background: radial-gradient(circle, #b8aef4 0, #dcd7fc 38%, transparent 70%);
}
.glow-blue {
  animation-duration: 11s;
  animation-delay: -4s;
  background: radial-gradient(circle, #a5d3ee 0, #d2e7f6 40%, transparent 70%);
}
.glow-mint {
  animation-duration: 13s;
  animation-delay: -6s;
}
.entry-contour {
  animation-duration: 10s;
  opacity: 0.09;
}
.lake-ripples {
  opacity: 0.4;
  animation-duration: 5s;
}
.entry-aurora {
  position: absolute;
  inset: -30%;
  opacity: 0.44;
  background: conic-gradient(
    from 40deg at 50% 50%,
    transparent 0 15%,
    rgba(169, 155, 243, 0.28) 24%,
    transparent 38% 60%,
    rgba(136, 211, 225, 0.24) 75%,
    transparent 88%
  );
  filter: blur(48px);
  animation: entry-aurora-turn 28s linear infinite;
}
.entry-flow-map {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.8;
}
.flow-track {
  stroke: #a4abc9;
  stroke-width: 1.2;
  opacity: 0.28;
}
.flow-stream {
  stroke-width: 3;
  stroke-dasharray: 110 1090;
  animation: entry-route-travel 5.5s linear infinite;
}
.stream-purple {
  stroke: #9b8ce8;
  filter: drop-shadow(0 0 5px #b8a7f1);
}
.stream-blue {
  stroke: #69b9d5;
  animation-delay: -3.5s;
  animation-duration: 7s;
  filter: drop-shadow(0 0 5px #9ed9e9);
}
.entry-motes {
  position: absolute;
  inset: 0;
}
.entry-motes i {
  position: absolute;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #a69ae7;
  box-shadow: 0 0 10px rgba(153, 133, 230, 0.4);
  animation: entry-mote-rise var(--mote-duration) var(--mote-delay) ease-in-out infinite;
}
.entry-motes i:nth-child(even) {
  width: 3px;
  height: 3px;
  background: #83bbc6;
}
.orbit-one {
  animation: entry-aurora-turn 20s linear infinite;
}
.orbit-two {
  animation: entry-aurora-turn 15s linear infinite reverse;
}
.orbit-one::after,
.orbit-two::after {
  content: '';
  position: absolute;
  top: 50%;
  right: -5px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #aea3ee;
  box-shadow:
    0 0 0 7px rgba(174, 163, 238, 0.1),
    0 0 20px rgba(156, 142, 228, 0.3);
}
.orbit-two::after {
  background: #94c4d2;
}
.scene-pin {
  animation-duration: 3s;
}
.scene-trail {
  animation-duration: 3s;
}
.entry-scenery {
  position: absolute;
  width: 100%;
  height: min(66vh, 640px);
  left: 0;
  bottom: 0;
  overflow: visible;
}
.scenery-landmarks {
  opacity: 0.5;
}
.scenery-far,
.scenery-near,
.scenery-cloud,
.scenery-reflection {
  will-change: transform;
}
.waypoint-wave {
  transform-box: fill-box;
  transform-origin: center;
  animation: entry-waypoint-wave 3.6s ease-out infinite;
}
.waypoint-two .waypoint-wave {
  animation-delay: -1.8s;
  stroke: #79b8cb;
}
.entry-card {
  position: relative;
  isolation: isolate;
}
.entry-card::before {
  content: '';
  position: absolute;
  inset: -9px;
  border: 1px solid rgba(153, 141, 218, 0.2);
  border-radius: 38px;
  pointer-events: none;
  animation: entry-panel-breathe 4.8s ease-in-out infinite;
}
.scene-mountain-back,
.scene-mountain-front,
.scene-shadow {
  transform-box: fill-box;
  transform-origin: center;
  animation: entry-scene-drift 5s ease-in-out infinite alternate;
}
.scene-mountain-front {
  animation-direction: alternate-reverse;
  animation-duration: 4s;
}
.scene-shadow {
  animation-name: entry-scene-shadow;
}
.scene-pin-wave {
  transform-box: fill-box;
  transform-origin: center;
  animation: entry-waypoint-wave 3s ease-out infinite;
}
.motion-paused *,
.motion-paused *::before,
.motion-paused *::after {
  animation-play-state: paused !important;
}
.entry-primary.el-button {
  position: relative;
  overflow: hidden;
}
.entry-primary::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(
    110deg,
    transparent 30%,
    rgba(255, 255, 255, 0.2) 49%,
    transparent 68%
  );
  transform: translateX(-130%);
  animation: entry-button-light 5s 1s ease-in-out infinite;
}
@keyframes entry-aurora-turn {
  to {
    transform: rotate(360deg);
  }
}
@keyframes entry-route-travel {
  from {
    stroke-dashoffset: 110;
  }
  to {
    stroke-dashoffset: -1090;
  }
}
@keyframes entry-waypoint-wave {
  0% {
    opacity: 0.7;
    transform: scale(0.8);
  }
  80%,
  100% {
    opacity: 0;
    transform: scale(2.7);
  }
}
@keyframes entry-panel-breathe {
  0%,
  100% {
    opacity: 0.25;
  }
  50% {
    opacity: 0.9;
  }
}
@keyframes entry-scene-drift {
  from {
    transform: translate(-3px, 3px);
  }
  to {
    transform: translate(4px, -5px);
  }
}
@keyframes entry-scene-shadow {
  from {
    transform: scaleX(0.96);
    opacity: 0.7;
  }
  to {
    transform: scaleX(1.04);
    opacity: 1;
  }
}
@keyframes entry-mote-rise {
  0%,
  100% {
    transform: translate(0, 22px) scale(0.6);
    opacity: 0;
  }
  25% {
    opacity: 0.6;
  }
  75% {
    opacity: 0.35;
  }
  95% {
    transform: translate(22px, -48px) scale(1.2);
    opacity: 0;
  }
}
@keyframes entry-button-light {
  0%,
  55% {
    transform: translateX(-130%);
  }
  85%,
  100% {
    transform: translateX(130%);
  }
}
@media (min-width: 601px) and (max-height: 800px) {
  .entry-card { padding-top: 20px; padding-bottom: 16px; }
  .entry-content { padding-top: 16px; }
  .entry-visitor-body { grid-template-rows: 140px minmax(100px, 1fr) 100px; }
  .entry-features { padding-top: 8px; padding-bottom: 12px; }
  .entry-status { margin-top: 12px; padding-top: 10px; }
}
@media (max-width: 600px) {
  .entry-scenery {
    height: 52vh;
    opacity: 0.65;
  }
  .scenery-landmarks,
  .scenery-cloud {
    display: none;
  }
  .entry-card::before {
    inset: -6px;
    border-radius: 30px;
  }
  .entry-aurora {
    opacity: 0.28;
  }
  .entry-motes i:nth-child(n + 6) {
    display: none;
  }
  .entry-flow-map {
    opacity: 0.4;
  }
  .entry-page {
    padding: 20px 16px;
  }
  .entry-center {
    padding: 24px 0;
  }
  .entry-card {
    padding: 20px 22px 16px;
    border-radius: 24px;
    height: 760px;
  }
  .entry-tabs { height: 104px; }
  .entry-content {
    padding-top: 24px;
    min-height: 0;
  }
  .entry-visitor-body { grid-template-rows: 200px minmax(100px, 1fr) 144px; }
  .entry-content > .entry-primary { height: 72px; padding: 8px 16px; line-height: 1.4; }
  .entry-heading h1 {
    font-size: 25px;
  }
  .entry-glow {
    width: 120vw;
  }
  .glow-purple {
    left: -65%;
    top: -15%;
  }
  .glow-blue {
    right: -65%;
    top: 15%;
  }
  .glow-mint {
    bottom: -25%;
  }
  .entry-contour {
    width: 520px;
    height: 340px;
    opacity: 0.1;
  }
  .contour-left {
    left: -200px;
    bottom: 0;
  }
  .contour-right {
    right: -330px;
    top: 80px;
  }
  .entry-features {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }
  .entry-features > span {
    flex-direction: column;
    justify-content: flex-start;
    font-size: 18px;
    gap: 7px;
    white-space: normal;
    text-align: center;
  }
}
@media (max-width: 360px) {
  .entry-card {
    padding: 18px 18px 16px;
    height: 840px;
  }
  .entry-visitor-body { grid-template-rows: 230px minmax(100px, 1fr) 170px; }
  .entry-tabs button {
    font-size: 18px;
    gap: 6px;
  }
  .entry-features {
    flex-wrap: wrap;
    justify-content: center;
    column-gap: 14px;
    row-gap: 10px;
    padding-bottom: 20px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .entry-atmosphere {
    transform: none !important;
  }
  .flow-stream,
  .entry-motes,
  .entry-primary::after,
  .waypoint-wave,
  .scene-pin-wave {
    display: none;
  }
  .entry-page *,
  .entry-page *::before,
  .entry-page *::after {
    animation: none !important;
    transition: none !important;
  }
}
</style>
