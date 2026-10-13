import * as THREE from './vendor/three.module.js';
import { createVictoryInk } from './victory-ink.js';

const $ = (id) => document.getElementById(id);
const state = { size: 13, board: [], moves: [], player: 1, human: 1, mode: 'ai', algorithm: 'alphabeta', depth: 3, busy: false, winner: 0, revision: 0, lastAnalysis: null, feedback: null, showNumbers: false, showHeat: false, topView: false, sound: false, keyboard: [6, 6], panel: 'arena' };
let activeRequest, toastTimer, audioContext;
const cloneBoard = () => state.board.map(row => [...row]);
const coord = ([r,c]) => `${String.fromCharCode(65+c)}${r+1}`;
const number = value => Number.isFinite(Number(value)) ? Number(value).toLocaleString('en-US') : '—';
const engineName = () => state.algorithm === 'alphabeta' ? 'ALPHA–BETA' : 'MINIMAX';
const el = (tag, className, text) => { const result = document.createElement(tag); if(className) result.className = className; if(text !== undefined) result.textContent = text; return result; };
function toast(message) { $('toast').textContent=message; $('toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),4100); }

// Renderer and picking are built on the official three.js r160 interactive examples.
// All vendor code stays local; attribution and the original license are in vendor/.
const scene = new THREE.Scene();
scene.fog = null;
let renderer;
try { renderer = new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'}); }
catch(error) { const warning=el('div','webgl-fallback','此设备未能启用 WebGL。请启用浏览器硬件加速后刷新，或使用支持 WebGL 的浏览器。'); document.body.append(warning); throw error; }
renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));
renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap;
renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.3;
$('scene').append(renderer.domElement);
const camera=new THREE.PerspectiveCamera(35,innerWidth/innerHeight,.1,180);
const world=new THREE.Group(); scene.add(world);
const boardGroup=new THREE.Group(); world.add(boardGroup);
const stones=new THREE.Group(), gridGroup=new THREE.Group(), labels=new THREE.Group(), heatGroup=new THREE.Group(), effects=new THREE.Group();
boardGroup.add(stones,gridGroup,labels,heatGroup,effects);
scene.add(new THREE.HemisphereLight(0xfff9e9,0x6b7764,2.6));
const key=new THREE.DirectionalLight(0xfff9eb,4.3);key.position.set(-9,23,12);key.castShadow=true;key.shadow.mapSize.set(2048,2048);key.shadow.camera.left=-14;key.shadow.camera.right=14;key.shadow.camera.top=14;key.shadow.camera.bottom=-14;key.shadow.camera.near=.5;key.shadow.camera.far=60;key.shadow.bias=-.0004;scene.add(key);
const blueLight=new THREE.PointLight(0xe1f3e1,40,45,2);blueLight.position.set(-11,4,-7);scene.add(blueLight);
const goldLight=new THREE.PointLight(0xffe0a6,40,35,2);goldLight.position.set(10,4,5);scene.add(goldLight);
const rim=new THREE.DirectionalLight(0xf3fbef,3);rim.position.set(4,9,-14);scene.add(rim);
const material=(color,metalness=.1,roughness=.7)=>new THREE.MeshStandardMaterial({color,metalness,roughness});
const obsidian=material(0x706447,.2,.48), boardMat=material(0xd3bc87,.12,.65), bronze=material(0x907c46,.55,.4), stoneMat=material(0x243340,.18,.87);
function box(w,h,d,mat,x,y,z,parent=world) { const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);mesh.position.set(x,y,z);mesh.receiveShadow=true;mesh.castShadow=true;parent.add(mesh);return mesh; }
box(17.9,.32,17.9,obsidian,0,-.73,0,boardGroup);
box(17.4,.13,17.4,bronze,0,-.505,0,boardGroup);
box(17.2,.58,17.2,obsidian,0,-.15,0,boardGroup);
box(16.9,.085,16.9,bronze,0,.16,0,boardGroup);
box(16.72,.1,16.72,boardMat,0,.23,0,boardGroup);
const boardSurface=.284, extent=7.45;
// Subtle grain tones keep the board readable against the painted courtyard.
for(let x=-8;x<8;x+=2)for(let z=-8;z<8;z+=2){const tile=box(1.97,.012,1.97,material((Math.round(x+z)%4===0)?0xd0b785:0xd3bc8e,.12,.65),x+1,.29,z+1,boardGroup);tile.castShadow=false;}
for(const sign of [-1,1]){box(.025,.016,16.35,bronze,sign*8.14,.299,0,boardGroup);box(16.35,.016,.025,bronze,0,.299,sign*8.14,boardGroup);}
for(const x of [-8.35,8.35])for(const z of [-8.35,8.35]){const cap=box(.34,.12,.34,bronze,x,.28,z,boardGroup);cap.rotation.y=Math.PI/4;}
// The board bottom is y = -0.89; a receiver 0.015 below it makes contact visible.
const contactGround=new THREE.Mesh(new THREE.PlaneGeometry(75,75),new THREE.ShadowMaterial({color:0x39402b,opacity:.31}));
contactGround.rotation.x=-Math.PI/2;contactGround.position.y=-.905;contactGround.receiveShadow=true;world.add(contactGround);
const victoryInk=createVictoryInk(THREE,boardGroup,{extent});
let victoryKey=null;
const stoneGeometry=new THREE.SphereGeometry(1,36,22);
const blackMaterial=new THREE.MeshPhysicalMaterial({color:0x111713,metalness:.28,roughness:.22,clearcoat:.9,clearcoatRoughness:.18});
const whiteMaterial=new THREE.MeshPhysicalMaterial({color:0xfffdf2,metalness:.02,roughness:.25,clearcoat:.7,clearcoatRoughness:.17});
const ghost=new THREE.Mesh(stoneGeometry,new THREE.MeshPhysicalMaterial({color:0xc2a66c,transparent:true,opacity:.35,metalness:.3,roughness:.4,depthWrite:false}));ghost.visible=false;boardGroup.add(ghost);
const cursorRing=new THREE.Mesh(new THREE.RingGeometry(.27,.32,40),new THREE.MeshBasicMaterial({color:0xdac28b,transparent:true,opacity:.85,side:THREE.DoubleSide}));cursorRing.rotation.x=-Math.PI/2;cursorRing.visible=false;boardGroup.add(cursorRing);

