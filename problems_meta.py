"""
Problem hub pages — consequence-driven content targeting symptom searches.
Each page answers "why is X broken?" and links to the specific fix guides.
"""

PROBLEMS = {

"emails-going-to-spam": {
    "seo_title": "Why Are My Emails Going to Spam? 5 Causes & Fixes | didyouship.dev",
    "description": "Emails landing in spam? Missing SPF, DKIM, or DMARC records are the most common causes. Learn why each one matters and how to fix your email deliverability.",
    "h1": "Why Are Your Emails Going to Spam?",
    "intro": "If your signup confirmations, password resets, or invoices are landing in spam — or worse, never arriving at all — it's almost always a DNS configuration problem, not a code problem. Here are the most common causes, in order of impact.",
    "causes": [
        {
            "title": "No SPF record — email providers can't verify you're the sender",
            "severity": "critical",
            "detail": "SPF is a DNS record listing which servers are authorised to send email from your domain. Without it, Gmail and Outlook see email from your domain as unverified and apply aggressive spam filtering. Setting it up is a single DNS record change.",
            "guide": "spf-record",
            "fix_title": "How to Add an SPF Record",
        },
        {
            "title": "No DMARC record — your domain has no email policy",
            "severity": "critical",
            "detail": "DMARC tells email providers what to do when they receive email from your domain that fails SPF or DKIM checks. Without DMARC, providers give your domain lower trust scores. Gmail and Yahoo have required DMARC since 2024 for reliable inbox delivery.",
            "guide": "dmarc",
            "fix_title": "How to Add a DMARC Record",
        },
        {
            "title": "DKIM not configured — emails have no cryptographic signature",
            "severity": "high",
            "detail": "DKIM adds a digital signature to every email you send, proving it came from your authorised server and wasn't tampered with in transit. Without DKIM, Gmail can't cryptographically verify your email is genuine — even if SPF passes.",
            "guide": "dkim-setup",
            "fix_title": "How to Set Up DKIM",
        },
        {
            "title": "Mail server IP is blacklisted",
            "severity": "critical",
            "detail": "Email providers check real-time blacklists (Spamhaus, Barracuda, SpamCop) before accepting mail. If your server's IP is listed — which often happens on shared hosting — every email you send is silently dropped or spam-foldered. No error, no bounce, just silence.",
            "guide": "ip-blacklisted",
            "fix_title": "How to Check and Fix a Blacklisted IP",
        },
        {
            "title": "DMARC is set to monitor only (p=none)",
            "severity": "high",
            "detail": "A DMARC record with p=none collects reports but doesn't enforce anything. Spoofed emails still get delivered, and your domain has a weaker trust score with inbox providers than one with p=quarantine or p=reject.",
            "guide": "dmarc",
            "fix_title": "How to Enforce DMARC",
        },
    ],
    "faqs": [
        {
            "q": "Why do my emails work fine from Gmail but not from my app?",
            "a": "When you send from Gmail, Google handles all email authentication for you automatically. When your app sends email (password resets, notifications, invoices), it sends directly from your domain and needs SPF, DKIM, and DMARC configured for your specific sending service (Resend, Postmark, SendGrid, etc.). These are separate configurations.",
        },
        {
            "q": "Why are my password reset emails going to spam?",
            "a": "Transactional emails like password resets are automated bulk sends, which email providers scrutinise more heavily. Missing DKIM alone can push all transactional email to spam. Missing SPF or a blacklisted IP makes it worse. Use a dedicated transactional email service (Resend, Postmark) and set up SPF + DKIM + DMARC for guaranteed delivery.",
        },
        {
            "q": "How do I test if my emails will be delivered?",
            "a": "Send a test email to mail-tester.com — it gives your email a score out of 10 and shows exactly what's failing. GlockApps and Mailtrap also offer inbox testing across major providers. For DNS records specifically, use mxtoolbox.com/emailhealth.aspx.",
        },
        {
            "q": "How long does it take to fix email deliverability?",
            "a": "DNS changes (SPF, DKIM, DMARC) propagate within 0–48 hours. Once propagated, Gmail and Outlook apply them immediately. You should see improvement within 24–48 hours. Domain reputation recovery after a blacklisting can take 1–4 weeks. Getting delisted from Spamhaus usually takes 24–72 hours after submitting a removal request.",
        },
        {
            "q": "Do I need all three — SPF, DKIM, and DMARC?",
            "a": "Yes. SPF proves which server sent the email. DKIM proves the email content is authentic. DMARC ties them together and tells providers what to do when they fail. All three together are what Gmail and Yahoo now require for reliable delivery. Each one alone provides only partial protection.",
        },
        {
            "q": "My emails were landing in inboxes before — why did they suddenly start going to spam?",
            "a": "Common causes: your sending IP got blacklisted (especially on shared hosting), a spike in complaint rates flagged your domain, your DNS records were accidentally changed or expired, or your email provider changed something in their infrastructure. Check your DMARC reports for authentication failures and mxtoolbox.com for blacklist status.",
        },
    ],
},

"not-in-google": {
    "seo_title": "Why Isn't My Website Showing in Google? 5 Causes & Fixes | didyouship.dev",
    "description": "New website not appearing in Google search? Missing sitemap, no title tag, or viewport issues are the most common causes. Here's how to diagnose and fix each one.",
    "h1": "Why Isn't Your Website Showing in Google?",
    "intro": "Getting into Google's index is usually straightforward, but several common mistakes can prevent your site from appearing in search results entirely — or make it rank far lower than it should. Here's what to check.",
    "causes": [
        {
            "title": "No sitemap.xml — Google doesn't know your pages exist",
            "severity": "medium",
            "detail": "Without a sitemap, Google discovers your pages only by following links. New sites or sites with few external links may never be fully crawled. A sitemap.xml at /sitemap.xml tells Google exactly which pages exist and when they were last updated, and you can submit it directly in Google Search Console.",
            "guide": "sitemap",
            "fix_title": "How to Create a Sitemap.xml",
        },
        {
            "title": "No page title tag — Google can't understand what your page is about",
            "severity": "high",
            "detail": "The <title> tag is Google's primary signal for what a page is about. Without it, Google either invents a title from your page content or ranks you lower for relevant queries. The title is also the clickable headline shown in search results.",
            "guide": "page-title",
            "fix_title": "How to Add a Page Title Tag",
        },
        {
            "title": "No viewport meta tag — broken mobile experience hurts rankings",
            "severity": "high",
            "detail": "Google uses mobile-first indexing, meaning it crawls and ranks the mobile version of your site. A missing viewport meta tag means your site is broken on mobile — everything is tiny and users must pinch-zoom. Google penalises sites with poor mobile experience.",
            "guide": "viewport-meta",
            "fix_title": "How to Fix Mobile Display",
        },
        {
            "title": "No canonical URL — Google may be indexing the wrong version",
            "severity": "medium",
            "detail": "Your page might be accessible at yourdomain.com, www.yourdomain.com, and yourdomain.com/? as separate URLs. Without a canonical tag, Google might index all of them as duplicate pages and split your ranking signals instead of consolidating them.",
            "guide": "canonical-url",
            "fix_title": "How to Add Canonical URLs",
        },
        {
            "title": "No meta description — lower click-through from search results",
            "severity": "medium",
            "detail": "Meta description doesn't directly affect rankings, but it's the snippet shown under your title in Google results. Without one, Google picks random text from your page — usually something unhelpful. Better descriptions mean more clicks, which over time signals to Google that your result is worth ranking higher.",
            "guide": "meta-description",
            "fix_title": "How to Write a Meta Description",
        },
    ],
    "faqs": [
        {
            "q": "How long does it take to appear in Google after launching a site?",
            "a": "For new sites, it typically takes 1–4 weeks after your sitemap is submitted to Google Search Console. Submit your sitemap at search.google.com/search-console and use the URL Inspection tool to request indexing of your most important pages. Established domains with regular content see changes indexed within days.",
        },
        {
            "q": "How do I check if Google has indexed my site?",
            "a": "Search for site:yourdomain.com in Google — if no results appear, your site isn't indexed. More detail is available in Google Search Console under Pages, which shows exactly which URLs are indexed, which have errors, and why specific pages were excluded.",
        },
        {
            "q": "Why did my site disappear from Google?",
            "a": "Common causes: the site was down when Google crawled it, a robots.txt change accidentally blocked crawling (disallow: / is a common mistake), a noindex meta tag was added to the wrong pages, or the domain expired briefly. Check Google Search Console → Pages → Not Indexed for specific error reasons.",
        },
        {
            "q": "Does a single-page React or Vue app have trouble getting indexed?",
            "a": "Yes, often. Google can index JavaScript-rendered content, but it's a two-step process — Google first crawls the empty HTML, then comes back later to render the JS. This indexing lag can be weeks. For SEO-critical pages, use server-side rendering (Next.js, Nuxt, Astro) to put content directly in the HTML response.",
        },
        {
            "q": "My site is indexed but not ranking — why?",
            "a": "Being indexed and ranking are different things. To rank well, you need relevant content targeting specific search queries, quality external links pointing to your site, good Core Web Vitals (page speed, mobile experience), and proper on-page optimisation (title, descriptions, headings). Run a scan to find the technical issues first, then focus on content.",
        },
    ],
},

"link-preview-not-working": {
    "seo_title": "Why Links Look Bad on Slack, Discord & Twitter? Fix Previews | didyouship.dev",
    "description": "Links showing no image or preview on Slack, Discord, LinkedIn, or Twitter? Missing Open Graph tags are the cause. Learn how to fix link previews in under 10 minutes.",
    "h1": "Why Do Your Links Look Bad When Shared?",
    "intro": "When someone shares your URL on Slack, Discord, LinkedIn, iMessage, or Twitter, they expect a rich card — title, description, and an image preview. If they see a plain URL instead, Open Graph or Twitter Card tags are missing from your page. Here's what to add.",
    "causes": [
        {
            "title": "No Open Graph tags — no preview on Slack, Discord, LinkedIn, or iMessage",
            "severity": "medium",
            "detail": "Open Graph is the universal standard for link previews. Slack, Discord, LinkedIn, Facebook, WhatsApp, iMessage, and most other platforms use og:title, og:description, og:image, and og:url to build the preview card. Without these four tags, every shared link looks like a plain URL.",
            "guide": "open-graph",
            "fix_title": "How to Add Open Graph Tags",
        },
        {
            "title": "OG image missing — preview shows text but no image",
            "severity": "medium",
            "detail": "You have og:title and og:description but no og:image. Most platforms show a large image card when an image is present — links with images get dramatically more clicks than text-only previews. A 1200×630px image is the standard that works on all platforms.",
            "guide": "open-graph",
            "fix_title": "How to Add an OG Image",
        },
        {
            "title": "No Twitter Card tags — no preview on X/Twitter",
            "severity": "medium",
            "detail": "X (formerly Twitter) uses its own meta tag system, separate from Open Graph. Even with perfect OG tags, Twitter won't show a rich preview without twitter:card, twitter:title, twitter:description, and twitter:image tags.",
            "guide": "twitter-cards",
            "fix_title": "How to Add Twitter Card Tags",
        },
    ],
    "faqs": [
        {
            "q": "Why does my link preview work on some platforms but not others?",
            "a": "Different platforms use different standards. LinkedIn, Slack, Discord, iMessage, and WhatsApp all use Open Graph tags. Twitter/X uses Twitter Card tags. Facebook uses Open Graph. If only Twitter is broken, you're missing twitter:card tags. If it's broken everywhere, you're missing Open Graph tags entirely.",
        },
        {
            "q": "My preview is showing the wrong image or old content — how do I force a refresh?",
            "a": "Platforms cache previews aggressively. Each has a scrape/debug tool: Facebook Sharing Debugger (developers.facebook.com/tools/debug), LinkedIn Post Inspector (linkedin.com/post-inspector), and Twitter Card Validator (cards-dev.twitter.com/validator). Paste your URL and click 'Scrape Again' or 'Re-inspect'. Slack clears its cache automatically within ~30 minutes.",
        },
        {
            "q": "What size should my OG image be?",
            "a": "1200×630px is the universal standard that works well on all platforms. Use PNG or JPG, keep file size under 1MB. Don't put critical text in the bottom 15% — some platforms crop it. For Twitter's summary card, a square 1:1 image at 800×800px also works well.",
        },
        {
            "q": "Can I have different link previews for different pages?",
            "a": "Yes — and you should. Set OG tags dynamically based on each page's content. Product pages should show the product image; blog posts should show the post's featured image. For programmatically generated OG images (with your branding and page title), use Vercel OG (@vercel/og) or the Satori library.",
        },
        {
            "q": "Do link previews affect SEO or search rankings?",
            "a": "Not directly. OG tags aren't a Google ranking factor. But better link previews mean more clicks on shared links, more social traffic, and more backlinks — all of which indirectly improve SEO. For search results specifically, focus on your title tag and meta description instead.",
        },
    ],
},

"website-not-secure": {
    "seo_title": "Why Does My Website Say 'Not Secure'? 4 Causes & Fixes | didyouship.dev",
    "description": "'Not Secure' in the browser address bar? An expired SSL certificate, no HTTPS, broken redirect, or mixed content could be the cause. Here's how to diagnose and fix each.",
    "h1": "Why Does Your Website Say \"Not Secure\"?",
    "intro": "Chrome, Firefox, and Safari show \"Not Secure\" or \"Your connection is not private\" when something is wrong with your HTTPS configuration. There are several distinct causes — here's how to identify which one applies to you.",
    "causes": [
        {
            "title": "SSL certificate expired or invalid",
            "severity": "critical",
            "detail": "When an SSL certificate expires, browsers show a full-page red warning that blocks most visitors from reaching your site. An invalid certificate (issued for the wrong domain, self-signed, or with a verification error) has the same effect. Certificates need to be renewed — usually every 90 days for Let's Encrypt.",
            "guide": "ssl-certificate",
            "fix_title": "How to Fix an SSL Certificate",
        },
        {
            "title": "Site doesn't have HTTPS at all",
            "severity": "critical",
            "detail": "Your site serves content over plain HTTP, meaning all traffic between your server and visitors is unencrypted. Chrome labels every HTTP page as Not Secure. This affects your Google rankings and makes form submissions (logins, signups, payments) unsafe.",
            "guide": "ssl-certificate",
            "fix_title": "How to Enable HTTPS",
        },
        {
            "title": "HTTP doesn't redirect to HTTPS",
            "severity": "high",
            "detail": "Your HTTPS works, but typing your URL without https:// doesn't automatically redirect to the secure version. Visitors using an old link or bookmark, or anyone who doesn't explicitly type https://, lands on the insecure version with the Not Secure warning.",
            "guide": "https-redirect",
            "fix_title": "How to Force HTTPS Redirect",
        },
        {
            "title": "Mixed content — HTTP resources on an HTTPS page",
            "severity": "high",
            "detail": "Your HTTPS page loads images, scripts, or stylesheets over HTTP. Browsers silently block these resources — images don't appear, scripts don't run — and some browsers show a Not Secure warning even though the page itself is HTTPS. This happens when old HTTP URLs are hardcoded in your code.",
            "guide": "mixed-content",
            "fix_title": "How to Fix Mixed Content",
        },
        {
            "title": "HSTS header missing — first visit can be downgraded",
            "severity": "medium",
            "detail": "Even with HTTPS and a redirect, the very first visit to your site on public WiFi can be intercepted before the redirect happens. The HSTS header tells browsers to always use HTTPS for your domain, eliminating this vulnerability.",
            "guide": "hsts-header",
            "fix_title": "How to Add the HSTS Header",
        },
    ],
    "faqs": [
        {
            "q": "Is my site actually dangerous, or is it just a warning?",
            "a": "It depends. No HTTPS means all data in transit (form inputs, logins, cookies) is readable by anyone on the same network. An expired certificate means the security is broken. Mixed content means specific resources are blocked. In all cases, it's worth fixing — the warning actively drives users away and hurts SEO.",
        },
        {
            "q": "I added SSL but the browser still shows Not Secure — why?",
            "a": "Most likely cause: you have HTTPS but some pages still load resources over HTTP (mixed content). Open Chrome DevTools → Console and look for 'Mixed Content' warnings — they'll name the exact HTTP URLs causing the issue. Second cause: your HTTP doesn't redirect to HTTPS, so users landing on http:// still see the warning.",
        },
        {
            "q": "Does 'Not Secure' affect Google rankings?",
            "a": "Yes. Google has used HTTPS as a ranking signal since 2014. Sites without HTTPS rank lower than equivalent HTTPS sites. An expired certificate that fully blocks the site causes rankings to drop quickly as Google can no longer crawl it. Fixing HTTPS won't instantly boost rankings, but it removes an active penalty.",
        },
        {
            "q": "My SSL certificate auto-renews — why did it expire?",
            "a": "Common reasons: your domain's DNS A record was changed so Let's Encrypt can no longer verify domain ownership, your server's certbot cron job stopped running, or a billing issue paused your hosting. Check your hosting dashboard for certificate status and renewal logs.",
        },
    ],
},

"website-loading-slow": {
    "seo_title": "Why Is My Website Loading Slowly? 4 Causes & How to Fix | didyouship.dev",
    "description": "Website taking too long to load? Cold starts on free hosting, missing compression, or slow database queries are the most common causes. Learn how to diagnose and fix each.",
    "h1": "Why Is Your Website Loading Slowly?",
    "intro": "A slow website is one of the most damaging things for user retention — 53% of mobile users abandon a page that takes more than 3 seconds to load. There are a few distinct causes, and identifying which one you have determines the fix.",
    "causes": [
        {
            "title": "Server cold start — your app is sleeping between visitors",
            "severity": "high",
            "detail": "Free and hobby tiers of Railway, Render, and Fly.io spin your server down after 15–30 minutes of inactivity. The first visitor after idle has to wait 10–30 seconds for the server to wake up. Subsequent requests are fast. This is the most common cause for indie and side projects.",
            "guide": "response-time",
            "fix_title": "How to Fix Cold Starts",
        },
        {
            "title": "Response compression not enabled — pages are 3–5× bigger than needed",
            "severity": "medium",
            "detail": "Your server sends HTML, CSS, and JavaScript without compressing it first. Enabling gzip or Brotli typically reduces page size by 60–80% — a 200KB page becomes 40KB. This is a free performance improvement that affects every page load for every user.",
            "guide": "compression",
            "fix_title": "How to Enable Gzip Compression",
        },
        {
            "title": "Slow server response time — something heavy is on the request path",
            "severity": "high",
            "detail": "Your server consistently takes more than 3 seconds to respond, even when warm. Usually caused by slow database queries (missing indexes), heavy computation on the main request thread, or a server deployed in a region far from your users.",
            "guide": "response-time",
            "fix_title": "How to Improve Server Response Time",
        },
    ],
    "faqs": [
        {
            "q": "Why is my site fast for me but slow for my users?",
            "a": "Several reasons: you're physically close to your server (fewer network hops), your browser caches assets after the first visit so repeat visits are faster, and you test after the server is already warm. Use GTmetrix or WebPageTest to measure from specific regions. The first-visit cold start is invisible to you but hits every new visitor.",
        },
        {
            "q": "What's a good page load time?",
            "a": "Under 1 second for Time to First Byte (server response) is ideal. Under 3 seconds for full page load. Google's Core Web Vitals consider Largest Contentful Paint over 2.5 seconds 'needs improvement' and over 4 seconds 'poor'. Check your real-world scores in Google Search Console → Core Web Vitals.",
        },
        {
            "q": "Why is the first visit always slow but every visit after is fast?",
            "a": "Classic cold start. Your hosting provider spins down your server after inactivity to save resources on free/hobby tiers. The first request wakes it up — which can take 10–30 seconds. Subsequent requests hit the already-running server and are fast. Fix: upgrade to a paid plan (always-on) or use a keep-alive ping service (cron-job.org, BetterStack) that hits your /health endpoint every 5 minutes.",
        },
        {
            "q": "Does page speed affect SEO?",
            "a": "Yes. Google's Core Web Vitals — which include Time to First Byte, Largest Contentful Paint, and Interaction to Next Paint — are ranking factors. Slow sites rank lower. Google Search Console shows your Core Web Vitals score and flags pages that are underperforming. A fast site is a ranking advantage, not just a UX nicety.",
        },
        {
            "q": "My database queries seem fine locally — why are they slow in production?",
            "a": "Local databases have no network latency and small datasets. In production, network round-trips add 1–10ms per query (more if your database is in a different region than your server), and larger datasets expose missing indexes. Use EXPLAIN on slow queries to find missing indexes, and check that your database is in the same region as your app server.",
        },
    ],
},

"website-broken-on-mobile": {
    "seo_title": "Why Is My Website Broken on Mobile? How to Fix Mobile Display | didyouship.dev",
    "description": "Website looking tiny on phones or requiring pinch-zoom to read? A missing viewport meta tag is the most common cause. Learn how to fix mobile display in under 5 minutes.",
    "h1": "Why Is Your Website Broken on Mobile?",
    "intro": "If your site looks tiny on phones, renders at desktop width, or requires users to pinch-zoom to read anything — it's most likely a single missing HTML tag. Mobile devices account for over 60% of web traffic, and Google ranks the mobile version of your site first.",
    "causes": [
        {
            "title": "Missing viewport meta tag — site renders at desktop width on phones",
            "severity": "high",
            "detail": "Without the viewport meta tag, mobile browsers default to rendering your page at 980px (desktop width) and then shrink the whole page to fit the screen. Everything looks microscopic. This is the most common mobile display problem and takes 30 seconds to fix.",
            "guide": "viewport-meta",
            "fix_title": "How to Add the Viewport Meta Tag",
        },
    ],
    "faqs": [
        {
            "q": "Why does my site look fine on desktop but tiny and broken on mobile?",
            "a": "Mobile browsers default to a 980px viewport when there's no viewport meta tag, then scale the whole page down to fit the device screen — making everything tiny. Adding the viewport meta tag tells the browser to match the actual screen width. You also need responsive CSS (media queries or a framework like Tailwind) to adapt your layout for small screens.",
        },
        {
            "q": "Does a broken mobile site affect Google rankings?",
            "a": "Yes, significantly. Google uses mobile-first indexing — it crawls and ranks the mobile version of your site, not the desktop version. A broken mobile experience (missing viewport, tiny text, content wider than screen) is flagged in Google Search Console under Core Web Vitals and directly leads to lower rankings. Over 60% of global web traffic is from mobile.",
        },
        {
            "q": "I added the viewport tag but the site still looks wrong on mobile — why?",
            "a": "The viewport tag is a prerequisite, but you also need responsive CSS. The tag alone tells the browser what width to use, but your CSS needs to handle different screen widths with media queries or a responsive framework. If everything is still side-scrolling, check for fixed-width elements (like width: 1200px) that are wider than the screen.",
        },
        {
            "q": "How do I test my site on mobile without a real device?",
            "a": "Chrome DevTools has a device emulator — press F12 → click the mobile icon in the toolbar. It emulates phone screen sizes and touch events. For real-device testing at scale, BrowserStack and LambdaTest let you test on actual iOS and Android devices. Google's Mobile-Friendly Test (search.google.com/test/mobile-friendly) checks from Google's perspective.",
        },
        {
            "q": "What percentage of my users are on mobile?",
            "a": "Globally, about 60–65% of web traffic is from mobile. For consumer apps, landing pages, and marketing sites, it's often higher. For developer tools and B2B SaaS, it can be lower. Check your own Google Analytics or Plausible to see your actual split — it's usually surprising how high mobile is even for 'developer' audiences.",
        },
    ],
},

}

ALL_PROBLEM_SLUGS = list(PROBLEMS.keys())
