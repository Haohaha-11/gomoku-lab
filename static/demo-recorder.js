/** Record the real app renderer and scenery; loaded only by the explicit ?record hook. */
export async function startDemo(h) {
  const token = new URLSearchParams(location.search).get('record');
  const status = document.createElement('div');
  status.id = 'demo-recording-status';
  Object.assign(status.style, {position:'fixed',right:'12px',bottom:'12px',zIndex:'1000',padding:'12px 18px',background:'#172b2a',color:'#fff',font:'16px sans-serif'});
  status.textContent = '正在准备真实棋局录像…';
  document.body.append(status);
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  try {
    if (!['127.0.0.1', 'localhost'].includes(location.hostname)) throw new Error('录制接收器仅支持本机地址');
    const response = await fetch('./media/demo-game.json');
    if (!response.ok) throw new Error('无法读取真实棋谱');
    const game = await response.json();
    await document.fonts.ready;
    if (h.scenery && !h.scenery.complete) await new Promise((resolve,reject) => {h.scenery.addEventListener('load',resolve,{once:true});h.scenery.addEventListener('error',reject,{once:true});});
    document.getElementById('mode').value = 'local';
    document.getElementById('size').value = String(game.size);
    document.getElementById('side').value = '1';
    h.state.algorithm = 'alphabeta'; h.state.depth = game.depth; h.state.sound = false;
    h.state.showNumbers = false; h.state.showHeat = false; h.state.topView = false;
    h.setPanel('arena');
    Object.assign(h.stage.style,{width:'1280px',maxWidth:'none',height:'720px',minHeight:'720px'});
    h.newGame(false); h.resize();
    await sleep(700);

    const output = document.createElement('canvas');
    output.width = 1280; output.height = 800;
    const ctx = output.getContext('2d', {alpha:false});
    const stream = output.captureStream(30);
    const mimeType = ['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'].find(type => MediaRecorder.isTypeSupported(type));
    if (!mimeType) throw new Error('浏览器不支持 WebM 录制');
    const recorder = new MediaRecorder(stream, {mimeType,videoBitsPerSecond:8000000});
    const chunks = [];
    recorder.ondataavailable = event => {if (event.data.size) chunks.push(event.data);};
    let stopped = false, current = null, phase = 'intro', frameCount = 0;
    const titles = {
      intro: ['弈境 · 墨山对弈', '真实 3D 网页实录 / 经典博弈搜索'],
      opening: ['落子为阵', '预设合法开局 · 黑白交替'],
      block: ['守势 · 一步解围', '黑棋四连，Alpha–Beta 找到唯一防守点 H7'],
      attack: ['由守转攻', '白方继续真实搜索 · 候选落点与局面价值'],
      win: ['五子成势', '白棋斜线成五 · 规则引擎确认获胜'],
    };
    const paint = () => {
      if (stopped) return;
      const stageRect = h.stage.getBoundingClientRect();
      const sx = output.width / stageRect.width, sy = 720 / stageRect.height;
      ctx.fillStyle = '#d8dfd8'; ctx.fillRect(0,0,1280,800);
      if (h.scenery?.naturalWidth) {
        const rect = h.scenery.getBoundingClientRect();
        ctx.save(); ctx.globalAlpha = Number(getComputedStyle(h.scenery).opacity) || 1;
        ctx.drawImage(h.scenery,(rect.left-stageRect.left)*sx,(rect.top-stageRect.top)*sy,rect.width*sx,rect.height*sy); ctx.restore();
      }
      h.renderer.render(h.scene,h.camera);
      const canvasRect = h.renderer.domElement.getBoundingClientRect();
      ctx.drawImage(h.renderer.domElement,(canvasRect.left-stageRect.left)*sx,(canvasRect.top-stageRect.top)*sy,canvasRect.width*sx,canvasRect.height*sy);
      const shade = ctx.createLinearGradient(0,0,0,125);
      shade.addColorStop(0,'rgba(10,25,25,.82)'); shade.addColorStop(1,'rgba(10,25,25,0)');
      ctx.fillStyle=shade; ctx.fillRect(0,0,1280,125);
      const [title, subtitle] = titles[phase];
      ctx.textAlign='left'; ctx.fillStyle='#f3ecd9'; ctx.font='600 30px "Microsoft YaHei", sans-serif';
      ctx.fillText(title,34,45);
      ctx.font='17px "Microsoft YaHei", sans-serif'; ctx.fillStyle='#d8e4dd';ctx.fillText(subtitle,35,75);
      ctx.textAlign='right';ctx.font='14px "Microsoft YaHei", sans-serif';ctx.fillText('示例棋谱 · 已加速回放',1245,38);
      ctx.fillStyle='rgba(11,31,30,.96)';ctx.fillRect(0,720,1280,80);
      ctx.textAlign='left';ctx.fillStyle='#f3ecd9';ctx.font='18px "Microsoft YaHei", sans-serif';
      const moveLabel=current ? `第 ${String(current.ply).padStart(2,'0')} 手  ${current.player===1?'黑棋':'白棋'} · ${String.fromCharCode(65+current.c)}${current.r+1}` : '13 × 13  /  自由五子棋';
      ctx.fillText(moveLabel,34,755);
      ctx.font='13px "Microsoft YaHei", sans-serif';ctx.fillStyle='#bccfc8';ctx.fillText('前 7 手为示例布局；后续白方由真实搜索引擎计算。本片不代表棋力评测。',34,781);
      ctx.textAlign='right';ctx.font='16px "Microsoft YaHei", sans-serif';ctx.fillStyle='#e8cd92';
      const a=current?.analysis;
      ctx.fillText(a ? `α–β  深度 ${a.completed_depth}   ·   ${a.nodes} 节点   ·   ${a.cutoffs} 次剪枝   ·   ${a.elapsed_ms.toFixed(1)} ms` : '黑白交替 / 真实 3D 落子',1245,756);
      frameCount++; requestAnimationFrame(paint);
    };
    paint();
    recorder.start(1000);
    status.textContent='正在录制真实棋局，请保持页面打开…';
    await sleep(3000);
    for (const move of game.moves) {
      current=move;
      phase=move.ply<=7?'opening':move.ply===8?'block':move.winner_after?'win':'attack';
      if (h.state.player!==move.player || h.state.board[move.r][move.c]!==0) throw new Error(`第 ${move.ply} 手回放不合法`);
      if (move.analysis) { h.state.lastAnalysis=move.analysis;h.displayAnalysis(move.analysis); }
      if (!h.placeMove(move.r,move.c)) throw new Error(`第 ${move.ply} 手无法落子`);
      await sleep(move.ply<=7 ? 1400 : move.ply===8 ? 4200 : move.analysis ? 2600 : 1400);
    }
    if (h.state.winner!==game.winner) throw new Error('回放终局与规则校验不一致');
    await sleep(4300);
    const finished = new Promise(resolve => {recorder.onstop=resolve;});
    recorder.stop(); await finished; stopped=true;stream.getTracks().forEach(track=>track.stop());
    const blob = new Blob(chunks,{type:mimeType});
    status.textContent=`录像完成（${Math.round(blob.size/1048576)} MB），正在写入本机…`;
    const saved = await fetch(`./__recording/${encodeURIComponent(token)}`,{method:'POST',headers:{'Content-Type':mimeType,'X-Recording-Frames':String(frameCount)},body:blob});
    if (!saved.ok) throw new Error(`本机保存失败：HTTP ${saved.status}`);
    const result=await saved.json();
    status.textContent=`录像已保存 · ${result.bytes} 字节 · ${frameCount} 帧`;
    document.documentElement.dataset.recording='complete';
  } catch(error) {
    status.textContent=`录制失败：${error.message}`;
    document.documentElement.dataset.recording='failed';
    console.error(error);
  }
}
