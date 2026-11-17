export function sharedPlanUrl(handoff) {
  const ids=handoff?.ids
  if(!Array.isArray(ids)||!ids.length||ids.length>20||new Set(ids).size!==ids.length||ids.some(id=>!Number.isInteger(id)||id<=0))throw new Error('所选景点不可用，请重新规划')
  const areas=['auto','east','north','south'],plan=handoff.planning||{}
  return '/pages/scenic/scenic?view=plan&spotIds='+ids.join(',')
    +'&elderly='+(handoff.senior?'1':'0')+'&children='+(handoff.child?'1':'0')
    +'&avoidSteps='+(plan.avoid_steps?'1':'0')
    +'&startArea='+(areas.includes(plan.start_area)?plan.start_area:'auto')
    +'&endArea='+(areas.includes(plan.end_area)?plan.end_area:'auto')
}
