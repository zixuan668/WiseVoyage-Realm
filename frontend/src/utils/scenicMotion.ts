// Content-only motion. Every run cancels its predecessor so rapid navigation stays safe.
const easeOut = 'cubic-bezier(0.23, 1, 0.32, 1)'

export function createScenicMotion() {
  const animations = new Set<Animation>()
  const overlays = new Set<HTMLElement>()
  let version = 0
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches
  function cancel() {
    version++
    for (const animation of animations) animation.cancel()
    for (const overlay of overlays) overlay.remove()
    animations.clear()
    overlays.clear()
  }
  function play(element: HTMLElement, frames: Keyframe[], duration = 240) {
    if (reduced() || !element.animate) return
    const animation = element.animate(frames, {duration, easing:easeOut})
    animations.add(animation)
    void animation.finished.catch(() => {}).finally(() => animations.delete(animation))
  }
  function snapshot(element: HTMLElement | null) {
    cancel()
    if (!element || reduced()) return null
    const rect=element.getBoundingClientRect()
    const computed=getComputedStyle(element)
    const clone=element.cloneNode(true) as HTMLElement
    clone.classList.remove('catalog-panel')
    clone.removeAttribute('id')
    clone.querySelectorAll('[id]').forEach(child=>child.removeAttribute('id'))
    clone.setAttribute('aria-hidden','true')
    clone.inert=true
    clone.dataset.motionSnapshot='true'
    Object.assign(clone.style,{
      position:'fixed',inset:'auto',left:rect.left+'px',top:rect.top+'px',
      width:rect.width+'px',height:rect.height+'px',maxHeight:'none',
      margin:'0',zIndex:'190',pointerEvents:'none',boxSizing:'border-box',
      background:computed.background,borderRadius:computed.borderRadius,overflow:'hidden'
    })
    const host=element.closest<HTMLElement>('.phone') || element.parentElement
    host?.appendChild(clone)
    overlays.add(clone)
    return clone
  }
  function enter(element:HTMLElement|null, old:HTMLElement|null, back=false) {
    if(reduced()){old?.remove();return}
    if(element)play(element,[{transform:back?'translateX(-18px)':'translateX(32px)'},{transform:'translateX(0)'}])
    if(old){
      play(old,[{transform:'translateX(0)'},{transform:back?'translateX(100%)':'translateX(-100%)'}])
      const own=version
      setTimeout(()=>{if(own===version){old.remove();overlays.delete(old)}},250)
    }
  }
  function photo(source:HTMLElement, target:()=>HTMLElement|null) {
    cancel()
    if(reduced())return
    const img=source.matches('img')?source as HTMLImageElement:source.querySelector('img')
    if(!img?.src)return
    const from=source.getBoundingClientRect()
    const picture=document.createElement('img')
    picture.src=img.src
    picture.alt=''
    picture.setAttribute('aria-hidden','true')
    picture.dataset.motionPhoto='true'
    Object.assign(picture.style,{position:'fixed',objectFit:'cover',pointerEvents:'none',zIndex:'195',borderRadius:'12px'})
    document.body.appendChild(picture)
    overlays.add(picture)
    const own=version
    requestAnimationFrame(()=>{
      if(own!==version)return
      const destination=target()
      if(!destination){picture.remove();overlays.delete(picture);return}
      const to=destination.getBoundingClientRect()
      Object.assign(picture.style,{left:to.left+'px',top:to.top+'px',width:to.width+'px',height:to.height+'px'})
      play(picture,[
        {transform:`translate(${from.left-to.left}px,${from.top-to.top}px) scale(${from.width/to.width},${from.height/to.height})`,transformOrigin:'top left',borderRadius:'12px'},
        {transform:'translate(0,0) scale(1,1)',transformOrigin:'top left',borderRadius:'30px 30px 0 0'}
      ],320)
      setTimeout(()=>{picture.remove();overlays.delete(picture)},330)
    })
  }
  function flight(source:HTMLElement|null,target:HTMLElement|null) {
    cancel()
    if(!source||!target||reduced())return
    const from=source.getBoundingClientRect(),to=target.getBoundingClientRect()
    const img=source.querySelector('img')
    const token=document.createElement(img?'img':'span')
    if(img)(token as HTMLImageElement).src=img.src
    else token.textContent='✓'
    token.setAttribute('aria-hidden','true')
    Object.assign(token.style,{position:'fixed',left:from.left+'px',top:from.top+'px',width:'32px',height:'32px',
      borderRadius:'8px',objectFit:'cover',background:'#6957cd',color:'white',display:'grid',placeItems:'center',
      zIndex:'220',pointerEvents:'none',transformOrigin:'center'})
    document.body.appendChild(token);overlays.add(token)
    play(token,[{transform:'translate(0,0) scale(1)',opacity:1},
      {transform:`translate(${to.left+to.width/2-from.left-16}px,${to.top+to.height/2-from.top-16}px) scale(.5)`,opacity:.8}],280)
    const own=version
    setTimeout(()=>{
      token.remove();overlays.delete(token)
      if(own===version&&target.isConnected)play(target,[{transform:'scale(1)'},{transform:'scale(1.07)'},{transform:'scale(1)'}],160)
    },290)
  }
  return {cancel,play,snapshot,enter,photo,flight}
}
