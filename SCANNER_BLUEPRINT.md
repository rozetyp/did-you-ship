# Scanner Blueprint — didyouship.dev

## What this is

A production readiness checker for vibe coders who just deployed their first app and have no idea what they forgot. One scan, 25 checks, plain English results, copy-pasteable fixes.

## Who it's for

People who build with Cursor, Replit, v0, Bolt. They can ship a full-stack app in a weekend but have never configured DNS, never heard of DMARC, and don't know why their links look ugly on Twitter. They find out something is broken when a user complains or their emails go to spam.

## What we check and why

Every check answers one question: **"What breaks if I don't fix this?"**
If the answer is "nothing you'll ever notice" — it's not in the scanner.

---

## CATEGORY 1: Email — "Why are my emails going to spam?"

Vibe coders set up Resend/SendGrid/Postmark, send a test email, it works. Two weeks later their users say "I never got the verification email." It's in spam. They have no idea why.

### Check 1: SPF record
- **What:** Does your DNS say who's allowed to send email as you?
- **Why:** Without SPF, Gmail sees your emails as unverified. Spam folder.
- **How:** DNS TXT query for the domain. Look for `v=spf1`.
- **Outcomes:**
  - Missing → **Critical.** "Gmail can't verify your emails are real"
  - Has `+all` or `?all` → **Critical.** "Your SPF says anyone can send as you"
  - Has `~all` → **Low.** "Working but not fully locked down"
  - Has `-all` → Pass
- **Fix shown:** `Add this TXT record to your DNS: v=spf1 include:_spf.google.com ~all` (we detect their vendor from MX/SPF and customize the include)

### Check 2: DMARC record
- **What:** Does your DNS tell email providers what to do with fake emails from your domain?
- **Why:** Without DMARC, Gmail/Outlook penalize your domain. Even legit emails get flagged. Also anyone can send email pretending to be you.
- **How:** DNS TXT query for `_dmarc.{domain}`. Parse `p=` value.
- **Outcomes:**
  - Missing → **Critical.** "Anyone can send email as @yourdomain.com and your legit emails are penalized"
  - `p=none` → **High.** "Your email protection exists but isn't turned on"
  - `p=quarantine` → Pass (mention they can upgrade to reject later)
  - `p=reject` → Pass
- **Fix shown:** `Add TXT record at _dmarc.yourdomain.com: v=DMARC1; p=quarantine; rua=mailto:you@yourdomain.com`

### Check 3: DMARC reporting
- **What:** Are you getting reports when someone tries to spoof your domain?
- **Why:** Without `rua=`, you'll never know if someone is sending phishing emails as you.
- **How:** Parse DMARC record for `rua=` field.
- **Outcomes:**
  - DMARC exists but no `rua=` → **Medium.** "You won't know when someone spoofs you"
  - Has `rua=` → Pass
- **Fix shown:** Add `rua=mailto:dmarc@yourdomain.com` to your DMARC record

### Check 4: MX records (informational)
- **What:** Who handles your inbound email?
- **Why:** Not an issue — just useful context. Shows detected vendors (Google Workspace, Cloudflare Email, etc.)
- **How:** DNS MX query. Map hostnames to vendor names.
- **Outcomes:** Always pass. Display detected vendors.

**Implementation:** All 4 checks = DNS queries only. Use `dns.resolver`. Already built in current scanner. ~1 second total.

---

## CATEGORY 2: SSL / HTTPS — "Why does my site show 'Not Secure'?"

### Check 5: SSL certificate valid
- **What:** Does your site have a working SSL certificate?
- **Why:** Without it, browsers show a full-page warning. Nobody can use your site.
- **How:** Open SSL socket to port 443. Get cert. Check validity and expiry.
- **Outcomes:**
  - Invalid cert → **Critical.** "Browsers are blocking your site with a security warning"
  - Can't connect on 443 → **Critical.** "Your site doesn't have HTTPS at all"
  - Expires in <7 days → **Critical.** "Your SSL cert expires in X days — site will break"
  - Expires in <30 days → **High.** "Expires soon — make sure auto-renewal is set up"
  - Valid → Pass. Show issuer + days remaining.
- **Fix shown:** "Enable HTTPS in your Vercel/Railway/Cloudflare dashboard. Most do it automatically."

### Check 6: HTTP → HTTPS redirect ← NEW
- **What:** If someone types `http://yourdomain.com`, do they get sent to the HTTPS version?
- **Why:** Without this, visitors who don't type `https://` see the insecure version. Chrome shows "Not Secure" in the address bar.
- **How:** HTTP request to `http://{domain}`. Check if response is 301/302 to `https://`.
- **Outcomes:**
  - No redirect → **High.** "Visitors typing your URL get an insecure version"
  - Redirects to HTTPS → Pass
