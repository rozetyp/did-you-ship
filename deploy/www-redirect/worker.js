// Cloudflare Worker on www.didyouship.com/*: 301 to the apex, keeping path and query.
// www is proxied by Cloudflare but not registered on Railway, so without this it 404s.
export default {
  fetch(request) {
    const url = new URL(request.url);
    url.hostname = "didyouship.com";
    url.protocol = "https:";
    return Response.redirect(url.toString(), 301);
  },
};
