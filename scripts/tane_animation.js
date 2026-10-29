/* Pūrākau Pixels — Tāne and the First Light, V33 Character Edition.
 * All art original, procedural 2D pixel animation. No borrowed game assets.
 * Deterministic time sampling for frame-exact, voice-synced MP4 export.
 * This is one telling; culturally sensitive names/interpretations need review.
 */
(function(){
'use strict';
const canvas=document.getElementById('tane-stage');
const view=canvas.getContext('2d',{alpha:false});
const low=document.createElement('canvas');low.width=180;low.height=320;
const p=low.getContext('2d',{alpha:false});
view.imageSmoothingEnabled=false;p.imageSmoothingEnabled=false;
const W=180,H=320,C={night:'#0b162b',deep:'#1a2640',shadow:'#111b30',
 sky:'#426d91',dawn:'#e2ab6c',gold:'#ffdb8a',mist:'#c6d6c6',
 earth:'#293b30',soil:'#4f493f',green:'#315b47',fern:'#679879',
 leaf:'#87ac7a',skin:'#ae805d',skinLit:'#d49a6c',storm:'#1d3450',
 white:'#f5e8d2',water:'#6d91a0'};
let story=null,durations=Array(8).fill(11),audio=null,playing=false,raf=0,current=0;
let selectedScene=0;
const $=id=>document.getElementById(id);
const clamp=(v,a=0,b=1)=>Math.min(b,Math.max(a,v));
function smooth(x){let u=clamp(x);return u*u*(3-2*u)}
function ease(x,k='smooth'){
 if(window.ClayMotionV29){return ClayMotionV29.tween({v:0},{v:1},clamp(x),k).v}
 return smooth(x);
}
function px(x,y,w,h,c){if(w<=0||h<=0)return;p.fillStyle=c;p.fillRect(Math.round(x),Math.round(y),Math.ceil(w),Math.ceil(h))}
function line(x,y,X,Y,c,w=2){p.strokeStyle=c;p.lineWidth=w;p.lineCap='square';p.beginPath();p.moveTo(Math.round(x),Math.round(y));p.lineTo(Math.round(X),Math.round(Y));p.stroke()}
function shape(pts,c){p.fillStyle=c;p.beginPath();p.moveTo(pts[0][0],pts[0][1]);for(let i=1;i<pts.length;i++)p.lineTo(pts[i][0],pts[i][1]);p.closePath();p.fill()}
function circle(x,y,r,c){p.fillStyle=c;p.beginPath();p.arc(x,y,Math.max(0,r),0,Math.PI*2);p.fill()}
function ellipse(x,y,rx,ry,c){p.fillStyle=c;p.beginPath();p.ellipse(x,y,Math.max(.1,rx),Math.max(.1,ry),0,0,Math.PI*2);p.fill()}
function rand(i){let x=Math.sin(i*127.1+87.7)*43758.5453;return x-Math.floor(x)}
function stars(t,alpha=1){p.save();p.globalAlpha=alpha;
 for(let i=0;i<75;i++){const x=rand(i+30)*180,y=33+rand(i+460)*169;
  const light=.35+.65*Math.abs(Math.sin(t*.23+i*.8));
  if(light>.68)px(x,y,1+(i%19===0?1:0),1,i%3?'#6d88a4':'#f7e7c4')}
 p.restore()}
function glow(x,y,r,strength=1){for(let i=5;i>=0;i--){const a=.03*strength*(6-i);
  p.fillStyle='rgba(255,209,117,'+a.toFixed(3)+')';
  circle(x,y,r*(.2+i*.22),p.fillStyle)}}
function cloud(x,y,size,t,dark=false){const dx=Math.sin(t*.21+x)*2,cy=y+Math.sin(t*.18+x)*1.2;
 const main=dark?'#334660':'#f0d8aa',shadow=dark?'#1c304a':'#b2a99e';
 ellipse(x+dx,cy,size,7*size/19,shadow);
 ellipse(x-6+dx,cy-3,size*.68,6*size/19,main);
 ellipse(x+7+dx,cy-4,size*.60,7*size/19,main);
 ellipse(x+dx,cy-6,size*.48,5*size/19,main)}
function mountain(h,y,col){shape([[-20,268],[18,y+22],[43,y-15],[70,257],[95,y-23],[120,250],[151,y+12],[204,265],[204,319],[-20,319]],col)}
function terrain(y,t,bright=false){const earth=bright?'#3f5f49':C.earth,soil=bright?'#685b42':'#2d3a36';
 shape([[0,y+Math.sin(t*.23)*1],[19,y-6],[41,y+2],[66,y-10],[92,y-4],[117,y-15],[142,y+1],[170,y-9],[180,y],[180,319],[0,319]],earth);
 shape([[0,y+30],[33,y+20],[62,y+32],[91,y+16],[132,y+28],[180,y+13],[180,319],[0,319]],soil);
 for(let i=0;i<26;i++){const x=i*8+rand(i)*4,yy=y+rand(i+400)*39;px(x,yy,2+(i%3),1,bright?'#73785a':'#485441')}}
function sprout(x,y,k,t){const h=Math.max(0,21*k);line(x,y,x+Math.sin(t*.7+x)*2,y-h,C.green,2);
 for(let j=1;j<=3;j++){const yy=y-j*h/4;line(x,yy,x+(j%2?5:-5)*k,yy-3*k,C.leaf,2)}
 circle(x,y-h,1.5*k,'#9ab17f')}
function tree(x,y,size,t,detail=0){const sway=Math.sin(t*.7+x*.1)*size*.032;
 line(x,y,x+sway,y-size*.52,C.soil,Math.max(2,size*.13));
 const bx=x+sway,by=y-size*.55;
 const green=detail?'#345740':'#294a3d',light=detail?'#729968':'#50745e';
 circle(bx,by,size*.33,green);circle(bx-size*.23,by+size*.09,size*.22,green);circle(bx+size*.24,by+size*.09,size*.23,green);
 circle(bx-size*.16,by-size*.12,size*.16,light);circle(bx+size*.16,by-size*.13,size*.19,light);
 for(let j=0;j<7;j++)px(bx-size*.22+j*size*.066,by-size*.16+(j%3)*2,2,2,'#a0b483')}
function forest(t,growth=1){for(let i=0;i<9;i++){
 const size=(19+(i%4)*9)*growth,y=246+i%3*7,x=10+i*20; if(size>2)tree(x,y,size,t,i%2)
 }for(let j=0;j<15;j++)sprout((j*37)%180,275+j%3*9,growth,t)}
// V33: all acting and facial detail is drawn by the independent, reusable
// character rig. Keep its API separate from scenery so a real PNG sprite
// sheet can be substituted later without altering the film timeline.
function actor(role,x,y,scale,t,action='idle',expression='calm',phase=0,offset=0){
 if(!window.TaneCharacters)throw new Error('Detailed V33 character animator missing');
 return TaneCharacters.draw(p,{role,x,y,scale,t,action,expression,phase,offset});
}
function parentSky(y,t,detail=1){
 // Ranginui represented by a vast luminous dome, not a human caricature.
 p.save();p.translate(0,Math.round(y));const dark='#19263a';
 shape([[-20,-210],[200,-210],[200,12],[155,3],[111,16],[80,5],[42,17],[-20,6]],dark);
 shape([[-20,-210],[200,-210],[200,2],[150,-5],[102,5],[52,-7],[-20,-1]],'#25354d');
 if(detail){
   for(let j=0;j<9;j++){const x=j*22-3,cy=1+Math.sin(j*2+t*.12)*3;
     line(x,cy,x+14,cy-3,'#4a6178',2)}
 }
 p.restore()}
function windBands(t,intensity=1){
 p.save();p.globalAlpha=.65*intensity;
 for(let i=0;i<12;i++){
 const x=(i*36+t*(18+i%3*7))%265-44,y=62+i*17+Math.sin(t+i)*6;
 line(x,y,x+22+i%3*5,y-3,'#a8c6cd',1+i%3);
 line(x+5,y+4,x+18,y+2,'#6a8fa2',1)
 }p.restore()}
function rain(t,intensity=1){
 p.save();p.globalAlpha=.58*intensity;
 for(let i=0;i<94;i++){const x=((i*31+t*(36+i%4))%245)-18,y=((i*47+t*(95+i%3*6))%290)+26;
 line(x,y,x-5,y+9,'#93b9c7',1)}
 p.restore()}
function lightning(t){const strike=Math.sin(t*5.73)*Math.sin(t*2.43);
 if(strike>.71){p.fillStyle='rgba(218,231,239,.13)';p.fillRect(0,24,180,256);
 line(126,39,115,87,'#eff4e2',2);line(115,87,132,87,'#eff4e2',2);line(132,87,104,148,'#eff4e2',3);
 glow(118,97,22,1.4)}}
function bird(x,y,t,s=1){const flap=Math.sin(t*8+x)*4;line(x-8*s,y+flap,x,y,'#29393c',2);
 line(x,y,x+8*s,y+flap,'#29393c',2)}
function particles(t,scene,brightness=1){for(let j=0;j<52;j++){
 let x=(rand(j+scene*87)*183+Math.sin(t*.4+j)*6)%180,
 y=36+(rand(j+scene*33+900)*210-t*(1+j%4)*.7+800)%210;
 if(rand(j*2+6)>.35)px(x,y,1,1,brightness>0.5?'#f5d99c':'#8795a0');
 }}
function world(scene,phase,t){
 const release=(scene<4?0:scene===4?ease(phase*.12,'out'):scene===5?ease(phase,'cinematic'):1);
 const night=scene<5?1:1-ease((phase-.12)*2);
 // Background gradient reveals growing daylight.
 const bg=p.createLinearGradient(0,28,0,288);
 bg.addColorStop(0,scene<5?'#0c172c':scene===6?'#1b344f':'#426f94');
 bg.addColorStop(.68,scene<5?'#223348':scene===6?'#3f5775':'#e3ac71');
 bg.addColorStop(1,scene<5?'#2b3f41':'#a3a77a');
 p.fillStyle=bg;p.fillRect(0,25,180,264);
 if(scene<5)stars(t,.8);else if(scene===5)stars(t,1-ease(phase*.85));
 if(release>.07)glow(137,110-release*44,16+release*25,release);
 if(scene>=5){
  ellipse(140,77,11,11,'#fff0b9');glow(140,77,18,1.6);
  cloud(28,scene===6?84:76,23,t,scene===6);cloud(138,scene===6?94:125,24,t,scene===6)
 }
 if(scene===6){windBands(t,1.2);rain(t,1);lightning(t);}
 if(scene===7){cloud(62,65,19,t);rain(t,.18)}
 const earthY=scene<=4?204:213;
 terrain(earthY,t,scene>=5);
 if(scene<=2){
   parentSky(144,t);p.fillStyle='rgba(4,12,26,.65)';p.fillRect(0,143,180,58);
 }else if(scene===3){
   parentSky(144-ease(phase)*4,t);
 }else if(scene===4){
   const move=ease(phase*.18,'out')*12;
   parentSky(143-move,t);
 }else if(scene===5){
   // The moment of separation is a massive animated sky displacement.
   const rise=ease(phase,'cinematic')*126;
   parentSky(143-rise,t);
   const gap=ease(phase*1.5)*1;
   shape([[0,144-rise+15],[180,144-rise+15],[180,204],[0,204]],'rgba(247,202,113,'+(gap*.07).toFixed(3)+')');
   for(let j=0;j<9;j++){
    const xx=9+j*20;line(90,143-rise+14,xx,218,'rgba(252,213,129,'+(gap*.25).toFixed(3)+')',2)}
 }else{
   // After separation, Ranginui's dome spans the distant sky.
   parentSky(37,t);
   p.save();p.globalAlpha=.25;parentSky(35,t,0);p.restore();
 }
 if(scene===0){
  ellipse(90,166,77,18,'rgba(10,18,33,.75)');
  particles(t,scene,.2)
 }else if(scene===1){
  // Characters vary in scale and position so face silhouettes remain distinct.
  actor('earth',22,205,.72,t,'idle','calm',phase,.2);
  actor('river',51,204,.82,t,'listen','wonder',phase,.6);
  actor('tane',86,205,1.02,t,'wonder','wonder',phase,1.2);
  actor('ochre',126,205,.83,t,'idle','calm',phase,.4);
  actor('tawhirimatea',162,205,.77,t,'listen','fear',phase,.8);
  particles(t,scene,.2)
 }else if(scene===2){
  // Differentiated body language during the disagreement:
  // Tāne listens, a brother considers the idea, Tāwhirimātea argues.
  actor('earth',24,208,.76,t,'listen','calm',phase,.8);
  actor('river',53,208,.90,t,'reach','wonder',phase,.1);
  actor('tane',90,208,1.16,t,'listen','concerned',phase,1.1);
  actor('tawhirimatea',147,207,1.24,t,'argue','angry',phase,.3);
  windBands(t,.35+phase*.35);
  circle(148,145,7,'rgba(211,218,232,.18)');
 }else if(scene===3){
  // Each brother now reaches independently with bent elbows and braced knees.
  const strength=ease(phase*2,'out');
  actor('ochre',41,207,1.10,t,'strain','strain',phase,.11);
  actor('river',90,207,1.24,t,'strain','strain',phase,.59);
  actor('earth',140,207,1.10,t,'reach','fear',phase,1.27);
  for(let i=0;i<15;i++) {
   const dx=17+i*11,up=Math.sin(t*6+i*.89)*3*strength;
   px(dx,149+up,2,2,'#77818c');
  }
 }else if(scene===4){
  // Tāne lying back; vertical foot pressure is shown by anchored dust/glints.
  // Tāne's signature hero pose now has a horizontally braced torso,
  // flexing knees, visible palms, a strained face and sky-pressing soles.
  actor('tane',87,202,1.18,t,'push','strain',phase);
  for(let j=0;j<12;j++){
   const x=34+j*10,y=151+Math.sin(t*8+j)*3;
   if(j%2===0)px(x,y,2,2,'#c2b78a');
  }
  windBands(t,.21)
 }else if(scene===5){
  const lift=ease(phase,'cinematic');
  if(phase<.56){
   actor('tane',83,209,1.27,t,'push','strain',phase);
  }else{
   actor('tane',89,221,1.36,t,'wonder','joy',phase);
  }
  p.save();p.globalAlpha=lift;
  forest(t,.12+.6*lift);
  p.restore();
  for(let i=0;i<50;i++){
    const x=rand(i+11)*180,y=180-lift*rand(i+72)*160;
    p.save();p.globalAlpha=lift*.75;px(x,y,1+i%3,1+i%2,'#fff0b4');p.restore()
  }
 }else if(scene===6){
  forest(t,1);
  // Tāwhirimātea storms upward into the sky, differentiated by his wind cape.
  const ascend=ease(phase,'cinematic')*89;
  actor('tawhirimatea',95+Math.sin(t*4)*3,218-ascend,1.18,t,'storm','angry',phase,.17);
  p.save();p.globalAlpha=.35;ellipse(91,150-ascend,36,13,'#2c4662');p.restore()
 }else{
  forest(t,ease(phase*2));
  actor('tane',32,238,.77,t,'wonder','joy',phase,.49);
  for(let k=0;k<7;k++)bird(12+k*27+(t*.5)%15,87+(k%3)*15,t,k%2?.4:.7);
  particles(t,scene,1);
  for(let j=0;j<12;j++)sprout(12+j*15,270+j%3*4,ease(phase*1.4),t);
 }
 // Earth remains symbolically present throughout the embrace and separation.
 if(scene===7){for(let i=0;i<8;i++)px(i*24+6,291-(i%3)*3,4,1,'#afaa72')}
}
function sceneAt(t){
 let elapsed=0;
 for(let i=0;i<durations.length;i++){
  const d=durations[i];
  if(t<elapsed+d||i===durations.length-1)return {index:i,start:elapsed,local:clamp(t-elapsed,0,d),duration:d,phase:clamp((t-elapsed)/d)};
  elapsed+=d;
 }
 return {index:0,start:0,local:0,duration:durations[0],phase:0};
}
function wordWrap(context,text,x,y,maxWidth,lineHeight,maxLines=3){
 const words=text.split(/\s+/),lines=[];let line='';
 for(const word of words){
  if(context.measureText(line?line+' '+word:word).width>maxWidth&&line){lines.push(line);line=word}else line=line?line+' '+word:word;
 }if(line)lines.push(line);
 for(let i=0;i<Math.min(maxLines,lines.length);i++)context.fillText(lines[i],x,y+i*lineHeight);
}
function frameAt(t){
 if(!story)return;
 const total=durations.reduce((a,b)=>a+b,0);
 t=clamp(t,0,total);
 const sc=sceneAt(t),scene=story.scenes[sc.index];
 p.clearRect(0,0,W,H);px(0,0,W,H,'#0b1426');
 p.save();p.beginPath();p.rect(0,25,180,264);p.clip();
 world(sc.index,sc.phase,t);
 const vignette=p.createLinearGradient(0,25,0,289);
 vignette.addColorStop(0,'rgba(5,12,26,.35)');vignette.addColorStop(.4,'rgba(5,12,26,0)');
 vignette.addColorStop(1,'rgba(5,12,26,.25)');p.fillStyle=vignette;p.fillRect(0,25,180,264);
 const fadeIn=1-ease(sc.local/.32),fadeOut=ease((sc.local-sc.duration+.33)/.33);
 if(Math.max(fadeIn,fadeOut)>0){p.fillStyle='rgba(6,13,27,'+(Math.max(fadeIn,fadeOut)*.82).toFixed(3)+')';p.fillRect(0,25,180,264)}
 p.restore();
 px(0,0,180,25,'#111d30');px(0,289,180,31,'#111d30');
 px(5,23,170,2,'#ba995e');px(5,288,170,1,'#ba995e');
 p.fillStyle='#f6e4c2';p.font='bold 8px system-ui';p.textAlign='left';p.fillText('PŪRĀKAU PIXELS',8,11);
 p.fillStyle='#b9ad95';p.font='6px system-ui';p.fillText('TĀNE  •  FIRST LIGHT',8,19);
 p.textAlign='right';p.fillStyle='#ead3a4';p.font='7px system-ui';p.fillText(String(sc.index+1).padStart(2,'0')+' / 08',171,16);
 p.fillStyle='#e1b770';p.font='bold 9px system-ui';p.textAlign='center';
 wordWrap(p,scene.caption,90,303,164,10,1);
 px(5,315,170,2,'#304052');px(5,315,170*t/Math.max(total,.001),2,'#d4a962');
 view.clearRect(0,0,540,960);view.drawImage(low,0,0,540,960);
 // Text overlay at HD size preserves sharpness on mobile without blocking visuals.
 view.save();view.textAlign='center';view.fillStyle='#f5e7d3';
 view.font='bold 13px system-ui';
 const smallTitle=scene.title+'   ·   '+(sc.index+1)+'/8';
 view.fillText(smallTitle,270,894);
 view.restore();
 if(!playing)$('scene-label').textContent=scene.title;
 if(!playing)$('timeline').value=String(t);
 return sc;
}
function loadAudio(){if(audio){audio.pause();audio.src='';audio=null}
 audio=new Audio('audio/tane-nz-mix-balanced.mp3?v=1');
 audio.preload='metadata';audio.volume=1;
 audio.onended=stop;audio.onerror=()=>{
   $('status').textContent='Narration not available on this page yet. The review MP4 is downloadable from the film workflow.'
 }}
function stop(){playing=false;if(audio)audio.pause();if(raf)cancelAnimationFrame(raf);raf=0;$('play').textContent='Play with sound'}
function loop(){
 if(!playing)return;
 const total=durations.reduce((a,b)=>a+b,0);
 if(audio&&!audio.paused){current=Math.min(total,audio.currentTime)}
 else if(!audio){stop();return}
 frameAt(current);
 $('timeline').value=String(current);
 if(current>=total-.04){stop();return}
 raf=requestAnimationFrame(loop);
}
async function play(){
 if(!story)return;
 if(playing){stop();return}
 if(!audio)loadAudio();
 try{
  if(audio.ended||current>=durations.reduce((a,b)=>a+b,0)-.1){current=0;audio.currentTime=0}
  else audio.currentTime=current;
  await audio.play();
  playing=true;$('play').textContent='Pause';$('status').textContent='Playing cinematic narration';
  loop();
 }catch(error){$('status').textContent='Audio not yet published here. Watch the review MP4 from GitHub Actions instead.'}
}
async function init(){
 const reply=await fetch('stories/tane.json',{cache:'no-store'});
 if(!reply.ok)throw Error('Missing Tāne story storyboard');
 story=await reply.json();
 if(story.scenes.length!==8)throw Error('Expected eight original story scenes');
 try{
  const timing=await fetch('audio/tane-nz-timing.json?v=1',{cache:'no-store'});
  if(timing.ok){
   const manifest=await timing.json();
   if(Array.isArray(manifest.durations)&&manifest.durations.length===8&&manifest.durations.every(x=>x>3&&x<42))
     durations=manifest.durations;
  }
 }catch(error){console.warn('Using preview scene timings until soundtrack is ready',error)}
 $('timeline').max=String(durations.reduce((a,b)=>a+b,0));$('timeline').value='0';
 $('play').addEventListener('click',play);
 $('stop').addEventListener('click',()=>{stop();current=0;frameAt(0)});
 $('timeline').addEventListener('input',event=>{
  current=Number(event.target.value);if(audio&&audio.readyState>0)audio.currentTime=current;
  frameAt(current);
 });
 $('jump').addEventListener('change',e=>{
  const n=Number(e.target.value);current=durations.slice(0,n).reduce((a,b)=>a+b,0);
  if(audio&&audio.readyState>0)audio.currentTime=current;frameAt(current);
 });
 frameAt(0);
 $('status').textContent='Eight scenes ready. Review-only animation; watch the GitHub MP4 to hear the soundtrack.';
}
window.TaneFilm={ready:init(),version:33,drawAt(t){return frameAt(t)},sceneAt(t){return sceneAt(t)},getTotal(){return durations.reduce((a,b)=>a+b,0)},getStory(){return story},getDurations(){return durations.slice()},characters:()=>window.TaneCharacters,stop};
window.TaneFilm.ready.catch(error=>{$('status').textContent='Unable to load film: '+error.message;console.error(error)});
})();