- **Fix shown:** "Enable 'Force HTTPS' in your hosting dashboard" (platform-specific: Vercel does it by default, Railway needs config, Cloudflare has a toggle)

**Implementation:** Check 5 = `ssl` module socket connect. Check 6 = one `urllib` request to `http://` scheme, follow=False, check Location header. Both fast. ~2 seconds total.

---

## CATEGORY 3: Exposed Secrets — "Are my API keys public?" ← NEW CATEGORY

This is the hero category. The one that makes someone's stomach drop. The one they share.

### Check 7: .env file accessible ← NEW
- **What:** Can anyone read your `.env` file through the browser?
- **Why:** Your database password, API keys, everything — publicly readable. Bots actively crawl for this.
- **How:** HTTP HEAD request to `{url}/.env`. If 200, it's exposed.
- **Outcomes:**
  - Returns 200 → **Critical.** "Your .env file is publicly accessible — your secrets are exposed"
  - Returns 403/404 → Pass
- **Fix shown:** "Your deployment is serving your project root. Check your build output directory setting in your hosting config."

### Check 8: .git directory accessible ← NEW
- **What:** Can anyone download your source code and entire git history?
- **Why:** Every secret ever committed (even if later deleted) is recoverable from `.git`.
- **How:** HTTP HEAD request to `{url}/.git/config`. If 200, it's exposed.
- **Outcomes:**
  - Returns 200 → **Critical.** "Your entire source code and git history is downloadable"
  - Returns 403/404 → Pass
- **Fix shown:** "Block access to .git in your web server config, or fix your deployment to not serve the project root."

### Check 9: Secret keys in page source ← NEW
- **What:** Are there API secret keys, tokens, or database URLs in your HTML?
- **Why:** Bots scrape page source for these patterns. A leaked Stripe secret key = someone can charge your customers.
- **How:** Regex the HTML we already fetch for known secret patterns.
- **Patterns to flag (DEFINITELY secret — zero false positives):**
  ```
  sk_live_[a-zA-Z0-9]{20,}       # Stripe secret key
  sk_test_[a-zA-Z0-9]{20,}       # Stripe test secret key
  AKIA[A-Z0-9]{16}               # AWS access key
  sk-ant-[a-zA-Z0-9-]{20,}       # Anthropic API key
  xai-[a-zA-Z0-9]{20,}           # xAI API key
  ghp_[a-zA-Z0-9]{36,}           # GitHub personal access token
  gho_[a-zA-Z0-9]{36,}           # GitHub OAuth token
  glpat-[a-zA-Z0-9-]{20,}        # GitLab personal access token
  sk-[a-zA-Z0-9]{40,}            # OpenAI API key
  -----BEGIN.*PRIVATE KEY         # Private keys
  postgres(ql)?://\S+             # Database connection strings
  mongodb(\+srv)?://\S+           # MongoDB connection strings
  mysql://\S+                     # MySQL connection strings
  redis://\S+                     # Redis connection strings
  Bearer eyJ[a-zA-Z0-9]          # JWT tokens in HTML source
  ```
- **Patterns we DO NOT flag (public by design):**
  - `pk_live_`, `pk_test_` (Stripe publishable keys — meant to be in frontend)
  - Firebase config (`apiKey` in firebase config blocks)
  - Supabase anon key
  - Any key following `NEXT_PUBLIC_` or `VITE_` naming conventions in comments
- **Outcomes:**
  - Match found → **Critical.** "We found what looks like a [Stripe secret key / AWS access key / database URL] in your page source"
  - No match → Pass
- **Fix shown:** "Move this to a server-side environment variable. In Next.js, only variables starting with NEXT_PUBLIC_ are sent to the browser. Everything else stays on the server."

**Implementation:** Check 7-8 = two HEAD requests, trivial. Check 9 = regex scan of HTML we already fetch for SEO checks (no extra request). The regex list is specific enough for zero false positives. We only flag patterns that are NEVER meant to be public. Total: ~1 second.

---

## CATEGORY 4: DNS — "Why can't some people reach my site?"

### Check 10: www subdomain
- **What:** Does `www.yourdomain.com` work?
- **Why:** Many people still type www. If it doesn't resolve, they get an error page.
- **How:** DNS A/CNAME query for `www.{domain}`.
- **Outcomes:**
  - Doesn't resolve → **High.** "People typing www.yourdomain.com get an error"
  - Resolves → Pass