let isReady=false; const layout={};
function disposeGroup(group){for(const item of [...group.children]){group.remove(item);if(item.userData.owned){item.geometry?.dispose();if(item.material.map)item.material.map.dispose();item.material.dispose();}}}
function textSprite(text,color='#a69b7e',scale=.34){const canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;const ctx=canvas.getContext('2d');ctx.font='500 58px Georgia';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(text,64,64);const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,transparent:true,depthWrite:false}));sprite.scale.set(scale,scale,1);sprite.userData.owned=true;return sprite;}
const positionAt=(r,c)=>new THREE.Vector3((c-(state.size-1)/2)*extent*2/(state.size-1),.32,(r-(state.size-1)/2)*extent*2/(state.size-1));
function buildGrid(){disposeGroup(gridGroup);disposeGroup(labels);const points=[];for(let i=0;i<state.size;i++){const v=-extent+i*2*extent/(state.size-1);points.push(-extent,.318,v,extent,.318,v,v,.318,-extent,v,.318,extent);const a=textSprite(String.fromCharCode(65+i),'#5d593b',.36);a.position.set(v,.45,7.94);labels.add(a);const b=textSprite(String(i+1),'#5d593b',.33);b.position.set(-7.99,.45,v);labels.add(b);}
const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(points,3));const lines=new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:0x544b34,transparent:true,opacity:.76}));lines.userData.owned=true;gridGroup.add(lines);
const offset=state.size===9?2:3;const starIndices=[offset,(state.size-1)/2,state.size-1-offset];for(const r of starIndices)for(const c of starIndices){const star=new THREE.Mesh(new THREE.CircleGeometry(.06,14),new THREE.MeshBasicMaterial({color:0x645334,side:THREE.DoubleSide}));star.rotation.x=-Math.PI/2;star.position.copy(positionAt(r,c));star.position.y=.322;star.userData.owned=true;gridGroup.add(star);}}
function renderStones(animateLast=false){disposeGroup(stones);disposeGroup(effects);const spacing=extent*2/(state.size-1),radius=Math.min(.66,spacing*.43);state.moves.forEach((move,index)=>{const mesh=new THREE.Mesh(stoneGeometry,move.player===1?blackMaterial:whiteMaterial);const pos=positionAt(move.r,move.c);mesh.position.set(pos.x,.34+radius*.45,pos.z);mesh.scale.set(radius,radius*.55,radius);mesh.castShadow=true;mesh.receiveShadow=true;if(animateLast&&!reducedMotion&&index===state.moves.length-1){mesh.userData.drop=performance.now();mesh.userData.targetY=mesh.position.y;mesh.position.y+=1.1;}stones.add(mesh);if(state.showNumbers){const label=textSprite(String(index+1),move.player===1?'#ded3b8':'#344655',radius*.78);label.position.set(pos.x,.37+radius*1.05,pos.z);stones.add(label);}});
if(state.moves.length){const last=state.moves.at(-1);const p=positionAt(last.r,last.c);const marker=new THREE.Mesh(new THREE.RingGeometry(radius*.14,radius*.20,30),new THREE.MeshBasicMaterial({color:last.player===1?0xe1be76:0x546d83,side:THREE.DoubleSide}));marker.rotation.x=-Math.PI/2;marker.position.set(p.x,.355+radius*1.03,p.z);marker.userData.owned=true;if(!state.showNumbers)effects.add(marker);}
const win=state.winner===1||state.winner===2?winningLine(state.moves.at(-1)):null;
const nextVictoryKey=win?`${state.winner}:${state.moves.length}:${win.map(point=>point.join(',')).join(';')}`:null;
// Rebuilding stones for move numbers or a view change must not replay the finish.
if(nextVictoryKey!==victoryKey){victoryKey=nextVictoryKey;if(win){victoryInk.play(win.map(point=>positionAt(...point)),state.winner,performance.now());victoryInk.update(performance.now(),reducedMotion);}else victoryInk.clear();}
}
function orderedCandidates(data){return [...(data.candidates||[])].sort((a,b)=>Number(b.move?.[0]===data.move?.[0]&&b.move?.[1]===data.move?.[1])-Number(a.move?.[0]===data.move?.[0]&&a.move?.[1]===data.move?.[1]));}
function drawHeat(){disposeGroup(heatGroup);if(!state.showHeat||!state.lastAnalysis)return;const candidates=orderedCandidates(state.lastAnalysis);candidates.slice(0,8).forEach((item,index)=>{const move=item.move;if(!move||state.board[move[0]]?.[move[1]])return;const radius=extent*2/(state.size-1)*.34;const mark=new THREE.Mesh(new THREE.RingGeometry(radius*.75,radius,40),new THREE.MeshBasicMaterial({color:index===0?0xd7b267:0x6b9bbe,transparent:true,opacity:1-index*.09,side:THREE.DoubleSide,depthWrite:false}));mark.rotation.x=-Math.PI/2;mark.position.copy(positionAt(...move));mark.position.y=.335;mark.userData.owned=true;heatGroup.add(mark);const label=textSprite(String(index+1),index===0?'#e5c784':'#8bb6d0',.36);label.position.copy(mark.position);label.position.y=.45;heatGroup.add(label);});}
function resize(){
  const stage=$('arena-stage'),width=stage.clientWidth,height=stage.clientHeight;
  if(!width||!height)return;
  renderer.setSize(width,height);camera.aspect=width/height;camera.clearViewOffset();
  // The seated opponent ends above 47.4% of the artwork's intrinsic height.
  // Use that physical anchor instead of a viewport percentage, including when cropped.
  const imageHeight=Math.max(height,width*941/1672),imageWidth=imageHeight*1672/941;
  const imageLeft=(width-imageWidth)/2,groundTop=Math.ceil(imageHeight*.474)+24;
  const scenery=$('scenery');Object.assign(scenery.style,{width:`${imageWidth}px`,height:`${imageHeight}px`,left:`${imageLeft}px`,top:'0px'});
  const availableWidth=Math.min(width-30,940),availableHeight=Math.max(130,height-groundTop-24);
  const direction=state.topView?new THREE.Vector3(0,1,.0001):new THREE.Vector3(0,.59,.81).normalize();
  let distance=45,bounds;
  for(let pass=0;pass<5;pass++){
    camera.position.copy(direction.clone().multiplyScalar(distance));camera.lookAt(0,0,0);camera.updateProjectionMatrix();camera.updateMatrixWorld();
    const corners=[];for(const x of [-9,9])for(const y of [-.91,.98])for(const z of [-9,9]){const v=new THREE.Vector3(x,y,z).project(camera);corners.push([(v.x+1)*width/2,(1-v.y)*height/2]);}
    const xs=corners.map(p=>p[0]),ys=corners.map(p=>p[1]);bounds={left:Math.min(...xs),right:Math.max(...xs),top:Math.min(...ys),bottom:Math.max(...ys)};
    if(pass<4)distance*=Math.max((bounds.right-bounds.left)/availableWidth,(bounds.bottom-bounds.top)/availableHeight);
  }
  const boardWidth=bounds.right-bounds.left,boardHeight=bounds.bottom-bounds.top;
  camera.setViewOffset(width,height,(bounds.left+bounds.right)/2-width/2,bounds.top-groundTop,width,height);camera.updateProjectionMatrix();
  Object.assign($('board-hit').style,{left:`${(width-boardWidth)/2}px`,top:`${groundTop}px`,width:`${boardWidth}px`,height:`${boardHeight}px`});
  Object.assign(layout,{width,height,imageLeft,imageTop:0,imageWidth,imageHeight,characterBottom:imageHeight*.474,boardTop:groundTop,boardLeft:(width-boardWidth)/2,boardWidth,boardHeight,boardBottom:groundTop+boardHeight});
}
addEventListener('resize',resize);
new ResizeObserver(resize).observe($('arena-stage'));
const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2(),boardPlane=new THREE.Plane(new THREE.Vector3(0,1,0),-.33),intersection=new THREE.Vector3();
function pick(event){const rect=$('arena-stage').getBoundingClientRect();pointer.x=((event.clientX-rect.left)/rect.width)*2-1;pointer.y=-((event.clientY-rect.top)/rect.height)*2+1;raycaster.setFromCamera(pointer,camera);if(!raycaster.ray.intersectPlane(boardPlane,intersection))return null;const spacing=extent*2/(state.size-1),c=Math.round((intersection.x+extent)/spacing),r=Math.round((intersection.z+extent)/spacing);if(r<0||r>=state.size||c<0||c>=state.size)return null;const pos=positionAt(r,c);if(Math.abs(pos.x-intersection.x)>spacing*.49||Math.abs(pos.z-intersection.z)>spacing*.49)return null;return [r,c];}
function showCursor(move){if(!move||state.busy||state.winner||(state.mode==='ai'&&state.player!==state.human)||state.board[move[0]][move[1]]){ghost.visible=cursorRing.visible=false;return;}const p=positionAt(...move),radius=Math.min(.66,extent*2/(state.size-1)*.43);ghost.position.set(p.x,.36+radius*.45,p.z);ghost.scale.set(radius,radius*.55,radius);ghost.visible=true;cursorRing.position.set(p.x,.34,p.z);cursorRing.visible=true;}
$('board-hit').addEventListener('pointermove',event=>showCursor(pick(event)));
$('board-hit').addEventListener('pointerleave',()=>showCursor(null));
$('board-hit').addEventListener('click',event=>{const p=pick(event);if(p)humanMove(...p);});
$('board-hit').addEventListener('keydown',event=>{const keys={ArrowUp:[-1,0],ArrowDown:[1,0],ArrowLeft:[0,-1],ArrowRight:[0,1]};if(keys[event.key]){event.preventDefault();state.keyboard=state.keyboard.map((v,i)=>Math.max(0,Math.min(state.size-1,v+keys[event.key][i])));showCursor(state.keyboard);}else if(event.key==='Enter'||event.key===' '){event.preventDefault();humanMove(...state.keyboard);}});
$('board-hit').addEventListener('focus',()=>showCursor(state.keyboard));
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;
function animate(time){requestAnimationFrame(animate);if(document.hidden||state.panel!=='arena')return;const t=time/1000;if(!reducedMotion){for(const mesh of stones.children){if(mesh.userData.drop){const p=Math.min(1,(time-mesh.userData.drop)/320);mesh.position.y=mesh.userData.targetY+(1-p)**3*1.1;if(p===1)delete mesh.userData.drop;}}cursorRing.material.opacity=.62+Math.sin(t*3)*.2;}victoryInk.update(time,reducedMotion);renderer.render(scene,camera);}
requestAnimationFrame(animate);

