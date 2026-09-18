# Bateria de sincronia — a conta é uma só e não pode divergir

A conta do painel é **dividida** entre as pessoas que revezam o turno. Máquina,
celular, aparelho: nada disso é identidade — o que vale é o login. Estes testes
existem para provar que, com várias máquinas no mesmo login, **o estado nunca
fica diferente**.

Cada "máquina" é um contexto isolado do navegador, com o mesmo login, falando com
o mesmo servidor.

```bash
# contra o ambiente de teste publicado (o normal)
BASE=https://visionxma.github.io/arsenal-pro/roleta-teste node conv1.mjs

# contra uma cópia local (python3 -m http.server 8777 na raiz do repo)
node conv1.mjs
```

| arquivo | o que prova |
|---|---|
| `conv1.mjs` | duas máquinas editando ao mesmo tempo — experts diferentes, o **mesmo** expert, e uma removendo enquanto a outra edita |
| `conv2.mjs` | computador com a **hora 2 dias errada**, queda de internet com edição offline, três máquinas simultâneas |
| `conv3.mjs` | máquina que ficou fora e voltou, reiniciar rodada, **duas abas** na mesma máquina |
| `conv4.mjs` | maratona: três turnos seguidos em três máquinas, com a roleta da transmissão aberta o tempo todo |

**Nunca rode isto contra produção.** O `BASE` padrão é o ambiente de teste, que
tem sala, chave e tabela próprias.

## Dois defeitos que esta bateria encontrou (18/09/2026)

1. **Empate de carimbo.** Duas edições no mesmo expert no mesmo milissegundo
   davam o mesmo carimbo; com "maior vence", nenhum vencia e cada máquina ficava
   com a sua versão **para sempre**. Conserto: desempate pelo conteúdo em texto,
   que dá o mesmo resultado em qualquer máquina.
2. **Mensagem perdida não se corrigia.** O servidor só era lido ao abrir a
   página. Conserto: o banco avisa quando a linha muda e as páginas releem na
   hora; de 15 em 15 s conferem só o número da versão, como rede de segurança.