- **Fix shown:** "Add a CNAME record: www → yourdomain.com"

### Check 11: www ↔ apex redirect ← IMPROVED
- **What:** Do www and non-www point to the same site? Does one redirect to the other?
- **Why:** If both serve content independently, Google treats them as two separate sites. Your SEO splits in half.
- **How:** If www resolves (check 10 passed), request `https://www.{domain}` with redirect following disabled. Check if the response is a 301 to the apex (or vice versa). A 200 on both means both serve content independently — that's the problem.
- **Outcomes:**
  - Both return 200 (no redirect between them) → **High.** "Google sees two versions of your site — pick one and redirect the other"
  - One 301s to the other → Pass
  - www doesn't resolve → Skip (already flagged in check 10)
- **Fix shown:** "Set up a 301 redirect from www to your apex domain (or vice versa) in your hosting dashboard."

**Implementation:** Check 10 = DNS query (already built). Check 11 = two HTTP requests, compare final URLs. ~2 seconds total.

---

## CATEGORY 5: Security Headers — "Is my site vulnerable?"

We only check headers that have real, practical impact for a small app. No CSP (too complex to recommend), no X-Content-Type-Options (theoretical), no Referrer-Policy (privacy niche).

### Check 12: HSTS
- **What:** Does your site tell browsers "always use HTTPS, never HTTP"?
- **Why:** Without it, even with HTTPS redirect, the first request can be intercepted. Also: if you want to be on the HSTS preload list (Chrome hardcodes your domain as HTTPS-only), you need this header.
- **How:** Check response headers for `Strict-Transport-Security`.
- **Outcomes:**
  - Missing → **Medium.** "Your site allows insecure connections on first visit"
  - Present → Pass
- **Fix shown:** `Add header: Strict-Transport-Security: max-age=31536000; includeSubDomains`

**Implementation:** HSTS check uses headers from the HTTP response we already make. Zero extra requests. Trivial.

---

## CATEGORY 6: SEO & Shareability — "Why do my links look ugly?"

This is the category vibe coders notice first. They share their app on Twitter and it's a plain URL. They google their domain and it shows garbage.

### Check 14: Title tag
- **What:** Does your page have a `<title>`?
- **Why:** This is your browser tab text AND your Google search result title. Without it: blank tab, unrankable in search.
- **How:** Regex HTML for `<title>.+</title>`.
- **Outcomes:**
  - Missing → **High.** "Your browser tab is blank and Google can't rank you"
  - Present → Pass. Show the actual title.
- **Fix shown:** `Add <title>Your App — what it does</title> in your <head>`

### Check 15: Meta description
- **What:** Does your page have a meta description?
- **Why:** This is the text under your title in Google results. Without it, Google picks random text from your page.
- **How:** Regex HTML for `<meta name="description"`.
- **Outcomes:**
  - Missing → **High.** "Google shows random text from your page instead of your pitch"
  - Present → Pass. Show the actual description.
- **Fix shown:** `Add <meta name="description" content="What your app does in one sentence">`

### Check 16: Open Graph tags
- **What:** og:title, og:description, og:image meta tags.
- **Why:** Without them, sharing your link on Slack, Discord, LinkedIn, iMessage shows a plain URL. No preview image, no title, no description. Looks like spam.
- **How:** Regex HTML for `og:title`, `og:description`, `og:image`.
- **Outcomes:**
  - Missing all → **Medium.** "Your links look plain when shared — no image, no preview"
  - Missing og:image specifically → **Medium.** "Link previews have no image"
  - All present → Pass
- **Fix shown:** Copy-pasteable meta tags with placeholders

### Check 17: Twitter Card tags ← NEW
- **What:** `twitter:card`, `twitter:title`, `twitter:image` meta tags.
- **Why:** X/Twitter uses its own meta tags, separate from OG. Many vibe coders add OG tags and still get blank previews on X.
- **How:** Regex HTML for `twitter:card`.
- **Outcomes:**
  - Missing → **Medium.** "Your links on X/Twitter show no image preview even if OG tags are set"
  - Present → Pass
- **Fix shown:** `<meta name="twitter:card" content="summary_large_image">` + title + image tags

### Check 18: Viewport meta tag
- **What:** `<meta name="viewport" content="width=device-width, initial-scale=1">`
- **Why:** Without it, your site renders at desktop width on phones. Everything is tiny and broken.
- **How:** Regex HTML for `viewport`.
- **Outcomes:**
  - Missing → **High.** "Your site is broken on mobile phones"
  - Present → Pass
