"""
SEO metadata for each guide page.
Content lives in static/guide.html (JS). This module provides:
  - title        → short guide name (used for SSR h1 and schema)
  - severity     → critical / high / medium / low
  - summary      → one-line description (SSR intro paragraph)
  - seo_title    → <title> tag (keyword-optimised)
  - description  → <meta name="description">
  - how_steps    → plain-text steps for HowTo JSON-LD schema (rich snippets)
  - category     → for breadcrumb schema
"""

GUIDES_META = {
    "spf-record": {
        "title": "SPF Record",
        "severity": "critical",
        "summary": "A DNS record that tells the internet which servers are allowed to send email from your domain.",
        "seo_title": "SPF Record Missing: How to Fix Email Authentication (2026) | didyouship.com",
        "description": "No SPF record means Gmail can't verify your emails and routes them to spam. Step-by-step fix for Google Workspace, Resend, SendGrid, Postmark, and more.",
        "category": "Email Deliverability",
        "how_steps": [
            "List every service that sends email from your domain – your email provider, transactional email service, CRM, and newsletter tool.",
            "Get the SPF include value from each service's documentation (usually under 'Authentication' or 'Domain setup').",
            "Create a single TXT record at your root domain combining all your senders. Example: v=spf1 include:_spf.google.com include:_spf.resend.com ~all",
            "Add the TXT record in your DNS registrar (Cloudflare, Namecheap, Route 53, etc.) for the @ or root domain.",
            "Verify with: nslookup -type=TXT yourdomain.com or mxtoolbox.com/spf.aspx",
            "Once all your sending is confirmed covered, change ~all to -all for full enforcement.",
        ],
    
        "what": '''<p>SPF (Sender Policy Framework) is a DNS TXT record at your root domain. It lists the mail servers and services authorized to send email on your behalf. When someone receives an email from you@yourdomain.com, their email provider checks your SPF record to verify the sending server is on the allowed list.</p>
<p>An SPF record looks like this:</p>
<pre>v=spf1 include:_spf.google.com include:_spf.resend.com ~all</pre>
<p>The <code>~all</code> at the end means "all other servers should softfail" – mark as suspicious but don't reject. Use <code>-all</code> for hard rejection once you're confident the record is complete.</p>''',
        "why": '''<p>Without SPF, email providers have no way to verify whether an email from your domain is genuine. The consequences:</p>
<ul>
<li><strong>Your emails land in spam.</strong> Gmail, Outlook, and Yahoo use SPF as a key deliverability signal.</li>
<li><strong>Anyone can impersonate you.</strong> Without SPF, there's nothing stopping a spammer from sending email as you@yourdomain.com.</li>
<li><strong>Domain reputation damage.</strong> Even if your emails get through today, repeated failures lower your domain's long-term reputation.</li>
</ul>
<p>Since 2024, Gmail and Yahoo formally require SPF for senders over 5,000 emails/day – and penalize domains without it at lower volumes too.</p>''',
        "how": '''<ol>
<li>List every service that sends email from your domain: your email provider (Google Workspace, Microsoft 365), transactional email service (Resend, Postmark, SendGrid), CRM, newsletter tool, etc.</li>
<li>Get the SPF include value from each service's documentation (usually in their "Authentication" or "Domain setup" section).</li>
<li>Combine them into one TXT record at your root domain:<pre>v=spf1 include:_spf.google.com include:_spf.resend.com ~all</pre></li>
<li>Add it in your DNS settings (Cloudflare, Namecheap, GoDaddy, Route 53, etc.) as a TXT record for <code>@</code> or your root domain.</li>
<li>Verify with: <code>nslookup -type=TXT yourdomain.com</code> or mxtoolbox.com/spf.aspx</li>
<li>Once you've confirmed all your email is covered, harden to <code>-all</code>.</li>
</ol>''',
        "providers": '''<table class="provider-table">
<tr><th>Service</th><th>SPF include value</th></tr>
<tr><td>Google Workspace</td><td><code>include:_spf.google.com</code></td></tr>
<tr><td>Microsoft 365</td><td><code>include:spf.protection.outlook.com</code></td></tr>
<tr><td>Resend</td><td><code>include:_spf.resend.com</code></td></tr>
<tr><td>Postmark</td><td><code>include:spf.mtasv.net</code></td></tr>
<tr><td>SendGrid</td><td><code>include:sendgrid.net</code></td></tr>
<tr><td>Mailgun</td><td><code>include:mailgun.org</code></td></tr>
<tr><td>Amazon SES</td><td><code>include:amazonses.com</code></td></tr>
<tr><td>Brevo (Sendinblue)</td><td><code>include:spf.sendinblue.com</code></td></tr>
</table>
<p>Note: you can only have one SPF TXT record. Combine all includes into a single record – multiple SPF records will break validation.</p>''',
    },
    "dmarc": {
        "title": "DMARC Record",
        "severity": "critical",
        "summary": "A DNS policy that enforces what happens when someone tries to send email pretending to be from your domain.",
        "seo_title": "DMARC Record Missing: Stop Email Spoofing on Your Domain (2026) | didyouship.com",
        "description": "No DMARC record lets anyone send phishing emails pretending to be from your domain. Learn how to add DMARC and what policy to use.",
        "category": "Email Deliverability",
        "how_steps": [
            "Confirm SPF and DKIM are already set up – DMARC enforces them.",
            "Add a TXT record at _dmarc.yourdomain.com with value: v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com",
            "Replace the rua address with your own, or use a free DMARC reporting service like Postmark's DMARC monitor.",
            "If unsure whether all your legitimate email passes, start with p=none to observe reports for a week.",
            "Escalate to p=quarantine, then p=reject once you've confirmed all your real email passes.",
        ],
    
        "what": '''<p>DMARC (Domain-based Message Authentication, Reporting and Conformance) is a DNS TXT record at <code>_dmarc.yourdomain.com</code>. It builds on SPF and DKIM to give receiving email servers a clear instruction: <em>if an email claiming to be from us fails authentication, here's what to do with it.</em></p>
<p>There are three policies:</p>
<ul>
<li><code>p=none</code> – do nothing, just send me reports (monitoring mode)</li>
<li><code>p=quarantine</code> – move suspicious emails to spam</li>
<li><code>p=reject</code> – drop suspicious emails entirely</li>
</ul>
<pre>v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com</pre>''',
        "why": '''<p>Without DMARC:</p>
<ul>
<li><strong>Email spoofing is trivially easy.</strong> Anyone can send a phishing email that looks exactly like it's from you@yourdomain.com, and it'll be delivered normally to your customers.</li>
<li><strong>Gmail and Outlook penalize you.</strong> Since 2024, both require DMARC for bulk senders, and both use DMARC as a quality signal even for low-volume senders.</li>
<li><strong>You're flying blind.</strong> Without a DMARC record, you have no visibility into whether someone is impersonating your domain right now.</li>
</ul>''',
        "how": '''<ol>
<li>Make sure you have SPF and DKIM set up first – DMARC enforces them, so they need to work.</li>
<li>Add a TXT record at <code>_dmarc.yourdomain.com</code>:<pre>v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com</pre></li>
<li>Replace the <code>rua</code> address with your own, or use a free DMARC reporting service (see below).</li>
<li>If unsure whether all your legitimate email will pass, start with <code>p=none</code> to observe for a week, then escalate to <code>p=quarantine</code>, then <code>p=reject</code>.</li>
</ol>''',
        "providers": '''<p><strong>Free DMARC report monitoring:</strong></p>
<ul>
<li><strong>Postmark DMARC:</strong> dmarc.postmarkapp.com – free weekly digest</li>
<li><strong>MXToolbox:</strong> mxtoolbox.com/dmarc.aspx – instant lookup and validation</li>
<li><strong>Dmarcian:</strong> dmarcian.com – free tier for small senders</li>
<li><strong>EasyDMARC:</strong> easydmarc.com – free monitoring dashboard</li>
</ul>''',
    },
    "email-spoofing": {
        "title": "Email Spoofing Protection",
        "severity": "critical",
        "summary": "How to prevent anyone from sending email that appears to come from your domain.",
        "seo_title": "Email Spoofing Protection: SPF, DKIM and DMARC Explained (2026) | didyouship.com",
        "description": "Without SPF, DKIM, and DMARC, anyone can send email pretending to be from your domain. Learn how all three work and how to set them up.",
        "category": "Email Deliverability",
        "how_steps": [
            "Add an SPF record – TXT record at your root domain listing your authorised sending services.",
            "Enable DKIM signing in your email provider dashboard and add the DNS record they give you.",
            "Add a DMARC record at _dmarc.yourdomain.com with p=quarantine or p=reject.",
            "Monitor DMARC reports for a week to confirm no legitimate email is being rejected.",
        ],
    
        "what": '''<p>Email spoofing is when someone sends an email that looks like it's from your domain – but isn't. It's trivially easy to do: email's core protocol (SMTP) doesn't verify the sender by default. Without additional protections, anyone can claim to be from you@yourdomain.com.</p>
<p>The three defenses work together:</p>
<ul>
<li><strong>SPF</strong> – lists which servers are allowed to send as you</li>
<li><strong>DKIM</strong> – adds a cryptographic signature to emails from your authorized servers</li>
<li><strong>DMARC</strong> – tells receivers what to do when email fails SPF or DKIM, and sends you reports</li>
</ul>''',
        "why": '''<p>Spoofed emails from your domain can:</p>
<ul>
<li>Send phishing emails to your customers, tricking them into giving up passwords or payment details</li>
<li>Damage your brand reputation – users get suspicious emails "from you" and lose trust</li>
<li>Get your domain blacklisted, affecting your own email deliverability</li>
<li>Be used in business email compromise (BEC) attacks, one of the most costly types of cybercrime</li>
</ul>''',
        "how": '''<ol>
<li><strong>Add an SPF record</strong> – TXT record at your root domain listing your sending services</li>
<li><strong>Enable DKIM</strong> – in your email provider dashboard; they'll give you a TXT record to add</li>
<li><strong>Add a DMARC record</strong> – TXT record at <code>_dmarc.yourdomain.com</code> with <code>p=quarantine</code> or <code>p=reject</code></li>
</ol>
<p>In order of priority: DMARC first (biggest impact), then SPF, then DKIM. All three together give complete protection.</p>''',
        "providers": '''<p>Check each service's documentation for DKIM/SPF setup:</p>
<ul>
<li><strong>Google Workspace:</strong> Admin Console → Apps → Gmail → Authenticate email</li>
<li><strong>Resend:</strong> resend.com → Domains → your domain → DKIM records</li>
<li><strong>Postmark:</strong> Account → Sender Signatures → your domain → DKIM</li>
<li><strong>Microsoft 365:</strong> Defender portal → Email authentication settings</li>
</ul>''',
    },
    "dkim-setup": {
        "title": "DKIM Setup",
        "severity": "high",
        "summary": "Cryptographic signatures that prove your emails haven't been tampered with and came from your authorized server.",
        "seo_title": "DKIM Not Configured: How to Set Up Email Signing (2026) | didyouship.com",
        "description": "Without DKIM, Gmail can't verify your emails are genuine and inbox placement drops. Learn how to enable DKIM for any email provider in minutes.",
        "category": "Email Deliverability",
        "how_steps": [
            "Log in to your email sending service (Resend, Postmark, Google Workspace, SendGrid, etc.).",
            "Navigate to domain authentication, sender verification, or DKIM settings.",
            "The service will generate one or two DNS TXT records – copy them exactly.",
            "Add those TXT records to your DNS, named exactly as instructed (e.g. google._domainkey or s1._domainkey).",
            "Click Verify in the service dashboard – DNS propagation may take a few minutes.",
        ],
    
        "what": '''<p>DKIM (DomainKeys Identified Mail) adds a digital signature to every email you send. Your mail server signs each email with a private key, and publishes the matching public key as a DNS TXT record. When receiving servers get your email, they look up your public key and verify the signature.</p>
<p>The DNS record looks like this – at <code>selector._domainkey.yourdomain.com</code>:</p>
<pre>v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ...</pre>
<p>You don't write this by hand – your email provider generates it and tells you exactly what to add.</p>''',
        "why": '''<p>DKIM is a key trust signal for inbox placement:</p>
<ul>
<li><strong>Gmail uses DKIM to rank email trustworthiness.</strong> Emails without DKIM are more likely to be treated as spam, especially from newer domains.</li>
<li><strong>It's required for DMARC to work properly.</strong> DMARC alignment requires either SPF or DKIM to pass. Without DKIM, SPF alone isn't enough if email is forwarded.</li>
<li><strong>It proves the email wasn't tampered with in transit.</strong> SPF only verifies the sending server; DKIM also verifies the message content.</li>
</ul>''',
        "how": '''<ol>
<li>Log in to your email sending service (Resend, Postmark, Google Workspace, etc.)</li>
<li>Find the DKIM/domain authentication setup page</li>
<li>The service will give you one or two TXT records to add to your DNS</li>
<li>Add those records exactly as instructed (name like <code>google._domainkey</code> or <code>s1._domainkey</code>)</li>
<li>Click "Verify" in the service dashboard – it may take a few minutes for DNS to propagate</li>
</ol>''',
        "providers": '''<table class="provider-table">
<tr><th>Service</th><th>Where to find DKIM setup</th></tr>
<tr><td>Google Workspace</td><td>Admin Console → Apps → Gmail → Authenticate email</td></tr>
<tr><td>Resend</td><td>Dashboard → Domains → your domain → DNS records</td></tr>
<tr><td>Postmark</td><td>Account → Sender Signatures → your domain</td></tr>
<tr><td>SendGrid</td><td>Settings → Sender Authentication → Domain Authentication</td></tr>
<tr><td>Mailgun</td><td>Sending → Domains → your domain → DNS records</td></tr>
<tr><td>Amazon SES</td><td>Configuration → Verified Identities → your domain → DKIM</td></tr>
<tr><td>Microsoft 365</td><td>Defender → Policies → Email auth settings → DKIM</td></tr>
</table>''',
    },
    "ip-blacklisted": {
        "title": "Mail Server IP Blacklisted",
        "severity": "critical",
        "summary": "Your mail server's IP address appears on spam blacklists – email providers silently drop or spam-folder everything you send.",
        "seo_title": "Mail Server IP Blacklisted: How to Check and Get Delisted (2026) | didyouship.com",
        "description": "If your mail server IP is on Spamhaus or Barracuda, emails are silently dropped. Learn how to check your IP, request delisting, and prevent it recurring.",
        "category": "Email Deliverability",
        "how_steps": [
            "Check your mail server IP at mxtoolbox.com/blacklists.aspx to see which blacklists it appears on.",
            "For Spamhaus: visit spamhaus.org/lookup and follow the removal request instructions.",
            "For Barracuda: visit barracudacentral.org/rbl/removal-request and submit a removal form.",
            "For SpamCop: listings expire automatically within 24 hours of no new spam reports.",
            "If you're on shared hosting, consider switching to a managed sending service with clean IP pools (Resend, Postmark, SendGrid).",
        ],
    
        "what": '''<p>Email providers (Gmail, Outlook, Yahoo) check multiple real-time blacklists before accepting email. If the IP address your mail server sends from is listed on a blacklist like Spamhaus, Barracuda, SpamCop, or SORBS, your emails are either silently dropped or sent directly to spam – including password resets, signups, and invoices.</p>
<p>This commonly happens on shared hosting where you share a server IP with other tenants, one of whom got their IP listed.</p>''',
        "why": '''<p>A blacklisted IP is one of the most damaging email problems because it silently breaks everything:</p>
<ul>
<li>Users sign up but never get verification emails</li>
<li>Password reset emails never arrive</li>
<li>Invoices and receipts disappear</li>
<li>No errors – your app thinks emails sent successfully</li>
</ul>
<p>You can be blacklisted because of your own behavior, or because you're on shared infrastructure with bad neighbors.</p>''',
        "how": '''<ol>
<li>Check your mail server IP at <strong>mxtoolbox.com/blacklists.aspx</strong> – enter the IP to see which lists it's on</li>
<li>For each blacklist, visit their website and follow the delisting process (usually a form requesting removal)</li>
<li><strong>Spamhaus:</strong> spamhaus.org/lookup → follow removal instructions</li>
<li><strong>Barracuda:</strong> barracudacentral.org/rbl/removal-request</li>
<li><strong>SpamCop:</strong> listings expire automatically after 24 hours of no spam reports</li>
<li>If you're on shared hosting, strongly consider switching to a managed transactional email service – they maintain clean IP pools</li>
</ol>''',
        "providers": '''<p><strong>Managed sending services with clean IP pools:</strong></p>
<ul>
<li><strong>Resend</strong> – resend.com – developer-friendly, free tier available</li>
<li><strong>Postmark</strong> – postmarkapp.com – excellent deliverability track record</li>
<li><strong>SendGrid</strong> – sendgrid.com – large scale, dedicated IPs available</li>
<li><strong>Mailgun</strong> – mailgun.com – flexible, good for transactional email</li>
</ul>
<p>With these services, your email shares their reputation IP pools which are actively maintained and monitored.</p>''',
    },
    "email-deliverability": {
        "title": "Email Deliverability",
        "severity": "high",
        "summary": "Why your emails land in spam – and the three DNS records every domain needs to reach the inbox reliably.",
        "seo_title": "Email Deliverability: Why Emails Land in Spam and How to Fix It (2026) | didyouship.com",
        "description": "Emails landing in spam? Learn the three DNS records every domain needs – SPF, DKIM, and DMARC – to reliably reach the inbox.",
        "category": "Email Deliverability",
        "how_steps": [
            "Run an email health check at mxtoolbox.com/emailhealth.aspx to see what's missing.",
            "Add an SPF record – TXT record at your root domain listing your email sending services.",
            "Enable DKIM in your email provider dashboard and add the DNS record provided.",
            "Add a DMARC record at _dmarc.yourdomain.com with p=quarantine.",
            "Use a reputable transactional email service for all automated email (password resets, receipts, notifications).",
        ],
    
        "what": '''<p>Email deliverability is whether your emails actually reach the inbox vs. going to spam or being silently dropped. It depends on three DNS records working together:</p>
<ul>
<li><strong>SPF</strong> – lists which servers are allowed to send as your domain</li>
<li><strong>DKIM</strong> – cryptographically signs each email to prove it's genuine</li>
<li><strong>DMARC</strong> – enforces what happens when email fails SPF/DKIM, and provides reporting</li>
</ul>
<p>All three are DNS TXT records – no code changes required, just DNS configuration.</p>''',
        "why": '''<p>Missing email authentication affects every email you send: account verification, password resets, receipts, support replies. When these land in spam, users think your product is broken. Many churn silently without ever telling you.</p>
<p>Since 2024, Gmail and Yahoo require all three for bulk senders and use them as signals even for low-volume domains.</p>''',
        "how": '''<ol>
<li>Check what you're missing: run a scan at didyouship.com or check mxtoolbox.com/emailhealth.aspx</li>
<li>Add SPF first: TXT record at your root domain</li>
<li>Add DKIM: enable in your email provider dashboard, add the DNS record they give you</li>
<li>Add DMARC: TXT record at <code>_dmarc.yourdomain.com</code> with <code>p=quarantine</code></li>
<li>Use a reputable transactional email service for all automated email</li>
</ol>''',
        "providers": '''<p><strong>Recommended sending services:</strong></p>
<ul>
<li><strong>Resend</strong> – modern API, great DX, free tier includes 3,000 emails/month</li>
<li><strong>Postmark</strong> – best-in-class deliverability, 100 free emails/month</li>
<li><strong>SendGrid</strong> – 100 free/day, scales to millions</li>
<li><strong>Brevo (formerly Sendinblue)</strong> – 300 free/day, good EU option</li>
</ul>''',
    },
    "ssl-certificate": {
        "title": "SSL Certificate",
        "severity": "critical",
        "summary": "Your SSL certificate encrypts traffic and proves your domain identity. Expired or invalid certs block your site completely.",
        "seo_title": "SSL Certificate Expired or Invalid: How to Renew and Fix It (2026) | didyouship.com",
        "description": "An expired SSL certificate blocks your site with a full-page browser warning. Learn how to renew it, enable auto-renewal, and fix invalid cert errors.",
        "category": "SSL & HTTPS",
        "how_steps": [
            "Check your cert expiry: openssl s_client -connect yourdomain.com:443 | openssl x509 -noout -dates",
            "Log in to your hosting dashboard and look for SSL or Certificate settings.",
            "Enable auto-renewal – Vercel, Netlify, Cloudflare, and Render do this automatically.",
            "If renewal failed, verify your domain's DNS A/CNAME records still point to your host.",
            "For custom servers using certbot, run: certbot renew --dry-run to confirm the renewal process works.",
        ],
    
        "what": '''<p>An SSL/TLS certificate does two things: it encrypts traffic between your server and visitors (so no one can read it in transit), and it proves your server actually controls yourdomain.com (not an impersonator). Browsers show the padlock icon when the certificate is valid.</p>
<p>Certificates expire – typically every 90 days for Let's Encrypt or 1-2 years for commercial CAs. When they expire, browsers show a full-page warning that blocks most users from accessing your site.</p>''',
        "why": '''<p>An expired or invalid SSL certificate:</p>
<ul>
<li><strong>Blocks your site entirely.</strong> Chrome, Firefox, and Safari show a full-page red warning. Most users click "Go back" rather than proceed.</li>
<li><strong>Destroys trust.</strong> Even technical users see "Your connection is not private" and worry about a breach.</li>
<li><strong>Hurts SEO.</strong> Google penalizes sites with certificate errors.</li>
</ul>''',
        "how": '''<ol>
<li>Check certificate expiry: <code>openssl s_client -connect yourdomain.com:443 | openssl x509 -noout -dates</code></li>
<li>Enable auto-renewal in your hosting dashboard (see providers below)</li>
<li>If renewal failed, check that your domain's DNS still points to your host (A/CNAME records)</li>
<li>For custom servers, ensure your Let's Encrypt certbot cron job is running: <code>certbot renew --dry-run</code></li>
<li>Set a calendar reminder 30 days before expiry as a backup</li>
</ol>''',
        "providers": '''<table class="provider-table">
<tr><th>Host</th><th>Auto-renewal</th><th>Action</th></tr>
<tr><td>Vercel</td><td>Automatic</td><td>Nothing needed – managed for you</td></tr>
<tr><td>Netlify</td><td>Automatic</td><td>Nothing needed – managed for you</td></tr>
<tr><td>Cloudflare</td><td>Automatic</td><td>SSL/TLS → Overview → enable "Full (strict)"</td></tr>
<tr><td>Railway</td><td>Automatic</td><td>Check domain settings for cert status</td></tr>
<tr><td>Render</td><td>Automatic</td><td>Managed – check Settings → Custom Domains</td></tr>
<tr><td>Custom VPS</td><td>Manual</td><td>Use certbot with cron: <code>0 0 * * * certbot renew</code></td></tr>
</table>''',
    },
    "https-redirect": {
        "title": "HTTP → HTTPS Redirect",
        "severity": "high",
        "summary": "Visitors who type your URL without https:// get the insecure version unless you force a redirect.",
        "seo_title": "HTTP to HTTPS Redirect: Force HTTPS on Vercel, Cloudflare, Nginx (2026) | didyouship.com",
        "description": "Without a redirect, visitors get the insecure version of your site. Learn how to force HTTPS on Vercel, Netlify, Cloudflare, Railway, and Nginx.",
        "category": "SSL & HTTPS",
        "how_steps": [
            "Log in to your hosting dashboard and find HTTPS or redirect settings.",
            "Enable 'Force HTTPS' or 'Always Use HTTPS' – Vercel does this by default; Netlify has it under Domain settings.",
            "For Cloudflare: SSL/TLS → Edge Certificates → Always Use HTTPS → On.",
            "For Nginx: add a server block on port 80 that returns a 301 redirect to https://.",
            "Test by visiting http://yourdomain.com in a browser – it should redirect to https://.",
        ],
    
        "what": '''<p>Having HTTPS doesn't mean all traffic is secure by default. If someone types <code>yourdomain.com</code> in their browser (without the <code>https://</code>), their browser first tries plain HTTP. Without a redirect, they'll see your site over an insecure connection with "Not Secure" in the address bar.</p>
<p>The fix is a 301 redirect: when anyone visits <code>http://yourdomain.com</code>, immediately redirect them to <code>https://yourdomain.com</code>.</p>''',
        "why": '''<ul>
<li><strong>Users see "Not Secure" in Chrome.</strong> Any form submission or login over HTTP is unsafe.</li>
<li><strong>Attackers can intercept requests on public WiFi</strong> – cafés, airports, hotels – before the redirect happens.</li>
<li><strong>Links shared without https:// land on the insecure version.</strong></li>
<li><strong>Google prefers HTTPS</strong> and may index the HTTP version if there's no redirect.</li>
</ul>''',
        "how": '''<p>How you fix this depends on your hosting platform:</p>''',
        "providers": '''<table class="provider-table">
<tr><th>Platform</th><th>How to enable</th></tr>
<tr><td>Vercel</td><td>Enabled by default – no action needed</td></tr>
<tr><td>Netlify</td><td>Site settings → Domain management → HTTPS → Force HTTPS</td></tr>
<tr><td>Cloudflare</td><td>SSL/TLS → Edge Certificates → Always Use HTTPS → On</td></tr>
<tr><td>Railway</td><td>Add redirect rule or handle in app code</td></tr>
<tr><td>Nginx</td><td><pre>server {
  listen 80;
  return 301 https://$host$request_uri;
}</pre></td></tr>
<tr><td>Express</td><td><pre>app.use((req, res, next) => {
  if (!req.secure) {
    return res.redirect('https://' + req.headers.host + req.url);
  }
  next();
});</pre></td></tr>
</table>''',
    },
    "env-exposed": {
        "title": ".env File Exposed",
        "severity": "critical",
        "summary": "Your .env file is publicly accessible – anyone can read your database passwords, API keys, and other secrets.",
        "seo_title": ".env File Exposed: How to Secure Your Environment Variables (2026) | didyouship.com",
        "description": "A publicly accessible .env file exposes your database passwords and API keys to anyone. Learn how to fix it immediately and rotate compromised credentials.",
        "category": "Exposed Secrets",
        "how_steps": [
            "Immediately rotate all credentials in your .env – assume they have been compromised.",
            "Revoke and reissue: database passwords, API keys, OAuth secrets, and any other secrets in the file.",
            "Fix your deployment configuration to serve only the build output folder (e.g. .next/, dist/, build/), not the project root.",
            "In Vercel or Netlify, check your project's Output Directory setting in the dashboard.",
            "Verify the fix: visit yourdomain.com/.env in a browser – it should return a 404.",
        ],
    
        "what": '''<p>A <code>.env</code> file is where most apps store sensitive configuration: database credentials, API keys, payment processor secrets, OAuth tokens. It's meant to live on your server only – never served to the web. When your deployment accidentally serves your project root directory (instead of just the build output), <code>/.env</code> becomes publicly accessible to anyone who asks for it.</p>
<p>Automated bots scan millions of domains daily looking for exposed .env files. Once found, credentials are extracted and exploited within minutes.</p>''',
        "why": '''<ul>
<li><strong>Database breach</strong> – your full user database, including passwords, emails, and payment data, can be extracted</li>
<li><strong>API key abuse</strong> – your OpenAI, Stripe, AWS, or other service keys are used to run up charges or steal data</li>
<li><strong>Complete account takeover</strong> – any service credential in your .env can be used immediately</li>
<li><strong>Automated exploitation</strong> – this happens within minutes of exposure, not hours</li>
</ul>''',
        "how": '''<ol>
<li><strong>Immediately rotate all credentials</strong> in your .env – assume they've been compromised</li>
<li>Fix your deployment to serve only the build output folder:</li>
</ol>''',
        "providers": '''<table class="provider-table">
<tr><th>Framework</th><th>Build output directory</th></tr>
<tr><td>Next.js</td><td><code>.next/</code> – Vercel/Netlify handle this automatically</td></tr>
<tr><td>Vite / React</td><td><code>dist/</code> – set this as your publish directory</td></tr>
<tr><td>Create React App</td><td><code>build/</code></td></tr>
<tr><td>Astro</td><td><code>dist/</code></td></tr>
<tr><td>Hugo</td><td><code>public/</code></td></tr>
</table>
<p>In Nginx: set your <code>root</code> directive to point to the build output folder, not the project root.</p>
<p>In Vercel/Netlify: if you deployed the root directory by mistake, check your project's "Output Directory" setting in the dashboard.</p>''',
    },
    "git-exposed": {
        "title": ".git Directory Exposed",
        "severity": "critical",
        "summary": "Your entire source code and git history are downloadable – including secrets you committed and later deleted.",
        "seo_title": ".git Directory Exposed: Block Public Access to Your Source Code (2026) | didyouship.com",
        "description": "An exposed .git directory lets anyone download your full source code and commit history. Learn how to block it with Nginx, Apache, and Caddy.",
        "category": "Exposed Secrets",
        "how_steps": [
            "Immediately rotate any credentials that have ever been committed to your git history.",
            "Use BFG Repo Cleaner or git filter-repo to permanently remove secrets from git history.",
            "Add a rule to your web server to block access to .git/: in Nginx, use 'location ~ /\\.git { deny all; return 404; }'",
            "Fix your deployment to not serve the project root – only the build output directory.",
            "Verify the fix: visit yourdomain.com/.git/config – it should return 404.",
        ],
    
        "what": '''<p>The <code>.git/</code> directory is git's internal database – it contains your complete commit history, every version of every file, and all your branches. When it's accessible over the web, tools like <code>git-dumper</code> can reconstruct your entire repository from just the URL.</p>
<p>This is especially dangerous because <strong>git history doesn't forget</strong>. Even if you deleted a secret key from a commit two years ago, it's still in the git history and fully recoverable.</p>''',
        "why": '''<ul>
<li><strong>Complete source code exposure</strong> – your entire codebase, including private business logic</li>
<li><strong>Historical secrets</strong> – API keys, passwords, tokens committed at any point are recoverable</li>
<li><strong>Attack surface mapping</strong> – attackers can read your code to find vulnerabilities</li>
</ul>''',
        "how": '''<ol>
<li><strong>Immediately rotate any credentials that have ever been in your git history</strong></li>
<li>Block access to <code>/.git/</code> in your web server config</li>
<li>Fix your deployment to not serve the project root (same fix as .env exposure)</li>
</ol>''',
        "providers": '''<p><strong>Block .git in Nginx:</strong></p>
<pre>location ~ /\.git {
    deny all;
    return 404;
}</pre>
<p><strong>Block .git in Apache (.htaccess):</strong></p>
<pre>RedirectMatch 404 /\.git</pre>
<p><strong>Block .git in Caddy:</strong></p>
<pre>@dotfiles path */.*
respond @dotfiles 404</pre>
<p>Better yet: fix your deployment config so you're only serving the build output directory, not the project root. Vercel and Netlify do this correctly by default.</p>''',
    },
    "leaked-secrets": {
        "title": "API Keys in Page Source",
        "severity": "critical",
        "summary": "Secret keys found in your page's HTML source – visible to anyone who clicks \"View Source\".",
        "seo_title": "API Keys in Page Source: How to Remove Exposed Secrets (2026) | didyouship.com",
        "description": "API keys in your HTML source are scraped and exploited within minutes. Learn how to move them server-side in Next.js, Vite, and React.",
        "category": "Exposed Secrets",
        "how_steps": [
            "Immediately revoke and rotate the exposed key from its provider's dashboard.",
            "Audit recent usage of the key – check for unexpected API calls or charges.",
            "Move the key to a server-side environment variable.",
            "Create an API proxy endpoint in your backend that calls the third-party API using the server-side key.",
            "Update your frontend to call your own backend endpoint instead of the third-party API directly.",
            "In Next.js, only use NEXT_PUBLIC_ prefix for truly browser-safe values (like a Stripe publishable key).",
        ],
    
        "what": '''<p>When you embed an API key, database URL, or other secret directly in client-side code (JavaScript, HTML), it becomes part of your page's source – readable by any user who opens browser DevTools or views source. Automated scrapers continuously crawl the web extracting keys from page source.</p>
<p>Common ways this happens: pasting a key directly into a React component, accidentally using server-side env vars in a Vite build, or including a config object in a script tag.</p>''',
        "why": '''<ul>
<li><strong>Keys are exploited within minutes</strong> of being indexed. GitHub and web scrapers actively monitor for leaked keys.</li>
<li><strong>Stripe secret keys</strong> → can issue refunds, transfer funds, access all customer data</li>
<li><strong>AWS access keys</strong> → can spin up infrastructure, access S3 buckets, incur massive charges</li>
<li><strong>Database URLs</strong> → direct read/write access to your entire database</li>
<li><strong>OpenAI keys</strong> → run up API charges, access your conversation history</li>
</ul>''',
        "how": '''<ol>
<li><strong>Immediately revoke/rotate the exposed key</strong> – assume it's compromised</li>
<li>Move the key to a server-side environment variable</li>
<li>Use an API proxy: your frontend calls your own backend, which calls the third-party API using the server-side key</li>
</ol>''',
        "providers": '''<p><strong>Framework-specific env var rules:</strong></p>
<table class="provider-table">
<tr><th>Framework</th><th>Exposed to browser</th><th>Server-only</th></tr>
<tr><td>Next.js</td><td><code>NEXT_PUBLIC_*</code></td><td>All other vars</td></tr>
<tr><td>Vite</td><td><code>VITE_*</code></td><td>All other vars</td></tr>
<tr><td>Create React App</td><td><code>REACT_APP_*</code></td><td>All other vars</td></tr>
<tr><td>Astro</td><td><code>PUBLIC_*</code></td><td>All other vars</td></tr>
</table>
<p><strong>Never</strong> put secret keys in the exposed-to-browser category. Only put things like a public analytics ID or a Stripe <em>publishable</em> key there.</p>''',
    },
    "www-redirect": {
        "title": "www Subdomain & Redirect",
        "severity": "high",
        "summary": "www.yourdomain.com should either work (and redirect to the apex) or not exist – having both serve independent content splits your SEO.",
        "seo_title": "www Subdomain Not Working: Set Up www Redirect for SEO (2026) | didyouship.com",
        "description": "www.yourdomain.com not working or both serving content? You're splitting your SEO rankings. Learn how to set up a 301 redirect correctly.",
        "category": "DNS",
        "how_steps": [
            "Decide on your canonical domain – either yourdomain.com (apex) or www.yourdomain.com.",
            "In your DNS settings, add a CNAME record for www pointing to your apex domain or hosting provider.",
            "Configure a 301 redirect from the non-canonical version to the canonical one.",
            "In Cloudflare: Rules → Redirect Rules → match www.domain.com/* → 301 to https://domain.com/$1.",
            "Verify both versions work: one should redirect to the other with a 301 status code.",
        ],
    
        "what": '''<p>There are two common problems with <code>www</code>:</p>
<ol>
<li><strong>www doesn't resolve at all</strong> – users who type <code>www.yourdomain.com</code> get a connection error</li>
<li><strong>Both www and the apex domain serve content</strong> – Google treats them as two separate websites, splitting PageRank</li>
</ol>
<p>The right setup: pick one canonical domain (most apps use the apex – <code>yourdomain.com</code>), and have the other redirect to it with a 301.</p>''',
        "why": '''<ul>
<li><strong>Broken user experience.</strong> Many users still type "www" by habit. If it errors out, they think your site is down.</li>
<li><strong>SEO dilution.</strong> If both serve content, Google sees two sites competing for the same rankings. Your backlinks and PageRank get split 50/50.</li>
<li><strong>Crawl confusion.</strong> Search engines may index the wrong version or both versions of your pages.</li>
</ul>''',
        "how": '''<ol>
<li>Decide which is canonical: <code>yourdomain.com</code> (apex) or <code>www.yourdomain.com</code> – most modern sites use the apex</li>
<li>Add a CNAME record for <code>www</code> pointing to your apex (or your host's redirect service)</li>
<li>Configure a 301 redirect from the non-canonical version to the canonical one</li>
</ol>''',
        "providers": '''<table class="provider-table">
<tr><th>Platform</th><th>How to set up redirect</th></tr>
<tr><td>Vercel</td><td>Add www as a domain redirect in project Settings → Domains</td></tr>
<tr><td>Netlify</td><td>Domain settings → add www → configure to redirect to apex</td></tr>
<tr><td>Cloudflare</td><td>Rules → Redirect Rules → <code>www.domain.com/*</code> → 301 to <code>https://domain.com/$1</code></td></tr>
<tr><td>Nginx</td><td><pre>server {
  server_name www.yourdomain.com;
  return 301 https://yourdomain.com$request_uri;
}</pre></td></tr>
</table>''',
    },
    "hsts-header": {
        "title": "HSTS Header",
        "severity": "medium",
        "summary": "The Strict-Transport-Security header tells browsers to always use HTTPS – even on the very first visit.",
        "seo_title": "HSTS Header Missing: Add Strict-Transport-Security to Your Site (2026) | didyouship.com",
        "description": "Without HSTS, the first visit to your site on public WiFi can be intercepted. Learn how to add the Strict-Transport-Security header.",
        "category": "Security Headers",
        "how_steps": [
            "Add the Strict-Transport-Security response header to all HTTPS responses.",
            "Use value: max-age=31536000; includeSubDomains (1 year, including subdomains).",
            "For Cloudflare: SSL/TLS → Edge Certificates → HTTP Strict Transport Security → Enable.",
            "For Vercel: add a headers config in vercel.json with the Strict-Transport-Security key-value pair.",
            "For Nginx: add_header Strict-Transport-Security 'max-age=31536000; includeSubDomains' always;",
            "For Express/Node: use the helmet package – app.use(helmet()) enables HSTS by default.",
        ],
    
        "what": '''<p>HSTS (HTTP Strict Transport Security) is a response header that tells browsers: "always use HTTPS for this domain – never HTTP, even if someone types http://."</p>
<pre>Strict-Transport-Security: max-age=31536000; includeSubDomains</pre>
<p>Once a browser receives this header, it'll enforce HTTPS for your domain for <code>max-age</code> seconds (31536000 = 1 year), even if the user or a link tries to use HTTP.</p>''',
        "why": '''<p>Even with HTTPS and a redirect, there's a window of vulnerability on the very first visit to your site:</p>
<ol>
<li>User types <code>yourdomain.com</code></li>
<li>Browser connects over HTTP first</li>
<li>Your server redirects to HTTPS</li>
<li>Browser follows redirect</li>
</ol>
<p>Step 2-3 happens over plain HTTP. On public WiFi, an attacker (man-in-the-middle) can intercept that initial HTTP request, modify it, and keep the user on HTTP the whole time. This is called an SSL stripping attack. HSTS eliminates step 2 entirely – the browser goes straight to HTTPS.</p>''',
        "how": '''<p>Add this header to all HTTPS responses:</p>
<pre>Strict-Transport-Security: max-age=31536000; includeSubDomains</pre>''',
        "providers": '''<table class="provider-table">
<tr><th>Platform</th><th>How to add HSTS</th></tr>
<tr><td>Cloudflare</td><td>SSL/TLS → Edge Certificates → HTTP Strict Transport Security → Enable</td></tr>
<tr><td>Vercel</td><td>vercel.json headers config:<pre>{
  "headers": [{
    "source": "/(.*)",
    "headers": [{"key": "Strict-Transport-Security",
                 "value": "max-age=31536000; includeSubDomains"}]
  }]
}</pre></td></tr>
<tr><td>Nginx</td><td><code>add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;</code></td></tr>
<tr><td>Express</td><td>Use the <code>helmet</code> package: <code>app.use(helmet())</code> – includes HSTS by default</td></tr>
<tr><td>FastAPI</td><td><code>from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware</code></td></tr>
</table>''',
    },
    "page-title": {
        "title": "Page Title Tag",
        "severity": "high",
        "summary": "The title tag controls what appears in browser tabs and as your headline in Google search results.",
        "seo_title": "Page Title Tag Missing: How to Add a Title Tag for SEO (2026) | didyouship.com",
        "description": "A missing title tag means Google can't rank your page and browser tabs are blank. Learn the right format and how to set it in any framework.",
        "category": "SEO",
        "how_steps": [
            "Add a <title> tag inside your HTML <head> element.",
            "Format: Your App Name – what it does in 5-7 words (50-60 characters total).",
            "In Next.js App Router: export a metadata object with a title property from your page.js or layout.js.",
            "In Next.js Pages Router: use the <Head> component from next/head.",
            "In Astro: set a title variable in frontmatter and render it in your layout's <head>.",
            "Verify in browser: the tab should show your title text.",
        ],
    
        "what": '''<p>The <code>&lt;title&gt;</code> tag in your HTML <code>&lt;head&gt;</code> does two important things:</p>
<ul>
<li>It's the text shown in the browser tab</li>
<li>It's the clickable blue headline shown in Google search results</li>
</ul>
<pre>&lt;title&gt;didyouship.com – production readiness checker&lt;/title&gt;</pre>
<p>A good title is 50-60 characters, includes your brand name, and describes what the page does.</p>''',
        "why": '''<ul>
<li><strong>Google uses the title as the primary ranking signal</strong> for what your page is about</li>
<li><strong>Without a title, your search result looks broken</strong> – Google either shows the URL or makes something up</li>
<li><strong>Browser tabs are blank</strong> – users with multiple tabs can't find your site</li>
<li><strong>Social shares look poor</strong> – Open Graph uses the title tag as a fallback</li>
</ul>''',
        "how": '''<p>Add inside your <code>&lt;head&gt;</code>:</p>
<pre>&lt;title&gt;Your App Name – what it does in 5-7 words&lt;/title&gt;</pre>''',
        "providers": '''<table class="provider-table">
<tr><th>Framework</th><th>How to set title</th></tr>
<tr><td>Next.js (App Router)</td><td><pre>export const metadata = {
  title: 'Your App – tagline',
};</pre></td></tr>
<tr><td>Next.js (Pages Router)</td><td><pre>import Head from 'next/head';
&lt;Head&gt;&lt;title&gt;Your App&lt;/title&gt;&lt;/Head&gt;</pre></td></tr>
<tr><td>Astro</td><td>In frontmatter: <code>title: 'Your App'</code>, then <code>&lt;title&gt;{title}&lt;/title&gt;</code></td></tr>
<tr><td>React (plain)</td><td><code>document.title = 'Your App';</code> or use <code>react-helmet</code></td></tr>
<tr><td>Plain HTML</td><td>Directly in <code>&lt;head&gt;&lt;title&gt;...&lt;/title&gt;&lt;/head&gt;</code></td></tr>
</table>''',
    },
    "meta-description": {
        "title": "Meta Description",
        "severity": "high",
        "summary": "The snippet shown under your title in Google results – without it, Google picks random text from your page.",
        "seo_title": "Meta Description Missing: Write and Add It for Better Click-Through (2026) | didyouship.com",
        "description": "Without a meta description, Google shows random text in search results. Learn how to write a good one and add it in Next.js, Astro, and plain HTML.",
        "category": "SEO",
        "how_steps": [
            "Write a description of 150-160 characters that summarises what the page does.",
            "Add inside your <head>: <meta name=\"description\" content=\"Your description here.\">",
            "In Next.js App Router: add a description field to your exported metadata object.",
            "In Next.js Pages Router: add a <meta> tag inside the <Head> component.",
            "Verify with: view-source:yourdomain.com and search for 'description'.",
        ],
    
        "what": '''<p>The meta description is a short text summary of your page shown in search results under the title:</p>
<pre>&lt;meta name="description" content="Free production readiness scanner.
26 checks in 8 seconds. Find what you forgot before users do."&gt;</pre>
<p>Aim for 150-160 characters. It doesn't directly affect rankings, but it heavily influences click-through rate – it's your ad copy in search results.</p>''',
        "why": '''<ul>
<li><strong>Without it, Google picks random text</strong> – usually something like your nav menu or a sidebar item</li>
<li><strong>Poor click-through from search.</strong> A clear description of what your page does converts much better than random text</li>
<li><strong>Used as fallback for social previews</strong> when Open Graph description isn't set</li>
</ul>''',
        "how": '''<p>Add inside your <code>&lt;head&gt;</code>:</p>
<pre>&lt;meta name="description" content="Your one-sentence pitch here."&gt;</pre>''',
        "providers": '''<table class="provider-table">
<tr><th>Framework</th><th>How to set</th></tr>
<tr><td>Next.js (App Router)</td><td><pre>export const metadata = {
  description: 'Your pitch here.',
};</pre></td></tr>
<tr><td>Next.js (Pages Router)</td><td><pre>&lt;Head&gt;
  &lt;meta name="description" content="..." /&gt;
&lt;/Head&gt;</pre></td></tr>
<tr><td>Astro</td><td>Pass as a prop to your layout, use in head</td></tr>
<tr><td>Plain HTML</td><td>Directly in <code>&lt;head&gt;</code></td></tr>
</table>''',
    },
    "open-graph": {
        "title": "Open Graph Tags",
        "severity": "medium",
        "summary": "Meta tags that control how your links look when shared on Slack, LinkedIn, Discord, iMessage, and most social platforms.",
        "seo_title": "Open Graph Tags Missing: Add Rich Link Previews to Your Site (2026) | didyouship.com",
        "description": "Without Open Graph tags, links shared on Slack, Discord, and LinkedIn show as plain text. Learn how to add og:title, og:image, and og:url.",
        "category": "SEO",
        "how_steps": [
            "Add four core OG meta tags inside your <head>: og:title, og:description, og:image, og:url.",
            "Create an OG image at 1200x630px – this is the preview image shown when links are shared.",
            "Set og:url to the canonical URL of the page (e.g. https://yourdomain.com).",
            "Test with opengraph.xyz or the Facebook Sharing Debugger (developers.facebook.com/tools/debug).",
            "For dynamic OG images, use Vercel OG (@vercel/og) to generate images from JSX at the edge.",
        ],
    
        "what": '''<p>Open Graph is a protocol (created by Facebook, now universal) that lets you control the preview shown when someone shares your URL. Without OG tags, shared links show as plain text. With them, you get a rich card with image, title, and description.</p>
<p>The four core tags:</p>
<pre>&lt;meta property="og:title" content="Your App Name"&gt;
&lt;meta property="og:description" content="What it does in one sentence"&gt;
&lt;meta property="og:image" content="https://yourdomain.com/og.png"&gt;
&lt;meta property="og:url" content="https://yourdomain.com"&gt;</pre>''',
        "why": '''<ul>
<li><strong>Links shared on Slack, Discord, LinkedIn, iMessage</strong> show as a plain URL instead of a rich card</li>
<li><strong>Dramatically lower click-through.</strong> A rich preview with a good image can 2-3x clicks on a shared link</li>
<li><strong>Looks unprofessional.</strong> When you share your app link and it shows no preview, it looks unfinished</li>
</ul>''',
        "how": '''<ol>
<li>Add the four core OG tags to your <code>&lt;head&gt;</code></li>
<li>Create an OG image: 1200×630px PNG works best on all platforms</li>
<li>Test with: developers.facebook.com/tools/debug or opengraph.xyz</li>
</ol>''',
        "providers": '''<p><strong>Dynamic OG image generation:</strong></p>
<ul>
<li><strong>Vercel OG</strong> (<code>@vercel/og</code>) – generate images from JSX at the edge, free</li>
<li><strong>Satori</strong> – the underlying library, framework-agnostic</li>
<li><strong>Cloudinary</strong> – text overlays on images, URL-based generation</li>
</ul>
<p><strong>Design tools for static OG images:</strong></p>
<ul>
<li>Figma – 1200×630 frame, export as PNG</li>
<li>og-image.vercel.app – quick generator</li>
</ul>''',
    },
    "twitter-cards": {
        "title": "Twitter Card Tags",
        "severity": "medium",
        "summary": "X/Twitter uses its own meta tags for link previews – Open Graph tags aren't enough.",
        "seo_title": "Twitter Card Tags Missing: Add Rich Previews for X/Twitter (2026) | didyouship.com",
        "description": "Open Graph tags aren't enough for X/Twitter – you need Twitter Card tags too. Learn how to add them so your links show images on X.",
        "category": "SEO",
        "how_steps": [
            "Add twitter:card meta tag with value 'summary_large_image' for a large image preview.",
            "Add twitter:title, twitter:description, and twitter:image inside your <head>.",
            "You can reuse the same image as your og:image – point twitter:image to the same URL.",
            "Test with the Twitter Card Validator at cards-dev.twitter.com/validator.",
        ],
    
        "what": '''<p>X (formerly Twitter) uses its own card meta tags, separate from Open Graph. Even if you have perfect OG tags, X won't show a rich preview without Twitter Card tags. The minimum set:</p>
<pre>&lt;meta name="twitter:card" content="summary_large_image"&gt;
&lt;meta name="twitter:title" content="Your App Name"&gt;
&lt;meta name="twitter:description" content="What it does"&gt;
&lt;meta name="twitter:image" content="https://yourdomain.com/og.png"&gt;</pre>
<p><code>summary_large_image</code> shows a large image card. <code>summary</code> shows a smaller thumbnail.</p>''',
        "why": '''<ul>
<li><strong>Links posted on X show no image preview</strong> without Twitter Card tags – just a plain URL or small link box</li>
<li>If you or your users share links on X, this directly affects visibility and clicks</li>
<li>You can reuse the same image as your OG image – no extra work</li>
</ul>''',
        "how": '''<p>Add to your <code>&lt;head&gt;</code> alongside your OG tags:</p>
<pre>&lt;meta name="twitter:card" content="summary_large_image"&gt;
&lt;meta name="twitter:title" content="Your App Name"&gt;
&lt;meta name="twitter:description" content="What it does"&gt;
&lt;meta name="twitter:image" content="https://yourdomain.com/og.png"&gt;</pre>
<p>Test with: cards-dev.twitter.com/validator (Twitter Card Validator)</p>''',
        "providers": '''<p><strong>Same image for OG and Twitter Card:</strong></p>
<ul>
<li>Use 1200×630px PNG for both – works on all platforms</li>
<li>If your og:image is already set, point twitter:image to the same URL</li>
</ul>''',
    },
    "viewport-meta": {
        "title": "Viewport Meta Tag",
        "severity": "high",
        "summary": "Without the viewport tag, your site renders at desktop width on phones – everything is tiny and users must pinch-zoom.",
        "seo_title": "Viewport Meta Tag Missing: Fix Broken Mobile Display (2026) | didyouship.com",
        "description": "Without the viewport meta tag, your site renders at desktop width on phones. Learn how to add it and fix mobile rendering in any framework.",
        "category": "SEO",
        "how_steps": [
            "Add this tag inside your HTML <head>: <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            "In Next.js App Router: this is included automatically – check your root layout.js.",
            "In Next.js Pages Router: check your _document.js or add it to _app.js Head.",
            "In Astro: add it to your base layout file's <head> section.",
            "Test on a real device or using Chrome DevTools mobile emulation – site should fill screen width without zooming.",
        ],
    
        "what": '''<p>The viewport meta tag tells mobile browsers how to scale your page. Without it, mobile browsers render your page at a desktop viewport width (typically 980px) and then scale it down to fit the screen, making everything tiny.</p>
<pre>&lt;meta name="viewport" content="width=device-width, initial-scale=1"&gt;</pre>
<p><code>width=device-width</code> tells the browser to match the screen width. <code>initial-scale=1</code> sets the default zoom to 100%.</p>''',
        "why": '''<ul>
<li><strong>Site is broken on mobile.</strong> Text is tiny, buttons are impossible to tap, users must pinch-zoom to read anything</li>
<li><strong>Google ranks mobile-friendly sites higher.</strong> Google uses mobile-first indexing – it primarily indexes and ranks the mobile version of your site</li>
<li><strong>High bounce rate on mobile.</strong> Users leave immediately if they can't read the page</li>
</ul>
<p>Mobile devices account for over 60% of web traffic globally. A broken mobile experience means losing most of your users.</p>''',
        "how": '''<p>Add this single line inside your <code>&lt;head&gt;</code>:</p>
<pre>&lt;meta name="viewport" content="width=device-width, initial-scale=1"&gt;</pre>
<p>This is the standard tag included by every framework's default template. If you're missing it, check that your base layout/template includes it.</p>''',
        "providers": '''<p>Most framework starters include this automatically. Check your base layout file:</p>
<table class="provider-table">
<tr><th>Framework</th><th>Where to check</th></tr>
<tr><td>Next.js App Router</td><td>Included automatically in <code>&lt;html&gt;</code> layout</td></tr>
<tr><td>Next.js Pages Router</td><td>Check <code>pages/_document.js</code> or <code>_app.js</code></td></tr>
<tr><td>Astro</td><td>Your <code>src/layouts/Layout.astro</code> base layout</td></tr>
<tr><td>Plain HTML</td><td>Add to every <code>&lt;head&gt;</code> or your shared base template</td></tr>
</table>''',
    },
    "canonical-url": {
        "title": "Canonical URL",
        "severity": "medium",
        "summary": "Tells Google which version of a URL is the \"real\" one – prevents duplicate content from splitting your search rankings.",
        "seo_title": "Canonical URL Missing: Prevent Duplicate Content Splitting SEO (2026) | didyouship.com",
        "description": "Without a canonical URL tag, Google may index multiple versions of your page and split your rankings. Learn how to add it in any framework.",
        "category": "SEO",
        "how_steps": [
            "Add a canonical link tag inside your <head>: <link rel=\"canonical\" href=\"https://yourdomain.com/page\">",
            "Always use the https:// version, your preferred domain (www or apex), and a consistent trailing slash policy.",
            "In Next.js App Router: add alternates.canonical to your metadata export.",
            "In Next.js Pages Router: add the <link rel='canonical'> tag inside the <Head> component.",
            "Add the canonical tag to every page on your site, not just the homepage.",
        ],
    
        "what": '''<p>Your page might be accessible at multiple URLs: <code>yourdomain.com/page</code>, <code>yourdomain.com/page/</code>, <code>www.yourdomain.com/page</code>, <code>yourdomain.com/page?utm_source=twitter</code>. Without a canonical tag, Google might index all of these as separate pages.</p>
<pre>&lt;link rel="canonical" href="https://yourdomain.com/page"&gt;</pre>
<p>This tells Google: "This is the definitive URL for this content. Please consolidate all link signals here."</p>''',
        "why": '''<ul>
<li><strong>PageRank dilution.</strong> If 5 URL variants all rank, each gets 1/5 of the link equity instead of all signals going to one URL</li>
<li><strong>Crawl budget waste.</strong> Google spends crawl budget on duplicate pages instead of finding new content</li>
<li><strong>Wrong URL in search results.</strong> Google might show a query-parameter URL or www variant as the search result</li>
</ul>''',
        "how": '''<p>Add to your <code>&lt;head&gt;</code> on every page:</p>
<pre>&lt;link rel="canonical" href="https://yourdomain.com/current-page"&gt;</pre>
<p>The URL should be the preferred, stable version – always use <code>https://</code>, without trailing slashes (or consistently with them), and without UTM parameters.</p>''',
        "providers": '''<table class="provider-table">
<tr><th>Framework</th><th>How to set canonical</th></tr>
<tr><td>Next.js App Router</td><td><pre>export const metadata = {
  alternates: { canonical: 'https://yourdomain.com/page' }
};</pre></td></tr>
<tr><td>Next.js Pages Router</td><td><pre>&lt;Head&gt;
  &lt;link rel="canonical" href="https://..." /&gt;
&lt;/Head&gt;</pre></td></tr>
<tr><td>Astro</td><td><code>canonicalURL</code> in frontmatter, rendered in layout head</td></tr>
</table>''',
    },
    "sitemap": {
        "title": "Sitemap.xml",
        "severity": "medium",
        "summary": "A file that tells search engines what pages exist on your site – required for Google Search Console and full indexing.",
        "seo_title": "Sitemap.xml Missing: Create and Submit a Sitemap to Google (2026) | didyouship.com",
        "description": "Sitemap.xml helps Google find all your pages and is required for Google Search Console. Learn how to generate it for Next.js, Astro, Django, and more.",
        "category": "SEO",
        "how_steps": [
            "Choose a sitemap generator for your framework (see providers below).",
            "Configure it to include all public pages and their canonical URLs.",
            "Deploy and verify the sitemap is accessible at https://yourdomain.com/sitemap.xml.",
            "Go to Google Search Console (search.google.com/search-console).",
            "Navigate to Sitemaps in the left menu and submit your sitemap URL.",
        ],
    
        "what": '''<p>A sitemap.xml is an XML file at <code>/sitemap.xml</code> listing all the pages on your site that should be indexed, along with optional metadata like last-modified date and update frequency:</p>
<pre>&lt;?xml version="1.0" encoding="UTF-8"?&gt;
&lt;urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"&gt;
  &lt;url&gt;
    &lt;loc&gt;https://yourdomain.com/&lt;/loc&gt;
    &lt;lastmod&gt;2024-01-01&lt;/lastmod&gt;
  &lt;/url&gt;
&lt;/urlset&gt;</pre>
<p>You don't write this by hand – your framework generates it automatically.</p>''',
        "why": '''<ul>
<li><strong>Google Search Console requires a sitemap</strong> to show you which pages are indexed and flag indexing errors</li>
<li><strong>Pages may be missed without it</strong> – especially deeper pages or recently added content</li>
<li><strong>Faster indexing of new content.</strong> Submitting an updated sitemap signals Google to crawl your changes</li>
</ul>''',
        "how": '''<ol>
<li>Generate the sitemap using your framework's plugin</li>
<li>Verify it's accessible at <code>https://yourdomain.com/sitemap.xml</code></li>
<li>Submit it in Google Search Console: Sitemaps → add <code>/sitemap.xml</code></li>
</ol>''',
        "providers": '''<table class="provider-table">
<tr><th>Framework</th><th>Plugin/tool</th></tr>
<tr><td>Next.js (13.3+)</td><td>Built-in: create <code>app/sitemap.js</code> returning a sitemap config</td></tr>
<tr><td>Next.js (older)</td><td><code>next-sitemap</code> npm package</td></tr>
<tr><td>Astro</td><td><code>@astrojs/sitemap</code> integration</td></tr>
<tr><td>SvelteKit</td><td><code>svelte-sitemap</code> or manual generation</td></tr>
<tr><td>Django</td><td>Built-in: <code>django.contrib.sitemaps</code></td></tr>
<tr><td>Rails</td><td><code>sitemap_generator</code> gem</td></tr>
<tr><td>Static site</td><td>Create manually or use <code>xml-sitemap</code> CLI</td></tr>
</table>''',
    },
    "favicon": {
        "title": "Favicon",
        "severity": "low",
        "summary": "The small icon shown in browser tabs. Missing = 404 errors on every page load + blank tab icon.",
        "seo_title": "Favicon Missing: Add a Browser Tab Icon to Your Site (2026) | didyouship.com",
        "description": "A missing favicon causes a 404 error on every page load and leaves your browser tab blank. Learn how to create and add one in 5 minutes.",
        "category": "SEO",
        "how_steps": [
            "Create a 32x32px icon using Figma, favicon.io, or any image editor.",
            "Save it as favicon.ico and place it in your public directory.",
            "Add a link tag inside your <head>: <link rel=\"icon\" href=\"/favicon.ico\">",
            "For better quality on retina screens, also add an SVG version: <link rel=\"icon\" href=\"/favicon.svg\" type=\"image/svg+xml\">",
            "Verify: open your site and check the browser tab shows the icon.",
        ],
    
        "what": '''<p>A favicon is the small icon shown in the browser tab next to your page title. Every browser requests <code>/favicon.ico</code> automatically on every page load, even if you don't link to it. If it's missing, you get a 404 error in your server logs on every visit.</p>
<pre>&lt;link rel="icon" href="/favicon.ico"&gt;
&lt;!-- Or SVG, which scales better: --&gt;
&lt;link rel="icon" href="/favicon.svg" type="image/svg+xml"&gt;</pre>''',
        "why": '''<ul>
<li><strong>404 error on every page load</strong> pollutes your server logs and analytics</li>
<li><strong>Blank tab looks unfinished</strong> – a small but visible signal of quality</li>
<li><strong>Users with many tabs</strong> rely on favicons to identify tabs – blank icons are confusing</li>
</ul>''',
        "how": '''<ol>
<li>Create a 32×32 PNG (or SVG for best results)</li>
<li>Save as <code>favicon.ico</code> or <code>favicon.svg</code> in your public directory</li>
<li>Add to your <code>&lt;head&gt;</code>: <code>&lt;link rel="icon" href="/favicon.ico"&gt;</code></li>
</ol>''',
        "providers": '''<p><strong>Quick favicon creation:</strong></p>
<ul>
<li><strong>favicon.io</strong> – generate from text, emoji, or image; free</li>
<li><strong>realfavicongenerator.net</strong> – generates all sizes for all platforms</li>
<li><strong>Figma</strong> – design a 32×32 icon, export as PNG</li>
</ul>
<p>For best compatibility, use both an SVG (for modern browsers) and a PNG fallback:</p>
<pre>&lt;link rel="icon" href="/favicon.svg" type="image/svg+xml"&gt;
&lt;link rel="icon" href="/favicon.png" type="image/png"&gt;</pre>''',
    },
    "response-time": {
        "title": "Response Time & Cold Starts",
        "severity": "high",
        "summary": "Slow response times drive users away – and free hosting tiers put your server to sleep, causing 10–30 second cold starts.",
        "seo_title": "Slow Response Time & Cold Starts: Fix Server Performance (2026) | didyouship.com",
        "description": "Slow response times drive users away. Learn how to fix cold starts on Railway, Render, and Fly.io and how to diagnose a genuinely slow server.",
        "category": "Performance",
        "how_steps": [
            "Determine if it's a cold start: run two consecutive requests – if the first is slow but the second is fast, it's a cold start.",
            "For cold starts: upgrade to a paid plan on your hosting platform (Railway Hobby, Render Starter, Fly paid machines).",
            "Alternatively, use a keep-alive service to ping your health endpoint every 5 minutes (BetterStack, cron-job.org).",
            "For genuinely slow responses: check your server's region and deploy closer to your users.",
            "Profile slow database queries and add indexes for common query patterns.",
            "Move heavy computations out of the request path into background jobs or queues.",
        ],
    
        "what": '''<p>Response time is how long your server takes to send back the first byte of a response. Two different problems can cause slowness:</p>
<ol>
<li><strong>Cold starts:</strong> Free/hobby tiers of Railway, Render, and Fly.io spin down your app after 15-30 minutes of inactivity. The first request after idle wakes it up – typically taking 10-30 seconds. Subsequent requests are fast.</li>
<li><strong>Genuinely slow server:</strong> Slow database queries, heavy computations on the request path, or servers deployed in the wrong region.</li>
</ol>''',
        "why": '''<ul>
<li><strong>53% of mobile users abandon a site that takes more than 3 seconds to load</strong> (Google research)</li>
<li><strong>Cold starts hit first-time visitors hardest</strong> – the worst possible impression for someone trying your app for the first time</li>
<li><strong>Google uses Core Web Vitals (including Time to First Byte) as a ranking factor</strong></li>
</ul>''',
        "how": '''<p><strong>For cold starts:</strong></p>
<ol>
<li>Upgrade to a paid plan on your hosting platform (always-on instances)</li>
<li>Use an uptime monitoring service that pings your health endpoint every 5 minutes to keep it warm</li>
</ol>
<p><strong>For slow responses:</strong></p>
<ol>
<li>Check your server's region – deploy in the same region as most of your users</li>
<li>Profile slow database queries – add indexes for common query patterns</li>
<li>Move heavy computations out of the request path into background jobs</li>
<li>Add a CDN (Cloudflare) in front of your origin server</li>
</ol>''',
        "providers": '''<table class="provider-table">
<tr><th>Platform</th><th>Always-on option</th></tr>
<tr><td>Railway</td><td>Hobby plan ($5/mo) – no sleep</td></tr>
<tr><td>Render</td><td>Starter plan ($7/mo) – no sleep</td></tr>
<tr><td>Fly.io</td><td>Paid machines – always running</td></tr>
<tr><td>Vercel</td><td>Serverless – no cold starts on paid; edge functions always fast</td></tr>
</table>
<p><strong>Keep-alive ping services (free):</strong></p>
<ul>
<li><strong>BetterStack</strong> – uptimerobot.com – ping every 5 mins, free tier</li>
<li><strong>cron-job.org</strong> – HTTP cron job, free</li>
<li><strong>GitHub Actions</strong> – scheduled workflow that hits your health endpoint</li>
</ul>''',
    },
    "compression": {
        "title": "Response Compression",
        "severity": "medium",
        "summary": "Enabling gzip or Brotli compression reduces page size by 60–80%, making your site load significantly faster.",
        "seo_title": "Gzip Compression Not Enabled: Speed Up Your Site for Free (2026) | didyouship.com",
        "description": "Enabling gzip or Brotli compression reduces page size by 60-80% at zero cost. Learn how to enable it in Nginx, Express, FastAPI, and on Cloudflare.",
        "category": "Performance",
        "how_steps": [
            "Check if compression is already enabled: curl -H 'Accept-Encoding: gzip' -I https://yourdomain.com – look for Content-Encoding: gzip in the response.",
            "If using Cloudflare, Vercel, or Netlify – compression is enabled automatically, no action needed.",
            "For Nginx: add gzip on; and gzip_types for html/css/js/json to your server config.",
            "For Express/Node: install the compression package and add app.use(require('compression')()) before your routes.",
            "For FastAPI/uvicorn: add GZipMiddleware from starlette.middleware.gzip.",
            "Redeploy and verify: the Content-Encoding: gzip header should appear on responses.",
        ],
    
        "what": '''<p>HTTP compression compresses your server's responses before sending them over the wire. The browser decompresses them automatically. A 200KB HTML file compresses to ~40KB with gzip, and ~30KB with Brotli – making your pages 5-6x faster to transfer.</p>
<p>Your server indicates compression with the <code>Content-Encoding</code> header:</p>
<pre>Content-Encoding: gzip
Content-Encoding: br</pre>''',
        "why": '''<ul>
<li><strong>60-80% reduction in transfer size</strong> – free performance improvement with no code changes</li>
<li><strong>Faster page loads on all connections</strong> – especially important for mobile users on slower connections</li>
<li><strong>Lower bandwidth costs</strong> if you're paying for egress</li>
<li><strong>Better Core Web Vitals scores</strong> → better SEO rankings</li>
</ul>''',
        "how": '''<p>How to enable depends on your server:</p>''',
        "providers": '''<table class="provider-table">
<tr><th>Platform/Server</th><th>How to enable compression</th></tr>
<tr><td>Cloudflare</td><td>Enabled automatically for HTML, CSS, JS – no action needed</td></tr>
<tr><td>Vercel</td><td>Enabled automatically</td></tr>
<tr><td>Netlify</td><td>Enabled automatically</td></tr>
<tr><td>Nginx</td><td><pre>gzip on;
gzip_types text/plain text/css application/json
  application/javascript text/xml application/xml;
gzip_min_length 1000;</pre></td></tr>
<tr><td>Express (Node.js)</td><td><pre>const compression = require('compression');
app.use(compression());</pre></td></tr>
<tr><td>FastAPI / uvicorn</td><td>Use <code>GZipMiddleware</code>:<pre>from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)</pre></td></tr>
</table>''',
    },
    "mixed-content": {
        "title": "Mixed Content",
        "severity": "high",
        "summary": "HTTP resources on an HTTPS page are silently blocked by browsers – images don't show, scripts don't run.",
        "seo_title": "Mixed Content Errors: Fix HTTP Resources on HTTPS Pages (2026) | didyouship.com",
        "description": "HTTP resources on an HTTPS page are silently blocked by browsers – images don't show, scripts don't run. Learn how to find and fix mixed content.",
        "category": "Breakage",
        "how_steps": [
            "Open Chrome DevTools (F12) → Console tab and look for 'Mixed Content' warnings.",
            "Find all http:// resource URLs in your HTML, CSS, and JavaScript files.",
            "Change each http:// resource URL to https:// – most CDNs and services support HTTPS.",
            "For resources that don't support HTTPS, download and self-host them.",
            "Add a Content-Security-Policy header with upgrade-insecure-requests to auto-upgrade any remaining HTTP resources.",
            "Re-check the Console after deploying to confirm no mixed content warnings remain.",
        ],
    
        "what": '''<p>Mixed content is when an HTTPS page loads resources (images, scripts, stylesheets, fonts) over plain HTTP. Browsers block these resources as a security measure – an HTTP resource on an HTTPS page could be intercepted and modified by an attacker.</p>
<p>This commonly happens with hardcoded HTTP URLs in old code:</p>
<pre>&lt;img src="http://cdn.example.com/logo.png"&gt;  &lt;!-- blocked --&gt;
&lt;script src="http://cdn.example.com/app.js"&gt;&lt;/script&gt;  &lt;!-- blocked --&gt;</pre>''',
        "why": '''<ul>
<li><strong>Resources are silently blocked</strong> – no visible error, images just don't appear, scripts don't run</li>
<li><strong>You won't know unless you check the browser console</strong> – users don't see an error message, just broken functionality</li>
<li><strong>Scripts that don't load can break your entire app</strong> – if a framework dependency loads over HTTP, nothing works</li>
</ul>''',
        "how": '''<ol>
<li>Open Chrome DevTools → Console – look for "Mixed Content" warnings</li>
<li>Find all <code>http://</code> URLs in your HTML, CSS, and JavaScript</li>
<li>Change them to <code>https://</code> – most CDNs and services support HTTPS</li>
<li>For third-party resources that don't support HTTPS, host them yourself or find an alternative</li>
</ol>
<p>You can also add this to your HTML head to automatically upgrade HTTP resources to HTTPS:</p>
<pre>&lt;meta http-equiv="Content-Security-Policy"
      content="upgrade-insecure-requests"&gt;</pre>''',
        "providers": '''<p><strong>Quick search for mixed content:</strong></p>
<ul>
<li>Chrome DevTools → Console → filter by "Mixed Content"</li>
<li><code>grep -r "http://" src/</code> in your project (excluding http://localhost)</li>
<li>whynopadlock.com – scan a URL for mixed content issues</li>
</ul>''',
    },
    "custom-404": {
        "title": "Custom 404 Page",
        "severity": "low",
        "summary": "When someone hits a broken link, a custom 404 page keeps them on your site instead of showing a bare error.",
        "seo_title": "No Custom 404 Page: Create One for Next.js, Astro, and SvelteKit (2026) | didyouship.com",
        "description": "A missing custom 404 page shows users a bare error. Learn how to create a branded 404 page in Next.js, Astro, SvelteKit, Netlify, and Nginx.",
        "category": "Polish",
        "how_steps": [
            "Create a 404 page in your framework's designated location (see providers below).",
            "Include your site's header and navigation so users can easily find their way back.",
            "Add a clear heading ('Page not found'), a short explanation, and a link back to the homepage.",
            "Optionally add links to your most popular pages or a search box.",
            "Test by visiting a URL that doesn't exist on your site – the custom 404 page should appear.",
        ],
    
        "what": '''<p>A 404 page is shown when someone visits a URL that doesn't exist on your site. By default, most frameworks and servers show a minimal error message like "Cannot GET /path" or a blank page. A custom 404 page:</p>
<ul>
<li>Matches your site's design and branding</li>
<li>Explains what happened in plain language</li>
<li>Provides navigation back to the homepage or other key pages</li>
<li>Optionally offers a search box or popular links</li>
</ul>''',
        "why": '''<ul>
<li><strong>Users who hit broken links give up without a custom 404</strong> – they see an error and close the tab</li>
<li><strong>A good 404 page recovers the visit</strong> – a link back home or a search box keeps users engaged</li>
<li><strong>Looks unprofessional without one.</strong> A bare "Not Found" error signals an unfinished product</li>
</ul>''',
        "how": '''<p>Create a 404 page in your framework – it's usually just a file in the right location:</p>''',
        "providers": '''<table class="provider-table">
<tr><th>Framework</th><th>Where to create 404 page</th></tr>
<tr><td>Next.js App Router</td><td><code>app/not-found.js</code></td></tr>
<tr><td>Next.js Pages Router</td><td><code>pages/404.js</code></td></tr>
<tr><td>Astro</td><td><code>src/pages/404.astro</code></td></tr>
<tr><td>SvelteKit</td><td><code>src/routes/+error.svelte</code></td></tr>
<tr><td>Vite / static</td><td><code>public/404.html</code></td></tr>
<tr><td>Netlify</td><td>404.html in your publish directory</td></tr>
<tr><td>Nginx</td><td><code>error_page 404 /404.html;</code> in config</td></tr>
</table>
<p><strong>What to include on a good 404 page:</strong></p>
<ul>
<li>Clear message that the page wasn't found</li>
<li>Link back to the homepage</li>
<li>3-5 links to popular sections</li>
<li>Search box (optional but helpful)</li>
<li>Same header/nav as the rest of your site</li>
</ul>''',
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
