# Regenera o admin do sandbox a partir da producao:
# troca sala/chave para as de teste e reinsere o hook de QA (?qa=1).
# Rodar da raiz do repo: python testes-roleta/sync-sandbox-admin.py
import io, os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = os.path.join(RAIZ, "roleta", "admin", "index.html")
SAND = os.path.join(RAIZ, "testes-roleta", "sandbox", "roleta", "admin", "index.html")

HOOK = '''<body class="locked">
<script>
/* ===== HOOK DE QA (SOMENTE SANDBOX — nao existe em producao) ===== */
(function(){
  var q = new URLSearchParams(location.search);
  if (!q.has("qa")) return;
  var nomes = ["Taylon","Patrick","Miriele","Julin","Thon Carvalho","Ed Trader","Vitor Lela","Eduardo Bastos","Tio Vitao","Gustavo","Lucas Bemfica","Allan","Big Boss","Mineirinho","Molina","Trader Estoico"];
  var exps = nomes.map(function(n,i){ return { id:"d"+i, name:n, photo:null, active: i!==7 && i!==12, minutes: (i===1?45:(i===4?20:null)), updatedAt:1 }; });
  try {
    localStorage.setItem("cj_experts_v6", JSON.stringify(exps));
    localStorage.setItem("cj_experts_init_v1","1");
    localStorage.setItem("cj_rodada_v1", JSON.stringify(["d2","d5","d10"]));
    localStorage.setItem("cj_hist_v1", JSON.stringify([
      {name:"Lucas Bemfica", at:"21:36"},
      {name:"Ed Trader", at:"21:02"},
      {name:"Miriele", at:"20:31"}
    ]));
    localStorage.setItem("cj_listas_v1", JSON.stringify([
      { id:"L1", nome:"Formacao oficial do Corujao", criadoEm:new Date().toISOString(), experts:exps, tumbas:{} },
      { id:"L2", nome:"Teste noite 2", criadoEm:new Date(Date.now()-86400000).toISOString(), experts:exps.slice(0,8), tumbas:{} }
    ]));
    localStorage.setItem("cj_listas_auto_v1","1");
    if (q.has("min")) localStorage.setItem("cj_admin_sb","true"); else localStorage.removeItem("cj_admin_sb");
    if (q.has("url")) localStorage.setItem("cj_live_url_v1","https://meet.google.com/abc-defg-hij");
    if (q.has("live")) localStorage.setItem("cj_live_state_v1", JSON.stringify({status:"running", name:"Lucas Bemfica", photo:null, endsAt: Date.now()+17*60000}));
    else localStorage.removeItem("cj_live_state_v1");
  } catch(e){}
  var destrava = function(){
    document.body.classList.remove("locked");
    var g = document.getElementById("loginOverlay");
    if (g) g.classList.remove("show");
  };
  destrava();
  document.addEventListener("DOMContentLoaded", destrava);
  setInterval(destrava, 300);
})();
</script>'''

s = io.open(PROD, encoding="utf-8").read()
assert 'cj-corujao' in s and '<body class="locked">' in s
s = s.replace("cj-corujao", "cj-SANDBOX-TESTE")
s = s.replace("q1vcjZHdCejBqSJeQSXBKCNC", "SANDBOX-KEY-NAO-PRODUCAO")
s = s.replace('<body class="locked">', HOOK, 1)
assert "cj-SANDBOX-TESTE" in s and "HOOK DE QA" in s
io.open(SAND, "w", encoding="utf-8").write(s)
print("sandbox admin regenerado a partir da producao")