- **Fix shown:** Copy-pasteable tag

### Check 19: Canonical URL
- **What:** `<link rel="canonical" href="...">`
- **Why:** Without it, Google indexes `yourdomain.com/about`, `yourdomain.com/about/`, `www.yourdomain.com/about` as three different pages. Your ranking splits.
- **How:** Regex HTML for `rel="canonical"` or `rel='canonical'`.
- **Outcomes:**
  - Missing → **Medium.** "Google might index duplicate versions of your pages"
  - Present → Pass
- **Fix shown:** `Add <link rel="canonical" href="https://yourdomain.com/"> in <head>`

### Check 20: Sitemap.xml
- **What:** Does `/sitemap.xml` return a valid sitemap?
- **Why:** Google Search Console asks you to submit a sitemap. Without one, GSC can't show you which pages are indexed.
- **How:** HTTP GET `{url}/sitemap.xml`. Check for 200 + has content.
- **Outcomes:**
  - Missing/empty → **Medium.** "Google Search Console needs a sitemap to track your indexed pages"
  - Present → Pass
- **Fix shown:** "Most frameworks have a sitemap plugin. Next.js: next-sitemap. Astro: @astrojs/sitemap."

### Check 21: Favicon
- **What:** Does the site have a favicon?
- **Why:** Browser requests `/favicon.ico` on every page load. Missing = blank tab icon + 404s cluttering your server logs.
- **How:** Regex HTML for `favicon` or `icon` in link tags.
- **Outcomes:**
  - Missing → **Low.** "Your browser tab has a blank icon — looks unfinished"
  - Present → Pass
- **Fix shown:** "Add a 32×32 PNG at /favicon.ico and link it in <head>"

**Implementation:** All checks 14-21 use the HTML we already fetch for the page. Zero extra HTTP requests (except sitemap = 1 additional request). All regex-based. Already mostly built — just adding Twitter Card check.

---

## CATEGORY 7: Performance — "Why is my site slow?"

### Check 22: Response time ← NEW
- **What:** How long does your server take to respond?
- **Why:** >3 seconds and most visitors leave. Free-tier Railway/Render apps have 10-30 second cold starts.
- **How:** Time the HTTP request. Make TWO requests — first one warms up cold starts, second one measures real performance. Report both if they differ by >2x.
- **Outcomes:**
  - Warmup >10s, second request fast → **High.** "First visit takes Xs (cold start). After warmup: Xs. Your hosting sleeps when idle."
  - Both >3s → **High.** "Your site takes Xs to respond — most visitors will leave"
  - <3s → Pass. Show actual time.
- **Fix shown:** "If you're on a free tier, your app sleeps after inactivity. Upgrade to a paid plan or add a health check ping to keep it warm."

### Check 23: Compression
- **What:** Is your site using gzip or brotli compression?
- **Why:** Without compression, pages are 3-4x bigger than they need to be. Noticeably slower on mobile.
- **How:** Send request with `Accept-Encoding: gzip, deflate, br`. Check `Content-Encoding` response header.
- **Outcomes:**
  - No compression → **Medium.** "Your pages are 3-4x bigger than they need to be"
  - Compressed → Pass. Show encoding type.
- **Fix shown:** "Vercel and Cloudflare do this automatically. For custom servers: enable gzip in nginx or your framework config."

**Implementation:** Check 22 = two timed HTTP requests (~5-15 seconds depending on cold start). Check 23 = header from existing response. Already partially built.

---

## CATEGORY 8: Broken Resources — "Why are things missing on my site?"

### Check 24: Mixed content ← NEW
- **What:** Is your HTTPS page loading images, scripts, or stylesheets over plain HTTP?
- **Why:** Browsers silently block mixed content. Images don't show, scripts don't run. Your site looks broken with no visible error message — you'll never know unless someone tells you or you check the console.
- **How:** Regex the HTML for `http://` in `src=`, `href=` (for stylesheets/scripts, not regular `<a>` links), `action=` attributes. Exclude `http://localhost` and `http://127.0.0.1`.
- **Outcomes:**
  - Found http:// resources → **High.** "Your site loads images/scripts over insecure HTTP — browsers block them silently. These resources are invisible to your visitors."
  - Clean → Pass
- **Fix shown:** "Change these http:// URLs to https:// or use protocol-relative //. Broken resources: [list the specific URLs found]."

**Implementation:** Regex on existing HTML. Zero extra requests.

---

## CATEGORY 9: Polish — "Does my site look professional?"

