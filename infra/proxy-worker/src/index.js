// Serve o Arsenal Pro (GitHub Pages) como rotas do domínio:
//   safiriontradingbrasil.com/arsenal-pro/*  → visionxma.github.io/arsenal-pro/*
//   admin.safiriontradingbrasil.com/*        → visionxma.github.io/arsenal-pro/* (raiz redireciona ao painel)
// Nenhum registro DNS existente é alterado; só é preciso criar o subdomínio "admin"
// (AAAA @100:: com proxy laranja) e publicar este Worker na conta da zona.
const ORIGIN = "https://visionxma.github.io";

export default {
  async fetch(req) {
    const url = new URL(req.url);
    let path = url.pathname;

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
    res.headers.delete("X-Frame-Options");
    return res;
  },
};
