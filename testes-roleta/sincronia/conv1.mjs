import { chromium, EXE, abrirMaquina, retrato, iguais, log, ok, contaFalhas, esperar } from './lib-maquina.mjs';
const b = await chromium.launch({headless:true, executablePath:EXE});

log('== A. DUAS MAQUINAS, MESMO LOGIN, EDITANDO AO MESMO TEMPO ==');
const A = await abrirMaquina(b,{nome:'A', semear:true});
const B = await abrirMaquina(b,{nome:'B'});
await esperar(3000);
ok('as duas comecam iguais', iguais(await retrato(A), await retrato(B)));

// A renomeia o 1o; B renomeia o 3o — ao mesmo tempo
await Promise.all([
  A.p.evaluate(()=>{ const e=experts[0]; e.name = e.name + " [A]"; persistExperts(e); }),
  B.p.evaluate(()=>{ const e=experts[2]; e.name = e.name + " [B]"; persistExperts(e); }),
]);
await esperar(6000);
const rA = await retrato(A), rB = await retrato(B);
ok('edicoes simultaneas em experts diferentes convergem', iguais(rA,rB));
if (!iguais(rA,rB)){
  log('   A:', JSON.stringify(rA.experts.filter(e=>/\[A\]|\[B\]/.test(e.nome))));
  log('   B:', JSON.stringify(rB.experts.filter(e=>/\[A\]|\[B\]/.test(e.nome))));
}
ok('as duas edicoes sobreviveram', rA.experts.some(e=>/\[A\]/.test(e.nome)) && rA.experts.some(e=>/\[B\]/.test(e.nome)));

log('\n== B. AS DUAS EDITAM O MESMO EXPERT AO MESMO TEMPO ==');
const alvo = await A.p.evaluate(()=>experts[5].id);
await Promise.all([
  A.p.evaluate(id=>{ const e=experts.find(x=>x.id===id); e.minutes = 11; persistExperts(e); }, alvo),
  B.p.evaluate(id=>{ const e=experts.find(x=>x.id===id); e.minutes = 22; persistExperts(e); }, alvo),
]);
await esperar(7000);
const rA2 = await retrato(A), rB2 = await retrato(B);
const vA = rA2.experts.find(e=>e.id===alvo).min, vB = rB2.experts.find(e=>e.id===alvo).min;
log(`   A ve ${vA} min | B ve ${vB} min`);
ok('conflito no mesmo expert termina igual nos dois', vA===vB);

log('\n== C. UMA REMOVE ENQUANTO A OUTRA EDITA O MESMO ==');
const alvo2 = await A.p.evaluate(()=>experts[7].id);
await Promise.all([
  (async()=>{ await A.p.evaluate(id=>removerExpert(experts.find(x=>x.id===id)), alvo2);
              await A.p.waitForTimeout(500); await A.p.click('#cmOk'); })(),
  B.p.evaluate(id=>{ const e=experts.find(x=>x.id===id); if(e){ e.name = e.name+" [editado]"; persistExperts(e);} }, alvo2),
]);
await esperar(8000);
const rA3 = await retrato(A), rB3 = await retrato(B);
const temA = rA3.experts.some(e=>e.id===alvo2), temB = rB3.experts.some(e=>e.id===alvo2);
log(`   A ${temA?'tem':'nao tem'} | B ${temB?'tem':'nao tem'}`);
ok('remover x editar termina igual nos dois', temA===temB);
ok('estado inteiro identico depois do conflito', iguais(rA3,rB3));

log('\n===== ' + (contaFalhas()? contaFalhas()+' FALHA(S)' : 'TUDO VERDE') + ' =====');
await b.close(); process.exit(contaFalhas()?1:0);