### Check 24: Custom 404 page
- **What:** Does a nonexistent URL return a styled error page?
- **Why:** Default framework 404s ("Cannot GET /whatever") look abandoned. A custom 404 with a link home keeps visitors on your site.
- **How:** HTTP GET `{url}/{random-string}`. Check if response has meaningful HTML (>500 bytes, has a link) vs bare error text.
- **Outcomes:**
  - Raw error or empty → **Low.** "Broken links show a default error page — visitors will think your site is abandoned"
  - Styled page → Pass
- **Fix shown:** "Create a 404.html (or /404 route) in your framework with a link back to your homepage."

**Implementation:** One HTTP request to a random path. ~1 second.

---

## What we DON'T check (and why)

| Dropped check | Why |
|---------------|-----|
| Server version disclosure | Vibe coders deploy on Vercel/Railway/Render — they don't control the Server header. Can't fix it. Showing an unfixable issue erodes trust. |
| Content Security Policy | Too complex to configure correctly. A wrong CSP breaks your own site. Harmful to recommend to beginners. |
| CAA record | Your hosting provider handles certificate issuance. Enterprise concern, not vibe coder concern. |
| X-Content-Type-Options | Prevents a theoretical browser sniffing attack with near-zero real-world impact. |
| X-Frame-Options | Clickjacking protection. Your MVP is not getting clickjacked. |
| Referrer-Policy | Prevents URL leaking to third parties. Privacy niche, nothing breaks without it. |
| robots.txt | Default = crawl everything. That's what new sites want. |
| Cookie security flags | Modern framework auth libraries handle this by default. |
| manifest.json | PWA install — irrelevant to 95% of audience. |
| Permissions-Policy | Controls camera/mic/geolocation access. Too niche. |
| DNSSEC | Users don't control this — registrar/nameserver does. |

---

## Total: 24 checks

| # | Check | Category | Severity | Extra requests needed |
|---|-------|----------|----------|-----------------------|
| 1 | SPF record | Email | C/L | DNS query |
| 2 | DMARC record | Email | C/H/M | DNS query |
| 3 | DMARC reporting | Email | M | — (parsed from #2) |
| 4 | MX records | Email | Info | DNS query |
| 5 | SSL certificate | SSL | C/H | SSL socket |
| 6 | HTTP→HTTPS redirect | SSL | H | 1 HTTP request |
| 7 | .env exposed | Secrets | C | 1 HEAD request |
| 8 | .git exposed | Secrets | C | 1 HEAD request |
| 9 | Secret keys in HTML | Secrets | C | — (uses existing HTML) |
| 10 | www resolves | DNS | H | DNS query |
| 11 | www ↔ apex redirect | DNS | H | 1-2 HTTP requests |
| 12 | HSTS header | Security | M | — (uses existing headers) |
| 13 | Title tag | SEO | H | — (uses existing HTML) |
| 14 | Meta description | SEO | H | — (uses existing HTML) |
| 15 | Open Graph tags | SEO | M | — (uses existing HTML) |
| 16 | Twitter Card tags | SEO | M | — (uses existing HTML) |
| 17 | Viewport tag | SEO | H | — (uses existing HTML) |
| 18 | Canonical URL | SEO | M | — (uses existing HTML) |
| 19 | Sitemap.xml | SEO | M | 1 HTTP request |
| 20 | Favicon | SEO | L | — (uses existing HTML) |
| 21 | Response time | Perf | H | 2 HTTP requests (warmup + measure) |
| 22 | Compression | Perf | M | — (uses existing headers) |
| 23 | Mixed content | Breakage | H | — (uses existing HTML) |
| 24 | Custom 404 | Polish | L | 1 HTTP request |

### Network requests per scan

- 3-4 DNS queries (SPF/TXT, DMARC, MX, www)
- 1 SSL socket connection
- ~7-8 HTTP requests (main page, http:// redirect check, .env, .git, www version, sitemap, 404 page, warmup for timing)
- Several regex passes on one HTML document

**Total scan time estimate: 5-8 seconds** (dominated by the response time warmup request on cold-start sites).

---

## Implementation plan

**Phase 1 — Rewrite scanner.py with the 25 checks.** Replace current checks with the blueprint above. Human-readable titles, actionable fix text, no jargon.

**Phase 2 — Update the landing page.** Match the new categories and check titles. Make sure each issue card shows the fix, not just the problem.

**Phase 3 — Add SEO article links.** Each issue links to a guide page. "Why are my emails going to spam?" → `/guides/email-deliverability`. Build these pages over time.
