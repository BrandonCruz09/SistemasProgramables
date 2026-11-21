'use strict';
const el = id => document.getElementById(id);
const demo = document.body.dataset.demo === 'true';
const videoBase = `${location.protocol}//${location.hostname}:8765`;
let last = null, pending = 0, waterLock = 0, refreshing = false;
let videoPaused = demo, videoError = false, videoRetry = null;
const finite = v => typeof v === 'number' && Number.isFinite(v);
const number = (v, unit) => finite(v) ? `${v.toFixed(1)} ${unit}` : 'Sin lectura';
const states = {LISTO:'Lista para operar',COMPUERTA_ABIERTA:'Sirviendo alimento',COMPUERTA_CERRANDO:'Cerrando el plato',BOMBA_ACTIVA:'Sirviendo agua',ERROR_ACTUADOR:'Necesita una revisión'};
const actionNames = {tone:'Tono de buzzer',beep:'Buzzer',gate_open:'Abrir compuerta',gate_close:'Cerrar compuerta',feed:'Alimento',water:'Agua',stop_food:'Alimento cancelado',stop_water:'Agua detenida',signal_dog:'Detección de perro',auto_enable:'Automático habilitado',auto_disable:'Automático deshabilitado',reset_demo:'Demostración reiniciada'};

el('demoBanner').hidden = !demo;
el('resetDemo').addEventListener('click', () => command('reset_demo'));
if (demo) {
  el('camera').setAttribute('aria-disabled','true');
  el('camera').removeAttribute('href');
  el('camera').setAttribute('tabindex','-1');
  el('pauseVideo').disabled = true;
  el('pauseVideo').textContent = 'Demo';
} else {
  el('camera').href = videoBase + '/';
}
function cameraState() {
  const available = !demo && !videoPaused && !videoError && last?.vision?.available;
  el('liveVideo').hidden = !available;
  el('cameraEmpty').hidden = !!available;
  el('cameraBadge').dataset.live = String(!!available);
  el('cameraState').textContent = demo ? 'Demo' : available ? 'En vivo' : videoPaused ? 'En pausa' : 'Sin señal';
  el('cameraEmptyTitle').textContent = demo ? 'Aquí verás su estación' : videoPaused ? 'Video en pausa' : 'Esperando a la cámara';
  el('cameraEmptyText').textContent = demo ? 'La cámara real está desactivada en esta demostración.' : videoPaused ? 'Puedes reanudarlo cuando quieras.' : 'El video aparecerá cuando la cámara y el servidor estén disponibles.';
}
function connectVideo() {
  clearTimeout(videoRetry); videoRetry = null;
  if (demo || videoPaused) return;
  videoError = false;
  el('liveVideo').src = videoBase + '/stream?t=' + Date.now();
}
el('liveVideo').addEventListener('error', () => {
  videoError = true; cameraState();
  clearTimeout(videoRetry);
  if (!demo && !videoPaused) videoRetry = setTimeout(connectVideo,5000);
});
el('liveVideo').addEventListener('load', () => {videoError=false;cameraState();});
el('pauseVideo').addEventListener('click', () => {
  if (demo) return;
  videoPaused = !videoPaused;
  el('pauseVideo').textContent = videoPaused ? 'Reanudar' : 'Pausar';
  if (videoPaused) {clearTimeout(videoRetry);el('liveVideo').removeAttribute('src');}
  else connectVideo();
  cameraState();
});
cameraState(); connectVideo();

