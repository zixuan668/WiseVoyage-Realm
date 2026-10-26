<template>
  <view class="repair-mask" @tap="close"><view class="repair-panel" @tap.stop>
    <view class="repair-heading"><view><text class="repair-title">{{ t('调整剩余行程') }}</text><text class="repair-caption">{{ t('当前站') }} · {{ t(currentName) }}</text></view><button :disabled="applying" @tap="close" :aria-label="t('关闭')"><text class="iconfont icon-close" aria-hidden="true"></text></button></view>
    <scroll-view scroll-y class="repair-body">
      <text class="repair-note">{{ t('已游览的景点保持不变') }}</text>
      <view class="repair-goals"><button v-for="goal in goals" :key="goal.key" :class="{on:scenario===goal.key}" :disabled="applying" @tap="changeGoal(goal.key)">{{ t(goal.label) }}</button></view>
      <view class="repair-fields">
        <view class="repair-field"><text>{{ t(scenario==='time'?'剩余时间（分钟）':'时间上限（选填）') }}</text><input v-model="minutes" type="number" :disabled="applying" :placeholder="t('不限制时间')" maxlength="3" /></view>
        <picker :range="exitLabels" :value="exitIndex" :disabled="applying" @change="end=exits[Number($event.detail.value)]"><view class="repair-field"><text>{{ t('离园出口') }}</text><text class="repair-picker">{{ exitLabels[exitIndex] }} ⌄</text></view></picker>
      </view>
      <button class="repair-expand" :disabled="applying" @tap="advanced=!advanced">{{ t('保留景点与通行条件') }} {{ advanced?'−':'+' }}</button>
      <view v-if="advanced" class="repair-advanced">
        <view v-if="scenario!=='exit'" v-for="spot in remainingSpots" :key="spot.spot_id" class="repair-choice"><text>{{ t(spot.spot_name) }}</text><picker :range="choiceLabels" :value="choiceValues.indexOf(choices[spot.spot_id]||'auto')" :disabled="applying" @change="setChoice(spot.spot_id,choiceValues[Number($event.detail.value)])"><view class="repair-picker">{{ choiceLabels[choiceValues.indexOf(choices[spot.spot_id]||'auto')] }} ⌄</view></picker></view>
        <picker :range="[t('正常游览'),t('轻松慢走')]" :value="pace==='relaxed'?1:0" :disabled="applying" @change="pace=Number($event.detail.value)?'relaxed':'standard'"><view class="repair-field"><text>{{ t('行走节奏') }}</text><text>{{ t(pace==='relaxed'?'轻松慢走':'正常游览') }} ⌄</text></view></picker>
        <view class="repair-field"><text>{{ t('额外预留（分钟）') }}</text><input v-model="reserve" type="number" :disabled="applying" maxlength="3" /></view>
        <view class="repair-toggle"><text>{{ t('避开已标注台阶') }}</text><switch :checked="avoidSteps" :disabled="applying" color="#4f46e5" @change="avoidSteps=$event.detail.value" /></view>
        <view class="repair-toggle"><text>{{ t('允许优化未游览景点顺序') }}</text><switch :checked="reorder" :disabled="applying" color="#4f46e5" @change="reorder=$event.detail.value" /></view>
        <view class="repair-field"><text>{{ t('补充要求（选填）') }}</text><textarea v-model="message" :disabled="applying" maxlength="2000" :placeholder="t('例如：还剩40分钟，想少走路，从东宫门离园')" auto-height /></view>
      </view>
      <button class="repair-generate" :disabled="busy||applying" @tap="preview">{{ t(busy?'正在沿步道计算…':'生成调整方案') }}</button>
      <text v-if="error" class="repair-error">{{ t(error) }}</text>
      <template v-if="proposal">
        <view class="repair-plan-choices"><button v-for="(plan,index) in plans" :key="index" :class="{on:selected===index}" :disabled="applying" @tap="selected=index"><text>{{ t(plan.exit_only?(plan.end_anchor?'直接离园':'结束景点游览'):plan.strategy==='shortest'?'少走路方案':'保留重点方案') }}</text><text class="repair-note">{{ distance(plan.totals.walking_meters) }} · {{ plan.totals.total_minutes??'—' }} {{ t('分钟') }} · {{ plan.next_spots.length }} {{ t('个景点') }}</text></button></view>
        <text class="repair-summary">{{ summary }}</text>
        <text v-if="!proposal.feasible" class="repair-error">{{ failure }}</text>
        <view class="repair-deltas"><text>{{ t('时间变化') }} {{ delta(proposal.totals.total_minutes,proposal.original_totals.total_minutes) }} {{ t('分钟') }}</text><text>{{ t('步行变化') }} {{ delta(proposal.totals.walking_meters,proposal.original_totals.walking_meters) }} m</text></view>
        <view class="repair-stops"><text>{{ t(currentName) }} · {{ t('当前站') }}</text><text v-for="spot in proposal.next_spots" :key="spot.spot_id">↓ {{ t(spot.spot_name) }} {{ proposal.options.required_spot_ids?.includes(spot.spot_id)?t('必游'):'' }}</text><text v-if="proposal.end_anchor">↗ {{ t(proposal.end_anchor) }} · {{ t('离园') }}</text></view>
        <view v-if="proposal.removed.length" class="repair-removed"><text>{{ t('本次不再前往') }}</text><text v-for="spot in proposal.removed" :key="spot.spot_id">{{ t(spot.spot_name) }} · {{ removalReason(spot.reason) }}</text></view>
        <text v-if="proposal.reordered" class="repair-note">{{ t('已优化后续景点顺序，减少回头路。') }}</text>
        <RouteOverview :overview="proposal.proposed_route" :compare="proposal.original_route" :current-id="proposal.current_spot_id" />
        <text v-if="dirty||expired" class="repair-warning">{{ t(dirty?'条件已修改，请重新生成方案':'方案已过期，请重新生成') }}</text>
      </template>
      <text v-else class="repair-note">{{ t('选择调整目标，生成沿园内步道连接的行程。') }}</text>
    </scroll-view>
    <button v-if="proposal" class="repair-apply" :disabled="!canApply" @tap="apply">{{ t(applying?'正在更新…':proposal.unchanged?'保留当前路线':'采用此方案') }}</button>
  </view></view>
