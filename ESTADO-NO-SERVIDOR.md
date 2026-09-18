# Estado da roleta no servidor — o passo que falta (18/09/2026)

## O problema, em uma frase

Hoje a lista de experts e a rodada moram no **navegador de cada pessoa**
(`localStorage`). Nada disso fica guardado no servidor: a sincronização é por
mensagem em tempo real, que só alcança **quem está com a página aberta naquele
instante**.

Como o Corujão roda com **um login só, dividido entre várias pessoas que se
revezam durante a noite**, isso dava a divergência relatada: quem entrava no
turno seguinte via a lista que tinha sobrado no computador dele.

## O que já foi consertado (commit `b256e4f`, no ar)

- O painel **pergunta sempre** a lista a quem está no ar ao conectar, tendo lista
  salva ou não — e o que volta é **mesclado**, nunca substitui.
- A roleta passa a mandar **a lista** quando um painel chega (antes só mandava a
  rodada), e um painel responde ao "olá" de outro painel.
- Se **ninguém** responder, o painel avisa: *"Lista não conferida — ninguém no
  ar"*. Ele para de fingir que a tela está certa.

Isso cobre a noite inteira do Corujão, porque a **roleta fica aberta na
transmissão** — sempre há alguém para confirmar. O buraco que sobra é o caso em
que **ninguém** está com a página aberta na hora da troca.

## O que fecha o buraco de vez

Uma linha no banco do Supabase com o estado atual. Quem abre o painel lê essa
linha antes de operar; quem edita, grava. Aí não importa quem está no ar.

**Você roda isto uma vez** (Supabase → seu projeto → SQL Editor → cole → Run):

```sql
-- Estado único da roleta do Corujão. Uma linha só, sempre a mesma.
create table if not exists public.roleta_estado (
  id          text primary key default 'cj-corujao',
  experts     jsonb not null default '[]'::jsonb,
  tumbas      jsonb not null default '{}'::jsonb,
  cfg         jsonb not null default '{}'::jsonb,
  sorteados   jsonb not null default '[]'::jsonb,
  hist        jsonb not null default '[]'::jsonb,
  rev         bigint not null default 0,
  atualizado  timestamptz not null default now()
);

insert into public.roleta_estado (id) values ('cj-corujao')
  on conflict (id) do nothing;

alter table public.roleta_estado enable row level security;

-- Qualquer um lê (a roleta aberta na live não faz login).
create policy "leitura publica" on public.roleta_estado
  for select using (true);

-- Só quem entrou com o login do operador escreve.
create policy "escrita do operador" on public.roleta_estado
  for update to authenticated using (true) with check (true);
```

## O código já está pronto e publicado

O painel e a roleta **já sabem usar essa tabela**. Assim que ela existir, eles
passam a usá-la sozinhos, sem novo deploy:

- o painel **lê** ao abrir e mescla com o que tem (nunca substitui em bloco);
- o painel **grava** a cada mudança, sempre lendo e mesclando antes, então dois
  operadores ao mesmo tempo não se apagam;
- a roleta **só lê** — a política do banco recusa escrita sem sessão;
- a rodada (quem já foi sorteado) e o histórico vão junto, com relógio lógico:
  quem tem o relógio mais velho adota o do servidor, nunca o contrário.

**Testado contra um Postgres de verdade** (projeto de ensaio, apagado depois):
turno trocando sem ninguém no ar, roleta subindo sozinha num computador novo,
rodada atravessando a virada e escrita anônima recusada pelo banco.

**Enquanto a tabela não existir, nada quebra:** o painel tenta **uma vez**,
percebe que ela não está lá, anota e nunca mais tenta — tudo segue funcionando
como hoje. Verificado.
