"""
SEO metadata for each guide page.
Content lives in static/guide.html (JS). This module only provides:
  - seo_title      → <title> tag (keyword-optimised)
  - description    → <meta name="description">
  - how_steps      → plain-text steps for HowTo JSON-LD schema (rich snippets)
  - category       → for breadcrumb schema
"""

GUIDES_META = {
    "spf-record": {
        "seo_title": "SPF Record Missing: How to Fix Email Authentication | didyouship.dev",
        "description": "No SPF record means Gmail can't verify your emails and routes them to spam. Step-by-step fix for Google Workspace, Resend, SendGrid, Postmark, and more.",
        "category": "Email Deliverability",
        "how_steps": [
            "List every service that sends email from your domain — your email provider, transactional email service, CRM, and newsletter tool.",
            "Get the SPF include value from each service's documentation (usually under 'Authentication' or 'Domain setup').",
            "Create a single TXT record at your root domain combining all your senders. Example: v=spf1 include:_spf.google.com include:_spf.resend.com ~all",
            "Add the TXT record in your DNS registrar (Cloudflare, Namecheap, Route 53, etc.) for the @ or root domain.",
            "Verify with: nslookup -type=TXT yourdomain.com or mxtoolbox.com/spf.aspx",
            "Once all your sending is confirmed covered, change ~all to -all for full enforcement.",
        ],
    },
    "dmarc": {
        "seo_title": "DMARC Record Missing: Stop Email Spoofing on Your Domain | didyouship.dev",
        "description": "No DMARC record lets anyone send phishing emails pretending to be from your domain. Learn how to add DMARC and what policy to use.",
        "category": "Email Deliverability",
        "how_steps": [
            "Confirm SPF and DKIM are already set up — DMARC enforces them.",
            "Add a TXT record at _dmarc.yourdomain.com with value: v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com",
            "Replace the rua address with your own, or use a free DMARC reporting service like Postmark's DMARC monitor.",
            "If unsure whether all your legitimate email passes, start with p=none to observe reports for a week.",
            "Escalate to p=quarantine, then p=reject once you've confirmed all your real email passes.",
        ],
    },
    "email-spoofing": {
        "seo_title": "Email Spoofing Protection: SPF, DKIM and DMARC Explained | didyouship.dev",
        "description": "Without SPF, DKIM, and DMARC, anyone can send email pretending to be from your domain. Learn how all three work and how to set them up.",
        "category": "Email Deliverability",
        "how_steps": [
            "Add an SPF record — TXT record at your root domain listing your authorised sending services.",
            "Enable DKIM signing in your email provider dashboard and add the DNS record they give you.",
            "Add a DMARC record at _dmarc.yourdomain.com with p=quarantine or p=reject.",
            "Monitor DMARC reports for a week to confirm no legitimate email is being rejected.",
        ],
    },
    "dkim-setup": {
        "seo_title": "DKIM Not Configured: How to Set Up Email Signing | didyouship.dev",
        "description": "Without DKIM, Gmail can't verify your emails are genuine and inbox placement drops. Learn how to enable DKIM for any email provider in minutes.",
        "category": "Email Deliverability",
        "how_steps": [
            "Log in to your email sending service (Resend, Postmark, Google Workspace, SendGrid, etc.).",
            "Navigate to domain authentication, sender verification, or DKIM settings.",
            "The service will generate one or two DNS TXT records — copy them exactly.",
            "Add those TXT records to your DNS, named exactly as instructed (e.g. google._domainkey or s1._domainkey).",
            "Click Verify in the service dashboard — DNS propagation may take a few minutes.",
        ],
    },
    "ip-blacklisted": {
        "seo_title": "Mail Server IP Blacklisted: How to Check and Get Delisted | didyouship.dev",
        "description": "If your mail server IP is on Spamhaus or Barracuda, emails are silently dropped. Learn how to check your IP, request delisting, and prevent it recurring.",
        "category": "Email Deliverability",
        "how_steps": [
            "Check your mail server IP at mxtoolbox.com/blacklists.aspx to see which blacklists it appears on.",
            "For Spamhaus: visit spamhaus.org/lookup and follow the removal request instructions.",
            "For Barracuda: visit barracudacentral.org/rbl/removal-request and submit a removal form.",
            "For SpamCop: listings expire automatically within 24 hours of no new spam reports.",
            "If you're on shared hosting, consider switching to a managed sending service with clean IP pools (Resend, Postmark, SendGrid).",
        ],
    },
    "email-deliverability": {
        "seo_title": "Email Deliverability: Why Emails Land in Spam and How to Fix It | didyouship.dev",
        "description": "Emails landing in spam? Learn the three DNS records every domain needs — SPF, DKIM, and DMARC — to reliably reach the inbox.",
        "category": "Email Deliverability",
        "how_steps": [
            "Run an email health check at mxtoolbox.com/emailhealth.aspx to see what's missing.",
            "Add an SPF record — TXT record at your root domain listing your email sending services.",
            "Enable DKIM in your email provider dashboard and add the DNS record provided.",
            "Add a DMARC record at _dmarc.yourdomain.com with p=quarantine.",
            "Use a reputable transactional email service for all automated email (password resets, receipts, notifications).",
        ],
    },
    "ssl-certificate": {
        "seo_title": "SSL Certificate Expired or Invalid: How to Renew and Fix It | didyouship.dev",
        "description": "An expired SSL certificate blocks your site with a full-page browser warning. Learn how to renew it, enable auto-renewal, and fix invalid cert errors.",
        "category": "SSL & HTTPS",
        "how_steps": [
            "Check your cert expiry: openssl s_client -connect yourdomain.com:443 | openssl x509 -noout -dates",
            "Log in to your hosting dashboard and look for SSL or Certificate settings.",
            "Enable auto-renewal — Vercel, Netlify, Cloudflare, and Render do this automatically.",
            "If renewal failed, verify your domain's DNS A/CNAME records still point to your host.",
            "For custom servers using certbot, run: certbot renew --dry-run to confirm the renewal process works.",
        ],
    },
    "https-redirect": {
        "seo_title": "HTTP to HTTPS Redirect: Force HTTPS on Vercel, Cloudflare, Nginx | didyouship.dev",
        "description": "Without a redirect, visitors get the insecure version of your site. Learn how to force HTTPS on Vercel, Netlify, Cloudflare, Railway, and Nginx.",
        "category": "SSL & HTTPS",
        "how_steps": [
            "Log in to your hosting dashboard and find HTTPS or redirect settings.",
            "Enable 'Force HTTPS' or 'Always Use HTTPS' — Vercel does this by default; Netlify has it under Domain settings.",
            "For Cloudflare: SSL/TLS → Edge Certificates → Always Use HTTPS → On.",
            "For Nginx: add a server block on port 80 that returns a 301 redirect to https://.",
            "Test by visiting http://yourdomain.com in a browser — it should redirect to https://.",
        ],
    },
    "env-exposed": {
        "seo_title": ".env File Exposed: How to Secure Your Environment Variables | didyouship.dev",
        "description": "A publicly accessible .env file exposes your database passwords and API keys to anyone. Learn how to fix it immediately and rotate compromised credentials.",
        "category": "Exposed Secrets",
        "how_steps": [
            "Immediately rotate all credentials in your .env — assume they have been compromised.",
            "Revoke and reissue: database passwords, API keys, OAuth secrets, and any other secrets in the file.",
            "Fix your deployment configuration to serve only the build output folder (e.g. .next/, dist/, build/), not the project root.",
            "In Vercel or Netlify, check your project's Output Directory setting in the dashboard.",
            "Verify the fix: visit yourdomain.com/.env in a browser — it should return a 404.",
        ],
    },
    "git-exposed": {
        "seo_title": ".git Directory Exposed: Block Public Access to Your Source Code | didyouship.dev",
        "description": "An exposed .git directory lets anyone download your full source code and commit history. Learn how to block it with Nginx, Apache, and Caddy.",
        "category": "Exposed Secrets",
        "how_steps": [
            "Immediately rotate any credentials that have ever been committed to your git history.",
            "Use BFG Repo Cleaner or git filter-repo to permanently remove secrets from git history.",
            "Add a rule to your web server to block access to .git/: in Nginx, use 'location ~ /\\.git { deny all; return 404; }'",
            "Fix your deployment to not serve the project root — only the build output directory.",
            "Verify the fix: visit yourdomain.com/.git/config — it should return 404.",
        ],
    },
    "leaked-secrets": {
        "seo_title": "API Keys in Page Source: How to Remove Exposed Secrets | didyouship.dev",
        "description": "API keys in your HTML source are scraped and exploited within minutes. Learn how to move them server-side in Next.js, Vite, and React.",
        "category": "Exposed Secrets",
        "how_steps": [
            "Immediately revoke and rotate the exposed key from its provider's dashboard.",
            "Audit recent usage of the key — check for unexpected API calls or charges.",
            "Move the key to a server-side environment variable.",
            "Create an API proxy endpoint in your backend that calls the third-party API using the server-side key.",
            "Update your frontend to call your own backend endpoint instead of the third-party API directly.",
            "In Next.js, only use NEXT_PUBLIC_ prefix for truly browser-safe values (like a Stripe publishable key).",
        ],
    },
    "www-redirect": {
        "seo_title": "www Subdomain Not Working: Set Up www Redirect for SEO | didyouship.dev",
        "description": "www.yourdomain.com not working or both serving content? You're splitting your SEO rankings. Learn how to set up a 301 redirect correctly.",
        "category": "DNS",
        "how_steps": [
            "Decide on your canonical domain — either yourdomain.com (apex) or www.yourdomain.com.",
            "In your DNS settings, add a CNAME record for www pointing to your apex domain or hosting provider.",
            "Configure a 301 redirect from the non-canonical version to the canonical one.",
            "In Cloudflare: Rules → Redirect Rules → match www.domain.com/* → 301 to https://domain.com/$1.",
            "Verify both versions work: one should redirect to the other with a 301 status code.",
        ],
    },
    "hsts-header": {
        "seo_title": "HSTS Header Missing: Add Strict-Transport-Security to Your Site | didyouship.dev",
        "description": "Without HSTS, the first visit to your site on public WiFi can be intercepted. Learn how to add the Strict-Transport-Security header.",
        "category": "Security Headers",
        "how_steps": [
            "Add the Strict-Transport-Security response header to all HTTPS responses.",
            "Use value: max-age=31536000; includeSubDomains (1 year, including subdomains).",
            "For Cloudflare: SSL/TLS → Edge Certificates → HTTP Strict Transport Security → Enable.",
            "For Vercel: add a headers config in vercel.json with the Strict-Transport-Security key-value pair.",
            "For Nginx: add_header Strict-Transport-Security 'max-age=31536000; includeSubDomains' always;",
            "For Express/Node: use the helmet package — app.use(helmet()) enables HSTS by default.",
        ],
    },
    "page-title": {
        "seo_title": "Page Title Tag Missing: How to Add a Title Tag for SEO | didyouship.dev",
        "description": "A missing title tag means Google can't rank your page and browser tabs are blank. Learn the right format and how to set it in any framework.",
        "category": "SEO",
        "how_steps": [
            "Add a <title> tag inside your HTML <head> element.",
            "Format: Your App Name — what it does in 5-7 words (50-60 characters total).",
            "In Next.js App Router: export a metadata object with a title property from your page.js or layout.js.",
            "In Next.js Pages Router: use the <Head> component from next/head.",
            "In Astro: set a title variable in frontmatter and render it in your layout's <head>.",
            "Verify in browser: the tab should show your title text.",
        ],
    },
    "meta-description": {
        "seo_title": "Meta Description Missing: Write and Add It for Better Click-Through | didyouship.dev",
        "description": "Without a meta description, Google shows random text in search results. Learn how to write a good one and add it in Next.js, Astro, and plain HTML.",
        "category": "SEO",
        "how_steps": [
            "Write a description of 150-160 characters that summarises what the page does.",
            "Add inside your <head>: <meta name=\"description\" content=\"Your description here.\">",
            "In Next.js App Router: add a description field to your exported metadata object.",
            "In Next.js Pages Router: add a <meta> tag inside the <Head> component.",
            "Verify with: view-source:yourdomain.com and search for 'description'.",
        ],
    },
    "open-graph": {
        "seo_title": "Open Graph Tags Missing: Add Rich Link Previews to Your Site | didyouship.dev",
        "description": "Without Open Graph tags, links shared on Slack, Discord, and LinkedIn show as plain text. Learn how to add og:title, og:image, and og:url.",
        "category": "SEO",
        "how_steps": [
            "Add four core OG meta tags inside your <head>: og:title, og:description, og:image, og:url.",
            "Create an OG image at 1200x630px — this is the preview image shown when links are shared.",
            "Set og:url to the canonical URL of the page (e.g. https://yourdomain.com).",
            "Test with opengraph.xyz or the Facebook Sharing Debugger (developers.facebook.com/tools/debug).",
            "For dynamic OG images, use Vercel OG (@vercel/og) to generate images from JSX at the edge.",
        ],
    },
    "twitter-cards": {
        "seo_title": "Twitter Card Tags Missing: Add Rich Previews for X/Twitter | didyouship.dev",
        "description": "Open Graph tags aren't enough for X/Twitter — you need Twitter Card tags too. Learn how to add them so your links show images on X.",
        "category": "SEO",
        "how_steps": [
            "Add twitter:card meta tag with value 'summary_large_image' for a large image preview.",
            "Add twitter:title, twitter:description, and twitter:image inside your <head>.",
            "You can reuse the same image as your og:image — point twitter:image to the same URL.",
            "Test with the Twitter Card Validator at cards-dev.twitter.com/validator.",
        ],
    },
    "viewport-meta": {
        "seo_title": "Viewport Meta Tag Missing: Fix Broken Mobile Display | didyouship.dev",
        "description": "Without the viewport meta tag, your site renders at desktop width on phones. Learn how to add it and fix mobile rendering in any framework.",
        "category": "SEO",
        "how_steps": [
            "Add this tag inside your HTML <head>: <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            "In Next.js App Router: this is included automatically — check your root layout.js.",
            "In Next.js Pages Router: check your _document.js or add it to _app.js Head.",
            "In Astro: add it to your base layout file's <head> section.",
            "Test on a real device or using Chrome DevTools mobile emulation — site should fill screen width without zooming.",
        ],
    },
    "canonical-url": {
        "seo_title": "Canonical URL Missing: Prevent Duplicate Content Splitting SEO | didyouship.dev",
        "description": "Without a canonical URL tag, Google may index multiple versions of your page and split your rankings. Learn how to add it in any framework.",
        "category": "SEO",
        "how_steps": [
            "Add a canonical link tag inside your <head>: <link rel=\"canonical\" href=\"https://yourdomain.com/page\">",
            "Always use the https:// version, your preferred domain (www or apex), and a consistent trailing slash policy.",
            "In Next.js App Router: add alternates.canonical to your metadata export.",
            "In Next.js Pages Router: add the <link rel='canonical'> tag inside the <Head> component.",
            "Add the canonical tag to every page on your site, not just the homepage.",
        ],
    },
    "sitemap": {
        "seo_title": "Sitemap.xml Missing: Create and Submit a Sitemap to Google | didyouship.dev",
        "description": "Sitemap.xml helps Google find all your pages and is required for Google Search Console. Learn how to generate it for Next.js, Astro, Django, and more.",
        "category": "SEO",
        "how_steps": [
            "Choose a sitemap generator for your framework (see providers below).",
            "Configure it to include all public pages and their canonical URLs.",
            "Deploy and verify the sitemap is accessible at https://yourdomain.com/sitemap.xml.",
            "Go to Google Search Console (search.google.com/search-console).",
            "Navigate to Sitemaps in the left menu and submit your sitemap URL.",
        ],
    },
    "favicon": {
        "seo_title": "Favicon Missing: Add a Browser Tab Icon to Your Site | didyouship.dev",
        "description": "A missing favicon causes a 404 error on every page load and leaves your browser tab blank. Learn how to create and add one in 5 minutes.",
        "category": "SEO",
        "how_steps": [
            "Create a 32x32px icon using Figma, favicon.io, or any image editor.",
            "Save it as favicon.ico and place it in your public directory.",
            "Add a link tag inside your <head>: <link rel=\"icon\" href=\"/favicon.ico\">",
            "For better quality on retina screens, also add an SVG version: <link rel=\"icon\" href=\"/favicon.svg\" type=\"image/svg+xml\">",
            "Verify: open your site and check the browser tab shows the icon.",
        ],
    },
    "response-time": {
        "seo_title": "Slow Response Time & Cold Starts: Fix Server Performance | didyouship.dev",
        "description": "Slow response times drive users away. Learn how to fix cold starts on Railway, Render, and Fly.io and how to diagnose a genuinely slow server.",
        "category": "Performance",
        "how_steps": [
            "Determine if it's a cold start: run two consecutive requests — if the first is slow but the second is fast, it's a cold start.",
            "For cold starts: upgrade to a paid plan on your hosting platform (Railway Hobby, Render Starter, Fly paid machines).",
            "Alternatively, use a keep-alive service to ping your health endpoint every 5 minutes (BetterStack, cron-job.org).",
            "For genuinely slow responses: check your server's region and deploy closer to your users.",
            "Profile slow database queries and add indexes for common query patterns.",
            "Move heavy computations out of the request path into background jobs or queues.",
        ],
    },
    "compression": {
        "seo_title": "Gzip Compression Not Enabled: Speed Up Your Site for Free | didyouship.dev",
        "description": "Enabling gzip or Brotli compression reduces page size by 60-80% at zero cost. Learn how to enable it in Nginx, Express, FastAPI, and on Cloudflare.",
        "category": "Performance",
        "how_steps": [
            "Check if compression is already enabled: curl -H 'Accept-Encoding: gzip' -I https://yourdomain.com — look for Content-Encoding: gzip in the response.",
            "If using Cloudflare, Vercel, or Netlify — compression is enabled automatically, no action needed.",
            "For Nginx: add gzip on; and gzip_types for html/css/js/json to your server config.",
            "For Express/Node: install the compression package and add app.use(require('compression')()) before your routes.",
            "For FastAPI/uvicorn: add GZipMiddleware from starlette.middleware.gzip.",
            "Redeploy and verify: the Content-Encoding: gzip header should appear on responses.",
        ],
    },
    "mixed-content": {
        "seo_title": "Mixed Content Errors: Fix HTTP Resources on HTTPS Pages | didyouship.dev",
        "description": "HTTP resources on an HTTPS page are silently blocked by browsers — images don't show, scripts don't run. Learn how to find and fix mixed content.",
        "category": "Breakage",
        "how_steps": [
            "Open Chrome DevTools (F12) → Console tab and look for 'Mixed Content' warnings.",
            "Find all http:// resource URLs in your HTML, CSS, and JavaScript files.",
            "Change each http:// resource URL to https:// — most CDNs and services support HTTPS.",
            "For resources that don't support HTTPS, download and self-host them.",
            "Add a Content-Security-Policy header with upgrade-insecure-requests to auto-upgrade any remaining HTTP resources.",
            "Re-check the Console after deploying to confirm no mixed content warnings remain.",
        ],
    },
    "custom-404": {
        "seo_title": "No Custom 404 Page: Create One for Next.js, Astro, and SvelteKit | didyouship.dev",
        "description": "A missing custom 404 page shows users a bare error. Learn how to create a branded 404 page in Next.js, Astro, SvelteKit, Netlify, and Nginx.",
        "category": "Polish",
        "how_steps": [
            "Create a 404 page in your framework's designated location (see providers below).",
            "Include your site's header and navigation so users can easily find their way back.",
            "Add a clear heading ('Page not found'), a short explanation, and a link back to the homepage.",
            "Optionally add links to your most popular pages or a search box.",
            "Test by visiting a URL that doesn't exist on your site — the custom 404 page should appear.",
        ],
    },
}

# Sidebar navigation order
NAV = [
    {"cat": "Email",       "guides": ["spf-record", "dmarc", "email-spoofing", "dkim-setup", "ip-blacklisted", "email-deliverability"]},
    {"cat": "SSL",         "guides": ["ssl-certificate", "https-redirect"]},
    {"cat": "Secrets",     "guides": ["env-exposed", "git-exposed", "leaked-secrets"]},
    {"cat": "DNS",         "guides": ["www-redirect"]},
    {"cat": "Security",    "guides": ["hsts-header"]},
    {"cat": "SEO",         "guides": ["page-title", "meta-description", "open-graph", "twitter-cards", "viewport-meta", "canonical-url", "sitemap", "favicon"]},
    {"cat": "Performance", "guides": ["response-time", "compression"]},
    {"cat": "Breakage",    "guides": ["mixed-content"]},
    {"cat": "Polish",      "guides": ["custom-404"]},
]

ALL_SLUGS = [slug for group in NAV for slug in group["guides"]]
