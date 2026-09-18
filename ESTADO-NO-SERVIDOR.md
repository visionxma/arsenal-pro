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

Depois de rodar, me avise: eu ligo o painel e a roleta nessa tabela, com o
cuidado de sempre — o merge continua sendo por carimbo e lápide (a gravação
nunca vira "o último a falar vence"), e tudo passa pelo sandbox
(`testes-roleta/`) antes de ir para o ar.

**Enquanto você não rodar, nada quebra:** o que está publicado hoje funciona sem
essa tabela.
