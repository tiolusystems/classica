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
$('download-form').addEventListener('submit',async event=>{event.preventDefault();const urls=$('urls').value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);if(!urls.length){toast('Cole pelo menos um link de vídeo.',true);return;}const submit=$('submit-button');submit.disabled=true;try{const isVideo=document.querySelector('input[name="kind"]:checked').value==='video';const format=document.querySelector(isVideo?'input[name="video-format"]:checked':'input[name="format"]:checked').value;const r=await api('enqueue',{urls,format,authorized:true,resolution:isVideo?$('resolution').value:'best'});$('urls').value='';$('link-preview').hidden=true;toast(`${r.added} ${r.added===1?'download adicionado':'downloads adicionados'} à fila.${r.skipped?' '+r.skipped+' já estavam na fila.':''}`);await refresh();}catch(error){toast(error.message,true);}finally{submit.disabled=false;}});
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
  $('install-app').hidden=!!m.installed;
  $('install-app').disabled=!desktop||busy||pending>0||previewBusy;
  $('apply-update').hidden=!m.update_available;
  $('apply-update').disabled=!desktop||busy||pending>0||previewBusy;
  $('rollback-app').hidden=!m.can_rollback;
  $('rollback-app').disabled=!desktop||busy||pending>0||previewBusy;
  $('maintenance-status').textContent=m.message||(m.latest_version?(m.update_available?'Nova versão disponível: '+m.latest_version+'.':'Você está na versão mais recente disponível.'):(m.installed?'Instalada neste computador.':'Versão portátil. A instalação é opcional.'));
  if(!busy&&!desktop)$('maintenance-status').textContent+=' Para instalar ou atualizar, abra pelo executável Clássica.';
  else if(!busy&&pending)$('maintenance-status').textContent+=' Conclua ou cancele os downloads pendentes antes de continuar.';
}
$('check-update').addEventListener('click',async()=>{
  checkingUpdate=true;renderMaintenance(snapshot.jobs.filter(j=>!terminal.has(j.status)).length);
  try{await api('update/check',{});await refresh();}catch(error){$('maintenance-status').textContent=error.message;toast(error.message,true);}
  finally{checkingUpdate=false;$('check-update').disabled=!!snapshot?.maintenance?.busy;}
});
for(const [id,kind,label] of [['install-app','install','Instalar no seu perfil e criar atalhos'],['apply-update','update','Preparar e abrir a nova versão'],['rollback-app','rollback','Preparar e abrir a versão anterior']]){
  $(id).addEventListener('click',async()=>{
    if(!confirm(label+'? A preparação usa internet e espaço em disco. Ao concluir, a aplicação será reaberta. Histórico, preferências e arquivos baixados serão preservados.'))return;
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
