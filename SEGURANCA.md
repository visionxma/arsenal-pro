# Segurança — Arsenal Pro / Roleta

Arquitetura: site **estático** (GitHub Pages) atrás do **Cloudflare** (proxy), com
sincronização em tempo real via **Supabase** (Auth + Realtime). Não há backend próprio,
banco sob nossa gestão direta, nem uploads — o que elimina de raiz injeção server-side,
RCE, LFI, XXE, SSRF e afins.

## Automatizado neste repositório

| Item | Onde | O que faz |
|---|---|---|
| SAST | `.github/workflows/security.yml` (CodeQL) | Análise estática de JS a cada push/PR e semanal |
| Varredura de segredos | mesmo workflow (Gitleaks) + `.gitleaks.toml` | Bloqueia commit de segredos (libera só a chave anon pública) |
| Headers em produção | mesmo workflow | Falha o CI se CSP/HSTS/etc sumirem do domínio |
| Dependency scan | `.github/dependabot.yml` | PRs automáticos p/ Actions vulneráveis |
| Backup do banco | `.github/workflows/supabase-backup.yml` | Dump diário criptografado (AES-256), retenção 30 dias |
| Headers de segurança | `infra/proxy-worker/src/index.js` | CSP, HSTS, X-Frame-Options DENY, nosniff, Referrer/Permissions-Policy, COOP |
| Autorização de comandos | `roleta/index.html` | Girar/encerrar/forçar exige JWT do painel verificado no Supabase |
| Login | `roleta/admin/index.html` | Supabase Auth (e-mail+senha, sessão com refresh) |
| Supply chain | ambos HTML | supabase-js fixado por versão + SRI + crossorigin |

## Checklist manual — FAZER antes do evento

### Cloudflare (painel da zona safiriontradingbrasil.com)
- [ ] **Security → Bots → Bot Fight Mode: ON** (plano free)
- [ ] **Security → WAF → Rate limiting rules**: criar regra no login do admin
      (path `admin.safiriontradingbrasil.com/roleta/admin/`, ~10 req/min por IP → Block)
- [ ] **Security → Settings → Security Level: Medium/High** durante o evento
- [ ] **SSL/TLS → Overview: Full (strict)**

### Supabase (projeto)
- [ ] **ROTACIONAR a service_role** (Settings → API → Reset) — foi exposta em chat
- [ ] **Trocar a senha do operador** (Authentication → Users)
- [ ] **Ativar MFA/2FA** para a conta admin (Authentication → Providers → habilitar, exigir p/ operador)
- [ ] **Auth → Rate limits**: manter limites de sign-in ligados (padrão do Supabase)
- [ ] **Point-in-time recovery / backups** do plano (além do dump do CI)

### GitHub
- [ ] Secrets do backup: `SUPABASE_DB_URL` e `BACKUP_PASSPHRASE` (Settings → Secrets → Actions)
- [ ] **Settings → Code security**: ligar *Secret scanning* e *Push protection*
- [ ] Avaliar tornar o repositório **privado** (a chave anon e a sala ficam no código)

### App
- [ ] Preencher `CHECKOUT_URL` (landing) e `EMBED_URL` (página ao vivo)

## LGPD (mínimo aplicável)
- A roleta guarda apenas nomes/fotos de experts (dado profissional, com consentimento deles).
- Não coletamos dado de visitante no site. Se adicionar formulário/checkout, incluir
  aviso de privacidade e base legal, e não logar dados sensíveis.

## Resposta a incidentes (rápido)
1. Suspeita de abuso da roleta → trocar a senha do operador (invalida sessões após refresh).
2. Vazamento de chave → rotacionar no Supabase; a sala/anon podem ser trocadas no código.
3. Ataque volumétrico → Cloudflare "Under Attack Mode" (1 clique).
