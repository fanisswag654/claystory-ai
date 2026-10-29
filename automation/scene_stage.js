/* ClayStory automatic review-stage V1 — original procedural pixel scenes.
 * V33 detailed actor rigs reused with source-grounded theme/environment cues.
 * No proprietary sprites. Every frame is a pure function of absolute seconds.
 * Visuals are illustrative, not depictions of specific iwi ceremonies.
 */
(function(){
"use strict";
const canvas=document.getElementById("candidate-stage");
if(!canvas||!window.TaneCharacters)throw Error("Missing original pixel actor renderer");
const hd=canvas.getContext("2d",{alpha:false});
const low=document.createElement("canvas");low.width=180;low.height=320;
const p=low.getContext("2d",{alpha:false});hd.imageSmoothingEnabled=false;p.imageSmoothingEnabled=false;
let story=null,durations=null;
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const ease=x=>{x=clamp(x);return x*x*(3-2*x)};
const wave=(t,a=1,f=1)=>Math.sin(t*f)*a;
function px(x,y,w,h,c){p.fillStyle=c;p.fillRect(Math.round(x),Math.round(y),Math.max(1,Math.ceil(w)),Math.max(1,Math.ceil(h)))}
function circ(x,y,r,c){p.fillStyle=c;p.beginPath();p.arc(x,y,Math.max(.3,r),0,Math.PI*2);p.fill()}
function ell(x,y,w,h,c){p.fillStyle=c;p.beginPath();p.ellipse(x,y,w,h,0,0,2*Math.PI);p.fill()}
function line(x,y,X,Y,c,w=2){p.strokeStyle=c;p.lineWidth=w;p.beginPath();p.moveTo(x,y);p.lineTo(X,Y);p.stroke()}
function poly(points,c){p.fillStyle=c;p.beginPath();p.moveTo(points[0][0],points[0][1]);for(let i=1;i<points.length;i++)p.lineTo(points[i][0],points[i][1]);p.closePath();p.fill()}
function rnd(n){let v=Math.sin(n*127.17+5.18)*44735.19;return v-Math.floor(v)}
function text(t,y,size=7,color="#f6e6c8"){p.fillStyle=color;p.font="bold "+size+"px system-ui";p.textAlign="center";p.fillText(t,90,y)}
function bg(v,phase,t,theme){
 const top=theme==="fire"?"#27182c":"#172b43",ground=theme==="fire"?"#a06a50":"#5c6f63";
 const g=p.createLinearGradient(0,25,0,270);g.addColorStop(0,top);g.addColorStop(.68,theme==="fire"?"#6c4150":"#3b5362");g.addColorStop(1,ground);
 p.fillStyle=g;p.fillRect(0,25,180,264);
 for(let i=0;i<54;i++){let x=rnd(i+10)*180,y=40+rnd(i+600)*145;
  if(i%4!==0||theme==="earth")px(x,y,1,1,theme==="fire"?"#d5a786":"#a9bac3")}
 const shift=wave(t*.42,2);
 poly([[0,248],[25,230+shift],[52,246],[83,221],[109,244],[154,225],[180,242],[180,320],[0,320]],"#354539");
 poly([[0,278],[45,264],[90,276],[132,263],[180,271],[180,320],[0,320]],"#54443f");
 for(let i=0;i<15;i++)px(i*13,267+rnd(i+160)*16,3,2,theme==="fire"?"#96714f":"#758467");
}
function tree(x,y,k,t,lit=false){
 line(x,y,x+wave(t+x,.8),y-k*.60,"#403e32",3);
 for(let j=0;j<3;j++){
  const d=wave(t*.8+j+x,1.3);
  circ(x+d+(j-1)*k*.22,y-k*.69+j%2*k*.09,k*.24,
       lit?"#b57b42":j%2?"#41634c":"#52745c");
 }
 for(let j=0;j<5;j++)px(x-k*.22+j*k*.11,y-k*.77+j%2*3,2,2,lit?"#ecac61":"#9bbf8b");
}
function silhouetteMountains(t){
 poly([[0,240],[26,152],[55,225],[93,130],[132,222],[170,159],[180,170],[180,290],[0,290]],"#374451");
 poly([[0,236],[26,167],[55,231],[93,151],[132,234],[170,175],[180,181],[180,288],[0,288]],"#58636d");
}
function flames(x,y,t,k=1){
 for(let i=0;i<7;i++){
  const fx=x+(i-3)*4*k+wave(t*2+i,2*k),height=(14+i%3*7+wave(t*5+i,3))*k;
  poly([[fx-4*k,y],[fx-1*k,y-height*.5],[fx+2*k,y-height],[fx+6*k,y-height*.45],[fx+6*k,y]],i%3?"#e78a49":"#fbd283");
 }
 circ(x,y-10*k,4*k,"#ffda77");
}
function cave(t,fire=false){
 silhouetteMountains(t);
 circ(90,220,52,"#2d2831");ell(90,242,34,53,"#101b29");
 for(let i=0;i<12;i++)px(60+i*5,204+(i%3)*9,3,2,"#6e6260");
 if(fire){flames(114,241,t,.8);flames(56,250,t,.65)}
}
function river(t,light=false){
 poly([[0,259],[37,242],[87,251],[118,236],[180,246],[180,290],[0,290]],light?"#72999d":"#4b7886");
 for(let i=0;i<15;i++){
 let x=(i*17+t*(4+i%3))%212-10;
 line(x,257+i%4*7,x+11,257+i%4*7,light?"#cbdcdf":"#8bb6c2",1);
 }}
function storm(t){for(let i=0;i<60;i++){
 let x=((i*43+t*38)%235)-20,y=(i*29+t*(36+i%3))%245+26;
 line(x,y,x-5,y+11,"#b5ccd3",1);
 } if(Math.sin(t*4.22)>.75){
 px(0,25,180,225,"rgba(255,255,245,.13)");
 line(120,52,110,91,"#f1e8bd",2);line(110,91,125,88,"#f1e8bd",2);
 line(125,88,101,141,"#f1e8bd",3);
 }}
function earthQuake(t,phase){
 silhouetteMountains(t);
 const r=ease(phase)*9;
 for(let i=0;i<4;i++) {
 let x=18+i*44;
 line(x,250,x+3+wave(t*5+i,r),263,"#241b25",2);
 line(x+3+wave(t*5+i,r),263,x+17,277,"#241b25",2);
 }
 for(let i=0;i<28;i++)px(rnd(i+5)*180,220+rnd(i+12)*60,2,1,"#9b8b70");
}
function lighting(t,theme,v){
 if(theme!=="fire")return;
 const count=v==="forest_fire"?65:22;
 for(let i=0;i<count;i++){
 let x=rnd(i+101)*180+wave(t+i,3),y=215-(t*(6+i%5)+i*11)%160;
 px(x,y,i%3?1:2,i%4?1:2,i%3?"#ffa95b":"#ffe7a2");
 }}
function environment(scene,t,phase,theme){
 bg(scene.visual,phase,t,theme);
 const v=scene.visual;
 if(v==="volcano"||v==="mountains"||v==="earth_rumble"){silhouetteMountains(t)}
 if(v==="cavern")cave(t,theme==="fire");
 if(v==="village"){
  for(let i=0;i<3;i++){
    const x=18+i*57,y=232+i%2*4;
    poly([[x-13,y],[x,y-20],[x+15,y],[x+12,y+20],[x-11,y+20]],"#84735b");
    poly([[x-17,y],[x,y-20],[x+19,y]],"#534f42");
    px(x-3,y+4,8,15,"#3d3535");
  }
 }
 if(v==="river"||v==="ocean")river(t,phase>.4);
 if(v==="forest"||v==="forest_fire"||v==="fire_tree"||v==="storm"){
  for(let i=0;i<8;i++)tree(9+i*24,250+(i%3)*5,29+(i%4)*11,t,v==="forest_fire");
 }
 if(v==="night") {
  circ(140,63,13,"#c9cad0");circ(144,60,12,"#263b57");
 }
 if(v==="ember"||v==="forest_fire"||v==="fire_tree"){
  for(let i=0;i<(v==="forest_fire"?8:3);i++){
   flames(17+i*(v==="forest_fire"?23:58),248+wave(t+i,2),t+i,v==="forest_fire"?.75:1);
  }
 }
 if(v==="earth_rumble"||v==="earth")earthQuake(t,phase);
 if(v==="storm")storm(t);
 if(v==="dawn"){
  circ(140,90,20,"#fde0aa");
  for(let i=0;i<12;i++){
   let angle=i*Math.PI/6;line(140+Math.cos(angle)*27,90+Math.sin(angle)*27,
     140+Math.cos(angle)*(34+wave(t+i,3)),90+Math.sin(angle)*(34+wave(t+i,3)),"#ffdd93",2);
  }
 }
 if(v==="council"){
  circ(90,75,8,"#ccbec0");line(35,140,145,140,"#a9adb4",1);
 }
 lighting(t,theme,v);
}
function atTime(t){
 let total=durations.reduce((a,b)=>a+b,0);t=clamp(t,0,total-.0001);
 let elapsed=0;
 for(let i=0;i<8;i++){
  if(t<elapsed+durations[i]||i===7)return {index:i,phase:(t-elapsed)/durations[i],seconds:t-elapsed,duration:durations[i],total};
  elapsed+=durations[i];
 }
}
function draw(t) {
 if(!story||!durations)throw Error("Candidate data not ready");
 let sc=atTime(t),scene=story.scenes[sc.index],phase=sc.phase;
 p.clearRect(0,0,180,320);px(0,0,180,320,"#152034");
 p.save();p.beginPath();p.rect(0,25,180,263);p.clip();
 environment(scene,t,phase,story.theme);
 const act=scene.action;
 let role=story.hero_role,other=story.support_role;
 // Characters remain the original V33 procedural pixel rig, with per-story
 // palette roles and independent keyed expressions for every beat.
 if(sc.index%3===1||scene.visual==="council"){
  TaneCharacters.draw(p,{role:other,action:"listen",expression:"calm",
    x:39,y:252,t:t+.6,scale:.88});
 }
 let expression=["storm","argue","strain"].includes(act)?"angry":
   ["wonder","reach"].includes(act)?"wonder":"calm";
 TaneCharacters.draw(p,{role,action:act,expression,
   x:sc.index%2?115:93,y:257,t,scale:1.32,phase});
 if(scene.visual==="ember"||scene.visual==="forest_fire")flames(137,217,t,.75);
 p.restore();
 px(0,0,180,25,"#121e2e");px(0,288,180,32,"#121e2e");
 px(4,23,172,2,"#b6a17c");px(4,288,172,1,"#b6a17c");
 text("PŪRĀKAU PIXELS",11,8);text(String(story.title).slice(0,33),20,5,"#b1bbbd");
 text(scene.caption.slice(0,36),304,8,"#f2ce86");
 px(5,315,170,2,"#3f5361");px(5,315,170*t/sc.total,2,"#d6a65b");
 hd.clearRect(0,0,540,960);hd.drawImage(low,0,0,540,960);
 return sc;
}
const ready=(async()=>{
 const [sr,tr]=await Promise.all([
  fetch("output/story.json",{cache:"no-store"}),
  fetch("output/timing.json",{cache:"no-store"}),
 ]);
 if(!sr.ok||!tr.ok)throw Error("Missing generated candidate story or narration timing");
 story=await sr.json();let timing=await tr.json();
 if(story.scenes.length!==8||timing.voice!=="en-GB-RyanNeural"||timing.durations.length!==8)
  throw Error("Bad candidate story or cinematic voice metadata");
 durations=timing.durations;
 if(!durations.every(d=>d>3&&d<42))throw Error("Narration durations outside range");
 draw(0);
})();
window.AutoPurakau={ready,drawAt:draw,atTime,getDurations:()=>durations?.slice(),getStory:()=>story};
})();