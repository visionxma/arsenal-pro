import { chromium, EXE, abrirMaquina, retrato, iguais, log, ok, contaFalhas, esperar } from './lib-maquina.mjs';
const b = await chromium.launch({headless:true, executablePath:EXE});
const DIA = 24*60*60*1000;

log('== D. MAQUINA COM A HORA ERRADA (2 dias adiantada) ==');
{
  const A = await abrirMaquina(b,{nome:'A', semear:true});
  const X = await abrirMaquina(b,{nome:'X(hora errada)', relogioOffsetMs: 2*DIA});
  await esperar(4000);
  // a maquina com hora errada edita
  await X.p.evaluate(()=>{ const e=experts[1]; e.name = e.name+" [X]"; persistExperts(e); });
  await esperar(5000);
  // agora a maquina com hora certa CORRIGE o mesmo expert
  const alvo = await A.p.evaluate(()=>experts[1].id);
  await A.p.evaluate(id=>{ const e=experts.find(x=>x.id===id); e.name = "Nome certo"; persistExperts(e); }, id=>id, alvo).catch(()=>{});
  await A.p.evaluate(id=>{ const e=experts.find(x=>x.id===id); e.name = "Nome certo"; persistExperts(e); }, alvo);
  await esperar(7000);
  const rA=await retrato(A), rX=await retrato(X);
  const nA=rA.experts.find(e=>e.id===alvo).nome, nX=rX.experts.find(e=>e.id===alvo).nome;
  log(`   A ve "${nA}" | X ve "${nX}"`);
  ok('a correcao de quem tem a hora certa vale nas duas', nA===nX && nA==='Nome certo');
  ok('estado inteiro igual', iguais(rA,rX));
  await A.cx.close(); await X.cx.close();
}

log('\n== E. UMA MAQUINA FICA SEM INTERNET, EDITA, E VOLTA ==');
{
  const A = await abrirMaquina(b,{nome:'A'});
  const B = await abrirMaquina(b,{nome:'B'});
  await esperar(3500);
  await B.cx.setOffline(true);
  log('   B ficou sem internet');
  await B.p.evaluate(()=>{ const e=experts[3]; e.name = e.name+" [offline]"; persistExperts(e); });
  await A.p.evaluate(()=>{ const e=experts[4]; e.name = e.name+" [online]"; persistExperts(e); });
  await esperar(4000);
  await B.cx.setOffline(false);
  log('   B voltou');
  await esperar(20000);   // tempo do pulso de reconciliacao
  const rA=await retrato(A), rB=await retrato(B);
  ok('as duas voltam iguais depois da queda', iguais(rA,rB));
  ok('a edicao feita offline nao se perdeu', rA.experts.some(e=>/offline/.test(e.nome)));
  ok('a edicao feita online continua', rA.experts.some(e=>/online/.test(e.nome)));
  if(!iguais(rA,rB)) log('   A:', JSON.stringify(rA.experts.filter(e=>/\[/.test(e.nome))), '\n   B:', JSON.stringify(rB.experts.filter(e=>/\[/.test(e.nome))));
  await A.cx.close(); await B.cx.close();
}

log('\n== F. TRES MAQUINAS EDITANDO AO MESMO TEMPO ==');
{
  const M = [];
  for (const n of ['M1','M2','M3']) M.push(await abrirMaquina(b,{nome:n}));
  await esperar(4000);
  await Promise.all(M.map((m,i)=> m.p.evaluate(i=>{ const e=experts[i]; e.minutes = 10*(i+1); persistExperts(e); }, i)));
  await esperar(9000);
  const r = await Promise.all(M.map(retrato));
  ok('as tres terminam identicas', iguais(r[0],r[1]) && iguais(r[1],r[2]));
  ok('as tres edicoes sobreviveram', [10,20,30].every(v => r[0].experts.some(e=>e.min===v)));
  for (const m of M) await m.cx.close();
}
log('\n===== ' + (contaFalhas()? contaFalhas()+' FALHA(S)' : 'TUDO VERDE') + ' =====');
await b.close(); process.exit(contaFalhas()?1:0);