function chart(items = []) {
  const key = el('metric').value;
  const vals = items.map(x => x.status?.[key]);
  const valid = vals.filter(finite);
  if (!valid.length) {
    el('line').setAttribute('d',''); el('ymin').textContent='';el('ymax').textContent='';
    el('range').textContent = 'Todavía no hay lecturas para esta medición.';return;
  }
  let lo=Math.min(...valid), hi=Math.max(...valid);
  if(lo===hi){lo-=1;hi+=1;}
  let path='', open=false;
  vals.forEach((value,i)=>{
    if(!finite(value)){open=false;return;}
    const x=50+i*730/Math.max(vals.length-1,1), y=195-(value-lo)*170/(hi-lo);
    path+=(open?'L':'M')+x+' '+y+' ';open=true;
  });
  el('line').setAttribute('d',path);
  el('ymin').textContent=lo.toFixed(1);el('ymax').textContent=hi.toFixed(1);
  el('range').textContent=`${valid.length} lecturas recientes${demo?' · Datos de demostración':''}`;
}
function buttons() {
  const s=last?.telemetry?.status||{};
  const ready=last?.available && last.age_seconds<=15 && s.state==='LISTO' && s.actions_allowed!==false;
  el('serveFood').disabled=!!pending||!ready||!s.calibrated||!s.hx_ok||!s.servo_enabled||!!s.food_active;
  el('serveWater').disabled=!!pending||!ready||!el('supervised').checked||!!s.food_active||Date.now()<waterLock;
  const autoOn=s.auto_serve_enabled===true&&last?.automation_armed===true;
  const autoCanDisable=last?.available&&last.age_seconds<=15&&s.actions_allowed!==false;
  const autoCanEnable=ready&&s.auto_serve_available===true;
  el('toggleAuto').disabled=!!pending||!(autoOn?autoCanDisable:autoCanEnable);
  el('toggleAuto').textContent=autoOn?'Deshabilitar automático':'Habilitar automático';
  el('automationStatus').textContent=!last?.available?'Sin conexión. El modo queda desarmado.':autoOn?'Armado y confirmado por el ESP32; detecciones confirmadas pueden servir comida y agua.':'Desarmado. La cámara solo informa detecciones y no activa salidas.';
  el('resetDemo').disabled=!!pending;
  el('testBuzzer').disabled=!!pending||!ready||!s.buzzer_enabled;
  el('openGate').disabled=!!pending||!ready||!s.servo_manual_enabled||!!s.food_active||!s.hx_ok||!s.calibrated;
  const canClose=last?.available && last.age_seconds<=15 && ['LISTO','COMPUERTA_ABIERTA','COMPUERTA_CERRANDO'].includes(s.state) && s.actions_allowed!==false;
  el('closeGate').disabled=!!pending||!canClose||!s.servo_manual_enabled;
  el('gateStatus').textContent=!last?.available?'Esperando conexión.':!s.servo_manual_enabled?'Esperando firmware con control manual.':s.manual_food_active?'Abierta: se cerrará al llegar a 300 g. Puedes cerrar antes.':s.gate_command==='cerrar'?'Última orden: cerrar.':'Apertura manual con cierre automático a 300 g.';
  el('foodProgress').textContent = !last?.available ? 'Esperando una lectura reciente de la pesa.' : !s.servo_enabled ? 'Servido automático pendiente. Puedes usar los botones manuales.' : s.food_result || 'Listo para completar su plato.';
  el('waterReason').textContent = !last?.available ? 'Esperando conexión con la estación.' : s.food_active ? 'Primero debe terminar el alimento.' : s.state==='BOMBA_ACTIVA' ? 'Sirviendo. Se apagará al terminar el pulso.' : Date.now()<waterLock ? 'Espera unos segundos antes del siguiente servido.' : !el('supervised').checked ? 'Confirma el depósito antes de servir.' : 'Listo para servir durante 5 segundos.';
}
function render(data) {
  last=data;const s=data.telemetry?.status||{};
  el('connection').dataset.state = data.available ? (demo||data.telemetry?.simulated?'demo':'online') : 'offline';
  el('connectionLabel').textContent = data.available ? (demo||data.telemetry?.simulated?'Modo demostración':'Estación conectada') : 'Sin conexión';
  el('status').textContent=data.available?`${demo?'Datos de ejemplo':'Última lectura'} · ${data.age_seconds??0} s`:'Esperando datos recientes de la estación.';
  el('weight').textContent = data.available ? (s.calibrated ? number(s.weight_g,'g'):'Sin calibrar') : '—';
  el('foodMeter').value = data.available && s.calibrated && finite(s.weight_g) ? Math.max(0,Math.min(300,s.weight_g)):0;
  el('foodMeter').setAttribute('aria-valuetext',data.available&&finite(s.weight_g)?`${s.weight_g.toFixed(1)} de 300 gramos`:'Sin lectura reciente');
  el('temp').textContent=data.available?number(s.temperature_c,'°C'):'—';
  el('humidity').textContent=data.available?number(s.humidity_pct,'%'):'—';
  el('pir').textContent=data.available&&typeof s.pir==='boolean'?(s.pir?'Hay movimiento':'Sin movimiento'):'Sin lectura';
  el('water').textContent=typeof s.water_available==='boolean'?(s.water_available?'Agua disponible':'Nivel bajo'):'Nivel no medido';
  el('fsm').textContent=!data.available?'Sin conexión':s.food_active?'Completando su plato':states[s.state]||s.state||'Sin datos';
  el('vision').textContent=demo?'Detección pendiente en la demo':data.vision?.available?(data.vision.dog_detected?'Perro detectado':'Sin perro detectado'):'Sin imagen reciente';
  const cloud=data.firebase||{};
  el('cloud').textContent=demo?'Sin envíos durante la demo':cloud.status==='desactivado'?'Sin configurar':cloud.status||'Sin información';
  el('events').replaceChildren();
  const events=(data.events||[]).slice(-6).reverse();
  if(!events.length){const li=document.createElement('li');li.className='empty-event';li.textContent='Todavía no hay actividad. Aquí aparecerán las órdenes confirmadas.';el('events').append(li);}
  events.forEach(event=>{
    const li=document.createElement('li'), title=document.createElement('strong'),body=document.createElement('span');
    title.textContent=actionNames[event.action||event.id]||'Estación PetCare';
    body.textContent=event.message||event.estado||'Orden registrada';
    li.append(title,body);el('events').append(li);
  });
  el('waterLog').textContent=demo?'El historial de esta demo es temporal.':`${data.water_log?.total_events||0} registros de agua · ${data.water_log?.pending_cloud||0} por sincronizar`;
  chart(data.history||[]);buttons();cameraState();
}
function feedback(message,failed=false) {
  el('commandResult').hidden=false;
  el('commandResult').dataset.error=String(failed);
  el('commandResult').textContent=message;
}
async function command(action) {
  if(pending&&!['stop_water','stop_food'].includes(action))return;
  pending++;buttons();
  const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),5000);
  try {
    const r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-PetCare-Token':last?.command_token||''},body:JSON.stringify({action,supervised:el('supervised').checked}),signal:abort.signal});
    const d=await r.json();feedback(d.message||'Orden recibida',!r.ok||!d.ok);
    if(r.ok&&d.ok&&action==='water'){waterLock=Date.now()+15000;el('supervised').checked=false;}
    if(r.ok&&d.ok&&action==='reset_demo'){waterLock=0;el('supervised').checked=false;}
  } catch {feedback('No se pudo confirmar la orden. Revisa la estación antes de repetirla.',true);}
  finally {clearTimeout(timeout);pending--;buttons();await refresh();}
}
for(const [id,action] of Object.entries({testBuzzer:'tone',closeGate:'gate_close',serveFood:'feed',serveWater:'water',stopFood:'stop_food',stopWater:'stop_water'}))el(id).addEventListener('click',()=>command(action));
el('toggleAuto').addEventListener('click',()=>command(last?.telemetry?.status?.auto_serve_enabled&&last?.automation_armed?'auto_disable':'auto_enable'));
el('openGate').addEventListener('click',()=>command('gate_open'));
el('supervised').addEventListener('change',buttons);
el('metric').addEventListener('change',()=>chart(last?.history||[]));
async function refresh() {
  if(refreshing)return;refreshing=true;
  const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),4000);
  try {const r=await fetch('/api/state',{cache:'no-store',signal:abort.signal});if(!r.ok)throw Error();render(await r.json());}
  catch {
    if(last){last.available=false;render(last);}
    else {el('connectionLabel').textContent='Sin conexión';el('status').textContent='No hay conexión con el servidor de la estación.';buttons();cameraState();}
  } finally {clearTimeout(timeout);refreshing=false;}
}
refresh();setInterval(refresh,1000);
