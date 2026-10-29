/*
 * Pūrākau Pixels V33 — original high-detail character animation for Tāne.
 *
 * A frame-sampled skeletal pixel rig: expressive faces, animated hands,
 * bending arms and knees, layered hair, tunics, foliage/sky capes and
 * differentiated silhouettes. All positions come from film time, not a game
 * loop, making backwards scrubbing and FFmpeg frame captures deterministic.
 *
 * Costumes are imaginative, simple garments, NOT claims of specific iwi attire.
 * No moko, carving, or borrowed sprite artwork is reproduced.
 *
 * Exported as a separate draw module to allow later replacement of a
 * procedural rig by PNG sprite sheets from Pixelorama / LibreSprite.
 */
(function (global) {
  'use strict';

  const PALETTES = Object.freeze({
    tane: Object.freeze({
      skin:'#ba8a62', lit:'#ecc092', shade:'#835b46',
      hair:'#221f2b', hairShine:'#51403d',
      cloth:'#335c49', clothLit:'#6c9b68', trim:'#c1bb79',
      accent:'#a3ba75', dark:'#1e3932', eyes:'#211f29',
    }),
    tawhirimatea: Object.freeze({
      skin:'#c19776', lit:'#e6ba91', shade:'#865d4c',
      hair:'#1a2434', hairShine:'#6b7f8e',
      cloth:'#31465e', clothLit:'#5d83a1', trim:'#a6c6c8',
      accent:'#cbdce1', dark:'#182a40', eyes:'#202633',
    }),
    earth: Object.freeze({
      skin:'#ba8a64', lit:'#dfb58c', shade:'#815a45',
      hair:'#2d2728', hairShine:'#584641',
      cloth:'#675040', clothLit:'#937450', trim:'#c2a075',
      accent:'#c0a57b', dark:'#433b35', eyes:'#252126',
    }),
    ochre: Object.freeze({
      skin:'#c99b77', lit:'#ecc5a0', shade:'#956e55',
      hair:'#31262b', hairShine:'#614b3c',
      cloth:'#806042', clothLit:'#bd875c', trim:'#dcbe82',
      accent:'#e5b77e', dark:'#493c33', eyes:'#2d2629',
    }),
    river: Object.freeze({
      skin:'#ae856d', lit:'#ddb098', shade:'#785d51',
      hair:'#252b34', hairShine:'#57606d',
      cloth:'#395d62', clothLit:'#78a7a6', trim:'#c1b5a1',
      accent:'#9ac5bf', dark:'#284449', eyes:'#263038',
    }),
  });

  // Each action is an explicit animatable list of key poses, rather than
  // a single body shape oscillating up and down. This is the equivalent of
  // an 8-frame sprite track, ready for future painted frame substitution.
  const ACTIONS = Object.freeze({
    idle: Object.freeze([
      {bob:0,shift:0,arm:1,head:0,step:0,hand:0},
      {bob:-1,shift:1,arm:2,head:1,step:0,hand:1},
      {bob:-1,shift:1,arm:0,head:1,step:1,hand:1},
      {bob:0,shift:0,arm:-1,head:0,step:0,hand:0},
      {bob:1,shift:-1,arm:-2,head:-1,step:-1,hand:-1},
      {bob:0,shift:0,arm:-1,head:0,step:0,hand:0},
    ]),
    listen: Object.freeze([
      {bob:0,shift:0,arm:2,head:-2,step:0,hand:-1},
      {bob:0,shift:0,arm:2,head:-1,step:0,hand:0},
      {bob:-1,shift:1,arm:3,head:1,step:0,hand:1},
      {bob:0,shift:0,arm:2,head:0,step:0,hand:0},
    ]),
    argue: Object.freeze([
      {bob:0,shift:-1,arm:-4,head:-2,step:1,hand:-6},
      {bob:-2,shift:2,arm:5,head:2,step:2,hand:5},
      {bob:-1,shift:1,arm:8,head:3,step:-1,hand:7},
      {bob:0,shift:-2,arm:-2,head:-1,step:1,hand:-3},
      {bob:1,shift:0,arm:-5,head:-2,step:0,hand:-5},
      {bob:0,shift:0,arm:0,head:0,step:-1,hand:0},
    ]),
    reach: Object.freeze([
      {bob:0,shift:0,arm:0,head:0,step:0,hand:0},
      {bob:-1,shift:1,arm:3,head:1,step:-2,hand:3},
      {bob:-3,shift:2,arm:8,head:2,step:-4,hand:8},
      {bob:-1,shift:1,arm:6,head:1,step:-3,hand:6},
      {bob:0,shift:0,arm:2,head:0,step:-1,hand:2},
    ]),
    strain: Object.freeze([
      {bob:0,shift:0,arm:4,head:-2,step:3,hand:2},
      {bob:-2,shift:-2,arm:8,head:-3,step:5,hand:6},
      {bob:-3,shift:-3,arm:10,head:-4,step:7,hand:8},
      {bob:-1,shift:-1,arm:7,head:-2,step:5,hand:4},
      {bob:0,shift:0,arm:3,head:0,step:2,hand:1},
      {bob:-2,shift:-2,arm:9,head:-3,step:6,hand:7},
    ]),
    push: Object.freeze([
      {bob:0,shift:0,arm:0,head:0,step:0,hand:0},
      {bob:-1,shift:0,arm:1,head:-1,step:2,hand:1},
      {bob:-1,shift:-2,arm:3,head:-2,step:5,hand:2},
      {bob:-2,shift:-2,arm:4,head:-3,step:6,hand:4},
      {bob:-1,shift:-3,arm:6,head:-4,step:8,hand:4},
      {bob:-1,shift:-2,arm:4,head:-2,step:6,hand:3},
      {bob:0,shift:-1,arm:2,head:-1,step:3,hand:1},
      {bob:0,shift:0,arm:0,head:0,step:0,hand:0},
    ]),
    wonder: Object.freeze([
      {bob:0,shift:0,arm:0,head:-1,step:0,hand:0},
      {bob:-1,shift:1,arm:4,head:0,step:0,hand:3},
      {bob:-2,shift:1,arm:9,head:2,step:1,hand:6},
      {bob:-1,shift:0,arm:6,head:1,step:0,hand:4},
      {bob:0,shift:0,arm:3,head:0,step:0,hand:2},
    ]),
    storm: Object.freeze([
      {bob:0,shift:-2,arm:-5,head:-2,step:-2,hand:-7},
      {bob:-3,shift:3,arm:9,head:2,step:3,hand:8},
      {bob:-1,shift:-3,arm:-8,head:-2,step:-3,hand:-9},
      {bob:-4,shift:4,arm:10,head:3,step:4,hand:10},
      {bob:-1,shift:1,arm:5,head:1,step:1,hand:7},
      {bob:1,shift:-3,arm:-6,head:-1,step:-2,hand:-7},
    ]),
  });

  function rect(c,x,y,w,h,color) {
    if(w<=0||h<=0) return;
    c.fillStyle=color;
    c.fillRect(Math.round(x),Math.round(y),Math.max(1,Math.round(w)),Math.max(1,Math.round(h)));
  }
  function poly(c,coordinates,color){
    c.fillStyle=color;c.beginPath();c.moveTo(coordinates[0][0],coordinates[0][1]);
    for(let i=1;i<coordinates.length;i++)c.lineTo(coordinates[i][0],coordinates[i][1]);
    c.closePath();c.fill();
  }
  function stroke(c,x,y,x2,y2,color,w=3){
    c.beginPath();c.strokeStyle=color;c.lineWidth=w;c.lineCap='square';
    c.moveTo(Math.round(x),Math.round(y));
    c.lineTo(Math.round(x2),Math.round(y2));c.stroke();
  }
  function face(c,x,y,palette,expression,t,hero){
    // Front-facing 15px head: eyebrows, eyes, nose, 3 mouth shapes,
    // ear highlights and blinking eyes are all separate pixel details.
    rect(c,x-8,y-10,16,14,palette.hair);
    rect(c,x-7,y-8,14,16,palette.shade);
    rect(c,x-6,y-8,12,14,palette.skin);
    rect(c,x-5,y-6,8,5,palette.lit);
    rect(c,x-8,y-2,2,4,palette.skin);
    rect(c,x+6,y-2,2,4,palette.skin);
    // Defined hairline and two asymmetric locks: stylistic, not a moko.
    rect(c,x-8,y-11,16,4,palette.hair);
    rect(c,x-9,y-9,4,8,palette.hair);
    rect(c,x+6,y-8,3,4,palette.hair);
    rect(c,x-5,y-10,5,2,palette.hairShine);
    rect(c,x+2,y-10,3,1,palette.hairShine);
    // Two loose locks respond to the same exact film clock as the limbs.
    const hairShift=Math.round(Math.sin(t*3.2+x*.3)*1.5);
    rect(c,x-10+hairShift,y-8,2,6,palette.hair);
    rect(c,x+7+hairShift,y-6,2,4,palette.hairShine);
    const blink=(Math.sin(t*.83+x*1.17)>.985);
    const scared=expression==='fear'||expression==='surprise';
    const angry=expression==='angry'||expression==='strain';
    const brow=angry?2:scared?-2:0;
    stroke(c,x-5,y-3+brow,x-2,y-3,palette.hair,1);
    stroke(c,x+2,y-3,x+5,y-3+brow,palette.hair,1);
    if(blink){
      stroke(c,x-4,y,x-2,y,palette.eyes,1);
      stroke(c,x+2,y,x+4,y,palette.eyes,1);
    }else{
      rect(c,x-4,y-1,2,2,palette.eyes);
      rect(c,x+2,y-1,2,2,palette.eyes);
      if(scared)rect(c,x-4,y-2,2,1,'#f3e4d5');
      if(scared)rect(c,x+2,y-2,2,1,'#f3e4d5');
    }
    rect(c,x,y+1,2,2,palette.shade); // nose
    const mouthBeat=Math.sin(t*(expression==='angry'?7.3:3.7)+x*.19)>.12;
    if(expression==='surprise'||expression==='fear'){
      rect(c,x-1,y+4,3,3,palette.eyes);
      if(mouthBeat)rect(c,x,y+5,1,1,palette.lit);
    }else if(angry){
      // Animated effort/shouting, with a visible closed and open mouth pose.
      if(mouthBeat){
        rect(c,x-3,y+4,6,3,palette.eyes);
        rect(c,x-1,y+5,3,1,palette.lit);
      }else{
        stroke(c,x-3,y+5,x+3,y+4,palette.eyes,1);
      }
    }else if(expression==='joy'||expression==='wonder'){
      rect(c,x-3,y+4,6,1,palette.eyes);
      rect(c,x-2,y+5,4,mouthBeat?2:1,palette.eyes);
    }else{
      stroke(c,x-2,y+4,x+3,y+4,palette.shade,1);
    }
    if(hero){rect(c,x-5,y+6,9,1,palette.lit)}
  }

  function legs(c,palette,pose,frame,t){
    const spread=pose==='strain'||pose==='reach'?3:0;
    const stepping=frame.step;
    const baseline=0;
    // Underlying rear leg first, then an articulated front leg and feet.
    poly(c,[[-6,-13],[-1,-13],[-3+stepping,-5],[spread-7+stepping,baseline-2],[-12+stepping,baseline-2]],palette.shade);
    poly(c,[[1,-13],[7,-13],[6-stepping,-6],[11+spread-stepping,baseline-2],[5-stepping,baseline-2]],palette.skin);
    rect(c,-13+stepping,-3,8,3,palette.dark);
    rect(c,5-stepping+spread,-3,9,3,palette.dark);
    rect(c,-11+stepping,-4,5,1,palette.clothLit);
    rect(c,5-stepping+spread,-4,5,1,palette.clothLit);
  }

  function costume(c,palette,role,frame,t){
    const lean=frame.shift;
    // Distinct neck, collar, layered waist wrap and cloth shading.
    rect(c,-3+lean,-35,7,6,palette.skin);
    poly(c,[[-10+lean,-32],[7+lean,-32],[12+lean,-15],[8+lean,-11],[-11+lean,-12],[-13+lean,-20]],palette.dark);
    poly(c,[[-8+lean,-31],[7+lean,-30],[9+lean,-15],[-8+lean,-14]],palette.cloth);
    poly(c,[[-6+lean,-30],[-2+lean,-30],[3+lean,-17],[-3+lean,-16]],palette.clothLit);
    // Fabric seam, shoulder band, belt, flickering weave texture.
    stroke(c,-9+lean,-29,-3+lean,-24,palette.trim,2);
    stroke(c,7+lean,-28,2+lean,-24,palette.trim,2);
    rect(c,-8+lean,-15,17,3,palette.trim);
    rect(c,3+lean,-14,4,2,palette.accent);
    rect(c,-6+lean,-12,14,3,palette.cloth);
    rect(c,-6+lean,-10,4,7,palette.clothLit);
    rect(c,0+lean,-11,6,7,palette.cloth);
    for(let i=0;i<3;i++)rect(c,-5+lean+i*4,-19,2,1,palette.accent);
    if(role==='tane'){
      // A leaf mantle is symbolic of the forest; not a ceremonial garment.
      poly(c,[[-12+lean,-32],[-21+lean,-26],[-18+lean,-18],[-10+lean,-16]],palette.cloth);
      poly(c,[[8+lean,-32],[19+lean,-26],[19+lean,-16],[9+lean,-17]],palette.clothLit);
      for(let j=0;j<4;j++){
        rect(c,-18+lean+j*2,-25+j*2,4,2,palette.accent);
        rect(c,10+lean+j*2,-25+j*2,4,2,palette.trim);
      }
    }else if(role==='tawhirimatea'){
      // Wind-trailing scarf with a frame-dependent lateral wave.
      const gust=frame.hand*.8+Math.sin(t*3)*4;
      poly(c,[[-9+lean,-32],[-18+lean,-29],[-25+lean+gust,-23],[-34+lean+gust,-27],
        [-25+lean+gust,-31],[-12+lean,-35]],palette.clothLit);
      stroke(c,-24+lean+gust,-29,-34+lean+gust,-27,palette.accent,1);
      poly(c,[[9+lean,-30],[14+lean,-26],[21+lean+gust*.55,-19],
        [13+lean+gust*.55,-20]],palette.dark);
    }else{
      // Simple layered tabard, no invented traditional tā moko patterns.
      rect(c,-8+lean,-17,3,5,palette.clothLit);
      rect(c,6+lean,-17,2,5,palette.trim);
    }
  }

  function arms(c,palette,frame,pose){
    const shoulder=frame.shift,up=pose==='reach'||pose==='wonder';
    const strain=pose==='strain',debate=pose==='argue'||pose==='storm';
    let leftElbow=[-15+shoulder,-24-frame.arm*.30],leftHand=[-22+frame.hand*.30,-18-frame.arm*.35];
    let rightElbow=[16+shoulder,-23-frame.arm*.32],rightHand=[22+frame.hand*.35,-17-frame.arm*.45];
    if(up){
      leftElbow=[-18+shoulder,-31-frame.arm*.25];leftHand=[-22+frame.hand*.3,-42-frame.arm*.5];
      rightElbow=[18+shoulder,-30-frame.arm*.25];rightHand=[22+frame.hand*.4,-43-frame.arm*.4];
    } else if(strain){
      leftElbow=[-18+shoulder,-29];leftHand=[-17+frame.hand*.15,-42-frame.arm*.4];
      rightElbow=[16+shoulder,-29];rightHand=[18+frame.hand*.18,-43-frame.arm*.35];
    } else if(debate){
      leftElbow=[-19+shoulder,-29-frame.arm*.20];leftHand=[-27-frame.hand*.25,-34-frame.arm*.48];
      rightElbow=[19+shoulder,-30-frame.arm*.18];rightHand=[29+frame.hand*.45,-36-frame.arm*.58];
    }
    for(const side of [
      {anchor:[-9+shoulder,-29],elbow:leftElbow,hand:leftHand},
      {anchor:[9+shoulder,-29],elbow:rightElbow,hand:rightHand},
    ]){
      stroke(c,...side.anchor,...side.elbow,palette.shade,6);
      stroke(c,...side.anchor,...side.elbow,palette.skin,4);
      stroke(c,...side.elbow,...side.hand,palette.skin,4);
      // Highlight and articulate a visible wrist/hand.
      rect(c,side.hand[0]-3,side.hand[1]-3,6,6,palette.skin);
      rect(c,side.hand[0]-2,side.hand[1]-2,2,3,palette.lit);
      rect(c,side.hand[0]+2,side.hand[1]-1,2,2,palette.shade);
      // Three visible fingertip accents make grabbing/reaching legible.
      rect(c,side.hand[0]-3,side.hand[1]+2,1,2,palette.shade);
      rect(c,side.hand[0],side.hand[1]+3,1,2,palette.shade);
      rect(c,side.hand[0]+3,side.hand[1]+2,1,2,palette.shade);
    }
  }

  function drawBracing(c,palette,frame,expression,t) {
    // Horizontal anatomical silhouette: back touches earth; head left,
    // torso lies horizontally; thighs bend upward and feet push the sky.
    // X=0 local torso center; y=0 corresponds to nearby soil.
    const pulse=frame.step;
    poly(c,[[-37,-10],[-31,-20],[-23,-25],[-10,-24],[6,-24],[18,-19],[18,-10],[-10,-9]],palette.dark);
    poly(c,[[-25,-22],[-8,-26],[9,-24],[18,-15],[2,-12],[-22,-13]],palette.cloth);
    // Mantle drapes behind the shoulders and rustles while bracing.
    poly(c,[[-25,-24],[-35,-20],[-45,-6],[-29,-12]],palette.clothLit);
    for(let i=0;i<5;i++)rect(c,-31+i*5,-21+(i%2),4,2,palette.accent);
    // Head facing upwards, with a clearly drawn expression of effort.
    face(c,-36,-17+frame.head*.28,palette,expression,t,true);
    // One forearm grips soil, another braces by the rib cage.
    stroke(c,-21,-16,-35,-8,palette.skin,5);
    stroke(c,-35,-8,-44,-4,palette.skin,5);
    rect(c,-46,-6,7,5,palette.lit);
    stroke(c,-9,-15,-15,-7,palette.skin,5);
    stroke(c,-15,-7,-24,-3,palette.skin,4);
    rect(c,-26,-4,7,4,palette.lit);
    // Left thigh / knees and visibly pressing soles at the skyward limit.
    const k1=[25,-37-frame.step*.35],k2=[35,-36-frame.step*.25];
    const foot1=[28+frame.shift*.22,-58-frame.step*.25];
    const foot2=[38+frame.shift*.22,-57-frame.step*.20];
    stroke(c,13,-16,...k1,palette.shade,8);
    stroke(c,...k1,...foot1,palette.skin,7);
    stroke(c,17,-14,...k2,palette.shade,7);
    stroke(c,...k2,...foot2,palette.lit,6);
    // Pale soles tell the audience his feet push the upper sky.
    rect(c,foot1[0]-5,foot1[1]-4,10,5,palette.dark);
    rect(c,foot1[0]-4,foot1[1]-4,8,2,palette.trim);
    rect(c,foot2[0]-4,foot2[1]-4,10,5,palette.dark);
    rect(c,foot2[0]-3,foot2[1]-4,8,2,palette.trim);
    // Earth tremor and sparkling dust appear only during effort frames.
    for(let i=0;i<5;i++){
      rect(c,-38+i*18,-3+(i%2),2,1,palette.accent);
    }
  }

  function sample(action,t,offset=0){
    const frames=ACTIONS[action]||ACTIONS.idle;
    const fps=(action==='push'||action==='strain')?8:action==='storm'?9:6;
    const index=((Math.floor((t+offset)*fps)%frames.length)+frames.length)%frames.length;
    return {frame:frames[index],index,count:frames.length};
  }

  function draw(c,options){
    const {
      x=0,y=0,scale=1,t=0,role='earth',action='idle',
      expression='calm',facing=1,phase=0,offset=0,opacity=1
    }=options||{};
    const palette=PALETTES[role]||PALETTES.earth;
    const {frame,index}=sample(action,t,offset);
    c.save();
    c.globalAlpha*=Math.max(0,Math.min(1,opacity));
    c.translate(Math.round(x),Math.round(y));
    c.scale(scale*(facing<0?-1:1),scale);
    // A subtle independent head/body breath, not random bobbing.
    if(action==='push'){
      drawBracing(c,palette,frame,expression,t);
    }else{
      const standing=Object.assign({},frame);
      standing.bob+=Math.sin(t*.45+offset)*.5;
      c.translate(0,standing.bob);
      legs(c,palette,action,standing,t);
      // Coat/cape is behind arms and face, creating meaningful depth.
      costume(c,palette,role,standing,t);
      arms(c,palette,standing,action);
      face(c,standing.shift+standing.head*.28,-46+standing.head*.2,palette,expression,t,scale>=1);
      if(role==='tane' && action==='wonder'){
        // Soft leaf sparks around Tāne as the new world brightens.
        const lift=phase;
        for(let n=0;n<3;n++){
          rect(c,-26+n*22,-30+Math.sin(t*2+n)*4-3*lift,2,2,palette.accent);
        }
      }
    }
    c.restore();
    return {role,action,expression,frameIndex:index,frameCount:ACTIONS[action]?.length||ACTIONS.idle.length};
  }

  global.TaneCharacters=Object.freeze({
    version:33,
    palette:PALETTES,
    actions:ACTIONS,
    sample,
    draw,
  });
})(typeof window!=='undefined'?window:globalThis);
