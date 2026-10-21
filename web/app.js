'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="classica-token"]').content;
const states = {queued:'Na fila',preparing:'Consultando vídeo…',downloading:'Baixando',converting:'Preparando arquivo…',done:'Concluído',error:'Falha no download',cancelled:'Cancelado',interrupted:'Sessão interrompida'};
const terminal = new Set(['done','error','cancelled','interrupted']);
const active = new Set(['preparing','downloading','converting']);
let snapshot = null, signature = '', timer, stopped = false, failures = 0;
function toast(text, error=false) { clearTimeout(timer); $('toast').textContent=text; $('toast').classList.toggle('error', error); $('toast').hidden=false; timer=setTimeout(()=>$('toast').hidden=true,6500); }
async function api(path, data) {
  const response = await fetch('/api/'+path,{method:data===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-Classica-Token':token},body:data===undefined?undefined:JSON.stringify(data)});
  const result = await response.json();
  if(!response.ok) throw new Error(result.error || 'Não foi possível concluir esta operação.');
  return result;
}
function el(tag, cls, text) { const n=document.createElement(tag); if(cls)n.className=cls; if(text!==undefined)n.textContent=text; return n; }
async function action(name, data={}) { try { await api(name,data); await refresh(); } catch(error) { toast(error.message,true); } }
function button(text, fn) { const b=el('button','',text); b.type='button'; b.addEventListener('click',fn); return b; }
function render() {
  if(!snapshot)return;
  const all=snapshot.jobs, completed=all.filter(j=>j.status==='done').length, running=all.filter(j=>!terminal.has(j.status)).length;
  $('folder-label').textContent=snapshot.folder; $('folder-button').title=snapshot.folder+' · alterar pasta';
  $('summary').textContent=all.length?`${completed} ${completed===1?'arquivo salvo':'arquivos salvos'}${running?' · '+running+' na fila ou em andamento':''}`:'Nenhum download por enquanto.';
  const missing=Object.entries(snapshot.dependencies).filter(([,v])=>!v).map(([k])=>k);
  $('dependency-warning').hidden=!missing.length;
  if(missing.length)$('dependency-warning').textContent='Componentes ausentes: '+missing.join(', ')+'. Feche a aplicação e execute Iniciar.bat para preparar o ambiente.';
  const pause=snapshot.queue_pause||{}, remaining=Math.max(0,Math.ceil(((pause.until||0)*1000-Date.now())/1000));
  $('queue-warning').hidden=!pause.manual&&!remaining;
  $('queue-warning-text').textContent=(pause.reason||'')+(remaining?' Aguarde '+remaining+' segundos.':'')+(pause.manual?' Retome quando desejar fazer uma nova tentativa.':' A fila retomará automaticamente após a pausa.');
  $('resume-queue').hidden=!pause.manual;$('resume-queue').disabled=remaining>0;
  renderMaintenance(running);
  const filter=$('filter').value;
  const list=[...all].reverse().filter(j=>filter==='all'||(filter==='active'&&!terminal.has(j.status))||(filter==='done'&&j.status==='done')||(filter==='error'&&['error','interrupted','cancelled'].includes(j.status)));
  const sig=JSON.stringify([filter,list]);
  if(signature===sig)return;
  signature=sig;
  const openDetails=new Set([...$('jobs').querySelectorAll('details[open]')].map(d=>d.dataset.id));
  const focused=document.activeElement, focusedJob=focused?.closest('.job')?.dataset.id, focusedText=focused?.textContent;
  $('jobs').replaceChildren(); $('empty').hidden=!!list.length;
  $('empty').querySelector('h3').textContent=all.length?'Nenhum download neste filtro.':'Seu acervo começa com um link.';
  $('empty').querySelector('p').textContent=all.length?'Escolha outro filtro para consultar sua coleção.':'Adicione um link para salvar o áudio ou o vídeo completo.';
  for(const job of list) {
    const row=el('article','job'); row.dataset.id=job.id;
    const isVideo=['mp4','mkv','webm'].includes(job.format);
    row.append(el('div','job-icon',isVideo?'▸':job.status==='done'?'♫':'♩'));
    const main=el('div','job-main'); main.append(el('h3','job-title',job.title));
    const meta=el('div','job-meta');
    meta.append(el('span','',job.format==='original'?'Áudio original':(isVideo?'Vídeo · ':'')+job.format.toUpperCase()));
    if(isVideo)meta.append(el('span','',job.resolution&&job.resolution!=='best'?'Até '+job.resolution+'p':'Melhor disponível'));
    let status=states[job.status]||job.status;
    if(job.status==='downloading')status+=' · '+Math.floor(job.progress)+'%';
    meta.append(el('span','job-status '+job.status,status));
    if(job.speed)meta.append(el('span','',job.speed));
    if(job.eta)meta.append(el('span','','restam '+job.eta));
    const source=el('a','','Ver no YouTube ↗'); source.href=job.url; source.target='_blank'; source.rel='noopener noreferrer'; meta.append(source);
    main.append(meta);
    if(active.has(job.status)) { const bar=el('div','progress'+(job.status==='preparing'||job.status==='converting'?' indeterminate':'')); bar.setAttribute('role','progressbar'); bar.setAttribute('aria-label','Progresso do download'); bar.setAttribute('aria-valuemin','0'); bar.setAttribute('aria-valuemax','100'); const fill=el('span'); if(job.status==='downloading'){fill.style.width=job.progress+'%';bar.setAttribute('aria-valuenow',String(Math.floor(job.progress)));}bar.append(fill);main.append(bar); }
    if(job.error){const advice=job.diagnosis;main.append(el('p','job-error',advice?advice.summary+' '+advice.action:job.error));}
    if(job.status==='done'&&job.file)main.append(el('p','hint',job.file.split(/[\\/]/).pop()));
    if(job.log&&['error','interrupted'].includes(job.status)) {const details=el('details');details.dataset.id=job.id;details.open=openDetails.has(job.id);details.append(el('summary','','Detalhes técnicos'),el('pre','',job.log));main.append(details);}
    row.append(main);
    const actions=el('div','job-actions');
    if(!terminal.has(job.status))actions.append(button('Cancelar',()=>action('cancel',{id:job.id})));
    if(['error','interrupted','cancelled'].includes(job.status))actions.append(button('Tentar novamente',()=>action('retry',{id:job.id})));
    if(job.status==='done') {const a=el('a','','Salvar cópia ↓');a.href='/file/'+job.id;a.download='';actions.append(a);}
    main.append(actions);$('jobs').append(row);
  }
  if(focusedJob){const row=[...$('jobs').children].find(r=>r.dataset.id===focusedJob);const next=row&&[...row.querySelectorAll('button,a,summary')].find(n=>n.textContent===focusedText);next?.focus({preventScroll:true});}
  $('clear-button').disabled=!all.some(j=>terminal.has(j.status));
}
async function refresh() { if(stopped)return; try{snapshot=await api('state');failures=0;$('connection-text').textContent='Conexão local';$('connection-text').parentElement.classList.remove('offline');render();}catch(error){failures++;if(failures>=3){$('connection-text').textContent='Sem conexão';$('connection-text').parentElement.classList.add('offline');}if(failures===3)toast(snapshot?.maintenance?.busy?'A versão preparada está sendo aberta. Você pode fechar esta aba quando a nova janela aparecer.':'Conexão local perdida. Abra a Clássica pelo ícone perto do relógio.',!snapshot?.maintenance?.busy);} }
$('download-form').addEventListener('submit',async event=>{event.preventDefault();const urls=$('urls').value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);if(!urls.length){toast('Cole pelo menos um link de vídeo.',true);return;}const submit=$('submit-button');submit.disabled=true;try{const isVideo=document.querySelector('input[name="kind"]:checked').value==='video';const format=document.querySelector(isVideo?'input[name="video-format"]:checked':'input[name="format"]:checked').value;const r=await api('enqueue',{urls,format,authorized:$('yt-authorized').checked,resolution:isVideo?$('resolution').value:'best'});$('urls').value='';$('yt-authorized').checked=false;$('link-preview').hidden=true;toast(`${r.added} ${r.added===1?'download adicionado':'downloads adicionados'} à fila.${r.skipped?' '+r.skipped+' já estavam na fila.':''}`);await refresh();}catch(error){toast(error.message,true);}finally{submit.disabled=false;}});
function settings() {if(!snapshot)return;$('folder-input').value=snapshot.folder;$('settings-dialog').showModal();}
$('settings-button').addEventListener('click',settings);$('folder-button').addEventListener('click',settings);
$('settings-form').addEventListener('submit',async event=>{event.preventDefault();const submit=event.submitter;submit.disabled=true;try{await api('folder',{folder:$('folder-input').value});$('settings-dialog').close();toast('Pasta de destino atualizada.');await refresh();}catch(error){toast(error.message,true);}finally{submit.disabled=false;}});
$('open-folder-button').addEventListener('click',()=>action('open-folder'));
$('resume-queue').addEventListener('click',()=>action('resume'));
$('help-top-button').addEventListener('click',()=>$('help-dialog').showModal());
$('rights-details').addEventListener('click',()=>$('help-dialog').showModal());
for(const b of document.querySelectorAll('.close-dialog'))b.addEventListener('click',()=>b.closest('dialog').close());
$('filter').addEventListener('change',()=>{signature='';render();});
$('clear-button').addEventListener('click',()=>{if(confirm('Limpar da biblioteca os downloads concluídos, cancelados ou com falha? Os arquivos no computador NÃO serão apagados; itens na fila e em andamento continuam visíveis.'))action('clear');});
$('exit-button').addEventListener('click',async()=>{if(snapshot?.jobs.some(j=>!terminal.has(j.status))&&!confirm('Existem downloads pendentes. Encerrar a aplicação e interromper a fila?'))return;try{await api('shutdown',{});stopped=true;$('connection-text').textContent='Encerrada';$('connection-text').parentElement.classList.add('offline');toast('Aplicação encerrada. Você já pode fechar esta aba.');$('submit-button').disabled=true;$('exit-button').disabled=true;}catch(error){toast(error.message,true);}});
refresh();setInterval(refresh,1000);

function updateKind(){const video=document.querySelector('input[name="kind"]:checked').value==='video';$('audio-options').hidden=video;$('audio-hint').hidden=video;$('video-options').hidden=!video;$('video-hint').hidden=!video;$('download-button-text').textContent=video?'Baixar vídeo':'Baixar áudio';}
for(const input of document.querySelectorAll('input[name="kind"]'))input.addEventListener('change',updateKind);
updateKind();

function setReading(value) {
  const n=Math.max(100,Math.min(200,Number(value)||100));
  document.documentElement.style.setProperty('--font-scale',String(n/100));
  document.documentElement.dataset.reading=n>=160?'large':'normal';
  $('font-size').value=String(n);$('font-size-label').value=n+'%';
  try{localStorage.setItem('classica-reading',String(n));}catch{}
}
$('font-size').addEventListener('input',event=>setReading(event.target.value));
$('reset-reading').addEventListener('click',()=>setReading(100));
try{setReading(localStorage.getItem('classica-reading')||100);}catch{setReading(100);}

// Explicit consultations only: typing a link never contacts YouTube.
let previewBusy=false, checkingUpdate=false;
$('urls').addEventListener('input',()=>{$('link-preview').hidden=true;});
$('preview-button').addEventListener('click',async()=>{
  const urls=$('urls').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  if(urls.length!==1){toast('Para consultar os detalhes, deixe apenas um link no campo.',true);return;}
  previewBusy=true;$('preview-button').disabled=true;$('preview-button').textContent='Consultando detalhes…';
  try{
    const info=await api('preview',{url:urls[0]});
    if($('urls').value.trim()!==urls[0])return;
    $('preview-title').textContent=info.title||'Gravação sem título';
    const seconds=info.duration, duration=seconds===null?'Duração não informada':new Date(Math.min(seconds,359999)*1000).toISOString().slice(seconds>=3600?11:14,19);
    $('preview-meta').textContent=[info.channel,info.live?'Transmissão ao vivo':duration].filter(Boolean).join(' · ');
    $('preview-formats').textContent=(info.resolutions.length?'Imagem: '+info.resolutions.map(x=>x+'p').join(', ')+'. ':'')+(info.source_formats.length?'Formatos na fonte: '+info.source_formats.join(', ')+'. ':'')+'Os formatos de saída são escolhidos abaixo; a disponibilidade pode mudar.';
    $('link-preview').hidden=false;
  }catch(error){toast(error.message,true);}finally{previewBusy=false;$('preview-button').textContent='Ver detalhes do link';await refresh();}
});
function renderMaintenance(pending){
  const m=snapshot.maintenance||{}, desktop=snapshot.desktop_available, busy=!!m.busy;
  $('submit-button').disabled=busy;
  $('preview-button').disabled=busy||previewBusy;
  $('exit-button').disabled=busy;
  $('check-update').disabled=checkingUpdate||busy;
  $('install-app').hidden=false;
  $('install-app').textContent=m.installed?'Criar ou atualizar atalhos':'Instalar e criar atalhos';
  $('install-app').disabled=!desktop||busy||pending>0||previewBusy;
  $('apply-update').hidden=!m.update_available;
  $('apply-update').disabled=!desktop||busy||pending>0||previewBusy;
  $('rollback-app').hidden=!m.can_rollback;
  $('rollback-app').disabled=!desktop||busy||pending>0||previewBusy;
  $('maintenance-status').textContent=m.message||(m.latest_version?(m.update_available?'Nova versão disponível: '+m.latest_version+'.':'Você está na versão mais recente disponível.'):(m.installed?'Instalada neste computador.':'Versão portátil. Instalar e criar atalhos é opcional.'));
  if(!busy&&!desktop)$('maintenance-status').textContent+=' Para instalar ou atualizar, abra pelo executável Clássica.';
  else if(!busy&&pending)$('maintenance-status').textContent+=' Conclua ou cancele os downloads pendentes antes de continuar.';
}
$('check-update').addEventListener('click',async()=>{
  checkingUpdate=true;renderMaintenance(snapshot.jobs.filter(j=>!terminal.has(j.status)).length);
  try{await api('update/check',{});await refresh();}catch(error){$('maintenance-status').textContent=error.message;toast(error.message,true);}
  finally{checkingUpdate=false;$('check-update').disabled=!!snapshot?.maintenance?.busy;}
});
for(const [id,defaultKind,defaultLabel] of [['install-app','install','Instalar e criar atalhos'],['apply-update','update','Preparar e abrir a nova versão'],['rollback-app','rollback','Preparar e abrir a versão anterior']]){
  $(id).addEventListener('click',async()=>{
    const maintenance=snapshot.maintenance||{};
    const kind=id==='install-app'&&maintenance.installed?'shortcuts':defaultKind;
    const label=id==='install-app'&&maintenance.installed?'Criar ou atualizar atalhos':defaultLabel;
    const completion=kind==='shortcuts'?' Os atalhos serão criados ou atualizados sem reinstalar a aplicação.':' A aplicação será reaberta ao concluir.';
    if(!confirm(label+'? A preparação usa internet e espaço em disco.'+completion+' Histórico, preferências e arquivos baixados serão preservados.'))return;
    try{await api('update/prepare',{kind});await refresh();}catch(error){toast(error.message,true);}
  });
}
$('copy-report').addEventListener('click',async()=>{
  const b=$('copy-report');b.disabled=true;
  try{const r=await api('diagnostics');$('support-report').value=r.report;$('support-report').hidden=false;
    try{await navigator.clipboard.writeText(r.report);$('report-status').textContent='Relatório copiado. Você também pode revisá-lo abaixo.';}
    catch{$('support-report').focus();$('support-report').select();$('report-status').textContent='Selecione e copie o relatório abaixo (Ctrl+C).';}
  }catch(error){toast(error.message,true);}finally{b.disabled=false;}
});


// Clássica is now the shell: change tabs, not windows. The X process and
// history remain independent and communicate through a private loopback session.
let currentWorkspace='youtube', modulesPolling=false, embeddedRequested=false;
window.addEventListener('message',event=>{
  const frame=$('x-frame');
  // Only the exact X iframe and its loopback origin can adjust layout.
  if(!frame||event.source!==frame.contentWindow||!frame.src)return;
  let expected;
  try{expected=new URL(frame.src).origin;}catch{return;}
  if(event.origin!==expected || !expected.startsWith('http://127.0.0.1:'))return;
  const payload=event.data;
  if(!payload || payload.type!=='classica-x:height')return;
  const height=Number(payload.height);
  if(!Number.isFinite(height)||height<200||height>8000)return;
  frame.style.height=Math.ceil(height+16)+'px';
});
function selectWorkspace(name){
  if(!['youtube','x'].includes(name))return;
  currentWorkspace=name;
  for(const item of ['youtube','x']){
    const selected=item===name,button=$('tab-'+item);
    button.setAttribute('aria-selected',String(selected));
    button.tabIndex=selected?0:-1;
    $(item+'-workspace').hidden=!selected;
  }
  document.title=name==='x'?'Clássica · X':'Clássica · YouTube';
  if(name==='x')void refreshX();
}
for(const name of ['youtube','x']){
  $('tab-'+name).addEventListener('click',()=>selectWorkspace(name));
}
$('tab-youtube').parentElement.addEventListener('keydown',event=>{
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();
  const next=event.key==='Home'?'youtube':event.key==='End'?'x':currentWorkspace==='youtube'?'x':'youtube';
  $('tab-'+next).focus();
  selectWorkspace(next);
});
function supportsEmbedded(version){
  const parts=String(version||'0.0.0').split('.').map(Number);
  return parts.length===3 && parts.every(Number.isInteger) &&
    (parts[0]>1 || parts[0]===1 && (parts[1]>1 || parts[1]===1 && parts[2]>=1));
}
async function startEmbeddedX(){
  embeddedRequested=true;
  try{
    await api('modules/embed',{});
    $('x-status').textContent='Abrindo o módulo X nesta aba…';
  }catch(error){
    $('x-status').textContent=error.message;
    $('x-retry').hidden=false;
  }
}
async function refreshX(){
  if(currentWorkspace!=='x'||modulesPolling)return;
  modulesPolling=true;
  try{
    const state=await api('modules/status');
    const x=state.installed?.x||{};
    const embedded=state.embedded||{};
    const setup=$('x-module-setup'),frame=$('x-frame');
    const install=$('x-install'),retry=$('x-retry'),rollback=$('x-rollback');
    const canEmbed=x.available&&supportsEmbedded(x.version);
    install.hidden=canEmbed&&!state.busy;
    install.textContent=x.available?'Atualizar Clássica X':'Instalar Clássica X';
    install.disabled=!!state.busy;
    rollback.hidden=!x.can_rollback;
    retry.hidden=true;
    if(state.busy){
      setup.hidden=false;frame.hidden=true;
      $('x-status').textContent=state.message||'Instalando o módulo X…';
    }else if(!canEmbed){
      setup.hidden=false;frame.hidden=true;
      $('x-status').textContent=x.available?'O Clássica X instalado precisa ser atualizado para utilizar esta aba.':'Instale o Clássica X para baixar vídeos autorizados, sem abrir outras janelas.';
    }else if(embedded.status==='ready'&&embedded.url){
      if(frame.src!==embedded.url)frame.src=embedded.url;
      frame.hidden=false;setup.hidden=true;
    }else{
      setup.hidden=false;frame.hidden=true;
      $('x-status').textContent=embedded.status==='error'?(embedded.error||'Falha ao abrir o X.'):'Preparando a interface do X…';
      if(embedded.status==='error'){
        retry.hidden=false;
      }else if(embedded.status==='idle'&&!embeddedRequested){
        void startEmbeddedX();
      }
    }
  }catch(error){
    $('x-module-setup').hidden=false;
    $('x-frame').hidden=true;
    $('x-status').textContent=error.message||'Falha ao consultar módulo X.';
  }finally{modulesPolling=false;}
}
$('x-install').addEventListener('click',async()=>{
  if(!confirm('Instalar ou atualizar Clássica X de fonte oficial, sem alterar o YouTube?'))return;
  const b=$('x-install');b.disabled=true;
  try{
    const state=await api('modules/install',{module:'x'});
    embeddedRequested=false;
    $('x-status').textContent=state.message||'Preparando instalação…';
    void refreshX();
  }catch(error){$('x-status').textContent=error.message;toast(error.message,true);}
  finally{b.disabled=false;}
});
$('x-retry').addEventListener('click',async()=>{
  $('x-retry').hidden=true;
  embeddedRequested=false;
  await startEmbeddedX();
});
$('x-rollback').addEventListener('click',async()=>{
  if(!confirm('Voltar o X à versão anterior? O YouTube permanece intacto.'))return;
  try{await api('modules/rollback',{module:'x'});embeddedRequested=false;await refreshX();}
  catch(error){toast(error.message,true);}
});
setInterval(()=>{if(currentWorkspace==='x')void refreshX();},1200);
