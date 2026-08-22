/* ============================================================
   RESTAURAR O ESTADO DA ROLETA a partir do backup .json
   ------------------------------------------------------------
   Onde rodar: no painel admin de producao, MESMO navegador.
   Como: F12 -> Console -> cole isto -> Enter -> escolha o arquivo.
   Depois de restaurar, o painel empurra a lista para a roleta.
   ============================================================ */
(() => {
  const inp = document.createElement("input");
  inp.type = "file"; inp.accept = "application/json";
  inp.onchange = async () => {
    const arq = inp.files[0]; if (!arq) return;
    const { meta, dados } = JSON.parse(await arq.text());
    console.table(meta);
    if (!confirm(`Restaurar backup de ${meta.exportadoEm}?\n` +
                 `${meta.totalExperts} experts (${meta.ativos} ativos), ${meta.jaSorteados} sorteados.\n\n` +
                 `Isto sobrescreve o estado atual deste navegador.`)) return;

    Object.entries(dados).forEach(([k, v]) => localStorage.setItem(k, v));
    /* rev acima do atual para que ESTA lista vença o conflito e seja
       adotada pela roleta e pelos outros paineis ao recarregar */
    localStorage.setItem("cj_experts_rev", String(Date.now()));
    console.log("%cRestaurado. Recarregando para propagar para a roleta...", "color:#0f0;font-weight:bold");
    setTimeout(() => location.reload(), 800);
  };
  inp.click();
})();
