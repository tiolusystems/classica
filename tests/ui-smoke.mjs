import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {chromium} from 'playwright';

const directory=await mkdtemp(path.join(tmpdir(),'classica-ui-'));
const fixture=`import app, pathlib, sys
m=app.Manager(pathlib.Path(sys.argv[1]),start_worker=False)
m.set_folder(str(pathlib.Path(sys.argv[1])/'downloads'))
app.dependencies=lambda: dict(yt_dlp=True,ffmpeg=True,ffprobe=True,deno=True)
m.queue_pause=dict(until=0,manual=True,reason='Pausa de teste HTTP 429')
m.enqueue(['https://www.youtube.com/watch?v=BaW_jenozKc'],'original',True)
m.jobs[-1]['status']='done'
m.jobs[-1]['title']='Faixa concluída de teste'
m.save()
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
  await page.getByRole('button',{name:'Retomar fila',exact:true}).click();
  await page.locator('#queue-warning').waitFor({state:'hidden'});
  assert.equal(await page.locator('#use-edge-session').count(),0,'Sem controle de cookies na interface');
  await page.getByRole('button',{name:'Ler condições de uso'}).click();
  const terms=page.getByRole('dialog',{name:'Uso responsável da Clássica'});
  await terms.waitFor();
  assert.equal(await terms.getByText('A ferramenta não verifica licenças ou permissões automaticamente.',{exact:false}).count(),1);
  await page.getByRole('button',{name:'Entendi'}).click();
  assert.equal(await terms.isVisible(),false);
  assert.equal(await page.getByRole('button',{name:'Limpar concluídos'}).isEnabled(),true);
  await page.locator('.kind-choice').getByText('Vídeo com áudio',{exact:true}).click();
  assert.equal(await page.locator('#video-options').isVisible(),true);
  assert.equal(await page.locator('#audio-options').isVisible(),false);
  await page.locator('#resolution').selectOption('720');
  await page.locator('#urls').fill('https://www.youtube.com/watch?v=BaW_jenozKc');
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
  page.once('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'Limpar concluídos',exact:true}).click();
  await page.getByText('Faixa concluída de teste').waitFor({state:'detached'});
  await page.getByText('Cancelado',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Limpar concluídos',exact:true}).isDisabled(),true);
  for(const width of [320,768,1366,1920]){
    await page.setViewportSize({width,height:900});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,`Horizontal overflow at ${width}px`);
  }
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
  await page.getByRole('button',{name:'Ajuda',exact:true}).click();
  await page.getByRole('dialog',{name:'Como usar a Clássica'}).waitFor();
  await page.keyboard.press('Escape');
  assert.deepEqual(errors,[],'JavaScript runtime errors');
  console.log('UI smoke OK: sem seletor Edge, fila e retry sem cookies, audio/video, API local, cancelamento, 4 larguras, leitura 200%, persistencia e ajuda.');
} finally {
  if(browser)await browser.close();
  server.kill();
  await new Promise(resolve=>{if(server.exitCode!==null)resolve();else{server.once('exit',resolve);setTimeout(resolve,3000);}});
  await rm(directory,{recursive:true,force:true});
}