</template>
<script>
import RouteOverview from './RouteOverview.vue'
import { routeRequest, routeChangeText } from '../common/route-planning.js'
export default {
  components:{RouteOverview},props:{sid:Number,currentName:String,remainingSpots:{type:Array,default:()=>[]},prompt:{type:String,default:''},initial:{type:Object,default:()=>({})}},
  emits:['close','applied','refresh'],
  data(){return{scenario:'time',message:this.prompt,minutes:this.initial.minutes??'',pace:this.initial.pace||'standard',end:this.initial.end||'auto',reserve:0,avoidSteps:!!this.initial.avoidSteps,reorder:true,choices:Object.fromEntries((this.initial.required||[]).map(id=>[id,'required'])),advanced:false,busy:false,applying:false,error:'',plans:[],selected:0,accepted:'',clock:Date.now(),exits:['auto','east','north','south'],choiceValues:['auto','required','skip'],goals:[{key:'time',label:'时间不够'},{key:'less_walking',label:'想少走路'},{key:'skip',label:'跳过下一站'},{key:'exit',label:'准备离园'}]}},
  computed:{
    exitLabels(){return[this.t(this.scenario==='exit'?'请选择出口':'末站结束，不计离园'),this.t('东宫门'),this.t('北宫门'),this.t('新建宫门')]},exitIndex(){return this.exits.indexOf(this.end)},
    choiceLabels(){return[this.t('交给系统安排'),this.t('必须保留'),this.t('跳过')]},
    formKey(){return JSON.stringify([this.sid,this.remainingSpots.map(s=>s.spot_id),this.scenario,this.message,this.minutes,this.pace,this.end,this.reserve,this.avoidSteps,this.reorder,this.remainingSpots.map(s=>[s.spot_id,this.choices[s.spot_id]||'auto'])])},
    proposal(){return this.plans[this.selected]||null},dirty(){return !!this.plans.length&&this.formKey!==this.accepted},expired(){return !!this.proposal?.expires_at&&this.clock>=this.proposal.expires_at*1000},
    canApply(){return !!this.proposal?.feasible&&!this.dirty&&!this.expired&&!this.busy&&!this.applying},
    summary(){const p=this.proposal;if(!p)return'';return this.t(p.unchanged?'当前路线已满足条件，可以保留原路线。':p.exit_only?(p.end_anchor?'停止后续景点游览，沿步道前往所选出口。':'当前条件下没有可继续游览的景点，请选择离园出口或调整条件。'):p.strategy==='shortest'?'优先减少步行，兼顾原行程中的重点景点。':'在可用时间内优先保留兴趣匹配和必游景点。')},
    failure(){return this.t(this.proposal?.failure_code==='no_path'?'当前条件下没有连通的步行路线，请调整景点或通行条件。':this.proposal?.failure_code==='required_budget'?'时间不足以保留全部必游景点，请增加时间或减少必游景点。':'剩余时间不足以完成此方案，请增加时间或调整条件。')},
  },
  watch:{formKey(){if(this._hydrating)return;this._version=(this._version||0)+1;this._preview?.abort();this.busy=false}},
  mounted(){this._owner=this.owner();this._timer=setInterval(()=>{this.clock=Date.now()},1000)
    if(this.prompt){const intent=routeChangeText(this.prompt),timed=/\d|[一二两三四五六七八九十半].*(?:分钟|小时)|half an? hour/i.test(intent)
      if(!timed){if(/跳过|不去|skip/i.test(intent))this.changeGoal('skip');else if(/累了|少走|tired|less walking/i.test(intent))this.changeGoal('less_walking');else if(/离园|leave|exit/i.test(intent))this.changeGoal('exit')}
      this.$nextTick(()=>{if(timed||this.scenario!=='time'&&this.scenario!=='exit'||this.scenario==='exit'&&/东门|东宫门|北门|北宫门|南门|新建宫门|east|north|south/i.test(this.prompt))this.preview()})
    }
  },
  beforeUnmount(){this._disposed=true;this._version=(this._version||0)+1;this._preview?.abort();clearInterval(this._timer)},
  methods:{
    owner(){return String(uni.getStorageSync('user_id')||uni.getStorageSync('username')||'guest')},
    close(){if(!this.applying)this.$emit('close')},
    changeGoal(goal){if(this.applying)return;this.scenario=goal;if(goal==='skip'&&this.remainingSpots[0])this.setChoice(this.remainingSpots[0].spot_id,'skip');if(goal==='exit')this.choices={}},
    setChoice(id,choice){this.choices={...this.choices,[id]:choice}},distance(n){return n==null?'—':n>=1000?(n/1000).toFixed(2)+' km':n+' m'},delta(a,b){if(a==null||b==null)return'—';return(a-b>0?'+':'')+(a-b)},
    removalReason(key){return this.t(({visitor:'按你的要求',stairs:'避开已标注台阶',budget:'为其他景点与离园保留时间',less_walking:'减少步行与回头路',exit:'按你的要求直接离园',routing:'当前通行条件下没有连通路径'})[key]||key)},
    async preview(){
      if(this.busy||this.applying)return
      const time=this.minutes===''?null:Number(this.minutes),reserve=this.reserve===''?0:Number(this.reserve)
      if(time!==null&&(!Number.isInteger(time)||time<1||time>480)){this.error='剩余时间须为1至480分钟';return}
      if(!Number.isInteger(reserve)||reserve<0||reserve>120){this.error='额外预留须为0至120分钟';return}
      const timed=/\d|[一二两三四五六七八九十半].*(?:分钟|小时)|half an? hour/i.test(this.message)
      if(this.scenario==='time'&&!time&&!timed){this.error='请填写剩余时间，再生成方案';return}
      if(this.scenario==='exit'&&this.end==='auto'&&!/东门|东宫门|北门|北宫门|南门|新建宫门|east|north|south/i.test(this.message)){this.error='请选择具体离园出口';return}
      this.error='';this.busy=true;this.plans=[];const own=this._version=(this._version||0)+1,sid=this.sid,owner=this.owner()
      const options={message:this.message,remaining_minutes:time,pace:this.pace,end_area:this.end,reserve_minutes:reserve,excluded_spot_ids:this.remainingSpots.filter(s=>this.choices[s.spot_id]==='skip').map(s=>s.spot_id),required_spot_ids:this.remainingSpots.filter(s=>this.choices[s.spot_id]==='required').map(s=>s.spot_id),scenario:this.scenario,strategy:this.scenario==='less_walking'?'shortest':'highlights',avoid_steps:this.avoidSteps,allow_reorder:this.reorder}
      const task=this._preview=routeRequest('/tour-session/'+sid+'/replan/preview',options,sid)
      try{const result=await task.promise;if(this._disposed||own!==this._version||sid!==this.sid||owner!==this.owner())return
        const o=result.options;this._hydrating=true;this.message='';this.minutes=o.remaining_minutes??'';this.pace=o.pace;this.end=o.end_area;this.reserve=o.reserve_minutes;this.avoidSteps=!!o.avoid_steps;this.reorder=o.allow_reorder!==false;this.scenario=o.scenario||this.scenario
        this.choices=Object.fromEntries([...(o.excluded_spot_ids||[]).map(id=>[id,'skip']),...(o.required_spot_ids||[]).map(id=>[id,'required'])]);this.selected=0;this.plans=[result,...(result.alternatives||[])];this.accepted=this.formKey;this.clock=Date.now();await this.$nextTick();this._hydrating=false
      }catch(error){if(!this._disposed&&own===this._version)this.error=error.message||'调整方案生成失败，请重试'}
      finally{if(!this._disposed&&own===this._version)this.busy=false}
    },
    async apply(){
      if(!this.canApply)return
      if(this.owner()!==this._owner){this.plans=[];this.error='登录账号已变化，请重新开始导览';return}
      const p=this.proposal;if(p.unchanged){this.close();return}
      this.applying=true;this.error='';const sid=this.sid,owner=this.owner()
      try{const result=await routeRequest('/tour-session/'+sid+'/replan/apply',{proposal_token:p.proposal_token},sid,15000).promise;if(!this._disposed&&sid===this.sid&&owner===this.owner())this.$emit('applied',result)}
      catch(error){if(!this._disposed){this.error=error.message||'路线更新失败，请重试';if(error.status===409){this.plans=[];this.$emit('refresh')}}}
      finally{if(!this._disposed)this.applying=false}
    },
  },
}
</script>
<style scoped>
.repair-mask{position:fixed;inset:0;z-index:1600;background:rgba(26,30,48,.38);display:flex;align-items:flex-end;color:var(--ng-text)}.repair-panel{display:flex;flex-direction:column;width:100%;height:92vh;max-height:92vh;padding:28rpx 28rpx calc(24rpx + env(safe-area-inset-bottom));box-sizing:border-box;border-radius:30rpx 30rpx 0 0;background:var(--ng-surface,#fff)}.repair-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:16rpx;padding-bottom:20rpx;flex-shrink:0}.repair-title{display:block;font-size:35rpx;font-weight:600}.repair-caption{display:block;font-size:25rpx;color:var(--ng-secondary);margin-top:10rpx}.repair-heading button{margin:0;padding:0 18rpx;line-height:1.6;font-size:36rpx;background:#f4f1f9;color:#655574}.repair-body{height:0;flex:1;min-height:0}.repair-note{display:block;font-size:24rpx;color:var(--ng-secondary);line-height:1.7;margin:14rpx 0}.repair-goals{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12rpx;margin:20rpx 0}.repair-goals button{font-size:27rpx;padding:4rpx 10rpx;background:#f5f6fa;color:#566176;border:1rpx solid var(--ng-border);border-radius:14rpx;margin:0}.repair-goals .on,.repair-plan-choices .on{background:#eee8f8;color:#5e429c;border-color:#bda8de}.repair-fields{display:grid;grid-template-columns:1fr 1fr;gap:14rpx}.repair-field{margin:14rpx 0;font-size:25rpx;line-height:1.7;color:var(--ng-secondary)}.repair-field>text:first-child{display:block;margin-bottom:8rpx}.repair-field input,.repair-picker,.repair-field textarea{box-sizing:border-box;min-width:0;width:100%;border:1rpx solid var(--ng-border);background:#f9f9fc;border-radius:13rpx;padding:17rpx;font-size:27rpx;line-height:1.5;color:var(--ng-text)}.repair-field input{height:78rpx}.repair-field textarea{min-height:90rpx}.repair-expand{margin:18rpx 0;font-size:25rpx;background:#f5f2fa;color:#67518f;text-align:left}.repair-choice{display:flex;align-items:center;justify-content:space-between;gap:18rpx;padding:12rpx 0;font-size:26rpx}.repair-choice>text{min-width:0;flex:1}.repair-choice picker{width:270rpx;flex-shrink:0}.repair-toggle{display:flex;align-items:center;justify-content:space-between;gap:14rpx;font-size:25rpx;margin:20rpx 0}.repair-toggle text{flex:1}.repair-generate,.repair-apply{background:#6551af;color:#fff;font-size:29rpx;border-radius:15rpx;margin:22rpx 0}.repair-apply{flex-shrink:0;margin-bottom:0}.repair-generate[disabled],.repair-apply[disabled]{opacity:.4;color:#fff;background:#6551af}.repair-error{display:block;color:#a43b51;background:#fff0f3;padding:18rpx;border-radius:13rpx;line-height:1.7;font-size:26rpx;margin:20rpx 0}.repair-warning{display:block;color:#90632c;background:#fff5e3;padding:18rpx;font-size:25rpx;line-height:1.7}.repair-plan-choices{display:grid;gap:12rpx;margin-top:24rpx}.repair-plan-choices button{margin:0;padding:18rpx 20rpx;text-align:left;background:#f8f8fc;border:1rpx solid var(--ng-border);border-radius:15rpx;font-size:29rpx;line-height:1.7;color:var(--ng-text)}.repair-plan-choices text{display:block}.repair-summary{display:block;font-size:26rpx;line-height:1.8;margin:20rpx 0}.repair-deltas{display:flex;flex-wrap:wrap;gap:20rpx;font-size:25rpx;padding:18rpx;background:#f3f5fa;border-radius:14rpx}.repair-stops,.repair-removed{margin:22rpx 0;display:grid;gap:13rpx;font-size:27rpx;line-height:1.7}.repair-removed{font-size:24rpx;color:var(--ng-secondary);border-top:1rpx solid var(--ng-border);padding-top:18rpx}
</style>

<style scoped>
.repair-fields>picker,.repair-field{min-width:0}.repair-picker{display:block;overflow-wrap:anywhere;white-space:normal}
</style>
