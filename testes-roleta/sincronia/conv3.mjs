import { chromium, EXE, abrirMaquina, retrato, iguais, log, ok, contaFalhas, esperar } from './lib-maquina.mjs';
const b = await chromium.launch({headless:true, executablePath:EXE});

log('== G. MAQUINA QUE FICOU DIAS FORA VOLTA E EDITA ==');
{
  const A = await abrirMaquina(b,{nome:'A', semear:true});
  await esperar(2500);
  const velha = await A.cx.storageState();          // foto do estado de hoje
  // a operacao continua sem ela: varias mudancas
  await A.p.evaluate(()=>{ const e=experts[0]; e.name="Mudou 1"; persistExperts(e); });
  await esperar(2500);
  await A.p.evaluate(()=>{ const e=experts[1]; e.active=false; persistExperts(e); });
  await esperar(4000);
  const rDepois = await retrato(A);
  // agora a maquina velha volta, com o estado de antes
  const V = await abrirMaquina(b,{nome:'V(voltou)'});
  await V.cx.close();
  const cxV = await b.newContext({viewport:{width:1440,height:900}, storageState: velha});
  const pV = await cxV.newPage();
  await pV.goto(process.env.BASE || 'http://localhost:8777/roleta-teste'+'/admin/',{waitUntil:'domcontentloaded'}).catch(()=>{});
  await pV.goto((process.env.BASE || 'http://localhost:8777/roleta-teste')+'/admin/',{waitUntil:'domcontentloaded'});
  await pV.waitForTimeout(7000);
  const V2 = { nome:'V', cx:cxV, p:pV };
  const rV = await retrato(V2);
  ok('a maquina que voltou adota o que aconteceu sem ela', iguais(rV, rDepois));
  if(!iguais(rV,rDepois)) log('   voltou:', JSON.stringify(rV.experts.slice(0,2)), '\n   atual :', JSON.stringify(rDepois.experts.slice(0,2)));
  // e agora ela edita outra coisa: nao pode desfazer o que ja estava feito
  await pV.evaluate(()=>{ const e=experts[3]; e.name="Editado pela que voltou"; persistExperts(e); });
  await esperar(7000);
  const rA2 = await retrato(A), rV2 = await retrato(V2);
  ok('editar depois de voltar nao desfaz o que ja estava feito',
     rA2.experts.some(e=>e.nome==="Mudou 1") && rA2.experts.some(e=>/pela que voltou/.test(e.nome)));
  ok('as duas ficam iguais', iguais(rA2,rV2));
  await A.cx.close(); await cxV.close();
}

log('\n== H. RODADA: uma reinicia enquanto a outra ja tem sorteados ==');
{
  const A = await abrirMaquina(b,{nome:'A'});
  const B = await abrirMaquina(b,{nome:'B'});
  await esperar(4000);
  await A.p.evaluate(()=>{ sorteados = experts.slice(0,3).map(e=>e.id); save(LS_RODADA,sorteados); sendStateR(); render(); });
  await esperar(4000);
  const sA1=(await retrato(A)).sorteados.length, sB1=(await retrato(B)).sorteados.length;
  log(`   depois de marcar 3: A=${sA1} B=${sB1}`);
  ok('a rodada aparece nas duas', sA1===3 && sB1===3);
  await B.p.evaluate(()=>{ sorteados = []; save(LS_RODADA,sorteados); sendStateR(); render(); });
  await esperar(9000);
  const sA2=(await retrato(A)).sorteados.length, sB2=(await retrato(B)).sorteados.length;
  log(`   depois de reiniciar em B: A=${sA2} B=${sB2}`);
  ok('reiniciar a rodada vale nas duas', sA2===sB2);
  await A.cx.close(); await B.cx.close();
}

log('\n== I. DUAS ABAS NA MESMA MAQUINA ==');
{
  const A = await abrirMaquina(b,{nome:'aba1'});
  const aba2 = await A.cx.newPage();
  await aba2.goto((process.env.BASE || 'http://localhost:8777/roleta-teste')+'/admin/',{waitUntil:'domcontentloaded'});
  await aba2.waitForTimeout(6000);
  await A.p.evaluate(()=>{ const e=experts[6]; e.name="Feito na aba 1"; persistExperts(e); });
  await esperar(6000);
  const r1 = await retrato(A), r2 = await retrato({p:aba2});
  ok('as duas abas da mesma maquina ficam iguais', iguais(r1,r2));
  if(!iguais(r1,r2)) log('   aba1:', JSON.stringify(r1.experts.find(e=>/aba 1/.test(e.nome))), '\n   aba2:', JSON.stringify(r2.experts.find(e=>/aba 1/.test(e.nome))));
  await A.cx.close();
}
log('\n===== ' + (contaFalhas()? contaFalhas()+' FALHA(S)' : 'TUDO VERDE') + ' =====');
await b.close(); process.exit(contaFalhas()?1:0);
