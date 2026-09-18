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

- **Quem está operando**: a barra lateral mostra `no turno: <apelido>`, tirado do
  próprio login.
- **Quem mais está no painel agora**: presença em tempo real avisa *"Também no
  painel agora: Fulano"* ou, quando é o mesmo login, *"Este mesmo login está
  aberto em outro aparelho agora"*.
- **Diário do turno**: uma frase por ação, com hora e autor, guardada junto com o
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

Depois de publicar, confira no ar:

```bash
BASE=https://admin.safiriontradingbrasil.com/roleta node regressao.mjs
```

## Se algo der errado com a operação rodando

Voltar ao que estava é um comando, porque produção e teste são pastas
diferentes:

```bash
git revert <commit>   &&   git push origin main
```
