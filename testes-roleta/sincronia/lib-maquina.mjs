import pkg from '/Users/victorgabryellferreiraqueiroz/.jarvis/design-engine/node_modules/playwright-core/index.js';
export const { chromium } = pkg;
export const EXE='/Users/victorgabryellferreiraqueiroz/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell';
export const BASE = process.env.BASE || 'http://localhost:8777/roleta-teste';
export const EMAIL='teste-roleta@visionxma.com', SENHA='teste-roleta-2026';
export let falhas = 0;
export const log=(...a)=>console.log(...a);
export const ok=(t,c)=>{ log((c?'  OK   ':'  FALHA')+' · '+t); if(!c) falhas++; };
export const contaFalhas = () => falhas;

/* Uma "maquina" = um contexto isolado do navegador, com o MESMO login.
   relogioOffsetMs simula computador com a hora errada. */
export async function abrirMaquina(b, {nome='maquina', relogioOffsetMs=0, semear=false}={}){
  const cx = await b.newContext({viewport:{width:1440,height:900}});
  if (relogioOffsetMs){
    await cx.addInitScript(off => {
      const real = Date.now;
      Date.now = () => real() + off;
      const RD = Date;
      window.Date = new Proxy(RD, { construct(t,a){ return a.length ? new t(...a) : new t(real()+off); } });
      window.Date.now = Date.now;
    }, relogioOffsetMs);
  }
  const p = await cx.newPage();
  p.on('pageerror', e => { log(`   [erro js em ${nome}]`, e.message); falhas++; });
  await p.goto(BASE+'/admin/',{waitUntil:'domcontentloaded'});
  await p.waitForTimeout(2500);
  if (await p.evaluate(()=>document.getElementById('loginOverlay').classList.contains('show'))){
    await p.fill('#loginEmail',EMAIL); await p.fill('#loginPass',SENHA);
    await p.click('.gate-btn:not(.gate-btn--local)');
    await p.waitForFunction(()=>!document.getElementById('loginOverlay').classList.contains('show'),{timeout:25000});
  }
  if (semear){ try { await p.waitForSelector('#cmodal.show',{timeout:9000}); await p.click('#cmOk'); } catch {} }
  await p.waitForTimeout(4500);
  return { nome, cx, p };
}
/* Retrato do que importa: se duas maquinas divergirem, isso muda. */
export const retrato = m => m.p.evaluate(()=>({
  experts: experts.map(e=>({id:e.id,nome:e.name,ativo:!!e.active,min:e.minutes||null})).sort((a,b)=>a.id<b.id?-1:1),
  sorteados: [...sorteados].sort(),
  tumbas: Object.keys(tumbas).sort(),
  cfgMin: cfg.minutes,
}));
export const iguais = (a,b) => JSON.stringify(a)===JSON.stringify(b);
export async function esperar(ms){ await new Promise(r=>setTimeout(r,ms)); }
