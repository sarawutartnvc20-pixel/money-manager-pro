// Vercel serverless relay for sites that do not allow the app to read them directly (CORS): /api/px?u=<https url>
// Only the few hosts the app needs are allowed, so this cannot be used as an open proxy.
const ALLOW = /^(www\.myinstants\.com|media\.myinstants\.com|media\d?\.giphy\.com|i\.giphy\.com)$/;
module.exports = async (req, res) => {
  let target;
  try { target = new URL(new URL(req.url, 'http://localhost').searchParams.get('u')); } catch (_) { res.statusCode = 400; return res.end('bad url'); }
  if (target.protocol !== 'https:' || !ALLOW.test(target.hostname)) { res.statusCode = 403; return res.end('host not allowed'); }
  try {
    const r = await fetch(target.href, { headers: { 'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1', accept: '*/*', 'accept-language': 'en,th;q=0.8' }, redirect: 'follow' });
    const buf = Buffer.from(await r.arrayBuffer());
    res.statusCode = r.status;
    res.setHeader('content-type', r.headers.get('content-type') || 'application/octet-stream');
    res.setHeader('cache-control', r.ok ? 'public, s-maxage=600, max-age=300' : 'no-store');
    res.end(buf);
  } catch (e) { res.statusCode = 502; res.end('relay failed'); }
};
