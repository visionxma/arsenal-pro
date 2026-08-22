/* ============================================================
   EXPORTAR O ESTADO REAL DA ROLETA  (rode no SEU navegador)
   ------------------------------------------------------------
   Onde rodar: no navegador/perfil que JA usa o painel admin de
   producao (o que mostra 14 ativos / 12 sem sorteio / 2 sorteados).
   Como: abra https://admin.safiriontradingbrasil.com/roleta/admin/
         F12 -> Console -> cole isto -> Enter.
   Resultado: baixa um arquivo backup-roleta-<data>.json
   ============================================================ */
(() => {
  const CHAVES = [
    "cj_experts_v6",     // lista de experts (a mais importante)
    "cj_cfg_v2",         // configuracoes
    "cj_hist_v1",        // historico
    "cj_rodada_v1",      // quem ja foi sorteado nesta rodada
    "cj_live_state_v1",  // estado do cartao AO VIVO
    "cj_live_url_v1",    // link da live
    "cj_experts_rev",    // carimbo de versao (decide quem vence no sync)
    "cj_experts_init_v1" // flag de primeira semeadura
  ];
  const dump = {};
  CHAVES.forEach(k => { const v = localStorage.getItem(k); if (v !== null) dump[k] = v; });

  const experts = JSON.parse(dump.cj_experts_v6 || "[]");
  const meta = {
    exportadoEm: new Date().toISOString(),
    origem: location.href,
    totalExperts: experts.length,
    ativos: experts.filter(e => e.active).length,
    jaSorteados: JSON.parse(dump.cj_rodada_v1 || "[]").length,
    rev: dump.cj_experts_rev || "0"
  };
  console.table(meta);

  const blob = new Blob([JSON.stringify({ meta, dados: dump }, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `backup-roleta-${new Date().toISOString().slice(0,19).replace(/[:T]/g,"-")}.json`;
  a.click();
  console.log("%cBackup baixado. Guarde este arquivo antes de qualquer teste.", "color:#0f0;font-weight:bold");
  return meta;
})();
