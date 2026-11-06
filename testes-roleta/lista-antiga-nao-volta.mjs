/* Portão (06/11/2026): a lista ANTIGA guardada no navegador do operador não pode voltar.
   Põe no localStorage uma lista velha na chave de antes (padrão cj_experts_v6) e abre o painel de produção
   (login do cofre) e a roleta do Fechamento. Sai 1 se alguém que saiu reaparece, se a roda do time não tem
   o tamanho do banco ou se o painel tentaria gravar mais experts do que o banco tem.
   Só LÊ: escrita no banco e canal ao vivo bloqueados. Uso: node lista-antiga-nao-volta.mjs [chave-antiga] */
import fs from "node:fs";
import { chromium } from "/Users/victorgabryellferreiraqueiroz/.jarvis/design-engine/node_modules/playwright/index.mjs";
const cofre = fs.readFileSync(process.env.HOME + "/.claude/credenciais/arsenal-pro-roleta.md", "utf8");
const SENHA = /Senha[^`]*`([^`]+)`/.exec(cofre.slice(cofre.indexOf("## Painel do operador")))[1];
const CHAVE = process.argv[2] || "cj_experts_v6";
const SB = "https://ujwovqskcffrriepehal.supabase.co";
const html = await (await fetch("https://safiriontradingbrasil.com/arsenal-pro/roleta/")).text();
const ANON = /const SYNC_ANON\s*=\s*"([^"]+)"/.exec(html)[1];
const noBanco = async id => ((await (await fetch(`${SB}/rest/v1/roleta_estado?id=eq.${id}&select=experts`, { headers: { apikey: ANON, Authorization: "Bearer " + ANON } })).json())[0]?.experts || []).length;
const BANCO = { geral: await noBanco("cj-corujao"), __fechamento: await noBanco("cj-corujao__fechamento") };
let falhou = 0;
const b = await chromium.launch();
for (const [url, sufixo] of [["https://admin.safiriontradingbrasil.com/roleta/admin/", ""], ["https://safiriontradingbrasil.com/arsenal-pro/roleta/?time=fechamento", "__fechamento"]]) {
  const ctx = await b.newContext();
  await ctx.route("**/realtime/**", r => r.abort());
  let escrita = null;
  await ctx.route("**/rest/v1/**", r => { const q = r.request(); if (q.method() === "GET") return r.continue(); escrita = JSON.parse(q.postData() || "{}"); return r.abort(); });
  await ctx.addInitScript(([k, s]) => {
    if (sessionStorage.getItem("prep")) return; sessionStorage.setItem("prep", "1");
    const velho = Date.now() - 20 * 864e5;
    const lista = ["Mineirinho", "Lucas Bemfica", "Trader Estoico", "Miriele", "Tio Vitão"].map((n, i) => ({ id: "eantigo" + i, name: n, active: true, minutes: null, updatedAt: velho }));
    localStorage.setItem(k + s, JSON.stringify(lista));
    localStorage.setItem("cj_experts_init_v1" + s, "1");
  }, [CHAVE, sufixo]);
  const p = await ctx.newPage();
  await p.goto(url, { waitUntil: "domcontentloaded" });
  if (url.includes("/admin/")) {
    await p.fill("#loginEmail", "genesisapp360@gmail.com"); await p.fill("#loginPass", SENHA); await p.click(".gate-btn");
  }
  await p.waitForTimeout(8000);
  const txt = (await p.evaluate(() => document.body.textContent)).toLowerCase();
  const fatias = await p.evaluate(() => document.querySelectorAll("#wheel .seg-item").length);
  const voltaram = ["mineirinho", "lucas bemfica", "trader estoico"].filter(n => txt.includes(n));
  const nBanco = BANCO[sufixo || "geral"];
  if (voltaram.length || (sufixo && fatias !== nBanco) || (escrita && (escrita.experts || []).length > nBanco)) falhou++;
  console.log(url.split("/")[2], sufixo || "geral", "| no banco:", nBanco, "| quem saiu e reapareceu:", voltaram.join(", ") || "ninguém",
    "| fatias:", fatias, "| tentou gravar no banco:", escrita ? `${(escrita.experts || []).length} experts` : "não");
  await ctx.close();
}
await b.close();
console.log(falhou ? "FALHOU: a lista antiga do navegador voltou" : "OK: a lista antiga do navegador não volta");
process.exit(falhou ? 1 : 0);
