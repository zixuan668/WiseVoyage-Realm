<template>
  <view class="onboarding" :class="{ 'is-english': english, 'is-bursting': bursting, 'is-opening': showLogin, 'is-pressing': pressing, 'is-skipping': skipping }">
    <view class="intro-header">
      <button class="skip" :disabled="leaving" hover-class="none" @tap="skipIntro">{{ english ? 'Skip' : '跳过' }}</button>
      <button class="lang-switch" :class="{ 'is-eng': !english }" hover-class="none" :aria-label="english ? '切换到中文' : 'Switch to English'" :aria-pressed="english" @tap="toggleLanguage">{{ english ? '中' : 'ENG' }}</button>
    </view>

    <swiper class="intro-swiper" :current="current" :duration="520" :circular="false" :autoplay="false" :disable-touch="leaving" @change="onChange" @transition="onTransition" @animationfinish="onAnimationFinish" @touchstart="onTouchStart" @touchend="onTouchEnd" @touchcancel="onTouchEnd">
      <swiper-item v-for="(slide, index) in slides" :key="slide.id">
        <view class="intro-slide" :class="{ 'is-current': current === index }">
          <view class="illustration-space">
            <view class="illustration-halo" />
            <image class="intro-illustration" :src="slide.image" mode="aspectFit" :alt="slide.alt" />
          </view>
          <view class="intro-copy">
            <text class="intro-title">{{ slide.title }}</text>
          </view>
        </view>
      </swiper-item>
    </swiper>

    <view class="intro-footer">
      <view class="pagination" :class="{ tracking }" role="group" :aria-label="english ? 'Introduction pages' : '介绍页切换'">
        <button v-for="(slide, index) in slides" :key="slide.id" class="dot-target" :disabled="leaving" :aria-label="(english ? 'Page ' : '第 ') + (index + 1) + (english ? '' : ' 页')" :aria-current="current === index ? 'step' : undefined" @tap="selectSlide(index)">
          <view class="dot" />
        </button>
        <view class="active-dot" :style="indicatorStyle" aria-hidden="true" />
      </view>
      <view class="cta-space">
        <view v-if="current === slides.length - 1" class="cta-float">
          <button class="continue-button" :disabled="leaving" hover-class="none" @touchstart="holdStart" @touchend="holdEnd" @touchcancel="holdCancel" @tap="finish(true)">
            <text class="cta-label">{{ english ? 'Start exploring' : '开始体验' }}</text>
          </button>
        </view>
      </view>
    </view>

    <view v-if="showLogin" class="auth-reveal-layer" :style="revealStyle" aria-hidden="true"><AuthPage /></view>
    <view v-if="bursting" class="burst-layer" aria-hidden="true">
      <view v-for="particle in particles" :key="particle.id" class="burst-particle" :style="particle.style" />
    </view>
  </view>
</template>

<script>
import { LOGIN_PROVIDER } from '../../common/config.js'
import { LANGUAGE_STORAGE_KEY } from '../../common/tour-language.js'
import { ONBOARDING_STORAGE_KEY, appEntry } from '../../common/onboarding.js'
import AuthPage from '../auth/auth.vue'