function winningLine(last){if(!last)return null;for(const [dr,dc] of [[0,1],[1,0],[1,1],[1,-1]]){const line=[[last.r,last.c]];for(const sign of [-1,1]){let r=last.r+dr*sign,c=last.c+dc*sign;while(r>=0&&r<state.size&&c>=0&&c<state.size&&state.board[r][c]===last.player){if(sign===-1)line.unshift([r,c]);else line.push([r,c]);r+=dr*sign;c+=dc*sign;}}if(line.length>=5)return line;}return null;}
function invalidate(){state.revision++;activeRequest?.abort();activeRequest=null;state.busy=false;state.feedback=null;$('feedback-good').disabled=$('feedback-bad').disabled=true;$('feedback-status').textContent='反馈用于后续偏好学习研究';}
function resetAnalysis(){state.lastAnalysis=null;for(const key of ['nodes','time','depth','cutoffs'])$(`metric-${key}`).textContent='—';$('candidates').replaceChildren(el('div','empty-candidates','搜索完成后显示候选评分'));setEngineStatus('尚未搜索','完成一次 AI 落子后显示结果');drawHeat();}
function newGame(notify=true){invalidate();state.size=Number($('size').value);state.human=Number($('side').value);state.mode=$('mode').value;state.board=Array.from({length:state.size},()=>Array(state.size).fill(0));state.moves=[];state.player=1;state.winner=0;state.keyboard=[Math.floor(state.size/2),Math.floor(state.size/2)];buildGrid();renderStones();resetAnalysis();$('board-size-label').textContent=`${state.size} × ${state.size}`;updateHud();showCursor(null);if(notify)toast('新对局已开启，黑棋先行');resize();if(state.mode==='ai'&&state.human===2)requestAI();}
function updateHud(){const ai=state.mode==='ai';$('black-role').textContent=ai?(state.human===1?'你':'AI'):'玩家一';$('white-role').textContent=ai?(state.human===2?'你':'AI'):'玩家二';$('move-count').textContent=`第 ${String(state.moves.length+ (state.winner?0:1)).padStart(2,'0')} 手`;
if(state.winner){$('turn-label').textContent='对局结束';$('turn-message').textContent=state.winner===3?'势均力敌 · 和局':`${state.winner===1?'黑棋':'白棋'}获胜`;}
else if(state.busy){$('turn-label').textContent='引擎推演中';$('turn-message').textContent='AI 正在搜索';}
else{const yours=!ai||state.player===state.human;$('turn-label').textContent=yours?(ai?'轮到你落子':`轮到${state.player===1?'黑棋':'白棋'}落子`):'等待 AI 落子';$('turn-message').textContent=state.moves.length?`${state.player===1?'执黑':'执白'}`:'黑棋先行';}
$('undo').disabled=!state.moves.length;$('hint').disabled=state.busy||!!state.winner;$('side').disabled=!ai;$('turn-label').classList.toggle('thinking-glow',state.busy);}
function placeMove(r,c){if(state.winner||state.board[r]?.[c]!==0)return false;state.board[r][c]=state.player;const move={r,c,player:state.player};state.moves.push(move);if(winningLine(move))state.winner=state.player;else if(state.moves.length===state.size**2)state.winner=3;state.player=3-state.player;renderStones(true);showCursor(null);drawHeat();playSound(state.winner?'win':'stone');updateHud();if(state.winner)toast(state.winner===3?'棋盘已满，本局和棋':`${state.winner===1?'黑棋':'白棋'}连成五子，获胜！`);return true;}
function humanMove(r,c){if(state.busy){toast('引擎正在思考，请稍候');return;}if(state.winner){toast('对局已结束，点击「开启新对局」再战');return;}if(state.mode==='ai'&&state.player!==state.human){toast('AI 尚未落子，点击「落子提示」可重试');return;}if(state.board[r]?.[c]!==0)return;state.feedback=null;$('feedback-good').disabled=$('feedback-bad').disabled=true;if(placeMove(r,c)&&!state.winner&&state.mode==='ai')requestAI();}
function setEngineStatus(title,description,thinking=false){const status=$('engine-status');status.classList.toggle('thinking',thinking);status.querySelector('strong').textContent=title;status.querySelector('small').textContent=description;}
async function api(path,options={}){const response=await fetch(new URL(`./api/${path}`,location.href),{...options,headers:{'Content-Type':'application/json',...options.headers}});let data;try{data=await response.json();}catch{throw new Error('服务器未返回有效数据');}if(!response.ok)throw new Error(data.error||`请求失败（${response.status}）`);return data;}
async function requestAI(hintOnly=false){if(state.busy||state.winner)return;if(hintOnly){state.feedback=null;$('feedback-good').disabled=$('feedback-bad').disabled=true;$('feedback-status').textContent='提示结果不计入 AI 落子反馈';}const revision=state.revision,board=cloneBoard(),player=state.player;state.busy=true;activeRequest=new AbortController();const controller=activeRequest;const failSafe=setTimeout(()=>controller.abort(),15000);setEngineStatus(hintOnly?'正在寻找落点':'引擎正在推演',`${engineName()} · 目标深度 ${state.depth}`,true);updateHud();showCursor(null);
try{const analysis=await api('analyze',{method:'POST',body:JSON.stringify({board,player,algorithm:state.algorithm,depth:state.depth,max_candidates:10,time_limit_ms:2000}),signal:controller.signal});if(revision!==state.revision)return;if(!analysis.move||analysis.move.length!==2||board[analysis.move[0]]?.[analysis.move[1]]!==0)throw new Error('引擎未返回合法落点');state.busy=false;state.lastAnalysis=analysis;displayAnalysis(analysis);setConnection(true);if(hintOnly){state.showHeat=true;$('heat-toggle').classList.add('active');drawHeat();state.keyboard=[...analysis.move];showCursor(analysis.move);toast(`建议落点 ${coord(analysis.move)} · 已搜索 ${analysis.completed_depth} 层`);}else{state.feedback={board,player,ai_move:[...analysis.move]};placeMove(...analysis.move);$('feedback-good').disabled=$('feedback-bad').disabled=false;$('feedback-status').textContent='反馈用于后续偏好学习研究';}updateHud();}
catch(error){if(revision!==state.revision)return;state.busy=false;setConnection(false);setEngineStatus('本次推演未完成',error.name==='AbortError'?'请求超时，可点击落子提示重试':error.message);toast(error.name==='AbortError'?'网络请求超时，请点击「落子提示」重试':`引擎连接失败：${error.message}`);updateHud();}
finally{clearTimeout(failSafe);if(activeRequest===controller)activeRequest=null;}}
function displayAnalysis(data){$('metric-nodes').textContent=number(data.nodes);$('metric-time').textContent=number(Math.round(data.elapsed_ms));$('metric-depth').textContent=`${data.completed_depth} / ${data.requested_depth}`;$('metric-cutoffs').textContent=number(data.cutoffs);setEngineStatus(data.timeout?'思考预算已用尽':'推演完成',data.timeout?`返回最近完成深度 ${data.completed_depth} · 目标 ${data.requested_depth}`:`${engineName()} · ${coord(data.move)} · ${number(data.leaves)} 个叶节点`);const list=$('candidates');list.replaceChildren();const candidates=orderedCandidates(data).slice(0,3),max=Math.max(1,...candidates.map(x=>Math.abs(x.score||0)));if(!candidates.length)list.append(el('div','empty-candidates','本次搜索未提供候选评分'));candidates.forEach((item,index)=>{const row=el('div','candidate');row.append(el('span','rank',String(index+1).padStart(2,'0')),el('span','coord',coord(item.move)));const bar=el('span','candidate-bar'),fill=el('i');fill.style.width=`${Math.max(8,Math.abs(item.score||0)/max*100)}%`;bar.append(fill);row.append(bar);const bound=item.bound==='upper_bound'||item.bound==='upper'?'≤':item.bound==='lower_bound'||item.bound==='lower'?'≥':'';const score=el('span','score',bound+compactScore(item.score));score.title=`${bound}${number(item.score)}（启发式评分，不是胜率）`;row.append(score);list.append(row);});drawHeat();}
function compactScore(value){if(!Number.isFinite(value))return '—';const n=Math.abs(value);return n>=1e6?`${(value/1e6).toFixed(1)}m`:n>=1000?`${(value/1000).toFixed(1)}k`:String(Math.round(value));}
function undo(){if(!state.moves.length)return;invalidate();let count=1;if(state.mode==='ai'&&state.moves.length>=2&&state.moves.at(-1).player!==state.human)count=2;while(count--&&state.moves.length){const move=state.moves.pop();state.board[move.r][move.c]=0;}state.player=state.moves.length%2===0?1:2;state.winner=0;renderStones();resetAnalysis();updateHud();toast('已回到上一手');if(state.mode==='ai'&&state.player!==state.human)requestAI();}
async function submitFeedback(rating){if(!state.feedback)return;const payload=state.feedback,revision=state.revision;$('feedback-good').disabled=$('feedback-bad').disabled=true;try{await api('feedback',{method:'POST',body:JSON.stringify({...payload,rating})});if(revision===state.revision&&state.feedback===payload){$('feedback-status').textContent=rating===1?'已保存认可反馈，感谢你的判断':'已保存改进反馈，感谢你的判断';state.feedback=null;}toast('人类反馈已保存');}catch(error){if(revision===state.revision&&state.feedback===payload)$('feedback-good').disabled=$('feedback-bad').disabled=false;toast(`反馈保存失败：${error.message}`);}}
function playSound(kind){if(!state.sound)return;try{audioContext??=new (window.AudioContext||window.webkitAudioContext)();audioContext.resume();const now=audioContext.currentTime;const notes=kind==='win'?[523.25,659.25,783.99]:[state.player===1?640:480];notes.forEach((frequency,index)=>{const osc=audioContext.createOscillator(),gain=audioContext.createGain();osc.type='sine';osc.frequency.setValueAtTime(frequency,now+index*.13);osc.frequency.exponentialRampToValueAtTime(frequency*.55,now+index*.13+.16);gain.gain.setValueAtTime(.0001,now+index*.13);gain.gain.exponentialRampToValueAtTime(.12,now+index*.13+.007);gain.gain.exponentialRampToValueAtTime(.0001,now+index*.13+.22);osc.connect(gain);gain.connect(audioContext.destination);osc.start(now+index*.13);osc.stop(now+index*.13+.25);});}catch{state.sound=false;}}
function setConnection(ok){$('connection').className=`connection ${ok?'online':'error'}`;$('connection').replaceChildren(el('i'),document.createTextNode(ok?'引擎在线':'连接待恢复'));}
async function health(){try{await api('health');setConnection(true);}catch{setConnection(false);}}
function exportGame(){const content={format:'yijing-gomoku-v1',rules:'freestyle-five-or-more',size:state.size,mode:state.mode,algorithm:state.algorithm,requested_depth:state.depth,moves:state.moves,winner:state.winner,exported_at:new Date().toISOString()};const blob=new Blob([JSON.stringify(content,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=el('a');link.href=url;link.download=`gomoku-${state.size}x${state.size}-${state.moves.length}moves.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('棋谱已导出为 JSON');}
function showTree(){const data=state.lastAnalysis;$('tree-dialog').showModal();$('pv').replaceChildren();$('tree-visual').replaceChildren();if(!data){$('tree-summary').textContent='先完成一次 AI 搜索，即可查看轨迹。';return;}$('tree-summary').textContent=`${data.algorithm==='alphabeta'?'ALPHA–BETA':'MINIMAX'} · 完成 ${data.completed_depth} 层 · ${number(data.nodes)} 个访问节点 · ${number(data.cutoffs)} 次剪枝`;const pv=data.pv||[];$('pv').append(el('span','', '主变化线'));pv.forEach((move,index)=>$('pv').append(el('span','',`${index+1}. ${coord(move)}`)));const nodes=data.tree?.nodes||[];nodes.slice(0,180).forEach(node=>{const row=el('div',`tree-row ${node.pruned?'pruned':''}`);const depth=Math.max(0,Math.min(8,Number(node.depth)||0));row.style.paddingLeft=`${depth*20}px`;if(node.parent!=null)row.append(el('span','tree-branch'));row.append(el('i'),el('span','',node.move?coord(node.move):'ROOT'),el('small','',`#${node.id}${node.parent!=null?' ← #'+node.parent:''}`));if(node.pruned)row.append(el('small','','剪枝'));row.append(el('span','node-score',node.score==null?'—':(node.bound==='upper_bound'?'≤':node.bound==='lower_bound'?'≥':'')+compactScore(node.score)));$('tree-visual').append(row);});if(!nodes.length)$('tree-visual').append(el('p','','当前搜索没有可显示的轨迹。'));if(data.tree?.truncated||nodes.length>180)$('tree-visual').append(el('p','fine-print','为保证交互流畅，仅展示部分搜索记录。'));}
function setPanel(){state.panel='arena';resize();}
$('new-game').addEventListener('click',()=>newGame());$('undo').addEventListener('click',undo);$('hint').addEventListener('click',()=>requestAI(state.mode==='local'||state.player===state.human));$('export-game').addEventListener('click',exportGame);
$('mode').addEventListener('change',()=>newGame());$('size').addEventListener('change',()=>newGame());$('side').addEventListener('change',()=>newGame());
$('depth').addEventListener('input',()=>{$('depth-value').textContent=$('depth').value;});$('depth').addEventListener('change',()=>{state.depth=Number($('depth').value);if(state.busy){invalidate();updateHud();if(state.mode==='ai'&&state.player!==state.human)requestAI();}toast(`搜索深度设为 ${state.depth}，下一次思考生效`);});
document.querySelectorAll('[data-engine]').forEach(button=>button.addEventListener('click',()=>{if(state.algorithm===button.dataset.engine)return;state.algorithm=button.dataset.engine;document.querySelectorAll('[data-engine]').forEach(b=>b.classList.toggle('active',b===button));if(state.busy)invalidate();updateHud();if(state.mode==='ai'&&state.player!==state.human&&!state.winner)requestAI();toast(`已切换至 ${engineName()}`);}));
$('view-toggle').addEventListener('click',()=>{state.topView=!state.topView;$('view-toggle').querySelector('span').textContent=state.topView?'俯视视角':'透视视角';resize();});$('numbers-toggle').addEventListener('click',()=>{state.showNumbers=!state.showNumbers;$('numbers-toggle').classList.toggle('active',state.showNumbers);renderStones();});$('heat-toggle').addEventListener('click',()=>{state.showHeat=!state.showHeat;$('heat-toggle').classList.toggle('active',state.showHeat);drawHeat();if(state.showHeat&&!state.lastAnalysis)toast('完成一次搜索后，候选热区将在棋盘上显示');});
$('sound').addEventListener('click',()=>{state.sound=!state.sound;$('sound').textContent=state.sound?'♪':'♫';$('sound').title=state.sound?'关闭音效':'开启音效';$('sound').setAttribute('aria-label',$('sound').title);toast(state.sound?'落子音效已开启':'落子音效已关闭');playSound('stone');});
$('help').addEventListener('click',()=>$('info-dialog').showModal());$('tree-button').addEventListener('click',showTree);document.querySelectorAll('.dialog-close').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));document.querySelectorAll('dialog').forEach(dialog=>dialog.addEventListener('click',event=>{if(event.target===dialog){const rect=dialog.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)dialog.close();}}));
$('feedback-good').addEventListener('click',()=>submitFeedback(1));$('feedback-bad').addEventListener('click',()=>submitFeedback(-1));
function closePanels(){
  document.querySelectorAll('.panel').forEach(panel=>{panel.hidden=true;panel.classList.remove('drawer-open');});
  document.querySelectorAll('.drawer-controls button').forEach(button=>{button.classList.remove('active');button.setAttribute('aria-expanded','false');});
  $('panel-backdrop').hidden=true;document.body.style.overflow='';
}
for(const [buttonId,panelClass] of [['settings-drawer','left-panel'],['analysis-drawer','right-panel']]){
  const panel=document.querySelector(`.${panelClass}`),close=el('button','panel-close','×');close.setAttribute('aria-label','关闭侧栏');
  close.addEventListener('click',()=>{closePanels();$(buttonId).focus();});panel.append(close);
  $(buttonId).addEventListener('click',()=>{
    const open=panel.hidden;closePanels();if(!open)return;
    panel.hidden=false;panel.classList.add('drawer-open');$(buttonId).classList.add('active');$(buttonId).setAttribute('aria-expanded','true');
    $('panel-backdrop').hidden=false;document.body.style.overflow='hidden';close.focus();
  });
}
$('panel-backdrop').addEventListener('click',closePanels);
addEventListener('keydown',event=>{if(event.key==='Escape')closePanels();});
$('new-game').addEventListener('click',closePanels);
newGame(false);health();isReady=true;
// This explicit recording route is dormant during ordinary gameplay.
if(new URLSearchParams(location.search).has('record')){
  import('./demo-recorder.js').then(module=>module.startDemo({renderer,scene,camera,state,newGame,placeMove,displayAnalysis,renderStones,resize,positionAt,extent,setPanel,stage:$('arena-stage'),scenery:$('scenery'),getLayout:()=>({...layout})})).catch(error=>toast(`回放加载失败：${error.message}`));
}
