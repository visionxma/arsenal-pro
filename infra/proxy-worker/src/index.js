// Serve o Arsenal Pro (GitHub Pages) como rotas do domínio:
//   safiriontradingbrasil.com/arsenal-pro/*  → visionxma.github.io/arsenal-pro/*
//   admin.safiriontradingbrasil.com/*        → visionxma.github.io/arsenal-pro/* (raiz redireciona ao painel)
// Nenhum registro DNS existente é alterado; só é preciso criar o subdomínio "admin"
// (AAAA @100:: com proxy laranja) e publicar este Worker na conta da zona.
const ORIGIN = "https://visionxma.github.io";

// Cabeçalhos de segurança aplicados a todas as respostas
const SEC_HEADERS = {
  "Strict-Transport-Security": "max-age=15552000",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), fullscreen=(self)",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Content-Security-Policy": [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src https://fonts.gstatic.com",
    "img-src 'self' data: blob:",
    "connect-src 'self' https://*.supabase.co wss://*.supabase.co https://fonts.googleapis.com https://fonts.gstatic.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join("; "),
};

export default {
  async fetch(req) {
    const url = new URL(req.url);

    // proxy só de leitura: métodos de escrita não fazem sentido em site estático
    if (req.method !== "GET" && req.method !== "HEAD") {
      return new Response("Method Not Allowed", { status: 405, headers: { "Allow": "GET, HEAD" } });
    }

    let path = url.pathname;

    // Página /aovivo retirada do ar — responde 410 Gone (não proxeia).
    if (/^\/arsenal-pro\/aovivo(\/|$)/.test(path) || /^\/aovivo(\/|$)/.test(path)) {
      return new Response("Página indisponível.", {
        status: 410,
        headers: { "Content-Type": "text/plain; charset=utf-8", ...SEC_HEADERS },
      });
    }

    if (url.hostname.startsWith("admin.")) {
      if (path === "/" || path === "") {
        return Response.redirect(url.origin + "/roleta/admin/", 302);
      }
      path = "/arsenal-pro" + path;
    }
    // na rota de path o pathname já começa com /arsenal-pro

    const upstream = await fetch(ORIGIN + path + url.search, {
      method: req.method,
      headers: { "Accept": req.headers.get("Accept") || "*/*" },
      redirect: "follow",
    });

    const res = new Response(upstream.body, upstream);
    for (const [k, v] of Object.entries(SEC_HEADERS)) res.headers.set(k, v);
    return res;
  },
};
