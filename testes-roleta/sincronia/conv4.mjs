import { chromium, EXE, BASE, abrirMaquina, retrato, iguais, log, ok, contaFalhas, esperar } from './lib-maquina.mjs';
const b = await chromium.launch({headless:true, executablePath:EXE});

log('== J. MARATONA: 3 TURNOS, 3 MAQUINAS, A ROLETA ABERTA O TEMPO TODO ==');
// a roleta da transmissao fica aberta a noite inteira
const cxL = await b.newContext({viewport:{width:1280,height:800}});
const L = await cxL.newPage();
L.on('pageerror', e => { log('   [erro na roleta]', e.message); });
await L.goto(BASE+'/',{waitUntil:'networkidle'}); await esperar(5000);

const feitos = [];
for (const [i, nome] of [[0,'turno 1'],[1,'turno 2'],[2,'turno 3']]){
  const M = await abrirMaquina(b,{nome, semear:(i===0)});
  const antes = await retrato(M);
  log(`   ${nome} assumiu vendo ${antes.experts.length} experts, ${antes.sorteados.length} sorteados`);
  if (i > 0){
    // o que o turno anterior fez tem de estar aqui
    const esperado = feitos[i-1];
    ok(`${nome} vê o que o turno anterior fez`, antes.experts.some(e => e.nome === esperado));
  }
  // cada turno faz a sua alteracao
  const marca = "turno " + (i+1) + " mexeu";
  await M.p.evaluate(([idx, marca])=>{ const e=experts[Math.min(idx+2, experts.length-1)]; e.name = marca; persistExperts(e); }, [i, marca]);
  feitos.push(marca);
  await esperar(5000);
  const naRoleta = await L.evaluate(m=>experts.some(e=>e.name===m), marca);
  ok(`${nome}: a alteracao chega na roleta da transmissao`, naRoleta);
  await M.cx.close();                       // fim do turno: fecha o computador
  log(`   ${nome} fechou`);
  await esperar(4000);                      // NINGUEM no painel entre os turnos
}

log('\n   -- conferencia final --');
const F = await abrirMaquina(b,{nome:'conferencia'});
await esperar(4000);
const rF = await retrato(F);
const rL = await L.evaluate(()=>({
  experts: experts.map(e=>({id:e.id,nome:e.name,ativo:!!e.active,min:e.minutes||null})).sort((a,b)=>a.id<b.id?-1:1),
  sorteados: [...sorteados].sort(), tumbas: Object.keys(tumbas).sort(), cfgMin: cfg.minutes }));
ok('as tres alteracoes sobreviveram aos tres turnos', feitos.every(m => rF.experts.some(e=>e.nome===m)));
ok('painel e roleta terminam com exatamente o mesmo estado', iguais(rF, rL));
if(!iguais(rF,rL)){
  const dif = rF.experts.filter((e,i)=>JSON.stringify(e)!==JSON.stringify(rL.experts[i]));
  log('   diferenca:', JSON.stringify(dif.slice(0,3)));
}
log('\n===== ' + (contaFalhas()? contaFalhas()+' FALHA(S)' : 'TUDO VERDE') + ' =====');
await b.close(); process.exit(contaFalhas()?1:0);
