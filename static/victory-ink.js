/** A deterministic board-space brush stroke for a completed five-in-a-row. */
export function createVictoryInk(THREE, parent, {extent = 7.45} = {}) {
  const SWEEP_MS = 1100;
  const SETTLE_MS = 2000;
  const SURFACE_Y = .348;
  const group = new THREE.Group();
  group.name = 'VictoryInk';
  group.visible = false;
  parent.add(group);

  function randomSource(initial) {
    let seed = initial >>> 0;
    return () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296);
  }

  function brushTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 1024; canvas.height = 128;
    const ctx = canvas.getContext('2d');
    const random = randomSource(0x41f157);
    for (let strand = 0; strand < 58; strand++) {
      const y = 64 + (random() - .5) * 75;
      const bend = (random() - .5) * 22;
      ctx.strokeStyle = `rgba(12,22,16,${.24 + random() * .55})`;
      ctx.lineWidth = 1.7 + random() * 8;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(random() * 27, y + bend);
      ctx.bezierCurveTo(270, y - bend, 715, y + bend, 997 + random() * 27, y);
      ctx.stroke();
    }
    // Uneven wet patches and dry flecks prevent the wide sweep reading as a ruler line.
    for (let i = 0; i < 17; i++) {
      const x=45+random()*920,y=44+random()*40;
      ctx.fillStyle=`rgba(11,20,15,${.15+random()*.37})`;
      ctx.beginPath();
      ctx.ellipse(x,y,12+random()*40,4+random()*12,(random()-.5)*.28,0,Math.PI*2);
      ctx.fill();
    }
    for (let i = 0; i < 245; i++) {
      const x=random()*1024,y=64+(random()-.5)*121;
      ctx.fillStyle=`rgba(15,24,18,${.18+random()*.60})`;
      ctx.beginPath();
      ctx.ellipse(x,y,.45+random()*3.5,.4+random()*1.9,(random()-.5)*.8,0,Math.PI*2);
      ctx.fill();
    }
    // Removing small channels leaves paper-like flying-white grain inside the ink.
    ctx.globalCompositeOperation = 'destination-out';
    for (let i = 0; i < 195; i++) {
      const x = random() * 1024, y = 20 + random() * 88;
      ctx.strokeStyle = `rgba(0,0,0,${.23 + random() * .75})`;
      ctx.lineWidth = .6 + random() * 2.9;
      ctx.beginPath(); ctx.moveTo(x,y);
      ctx.lineTo(Math.min(1024,x + 12 + random() * 145), y + (random() - .5) * 6);
      ctx.stroke();
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.wrapS = texture.wrapT = THREE.ClampToEdgeWrapping;
    return texture;
  }

  function mistTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 96;
    const ctx = canvas.getContext('2d');
    const random = randomSource(0x1ab579);
    for (let i = 0; i < 18; i++) {
      const x = 22 + random() * 52, y = 22 + random() * 52;
      const radius = 12 + random() * 19;
      const gradient = ctx.createRadialGradient(x,y,0,x,y,radius);
      gradient.addColorStop(0,'rgba(255,255,255,.21)');
      gradient.addColorStop(.45,'rgba(255,255,255,.09)');
      gradient.addColorStop(1,'rgba(255,255,255,0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(x-radius,y-radius,radius*2,radius*2);
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  const brush = brushTexture(), mist = mistTexture();
  const planeGeometry = new THREE.PlaneGeometry(1,1);
  const vertexShader = `
    varying vec2 vInkUv;
    void main() {
      vInkUv=uv;
      gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);
    }`;
  const fragmentShader = `
    uniform sampler2D uBrush;
    uniform float uReveal;
    uniform float uOpacity;
    varying vec2 vInkUv;
    void main() {
      vec4 ink=texture2D(uBrush,vInkUv);
      float edge=1.0-smoothstep(uReveal-.028,uReveal,vInkUv.x);
      float ends=smoothstep(0.0,.018,vInkUv.x)*(1.0-smoothstep(.982,1.0,vInkUv.x));
      float alpha=ink.a*edge*ends*uOpacity;
      if(alpha<.002) discard;
      gl_FragColor=vec4(ink.rgb,alpha);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`;

  function layer(name, y) {
    const material = new THREE.ShaderMaterial({
      uniforms:{uBrush:{value:brush},uReveal:{value:0},uOpacity:{value:0}},
      vertexShader,fragmentShader,transparent:true,depthTest:true,depthWrite:false,
      side:THREE.DoubleSide,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1,
    });
    const mesh = new THREE.Mesh(planeGeometry,material);
    mesh.name = `VictoryInk.${name}`;
    mesh.rotation.order = 'YXZ';
    mesh.rotation.x = -Math.PI/2;
    mesh.position.y = y;
    // Ink stays on the board surface, below the stones, rather than painting over them.
    mesh.renderOrder = 2;
    group.add(mesh);
    return mesh;
  }

  const bleed = layer('Bleed',SURFACE_Y);
  const sweep = layer('Sweep',SURFACE_Y+.003);
  const settled = layer('Settled',SURFACE_Y+.006);
  const random = randomSource(0x7158b3);
  const clouds = Array.from({length:26},(_,index) => {
    const material = new THREE.SpriteMaterial({map:mist,color:0x122019,transparent:true,opacity:0,
      depthTest:true,depthWrite:false,rotation:(random()-.5)*Math.PI});
    const sprite = new THREE.Sprite(material);
    sprite.name = `VictoryInk.Mist.${index}`;
    sprite.visible = false;
    group.add(sprite);
    return {sprite,fraction:(index+.35+random()*.3)/26,side:(random()-.5)*2,
      drift:.35+random()*.58,lift:.12+random()*.34,size:(.43+random()*.42)*1.6,
      duration:1100+random()*900};
  });

  let active = false, startedAt = 0, winningPlayer = 0, elapsed = 0;
  let start = new THREE.Vector3(), end = new THREE.Vector3();
  let direction = new THREE.Vector3(1,0,0), perpendicular = new THREE.Vector3(0,0,1);
  let fullLength = 1, winStartFraction = 0, winLengthFraction = 1;
  let phase = 'idle';
  const clamp = (value,low,high) => Math.max(low,Math.min(high,value));
  const smooth = value => {const x=clamp(value,0,1);return x*x*(3-2*x);};

  function setLayer(mesh, first, last, width) {
    const length = first.distanceTo(last);
    mesh.position.x = (first.x+last.x)/2;
    mesh.position.z = (first.z+last.z)/2;
    mesh.rotation.y = -Math.atan2(last.z-first.z,last.x-first.x);
    mesh.scale.set(length,width,1);
    mesh.material.uniforms.uReveal.value = 0;
    mesh.material.uniforms.uOpacity.value = 0;
  }

  function clear() {
    active=false; phase='idle';winningPlayer=0;elapsed=0;group.visible=false;
    for (const item of clouds) item.sprite.visible=false;
  }

  function play(linePositions, winner, time) {
    clear();
    if (![1,2].includes(winner) || !Array.isArray(linePositions) || linePositions.length<2) return false;
    if (linePositions.some(point=>!Number.isFinite(point?.x)||!Number.isFinite(point?.z))) return false;
    let first=linePositions[0],last=linePositions[1],longest=0;
    for (let i=0;i<linePositions.length;i++) for (let j=i+1;j<linePositions.length;j++) {
      const dx=linePositions[j].x-linePositions[i].x,dz=linePositions[j].z-linePositions[i].z;
      const distance=dx*dx+dz*dz;
      if (distance>longest) {longest=distance;first=linePositions[i];last=linePositions[j];}
    }
    if (longest<.000001) return false;
    direction.set(last.x-first.x,0,last.z-first.z).normalize();
    // A canonical direction keeps mirrored/unsorted winning-cell inputs reproducible.
    if (direction.x<-.0001 || (Math.abs(direction.x)<.0001&&direction.z<0)) direction.negate();
    perpendicular.set(-direction.z,0,direction.x);
    const origin=new THREE.Vector3(first.x,0,first.z);
    let low=-Infinity,high=Infinity;
    for (const axis of ['x','z']) {
      if (Math.abs(direction[axis])<.000001) {
        if (Math.abs(origin[axis])>extent+.01) return false;
        continue;
      }
      const a=(-extent-origin[axis])/direction[axis],b=(extent-origin[axis])/direction[axis];
      low=Math.max(low,Math.min(a,b));high=Math.min(high,Math.max(a,b));
    }
    if (!Number.isFinite(low)||!Number.isFinite(high)||high<=low) return false;
    start.copy(origin).addScaledVector(direction,low);
    end.copy(origin).addScaledVector(direction,high);
    fullLength=high-low;
    const projections=linePositions.map(point=>(point.x-start.x)*direction.x+(point.z-start.z)*direction.z);
    const winLow=clamp(Math.min(...projections)-.22,0,fullLength);
    const winHigh=clamp(Math.max(...projections)+.22,0,fullLength);
    const winFirst=start.clone().addScaledVector(direction,winLow);
    const winLast=start.clone().addScaledVector(direction,winHigh);
    winStartFraction=winLow/fullLength;winLengthFraction=(winHigh-winLow)/fullLength;
    setLayer(bleed,start,end,2.35);
    setLayer(sweep,start,end,1.58);
    setLayer(settled,winFirst,winLast,.30);
    startedAt=Number.isFinite(time)?time:performance.now();
    winningPlayer=winner;active=true;group.visible=true;phase='sweep';
    update(startedAt,false);
    return true;
  }

  function update(time, reducedMotion=false) {
    if (!active) return;
    elapsed=Math.max(0,(Number.isFinite(time)?time:performance.now())-startedAt);
    const reveal=reducedMotion?1.04:Math.min(1.04,elapsed/SWEEP_MS*1.04);
    const settling=reducedMotion?1:smooth((elapsed-SWEEP_MS)/SETTLE_MS);
    phase=settling>=1?'settled':elapsed<SWEEP_MS?'sweep':'settling';
    sweep.material.uniforms.uReveal.value=reveal;
    sweep.material.uniforms.uOpacity.value=reducedMotion?0:.93*(1-settling);
    bleed.material.uniforms.uReveal.value=reveal;
    bleed.material.uniforms.uOpacity.value=reducedMotion?0:.26*(1-settling);
    bleed.scale.y=2.35+settling*.55;
    settled.material.uniforms.uReveal.value=reducedMotion?1.04:clamp((reveal-winStartFraction)/winLengthFraction,0,1.04);
    settled.material.uniforms.uOpacity.value=.60+settling*.17;
    for (const cloud of clouds) {
      const age=elapsed-cloud.fraction*SWEEP_MS;
      const p=clamp(age/cloud.duration,0,1);
      cloud.sprite.visible=!reducedMotion&&age>0&&p<1;
      if (!cloud.sprite.visible) continue;
      cloud.sprite.position.copy(start).addScaledVector(direction,fullLength*cloud.fraction);
      cloud.sprite.position.addScaledVector(perpendicular,cloud.side*(.055+cloud.drift*p));
      cloud.sprite.position.y=SURFACE_Y+.035+Math.sin(p*Math.PI/2)*cloud.lift;
      const size=cloud.size*(.48+p*.86);
      cloud.sprite.scale.set(size,size*.53,1);
      cloud.sprite.material.opacity=.34*Math.sin(Math.PI*p)*(1-settling*.55);
    }
  }

  function dispose() {
    clear(); parent.remove(group);
    for (const mesh of [bleed,sweep,settled]) mesh.material.dispose();
    for (const cloud of clouds) cloud.sprite.material.dispose();
    planeGeometry.dispose();brush.dispose();mist.dispose();
  }

  return {play,clear,update,dispose,
    get active(){return active;},get phase(){return phase;},get winner(){return winningPlayer;},
    get startedAt(){return startedAt;},
    get snapshot(){return {active,phase,winner:winningPlayer,startedAt,elapsedMs:elapsed,
      direction:direction.toArray(),start:start.toArray(),end:end.toArray(),
      sweepReveal:sweep.material.uniforms.uReveal.value,sweepOpacity:sweep.material.uniforms.uOpacity.value,
      settledReveal:settled.material.uniforms.uReveal.value,settledOpacity:settled.material.uniforms.uOpacity.value,
      visibleMist:clouds.filter(cloud=>cloud.sprite.visible).length};}};
}
