# Como levar o trabalho do ambiente de teste para o ar

O Corujão começou em 18/09/2026 às 18h e roda por cerca de três dias. Enquanto
isso, **nada se experimenta em produção**: o que muda vive no ramo
`turno-por-pessoa` e aparece publicado só em `/roleta-teste/`.

## Os dois endereços

| | endereço | fala com |
|---|---|---|
| **no ar** (não tocar até a operação acabar) | https://admin.safiriontradingbrasil.com/roleta/admin/ | sala `cj-corujao`, tabela `roleta_estado` |
| **teste** (pode tudo) | https://visionxma.github.io/arsenal-pro/roleta-teste/admin/ | sala `cj-TESTE`, tabela `roleta_estado_teste` |

Login do ambiente de teste: `teste-roleta@visionxma.com` / `teste-roleta-2026`.
A página de teste se identifica sozinha: título com `[TESTE]` e uma pílula no
canto. Nenhuma mensagem e nenhuma gravação do teste alcança a roleta do ar — a
chave da mensagem é conferida na entrada do canal e a tabela é outra.

## O que está pronto no ramo, esperando a operação terminar

> A conta é **uma só e dividida** entre as pessoas do turno. Máquina, celular,
> aparelho: nada disso é identidade — o que vale é o login.

- **Sincronia sem divergência** (o principal): desempate determinístico quando
  duas máquinas editam no mesmo milissegundo, e releitura contínua do servidor
  (aviso do banco + pulso de 15 s), para que uma mensagem perdida não deixe
  nenhuma máquina para trás.
- **A conta na tela**: a barra lateral mostra qual conta está aberta.
- **Quantos painéis abertos agora**: *"mais 1 painel aberto agora — sincronizado"*.
  É confirmação, não alerta: dividir a conta é o esperado.
- **Diário do turno**: uma frase por ação, com a hora, guardada junto com o
  estado. Quem assume o turno lê o que aconteceu no anterior mesmo sem ninguém
  para contar.

## Promover (quando a operação acabar)

```bash
cd "BACKUP_VICTOR/Projetos/VISIONX/Arsenal Pro"
git checkout main
git merge turno-por-pessoa          # traz roleta/ e roleta-teste/ juntos
python3 testes-roleta/gerar-ambiente-teste.py   # teste volta a espelhar produção
git push origin main
```

A coluna `diario` já existe **nas duas tabelas** (foi criada junto), então não há
nada a fazer no banco na hora de promover.

Antes de promover, rode a bateria de sincronia — 26 verificações com várias
máquinas no mesmo login (`testes-roleta/sincronia/`, só no ramo até o merge):

```bash
cd testes-roleta/sincronia
BASE=https://visionxma.github.io/arsenal-pro/roleta-teste node conv1.mjs
# e conv2.mjs, conv3.mjs, conv4.mjs
```

## Se algo der errado com a operação rodando

Voltar ao que estava é um comando, porque produção e teste são pastas
diferentes:

```bash
git revert <commit>   &&   git push origin main
```
