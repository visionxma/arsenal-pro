# Gera /roleta-teste/ a partir de /roleta/ — o ambiente onde se mexe enquanto o
# Corujao esta no ar. Isolamento em quatro camadas, nenhuma delas alcanca a
# producao:
#   sala em tempo real  cj-corujao      -> cj-TESTE
#   chave da mensagem   q1vcjZ...       -> TESTE-NAO-PRODUCAO   (conferida na entrada)
#   canal do navegador  cj-cmd          -> cj-cmd-TESTE
#   tabela do estado    roleta_estado   -> roleta_estado_teste
# Alem disso, a pagina se identifica: titulo com [TESTE] e uma pilula no canto.
# Rodar da raiz do repo:  python3 testes-roleta/gerar-ambiente-teste.py
import os, re, shutil

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(RAIZ, "roleta")
DEST = os.path.join(RAIZ, "roleta-teste")

# Pilula fixa: nao entra no fluxo (position:fixed), entao nao empurra nem cobre
# o layout; pointer-events:none para nunca roubar um clique do operador. Em
# 360px vira so "TESTE" para nao disputar largura com a barra do painel.
AVISO = '''
<style>
  .aviso-teste{
    position:fixed; top:max(8px, env(safe-area-inset-top)); right:max(8px, env(safe-area-inset-right));
    z-index:2147483647; pointer-events:none; user-select:none;
    display:inline-flex; align-items:center; gap:6px;
    padding:5px 10px; border-radius:999px;
    background:#b45309; color:#fff; border:1px solid #f59e0b;
    font:700 clamp(10px, 9px + .25vw, 12px)/1 Inter, system-ui, sans-serif;
    letter-spacing:.06em; text-transform:uppercase;
    box-shadow:0 2px 10px rgba(0,0,0,.4);
  }
  .aviso-teste::before{
    content:""; width:7px; height:7px; border-radius:50%; background:#fde68a; flex:none;
  }
  @media (prefers-reduced-motion: no-preference){
    .aviso-teste::before{ animation:aviso-pisca 1.6s ease-in-out infinite; }
    @keyframes aviso-pisca{ 50%{ opacity:.25 } }
  }
  .aviso-teste .longo{ display:none; }
  @media (min-width:600px){ .aviso-teste .longo{ display:inline; } }
</style>
<div class="aviso-teste" role="status" aria-label="Ambiente de teste">TESTE<span class="longo">&nbsp;· não é a roleta do ar</span></div>
'''

TROCAS = [
    ('"cj-corujao"', '"cj-TESTE"'),
    ("q1vcjZHdCejBqSJeQSXBKCNC", "TESTE-NAO-PRODUCAO"),
    ('BroadcastChannel("cj-cmd")', 'BroadcastChannel("cj-cmd-TESTE")'),
    ('"roleta_estado"', '"roleta_estado_teste"'),
    ('/rest/v1/roleta_estado', '/rest/v1/roleta_estado_teste'),
]

def gerar(rel):
    o = os.path.join(ORIG, rel)
    d = os.path.join(DEST, rel)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    s = open(o, encoding="utf-8").read()
    antes = s
    for a, b in TROCAS:
        s = s.replace(a, b)
    # sobrou alguma marca de producao?
    for marca in ("cj-corujao", "q1vcjZHdCejBqSJeQSXBKCNC", 'BroadcastChannel("cj-cmd")'):
        assert marca not in s, "%s ainda tem %r — o teste falaria com a producao" % (rel, marca)
    # a pagina se identifica
    s = re.sub(r"<title>([^<]*)</title>", lambda m: "<title>[TESTE] %s</title>" % m.group(1), s, count=1)
    s = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + AVISO, s, count=1)
    assert s != antes
    open(d, "w", encoding="utf-8").write(s)
    print("  gerado roleta-teste/%s" % rel)

if os.path.isdir(DEST):
    shutil.rmtree(DEST)
gerar("index.html")
gerar(os.path.join("admin", "index.html"))
shutil.copy2(os.path.join(ORIG, "version.json"), os.path.join(DEST, "version.json"))
print("ambiente de teste gerado a partir de roleta/ — producao intocada")
