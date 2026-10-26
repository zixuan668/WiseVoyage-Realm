export const tabMotion = { direction: 1, at: 0, from: 0, to: 0 }
export const tabMotionMixin = {
  data(){return {tabEnterClass:''}},
  onLoad(){if(Date.now()-tabMotion.at<2000)this.tabEnterClass=tabMotion.direction>0?'tab-enter-right':'tab-enter-left'},
}
