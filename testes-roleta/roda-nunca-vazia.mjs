/* Portao: a roda de um time nunca fica vazia (17/10/2026). So LE o banco; o canal
   ao vivo fica bloqueado em todos os cenarios. Uso: node roda-nunca-vazia.mjs [base]. Sai 1 se falhar. */
import { chromium } from "/Users/victorgabryellferreiraqueiroz/.jarvis/design-engine/node_modules/playwright/index.mjs";
const BASE = process.argv[2] || "https://safiriontradingbrasil.com/arsenal-pro/roleta/"; const URL = BASE + "?time=fechamento"; let falhou = 0;
const b = await chromium.launch();
async function cenario(nome, prep){
  const ctx = await b.newContext({ viewport:{width:1440,height:900} });
  /* nunca fala com o canal ao vivo: a roleta da live nao pode receber nada deste teste */
  await ctx.route("**/realtime/**", r => r.abort());
  const p = await ctx.newPage();
  const erros=[]; p.on("pageerror", e=>erros.push(e.message));
  await prep(ctx, p);
  await p.goto(URL, {waitUntil:"domcontentloaded"});
  const t0=Date.now(); let n=0;
  while (Date.now()-t0 < 15000){
    n = await p.evaluate(()=>document.querySelectorAll("#wheel .seg-item").length);
    if (n>0) break; await p.waitForTimeout(250);
  }
  if (!n || erros.length) falhou++;
  console.log(nome.padEnd(48), "fatias:", n, "em", ((Date.now()-t0)/1000).toFixed(1)+"s", erros.length? "ERROS: "+erros.join(" | "):"sem erro");
  await p.screenshot({path:(process.env.TMPDIR||"/tmp/")+"roda-"+nome.replace(/\W+/g,"-")+".png"});
  await ctx.close();
}
// A: navegador novo, as 2 primeiras leituras do banco falham
await cenario("A primeiras leituras do banco falham", async (ctx)=>{
  let falhas=0;
  await ctx.route("**/rest/v1/roleta_estado**", r => (falhas++ < 2) ? r.abort() : r.continue());
  await ctx.route("**/realtime/**", r => r.abort());
});
// B: copia local velha com todos DESATIVADOS e carimbo mais novo + lapides
await cenario("B copia local velha com todos desativados", async (ctx, p)=>{
  await ctx.route("**/realtime/**", r => r.abort());
  await ctx.addInitScript(()=>{
    if (sessionStorage.getItem("prep")) return; sessionStorage.setItem("prep","1");
    const agora = Date.now()+999999;
    const ex = ["fec1","fec2","fec3","fec5","fec6"].map((id,i)=>({id,name:["Miriele","Maciel","Tio Vitão","Julin","Adao"][i],active:false,minutes:null,updatedAt:agora}));
    localStorage.setItem("cj_experts_v6__fechamento", JSON.stringify(ex));
  });
});
// C: lapides locais para todos
await cenario("C lapides locais para todos", async (ctx)=>{
  await ctx.route("**/realtime/**", r => r.abort());
  await ctx.addInitScript(()=>{
    if (sessionStorage.getItem("prep")) return; sessionStorage.setItem("prep","1");
    const t={}; ["fec1","fec2","fec3","fec5","fec6"].forEach(id=>t[id]=Date.now()+999999);
    localStorage.setItem("cj_experts_tumbas_v1__fechamento", JSON.stringify(t));
  });
});
// D: normal
await cenario("D navegador novo normal", async ()=>{});
// E: roleta geral sem time continua igual
const ctx = await b.newContext(); await ctx.route("**/realtime/**", r => r.abort()); const p = await ctx.newPage();
await p.goto(BASE, {waitUntil:"domcontentloaded"}); await p.waitForTimeout(5000);
console.log("E roleta geral", await p.evaluate(()=>document.querySelectorAll("#wheel .seg-item").length), "fatias");
await b.close(); if (falhou) { console.log("FALHOU: roda vazia em", falhou, "cenario(s)"); process.exit(1); } console.log("OK: roda nunca vazia");
