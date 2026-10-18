import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,rm,mkdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {chromium} from 'playwright';

const directory=await mkdtemp(path.join(tmpdir(),'classica-ui-'));
const fixture=`import app, pathlib, sys
m=app.Manager(pathlib.Path(sys.argv[1]),start_worker=False)
m.set_folder(str(pathlib.Path(sys.argv[1])/'downloads'))
app.dependencies=lambda: dict(yt_dlp=True,ffmpeg=True,ffprobe=True,deno=True)
m.preview.inspect=lambda url: dict(title='Paganini <img src=x onerror=alert(1)>',channel='Acervo',duration=285,resolutions=[720,1080],source_formats=['M4A','MP4'],live=False)
m.queue_pause=dict(until=0,manual=True,reason='Pausa de teste HTTP 429')
s=app.create_server(m)
print('READY:'+str(s.server_port),flush=True)
s.serve_forever()
`;
const server=spawn(process.env.PYTHON||'python3',['-u','-c',fixture,directory],{stdio:['ignore','pipe','pipe']});
let browser;
try {
  const port=await new Promise((resolve,reject)=>{
    let output='';const timer=setTimeout(()=>reject(new Error('UI fixture startup timeout')),15000);
    server.stdout.on('data',data=>{output+=data.toString();const match=output.match(/READY:(\d+)/);if(match){clearTimeout(timer);resolve(Number(match[1]));}});
    server.once('error',reject);server.once('exit',code=>reject(new Error('UI fixture exited: '+code)));
  });
  browser=await chromium.launch();
  const page=await browser.newPage();
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`http://127.0.0.1:${port}`);
  await page.getByText('Conexão local',{exact:true}).waitFor();
  await page.keyboard.press('Tab');
  assert.equal(await page.locator('.skip-link').evaluate(node=>node===document.activeElement&&getComputedStyle(node).opacity==='1'),true,'Keyboard skip link is visible on focus');
  await page.keyboard.press('Enter');
  assert.equal(await page.locator('#main').evaluate(node=>node===document.activeElement),true,'Skip link focuses main content');
  await page.getByRole('button',{name:'Retomar fila',exact:true}).click();
  await page.locator('#queue-warning').waitFor({state:'hidden'});
  assert.equal(await page.locator('#use-edge-session').count(),0,'Sem controle de cookies na interface');
  await page.locator('.kind-choice').getByText('Vídeo com áudio',{exact:true}).click();
  assert.equal(await page.locator('#video-options').isVisible(),true);
  assert.equal(await page.locator('#audio-options').isVisible(),false);
  await page.locator('#resolution').selectOption('720');
  await page.locator('#urls').fill('https://www.youtube.com/watch?v=BaW_jenozKc');
  await page.getByRole('button',{name:'Ver detalhes do link',exact:true}).click();
  await page.locator('#link-preview').waitFor();
  assert.match(await page.locator('#preview-title').textContent(),/Paganini <img/);
  assert.equal(await page.locator('#link-preview img').count(),0,'Metadata rendered as text');
  assert.match(await page.locator('#preview-meta').textContent(),/04:45/);
  await page.getByRole('button',{name:'Baixar vídeo',exact:true}).click();
  await page.getByText('Vídeo · MP4',{exact:true}).waitFor();
  await page.getByText('Até 720p',{exact:true}).waitFor();
  assert.equal(await page.evaluate(async()=>{const r=await fetch('/api/state',{headers:{'X-Classica-Token':document.querySelector('meta[name="classica-token"]').content}});return Object.hasOwn((await r.json()).jobs[0],'use_edge_session');}),false);
  await page.getByRole('button',{name:'Cancelar',exact:true}).click();
  await page.getByText('Cancelado',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Tentar novamente',exact:true}).click();
  await page.getByText('Na fila',{exact:true}).waitFor();
  assert.equal(await page.evaluate(async()=>{const r=await fetch('/api/state',{headers:{'X-Classica-Token':document.querySelector('meta[name="classica-token"]').content}});return Object.hasOwn((await r.json()).jobs[0],'use_edge_session');}),false);
  await page.getByRole('button',{name:'Cancelar',exact:true}).click();
  await page.getByText('Cancelado',{exact:true}).waitFor();
  for(const width of [320,768,1366,1920]){
    await page.setViewportSize({width,height:900});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,`Horizontal overflow at ${width}px`);
  }
  await page.setViewportSize({width:1366,height:900});
  const presentation=await page.evaluate(()=>{
    const selectors=['.app-header','.panel','.brand-symbol','.toast','#settings-dialog'];
    return {
      shadows:selectors.map(selector=>getComputedStyle(document.querySelector(selector)).boxShadow),
      emblemColor:getComputedStyle(document.querySelector('.brand-symbol')).color,
      panelMarker:getComputedStyle(document.querySelector('.panel')).borderTopColor,
      pageBackground:getComputedStyle(document.body).backgroundColor
    };
  });
  assert.deepEqual(presentation.shadows,Array(5).fill('none'),'Flat design without shadows');
  assert.equal(presentation.emblemColor,'rgb(236, 213, 166)','Warm gold preserves Chi-Rho on dark tile');
  assert.equal(presentation.panelMarker,'rgb(215, 196, 156)','Muted gold used only for ornamental separators');
  assert.equal(presentation.pageBackground,'rgb(246, 242, 233)','Comfortable and light canvas');
  await page.locator('#toast').evaluate(node=>node.hidden=true);
  await page.locator(':focus').evaluateAll(nodes=>nodes.forEach(node=>node.blur()));
  await mkdir('output/ui',{recursive:true});
  await page.screenshot({path:'output/ui/classica-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'output/ui/classica-small.png',fullPage:true});
  await page.setViewportSize({width:1366,height:900});
  await page.getByRole('button',{name:'Preferências',exact:true}).click();
  await page.locator('#font-size').evaluate(input=>{input.value='200';input.dispatchEvent(new Event('input',{bubbles:true}));});
  assert.equal(await page.locator('#font-size-label').textContent(),'200%');
  await page.getByRole('button',{name:'Fechar',exact:true}).click();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,'Overflow with 200% text');
  await page.reload();
  await page.getByText('Conexão local',{exact:true}).waitFor();
  assert.equal(await page.locator('#use-edge-session').count(),0,'Controle de cookies continua ausente ao recarregar');
  assert.equal(await page.evaluate(()=>localStorage.getItem('classica-reading')),'200');
  assert.equal(await page.getByRole('button',{name:'Limpar biblioteca',exact:true}).count(),1);
  assert.equal(await page.getByRole('button',{name:'Limpar biblioteca',exact:true}).isEnabled(),true);
  page.once('dialog',dialog=>dialog.dismiss());
  await page.getByRole('button',{name:'Limpar biblioteca',exact:true}).click();
  assert.equal(await page.getByText('Cancelado',{exact:true}).count(),1,'Canceling clear prompt must preserve history');
  await page.getByRole('button',{name:'Entenda as responsabilidades',exact:true}).click();
  assert.equal(await page.getByRole('dialog',{name:'Como usar a Clássica'}).isVisible(),true);
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Ajuda',exact:true}).click();
  await page.getByRole('dialog',{name:'Como usar a Clássica'}).waitFor();
  assert.equal(await page.locator('#install-app').isEnabled(),false,'No desktop controller in Python fixture');
  await page.getByRole('button',{name:'Copiar relatório de diagnóstico',exact:true}).click();
  await page.locator('#support-report').waitFor();
  const report=await page.locator('#support-report').inputValue();
  assert.match(report,/Clássica 2.2.0/);
  assert.ok(!report.includes('BaW_jenozKc')&&!report.includes(directory));
  await page.screenshot({path:'output/ui/classica-help-200.png',fullPage:true});
  await page.keyboard.press('Escape');
  assert.deepEqual(errors,[],'JavaScript runtime errors');
  console.log('UI smoke OK: sem seletor Edge, fila e retry sem cookies, audio/video, API local, cancelamento, 4 larguras, leitura 200%, persistencia e ajuda.');
} finally {
  if(browser)await browser.close();
  server.kill();
  await new Promise(resolve=>{if(server.exitCode!==null)resolve();else{server.once('exit',resolve);setTimeout(resolve,3000);}});
  await rm(directory,{recursive:true,force:true});
}