export default {
  components: { AuthPage },
  data() {
    return { current: 0, progress: 0, transitionBase: 0, tracking: false, leaving: false, english: false,
      slideWidth: 375, dotStep: 32, bursting: false, showLogin: false, pressing: false, skipping: false,
      particles: [], originX: 187, originY: 700 }
  },
  computed: {
    slides() {
      const copy = this.english ? [
        { title: 'Your places.\nYour own journey.', alt: 'A garden, a bridge and a winding route' },
        { title: 'Every view\nhas a story.', alt: 'A welcoming digital tour guide' },
        { title: 'Stay curious.\nJust ask.', alt: 'An AI companion with a travel journal' },
      ] : [
        { title: '想去哪里\n就从这里出发', alt: '园林、石桥与连接景点的游览路线插画' },
        { title: '山水有故事\n一路讲给你听', alt: '向游客招手的数字人导游插画' },
        { title: '旅途有疑问\n随时问小导游', alt: 'AI 小导游与旅行手账插画' },
      ]
      return copy.map((slide, index) => ({ ...slide, id: index, image: '/static/onboarding/intro-' + (index + 1) + '.png' }))
    },
    indicatorStyle() {
      const fraction = this.progress - Math.floor(this.progress)
      const stretch = this.tracking ? 1 + Math.sin(fraction * Math.PI) * .7 : 1
      return { transform: 'translate3d(' + (this.progress * this.dotStep) + 'px,0,0) scaleX(' + stretch + ')' }
    },
    revealStyle() { return { transformOrigin: this.originX + 'px ' + this.originY + 'px' } },
  },
  onLoad() {
    this.english = uni.getStorageSync(LANGUAGE_STORAGE_KEY) === 'en'
    const info = uni.getSystemInfoSync()
    this.slideWidth = info.windowWidth || 375
    this.dotStep = this.slideWidth * 46 / 750
    if (uni.getStorageSync(ONBOARDING_STORAGE_KEY)) this.openEntry()
  },
  onUnload() { clearTimeout(this._shrinkTimer); clearTimeout(this._revealTimer); clearTimeout(this._entryTimer) },
  onResize(event) {
    this.slideWidth = event.size.windowWidth
    this.dotStep = this.slideWidth * 46 / 750
  },
  methods: {
    setLanguage(language) {
      if (this.leaving) return
      const next = language === 'en' ? 'en' : 'zh'
      this.english = next === 'en'
      try { uni.setStorageSync(LANGUAGE_STORAGE_KEY, next) } catch (error) {}
    },
    toggleLanguage() { this.setLanguage(this.english ? 'zh' : 'en') },
    onTouchStart() {
      if (this.leaving) return
      this.transitionBase = Math.round(this.progress)
      this.tracking = true
    },
    onTouchEnd() { this.tracking = false; this.progress = this.current },
    onTransition(event) {
      if (!this.tracking) return
      this.progress = Math.max(0, Math.min(this.slides.length - 1, this.transitionBase + event.detail.dx / this.slideWidth))
    },
    onChange(event) {
      this.current = event.detail.current
      if (!this.tracking) this.progress = this.current
    },
    onAnimationFinish(event) {
      this.current = event.detail.current
      this.progress = this.current
      this.transitionBase = this.current
      this.tracking = false
    },
    selectSlide(index) {
      if (this.leaving) return
      this.tracking = false
      this.current = index
      this.progress = index
    },
    completeIntro() {
      try { uni.setStorageSync(ONBOARDING_STORAGE_KEY, true); return true }
      catch (error) {
        uni.showToast({ title: this.english ? 'Could not save. Please try again.' : '保存失败，请重试', icon: 'none' })
        return false
      }
    },
    holdStart() {
      if (this.leaving) return
      this.pressing = true
    },
    holdEnd() {
      if (this.leaving) return
      this.pressing = false
      this.release()
    },
    holdCancel() {
      if (this.leaving) return
      this.pressing = false
    },
    release() {
      if (this.leaving) return
      this.pressing = false
      if (!this.completeIntro()) return
      this.leaving = true
      // The dots must leave from the words themselves, not from the whole pill.
      uni.createSelectorQuery().in(this).select('.cta-label').boundingClientRect(rect => {
        if (!rect) { this.navigateToLogin(); return }
        this.originX = rect.left + rect.width / 2
        this.originY = rect.top + rect.height / 2
        this.particles = this.makeParticles(rect)
        this.bursting = true
        this._revealTimer = setTimeout(() => { this.showLogin = true }, 320)
        this._entryTimer = setTimeout(() => this.navigateToLogin(), 1350)
      }).exec()
    },
    finish(animate = true) {
      if (this.leaving) return
      if (!animate) {
        if (!this.completeIntro()) return
        this.leaving = true
        this.navigateToLogin()
        return
      }
      // Mouse / H5 fallback: press briefly, then release into the dots.
      this.holdStart()
      this._shrinkTimer = setTimeout(() => this.release(), 180)
    },
    skipIntro() {
      if (this.leaving) return
      if (!this.completeIntro()) return
      this.leaving = true
      uni.createSelectorQuery().in(this).select('.skip').boundingClientRect(rect => {
        if (!rect) { this.navigateToLogin(); return }
        this.originX = rect.left + rect.width / 2
        this.originY = rect.top + rect.height / 2
        // The skip label lifts away while sign-in pops out from where it sat.
        this.skipping = true
        this._revealTimer = setTimeout(() => { this.showLogin = true }, 70)
        this._entryTimer = setTimeout(() => this.navigateToLogin(), 980)
      }).exec()
    },
    makeParticles(rect) {
      const particles = []
      const shades = ['#6750d9', '#8f7ce8', '#ae9bf0', '#c9bcf5', '#e0d8fb']
      // Sample the label box so the dissolve reads as the words breaking apart;
      // sizes run from tiny grains to a few larger beads.
      for (let row = 0; row < 4; row++) for (let column = 0; column < 18; column++) {
        const id = row * 18 + column
        const seed = ((id * 73 + 19) % 101) / 101
        const x = (column + .5) / 18 * rect.width
        const y = (row + .5) / 4 * rect.height
        const angle = Math.atan2(y - rect.height / 2, x - rect.width / 2)
        const size = 1.6 + seed * seed * 5.5
        const distance = 46 + seed * 150 + size * 5
        const wipe = Math.min(1, (x / rect.width) * .88 + (y / rect.height) * .12)
        particles.push({ id, style: {
          left: rect.left + x + 'px', top: rect.top + y + 'px', width: size + 'px', height: size + 'px',
          '--scatter-x': Math.cos(angle) * distance + 'px', '--scatter-y': Math.sin(angle) * distance - 24 + 'px',
          animationDelay: Math.round(wipe * 150 + seed * 22) + 'ms',
          backgroundColor: shades[id % shades.length],
        } })
      }
      return particles
    },
    navigateToLogin() {
      uni.reLaunch({ url: '/pages/auth/auth?fromOnboarding=1', fail: () => this.navigationFailed() })
    },
    navigationFailed() {
      clearTimeout(this._revealTimer); clearTimeout(this._entryTimer)
      this.leaving = false; this.bursting = false; this.showLogin = false; this.pressing = false; this.skipping = false
      uni.showToast({ title: this.english ? 'Could not open. Please try again.' : '页面打开失败，请重试', icon: 'none' })
    },
    openEntry() {
      if (this.leaving) return
      this.leaving = true
      uni.reLaunch({
        url: appEntry(uni, LOGIN_PROVIDER),
        fail: () => this.navigationFailed(),
      })
    },
  },
}
</script>

<style scoped>
.onboarding{--intro-purple:#6750d9;--intro-purple-soft:#8f7ce8;--intro-ink:#29263b;--intro-muted:#6d687f;position:relative;box-sizing:border-box;width:100%;height:100vh;height:100dvh;overflow:hidden;display:flex;flex-direction:column;color:var(--intro-ink);background:linear-gradient(135deg,#eee8ff 0%,#fbfbff 52%,#eef8fc 100%);padding-top:var(--status-bar-height,0px);font-family:var(--app-font-family)}
.intro-header{flex-shrink:0;display:flex;align-items:center;justify-content:flex-end;gap:20rpx;padding:18rpx 34rpx 0 34rpx;height:94rpx;box-sizing:border-box}
.lang-switch{width:64rpx;height:64rpx;min-height:0;padding:0;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.68);border:1rpx solid rgba(255,255,255,.92);box-shadow:0 6rpx 16rpx rgba(103,80,217,.14),inset 0 1rpx 0 rgba(255,255,255,.95);color:var(--intro-purple);font-size:26rpx;letter-spacing:0;-webkit-tap-highlight-color:transparent}
.lang-switch.is-eng{font-size:19rpx;letter-spacing:0;font-weight:600}
.lang-switch[disabled]{background:rgba(255,255,255,.68);color:var(--intro-purple)}
button{font-family:inherit;box-sizing:border-box;margin:0;padding:0;border:0;line-height:1.4;background:transparent}
button::after{border:0}
.skip{min-width:92rpx;min-height:88rpx;display:flex;align-items:center;justify-content:center;color:#6b617f;font-size:27rpx;-webkit-tap-highlight-color:transparent}
.skip[disabled]{background:transparent;color:#6b617f}
.is-skipping .skip{opacity:0;transform:translateY(-20rpx);transition:transform 260ms cubic-bezier(.3,.8,.3,1),opacity 200ms ease}
.intro-swiper{flex:1;min-height:0;width:100%}
.intro-slide{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;box-sizing:border-box;padding:10rpx 40rpx 30rpx}
.illustration-space{position:relative;display:flex;align-items:center;justify-content:center;width:620rpx;height:600rpx;max-height:50%;flex-shrink:1;margin-bottom:34rpx}
.illustration-halo{position:absolute;width:83%;height:83%;border-radius:50%;background:radial-gradient(ellipse,rgba(208,197,255,.28),rgba(229,225,255,.08) 60%,transparent 72%)}
.intro-illustration{position:relative;width:100%;height:100%;transform:translateY(12rpx) scale(.96);transition:transform 750ms cubic-bezier(.22,1,.36,1);will-change:transform}
.is-current .intro-illustration{transform:translateY(0) scale(1)}
.intro-copy{flex-shrink:0;text-align:center;width:100%;display:flex;flex-direction:column;align-items:center}
.intro-title{font-size:44rpx;font-weight:700;line-height:1.48;letter-spacing:3rpx;white-space:pre-line}
.intro-footer{flex-shrink:0;display:flex;flex-direction:column;align-items:center;padding:0 68rpx calc(24rpx + env(safe-area-inset-bottom));box-sizing:border-box}
.pagination{position:relative;display:flex;align-items:center;justify-content:center;margin-bottom:22rpx;height:80rpx}
.dot-target{width:46rpx;min-height:88rpx;display:flex;align-items:center;justify-content:center}
.dot-target[disabled]{background:transparent}
.dot{width:14rpx;height:14rpx;border-radius:50%;background:#d7cfed}
.active-dot{position:absolute;left:16rpx;top:33rpx;width:14rpx;height:14rpx;border-radius:50%;background:var(--intro-purple-soft);pointer-events:none;will-change:transform;transition:transform 520ms cubic-bezier(.34,1.65,.45,1)}
.tracking .active-dot{transition:none}
.cta-space{width:100%;height:100rpx;min-height:48px}
.cta-float{position:relative;width:100%;animation:ctaFloat 4.6s ease-in-out infinite;will-change:transform}
.continue-button{position:relative;width:100%;height:100rpx;min-height:48px;border-radius:30rpx;overflow:hidden;background:transparent;border:0;color:var(--intro-purple);font-size:31rpx;font-weight:600;letter-spacing:3rpx;display:flex;align-items:center;justify-content:center;box-shadow:none;transition:transform 180ms cubic-bezier(.3,.8,.35,1);-webkit-tap-highlight-color:transparent}
.cta-label{position:relative;z-index:2}
.is-pressing .continue-button{transform:scale(.95)}
.continue-button[disabled]{opacity:1;color:var(--intro-purple);background:transparent}
.continue-button{animation:ctaAppear 380ms cubic-bezier(.22,1,.36,1)}
.is-bursting .continue-button{-webkit-mask-image:linear-gradient(110deg,#000 0%,#000 38%,rgba(0,0,0,0) 58%,rgba(0,0,0,0) 100%);-webkit-mask-size:260% 100%;-webkit-mask-position:100% 0;-webkit-mask-repeat:no-repeat;animation:ctaWipe 260ms cubic-bezier(.4,0,.3,1) forwards;pointer-events:none}
.is-bursting .cta-float{animation:none}
@keyframes ctaFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-3rpx)}}
@keyframes ctaWipe{0%{-webkit-mask-position:0% 0;opacity:1}72%{opacity:1}100%{-webkit-mask-position:100% 0;opacity:0}}
.burst-layer{position:fixed;inset:0;z-index:60;pointer-events:none;overflow:hidden}/* dots scatter above the sign-in reveal */
.burst-particle{position:absolute;display:block;border-radius:50%;animation:particlePop 620ms cubic-bezier(.12,.65,.25,1) both;will-change:transform,opacity}
.is-opening .intro-header,.is-opening .intro-swiper,.is-opening .intro-footer{opacity:0;transition:opacity 200ms ease;pointer-events:none}
.auth-reveal-layer{position:fixed;inset:0;z-index:50;overflow:hidden;background:linear-gradient(135deg,#eee8ff 0%,#fbfbff 52%,#eef8fc 100%);pointer-events:none;animation:loginSpring 850ms linear both;will-change:transform,opacity,border-radius}
@keyframes ctaAppear{from{opacity:0;transform:translateY(12px) scale(.97)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes particlePop{0%{opacity:1;transform:translate3d(0,0,0) scale(1)}18%{opacity:1}100%{opacity:0;transform:translate3d(var(--scatter-x),var(--scatter-y),0) scale(.05)}}
@keyframes loginSpring{0%{opacity:0;transform:scale(.1,.045);border-radius:180px}12%{opacity:1}45%{transform:scale(1.045,1.025);border-radius:32px}64%{transform:scale(.985,.99);border-radius:12px}82%{transform:scale(1.007,1.004);border-radius:4px}100%{opacity:1;transform:scale(1);border-radius:0}}
button:focus-visible{outline:2px solid var(--intro-purple);outline-offset:4px}
.is-english .intro-title{font-size:39rpx;letter-spacing:0;line-height:1.35}

.is-english .continue-button{letter-spacing:0}
@media(max-height:700px){.illustration-space{margin-bottom:20rpx}.intro-slide{padding-bottom:8rpx}.intro-title{font-size:40rpx}.intro-description{margin-top:18rpx}.pagination{margin-bottom:10rpx}.intro-footer{padding-bottom:calc(20rpx + env(safe-area-inset-bottom))}}
@media(orientation:landscape) and (max-height:600px){.intro-header{height:54px;padding-top:0}.intro-slide{flex-direction:row;gap:24px;padding:0 8vw}.illustration-space{width:32vw;height:100%;max-height:100%;margin:0}.intro-copy{width:48%;text-align:left;align-items:flex-start}.intro-title{font-size:25px;letter-spacing:1px;line-height:1.3}.intro-description{font-size:14px;line-height:1.6;margin-top:12px}.intro-footer{padding:0 24px 10px;position:relative}.pagination{height:44px;margin:0}.dot-target{min-height:44px}.active-dot{top:calc(50% - 7rpx)}.cta-space{height:44px;min-height:44px;display:flex;justify-content:center}.continue-button{width:220px;height:44px;min-height:44px;font-size:16px}.skip{font-size:14px;min-height:44px;min-width:48px}}
@media(prefers-reduced-motion:reduce){.intro-illustration,.active-dot{transition:none}.intro-illustration{transform:none}.continue-button{animation:none}.cta-float{animation:none}.burst-particle{animation:none;opacity:0}.auth-reveal-layer{animation:loginFade 120ms ease both}.is-bursting .continue-button{animation:none;opacity:0;-webkit-mask-image:none}}
@keyframes loginFade{from{opacity:0}to{opacity:1}}
</style>