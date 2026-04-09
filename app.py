"""
Local SEO Page Generator — Dumpster Rental
Multi-AI Support: Anthropic, Groq, Together AI, OpenRouter
Blogspot URL Structure: dumpsterCityStateZip.blogspot.com
"""

import os, json, sqlite3, re, requests, secrets
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, session
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.locations import US_LOCATIONS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'local-seo-tool-2024'

BUSINESS_CONFIG = {
    "name": "Pro Dumpster Rental",
    "offer": "Dumpster Rental",
    "phone": "+16197596533",
    "phone_display": "(619) 759-6533",
    "hours": "Mon – Fri | 8:00 AM – 8:00 PM (EST)",
    "coverage": "USA (Except Alaska and Hawaii)",
    "target": "Construction and Commercial Clients Only",
    "sizes": ["10-Yard", "20-Yard", "30-Yard", "40-Yard"],
}

# Railway: use /tmp for writable storage, fallback to local for development
_BASE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("PORT"):
    OUTPUT_DIR = "/tmp/generated_pages"
    DB_PATH = "/tmp/pages.db"
else:
    OUTPUT_DIR = os.path.join(_BASE, "generated_pages")
    DB_PATH = os.path.join(_BASE, "data", "pages.db")
os.makedirs(OUTPUT_DIR, exist_ok=True)

AI_PROVIDERS = {
    "groq": {
        "name": "Groq (FREE)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.1-8b-instant",
        "free": True,
        "signup": "https://console.groq.com",
        "header_key": "Authorization",
        "header_format": "Bearer {key}",
    },
    "together": {
        "name": "Together AI (FREE $25 credit)",
        "url": "https://api.together.xyz/v1/chat/completions",
        "model": "meta-llama/Llama-3-8b-chat-hf",
        "free": True,
        "signup": "https://api.together.ai",
        "header_key": "Authorization",
        "header_format": "Bearer {key}",
    },
    "openrouter": {
        "name": "OpenRouter (FREE models)",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openai/gpt-oss-120b:free",
        "models": [
            "openai/gpt-oss-120b:free",
            "nvidia/nemotron-3-super-120b-a12b:free"
        ],
        "free": True,
        "signup": "https://openrouter.ai",
        "header_key": "Authorization",
        "header_format": "Bearer {key}",
    },
    "anthropic": {
        "name": "Anthropic Claude (Paid)",
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-haiku-4-5-20251001",
        "free": False,
        "signup": "https://console.anthropic.com",
        "header_key": "x-api-key",
        "header_format": "{key}",
    },
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS generated_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state TEXT NOT NULL, city TEXT NOT NULL, zip_code TEXT NOT NULL, county TEXT,
        filename TEXT NOT NULL UNIQUE, blogspot_url TEXT,
        title TEXT, meta_description TEXT, primary_keyword TEXT, long_tail_keywords TEXT,
        ai_provider TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ai_keys (
        provider TEXT PRIMARY KEY, api_key TEXT NOT NULL, active INTEGER DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS page_tokens (
        filename TEXT PRIMARY KEY,
        token TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

def get_ai_key(provider):
    keys = session.get('ai_keys', {})
    return keys.get(provider)

def save_ai_key(provider, key):
    keys = session.get('ai_keys', {})
    keys[provider] = key
    session['ai_keys'] = keys

def get_all_keys():
    keys = session.get('ai_keys', {})
    return {p: {"key": k[:8]+"****", "active": True} for p, k in keys.items()}

def get_saved_provider_keys():
    return session.get('ai_keys', {})

def get_active_provider():
    keys = get_saved_provider_keys()
    for p in ["groq","together","openrouter","anthropic"]:
        if p in keys:
            return p, keys[p]
    return None, None

def build_blogspot_url(city, state_abbr, zip_code):
    city_clean = city.replace(' ', '').replace('.', '').replace("'", "").lower()
    state_clean = state_abbr.lower()
    return f"https://dumpster{city_clean}{state_clean}{zip_code}.blogspot.com/"

def get_long_tail_keywords(city, state_abbr, zip_code, county):
    return [
        f"commercial dumpster rental {city} {state_abbr}",
        f"construction dumpster rental {city} {state_abbr} {zip_code}",
        f"roll off dumpster rental {city} {state_abbr}",
        f"affordable construction waste removal {city} {state_abbr}",
        f"best dumpster rental company {city} {zip_code}",
        f"20 yard dumpster rental {city} {state_abbr}",
        f"30 yard roll off dumpster {city} {state_abbr}",
        f"40 yard dumpster rental {city} {zip_code}",
        f"construction site waste management {city} {state_abbr}",
        f"commercial debris removal {city} {state_abbr}",
        f"dumpster rental near me {city} {state_abbr}",
        f"same day dumpster delivery {city} {zip_code}",
        f"roofing dumpster rental {city} {state_abbr}",
        f"demolition debris removal {city} {state_abbr}",
        f"concrete disposal dumpster {city} {zip_code}",
        f"renovation waste disposal {county}",
        f"large dumpster rental {city} {zip_code}",
        f"construction cleanup dumpster {city} {state_abbr}",
        f"bulk waste removal {city} {state_abbr}",
        f"dumpster rental prices {city} {state_abbr}",
    ]

def call_ai_openai_compat(provider_name, api_key, prompt):
    cfg = AI_PROVIDERS[provider_name]
    headers = {"Content-Type": "application/json", cfg["header_key"]: cfg["header_format"].format(key=api_key)}
    if provider_name == "openrouter":
        headers["HTTP-Referer"] = "https://produmpsterrental.com"
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": "You are an expert local SEO copywriter. Always respond with valid JSON only, no markdown, no extra text."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.85, "max_tokens": 2500,
    }
    r = requests.post(cfg["url"], headers=headers, json=payload, timeout=45)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def call_ai_anthropic(api_key, prompt):
    headers = {"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"}
    payload = {
        "model": AI_PROVIDERS["anthropic"]["model"], "max_tokens": 2500,
        "system": "You are an expert local SEO copywriter. Always respond with valid JSON only, no markdown, no extra text.",
        "messages": [{"role": "user", "content": prompt}]
    }
    r = requests.post(AI_PROVIDERS["anthropic"]["url"], headers=headers, json=payload, timeout=45)
    r.raise_for_status()
    return r.json()["content"][0]["text"].strip()

def get_or_create_token(filename):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT token FROM page_tokens WHERE filename=?', (filename,))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]
    token = secrets.token_urlsafe(32)
    c.execute('INSERT INTO page_tokens (filename, token) VALUES (?,?)', (filename, token))
    conn.commit()
    conn.close()
    return token

def verify_token(filename, token):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT token FROM page_tokens WHERE filename=?', (filename,))
    row = c.fetchone()
    conn.close()
    return row and row[0] == token

def generate_seo_content(city, state, state_abbr, zip_code, county):
    saved_keys = get_saved_provider_keys()
    if not saved_keys:
        raise RuntimeError('No AI provider key found. Please save a valid Groq, Together, OpenRouter, or Anthropic key before generating pages.')
    providers_to_try = [p for p in ["groq","together","openrouter","anthropic"] if p in saved_keys]
    keywords = get_long_tail_keywords(city, state_abbr, zip_code, county)
    primary_kw = f"commercial dumpster rental {city} {state_abbr}"
    county_short = county.replace(" County", "").replace(" Parish", "")

    # ---------------------------------------------------------------
    # IMPROVED PROMPT — forces unique, city-specific content
    # ---------------------------------------------------------------
    prompt = f"""You are an expert local SEO copywriter writing for a commercial dumpster rental company.

TARGET LOCATION:
- City: {city}
- State: {state} ({state_abbr})
- ZIP Code: {zip_code}
- County: {county}
- Primary Keyword: "{primary_kw}"

BUSINESS INFO:
- Name: Pro Dumpster Rental
- Phone: (619) 759-6533
- Hours: Mon-Fri 8AM-8PM EST
- Sizes: 10, 20, 30, 40 Yard Roll-Off Containers
- Target Clients: Construction contractors and commercial property managers ONLY. NO homeowners.

WRITING RULES (VERY IMPORTANT):
1. Every paragraph must be UNIQUE to {city}, {state_abbr} — mention the local economy, industries, or character of {city}
2. The intro_paragraph must be at least 4 sentences and reference {county} and ZIP {zip_code}
3. The service_area_paragraph must be at least 3 sentences with local {city} context
4. All 4 FAQ questions must be DIFFERENT from each other and specific to {city}
5. The 4 why_us_points must each mention {city} or {county} in their descriptions
6. Write naturally — do NOT keyword-stuff
7. B2B focus only — contractors, construction companies, commercial property managers
8. H1 must be UNDER 65 characters — short and punchy, city + keyword only
9. meta_description must be between 140-155 characters exactly — always include phone
10. NEVER start intro_paragraph with phrases like "As a leading provider" or "Located in the heart of" — write originally
11. Every intro_paragraph must mention a specific local industry, landmark, or economic fact unique to {city}
12. meta_title must be UNDER 60 characters — count carefully before responding

Respond ONLY with this exact JSON structure (no markdown, no preamble, no extra text):
{{"meta_title":"[STRICT MAX 60 chars — example: Commercial Dumpster Rental {city}, {state_abbr}]","meta_description":"[STRICT 140-155 chars — include phone (619) 759-6533 and {city} and {zip_code}]","h1":"[STRICT MAX 65 chars — city + primary keyword only]","hero_subtitle":"[1 sentence about serving {county} contractors]","intro_paragraph":"[4+ sentences unique to {city} — mention local construction market, {county}, ZIP {zip_code}, B2B focus]","why_us_points":[{{"title":"[Point 1 title]","desc":"[2 sentences mentioning {city} or {county}]"}},{{"title":"[Point 2 title]","desc":"[2 sentences]"}},{{"title":"[Point 3 title]","desc":"[2 sentences mentioning {city}]"}},{{"title":"[Point 4 title]","desc":"[2 sentences]"}}],"service_area_paragraph":"[3+ sentences about serving {city}, {county}, ZIP {zip_code} — mention nearby areas]","cta_headline":"[Strong CTA headline with {city} {state_abbr}]","faq":[{{"q":"[FAQ about getting a dumpster in {city}]","a":"[2 sentence answer with phone number]"}},{{"q":"[FAQ about construction waste types in {city} area]","a":"[2 sentence answer]"}},{{"q":"[FAQ about dumpster sizes for {city} projects]","a":"[2 sentence answer]"}},{{"q":"[FAQ about service coverage near {city} and {county}]","a":"[2 sentence answer]"}}],"schema_description":"[2-3 sentence LocalBusiness description for {city}, {state_abbr}]","og_description":"[1-2 sentence social share description for {city} service]"}}"""

    raw = None
    used_provider = None
    errors = []

    for provider in providers_to_try:
        api_key = saved_keys.get(provider)
        try:
            if provider == "anthropic":
                raw = call_ai_anthropic(api_key, prompt)
            else:
                raw = call_ai_openai_compat(provider, api_key, prompt)
            used_provider = provider
            break
        except Exception as e:
            print(f"AI Error ({provider}): {e}")
            errors.append(f"{provider}: {e}")
            raw = None

    if raw:
        try:
            raw = re.sub(r'^```json\s*', '', raw)
            raw = re.sub(r'^```\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            data = json.loads(raw)
            data['long_tail_keywords'] = keywords
            data['primary_keyword'] = primary_kw
            data['ai_provider'] = used_provider or 'unknown'
            return data
        except Exception as e:
            print(f"JSON parse error: {e}")
            raise RuntimeError('AI returned invalid JSON response. Please try a different provider or key.')

    raise RuntimeError('AI generation failed for all saved providers: ' + '; '.join(errors))
    return {
        "meta_title": f"Commercial Dumpster Rental {city}, {state_abbr} {zip_code} | Pro Dumpster Rental",
        "meta_description": f"Roll-off dumpster rental for contractors in {city}, {state_abbr} {zip_code}. 10-40 yard containers. Call (619) 759-6533. Mon-Fri 8AM-8PM EST.",
        "h1": f"Commercial Dumpster Rental {city}, {state_abbr}",
        "hero_subtitle": f"Reliable roll-off container delivery for construction and commercial projects throughout {county}.",
        "intro_paragraph": f"Pro Dumpster Rental serves construction companies and commercial property managers across {city}, {state_abbr} {zip_code} with dependable roll-off dumpster delivery. Whether you are managing a large-scale commercial renovation, a demolition project, or an ongoing construction site in {county}, our team keeps your waste removal on schedule. We exclusively serve B2B clients — contractors, general contractors, and commercial facilities managers — ensuring dedicated service for professional job sites. Call (619) 759-6533 to schedule delivery to your {city} worksite.",
        "why_us_points": [
            {"title": f"Serving {city} Contractors", "desc": f"We understand the pace of construction in {city} and {county}. Our team delivers on your schedule so your job site never slows down."},
            {"title": "4 Container Sizes Available", "desc": f"Choose from 10, 20, 30, and 40-yard roll-off dumpsters for any {city} project scope. Our team helps you pick the right size the first time."},
            {"title": "Construction-Grade Containers", "desc": f"Heavy-duty roll-off containers built for concrete, roofing debris, demolition waste, and bulk commercial materials common on {city} job sites."},
            {"title": "Flat-Rate Transparent Pricing", "desc": f"Receive a firm quote before delivery to your {city} worksite. No hidden fees, no surprises — just reliable service for {county} contractors."}
        ],
        "service_area_paragraph": f"Our service area covers all of {city}, {state_abbr} {zip_code} and the surrounding communities throughout {county}. We regularly deliver roll-off containers to active construction sites, commercial renovation projects, and industrial facilities across the greater {city} metro area. If your worksite is near {city}, call us at (619) 759-6533 to confirm same-region availability.",
        "cta_headline": f"Schedule Your Dumpster Delivery in {city}, {state_abbr} Today",
        "faq": [
            {"q": f"How do I rent a commercial dumpster in {city}, {state_abbr}?", "a": f"Simply call (619) 759-6533 Mon-Fri 8AM-8PM EST and our dispatcher will confirm availability in {city} and provide a flat-rate quote. We serve {county} contractors exclusively — no homeowner requests."},
            {"q": f"What types of waste can I dispose of in a roll-off dumpster in {city}?", "a": f"Our containers in {city} accept construction debris, concrete, roofing shingles, drywall, lumber, demolition waste, and commercial renovation materials. Hazardous materials are not accepted."},
            {"q": f"What dumpster size is right for my {city} construction project?", "a": f"10-yard containers work for small commercial cleanouts; 20-yard for mid-size renovations; 30-yard for major construction jobs; 40-yard for large demolition and industrial projects in {county}. Call us and we will recommend the right fit."},
            {"q": f"Does Pro Dumpster Rental serve areas near {city}, {state_abbr}?", "a": f"Yes — we cover all of {county} and nearby communities surrounding {city}. Call (619) 759-6533 to verify same-day or next-day availability at your specific worksite location."}
        ],
        "schema_description": f"Pro Dumpster Rental provides commercial and construction roll-off dumpster rental throughout {city}, {state_abbr} {zip_code} and {county}. We serve contractors and commercial property managers with 10, 20, 30, and 40-yard containers.",
        "og_description": f"Commercial roll-off dumpster rental in {city}, {state_abbr}. Serving {county} contractors and construction companies. Call (619) 759-6533.",
        "long_tail_keywords": keywords,
        "primary_keyword": primary_kw,
        "ai_provider": "fallback"
    }


def generate_html_page(city, state, state_abbr, zip_code, county, content, blogspot_url):
    kw_str = ", ".join(content['long_tail_keywords'][:12])
    county_short = county.replace(" County", "").replace(" Parish", "")

    # ── Auto-sanitize all SEO fields ──────────────────────────────
    # Title: hard cap 60 chars
    meta_title = content['meta_title']
    if len(meta_title) > 60:
        meta_title = f"Commercial Dumpster Rental {city}, {state_abbr}"

    # H1: hard cap 65 chars
    h1_raw = content['h1']
    if len(h1_raw) > 65:
        h1_raw = f"Commercial Dumpster Rental {city}, {state_abbr}"

    # Meta description: hard cap 155 chars, pad if too short
    meta_desc = content['meta_description']
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152] + '...'
    if len(meta_desc) < 130:
        meta_desc = f"Commercial dumpster rental in {city}, {state_abbr} {zip_code}. Roll-off containers for contractors. Call (619) 759-6533 Mon-Fri 8AM-8PM EST."

    schema = {
        "@context": "https://schema.org", "@type": "HomeAndConstructionBusiness",
        "name": f"Pro Dumpster Rental - {city}",
        "description": content['schema_description'],
        "telephone": "+16197596533", "openingHours": "Mo-Fr 08:00-20:00", "priceRange": "$$",
        "areaServed": {"@type": "City", "name": city, "containedIn": {"@type": "State", "name": state}},
        "address": {"@type": "PostalAddress", "addressLocality": city, "addressRegion": state_abbr, "postalCode": zip_code, "addressCountry": "US"},
        "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Dumpster Rental Services",
            "itemListElement": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": f"{s} Yard Roll-Off Dumpster Rental"}} for s in ["10","20","30","40"]]}
    }
    faq_schema = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in content['faq']]
    }
    icons = ["⚡","📦","🏗️","💰"]
    why_html = "".join([f'<div class="why-card"><div class="why-icon" aria-hidden="true">{icons[i%4]}</div><h3>{p["title"]}</h3><p>{p["desc"]}</p></div>' for i,p in enumerate(content['why_us_points'])])
    faq_html = "".join([f'<div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question"><div class="faq-q" onclick="toggleFaq(this)" role="button" aria-expanded="false"><span itemprop="name">{f["q"]}</span><div class="faq-arrow" aria-hidden="true">+</div></div><div class="faq-a" itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer"><div class="faq-a-inner" itemprop="text">{f["a"]}</div></div></div>' for f in content['faq']])
    h1_display = h1_raw.replace(city, f'<span>{city}</span>', 1)
    year = datetime.now().year

    # OG image — use a placeholder that works (can be swapped for a real image URL)
    og_image = "https://produmpsterrental.blogspot.com/og-image.jpg"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>{meta_title}</title>
<meta name="description" content="{meta_desc}">
<meta name="keywords" content="{kw_str}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
<meta name="geo.region" content="US-{state_abbr}">
<meta name="geo.placename" content="{city}, {state}">
<meta name="geo.position" content="">
<link rel="canonical" href="{blogspot_url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{meta_title}">
<meta property="og:description" content="{content['og_description']}">
<meta property="og:url" content="{blogspot_url}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:site_name" content="Pro Dumpster Rental">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{meta_title}">
<meta name="twitter:description" content="{content['og_description']}">
<meta name="twitter:image" content="{og_image}">
<script type="application/ld+json">{json.dumps(schema)}</script>
<script type="application/ld+json">{json.dumps(faq_schema)}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Barlow:wght@300;400;500;600&family=Barlow+Condensed:wght@600;700&display=swap" rel="stylesheet">
<style>
:root{{--black:#111010;--dark:#1c1c1c;--steel:#2b2b2b;--orange:#e8520a;--orange-bright:#ff6b1a;--yellow:#f5a623;--white:#ffffff;--gray-500:#888070;--gray-700:#4a4540;--radius:6px;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
html{{scroll-behavior:smooth;}}
body{{font-family:'Barlow',sans-serif;background:var(--white);color:var(--dark);overflow-x:hidden;}}
h1,h2,h3,h4{{font-family:'Oswald',sans-serif;text-transform:uppercase;letter-spacing:0.02em;}}
a{{text-decoration:none;}}
.skip-nav{{position:absolute;top:-40px;left:0;background:var(--orange);color:white;padding:8px 16px;z-index:9999;border-radius:0 0 4px 0;font-size:14px;}}
.skip-nav:focus{{top:0;}}
.topbar{{background:var(--orange);color:white;font-size:13px;font-weight:600;padding:9px 24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;}}
.topbar .hours{{color:var(--yellow);font-weight:700;}}
header{{background:var(--black);border-bottom:3px solid var(--orange);position:sticky;top:0;z-index:1000;box-shadow:0 4px 20px rgba(0,0,0,0.5);}}
.header-inner{{max-width:1200px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;gap:20px;}}
.logo{{display:flex;align-items:center;gap:12px;}}
.logo-icon{{width:48px;height:48px;background:var(--orange);border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:26px;flex-shrink:0;}}
.logo-text{{font-family:'Oswald',sans-serif;font-size:22px;font-weight:700;color:white;line-height:1.1;letter-spacing:0.04em;text-transform:uppercase;}}
.logo-text span{{color:var(--orange);}}
.logo-sub{{font-family:'Barlow',sans-serif;font-size:11px;color:rgba(255,255,255,0.5);font-weight:400;text-transform:none;letter-spacing:0;}}
.cta-call{{background:var(--orange);color:white;border:none;border-radius:4px;padding:12px 20px;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:16px;cursor:pointer;display:flex;align-items:center;gap:8px;text-decoration:none;transition:all 0.2s;box-shadow:0 4px 15px rgba(232,82,10,0.4);white-space:nowrap;text-transform:uppercase;}}
.cta-call:hover{{background:var(--orange-bright);transform:translateY(-1px);}}
.pulse{{width:8px;height:8px;background:var(--yellow);border-radius:50%;animation:pulse 1.5s infinite;flex-shrink:0;}}
@keyframes pulse{{0%,100%{{transform:scale(1);opacity:1;}}50%{{transform:scale(1.6);opacity:0.5;}}}}
.breadcrumb-bar{{background:var(--steel);padding:10px 24px;}}
.breadcrumb{{list-style:none;display:flex;align-items:center;flex-wrap:wrap;gap:6px;font-size:12px;color:rgba(255,255,255,0.4);max-width:1200px;margin:0 auto;}}
.breadcrumb li+li::before{{content:"›";margin-right:6px;}}
.breadcrumb a{{color:rgba(255,255,255,0.5);transition:color 0.2s;}}
.breadcrumb a:hover{{color:var(--orange);}}
.breadcrumb li:last-child{{color:var(--orange);}}
.hero{{background:var(--black);position:relative;overflow:hidden;padding:80px 24px 90px;}}
.hero::before{{content:'';position:absolute;inset:0;background:repeating-linear-gradient(45deg,transparent,transparent 40px,rgba(255,255,255,0.012) 40px,rgba(255,255,255,0.012) 80px);pointer-events:none;}}
.hero-inner{{max-width:1200px;margin:0 auto;position:relative;display:grid;grid-template-columns:1fr 340px;gap:56px;align-items:center;}}
.hero-badge{{display:inline-flex;align-items:center;gap:8px;background:rgba(232,82,10,0.15);border:1px solid rgba(232,82,10,0.4);color:var(--orange);padding:6px 16px;border-radius:4px;font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:20px;}}
.hero h1{{font-size:clamp(2rem,5vw,3.2rem);font-weight:700;color:white;line-height:1.1;margin-bottom:16px;}}
.hero h1 span{{color:var(--orange);}}
.hero-subtitle{{font-size:17px;color:rgba(255,255,255,0.6);margin-bottom:32px;line-height:1.6;}}
.hero-actions{{display:flex;flex-wrap:wrap;gap:14px;align-items:center;}}
.btn-primary{{background:var(--orange);color:white;border:none;border-radius:4px;padding:16px 28px;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:18px;cursor:pointer;display:inline-flex;align-items:center;gap:10px;text-decoration:none;transition:all 0.2s;box-shadow:0 6px 24px rgba(232,82,10,0.45);text-transform:uppercase;letter-spacing:0.04em;}}
.btn-primary:hover{{background:var(--orange-bright);transform:translateY(-2px);}}
.btn-outline{{background:transparent;color:white;border:2px solid rgba(255,255,255,0.3);border-radius:4px;padding:14px 24px;font-family:'Barlow Condensed',sans-serif;font-weight:600;font-size:16px;cursor:pointer;display:inline-flex;align-items:center;gap:8px;text-decoration:none;transition:all 0.2s;text-transform:uppercase;}}
.btn-outline:hover{{border-color:var(--orange);color:var(--orange);}}
.hero-stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:36px;}}
.stat{{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:var(--radius);padding:14px;text-align:center;}}
.stat-num{{font-family:'Oswald',sans-serif;font-size:1.8rem;font-weight:700;color:var(--orange);line-height:1;}}
.stat-lbl{{font-size:10px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.06em;margin-top:4px;}}
.call-card{{background:var(--steel);border:2px solid rgba(232,82,10,0.3);border-radius:8px;padding:28px 24px;text-align:center;}}
.call-card h3{{font-size:18px;color:white;margin-bottom:6px;font-family:'Oswald',sans-serif;text-transform:uppercase;}}
.call-phone{{font-family:'Oswald',sans-serif;font-size:26px;color:var(--orange);font-weight:700;display:block;margin:14px 0;text-decoration:none;}}
.call-note{{font-size:11px;color:rgba(255,255,255,0.3);margin-top:12px;line-height:1.6;}}
section{{padding:64px 24px;}}
.section-inner{{max-width:1200px;margin:0 auto;}}
.section-tag{{font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:var(--orange);margin-bottom:8px;}}
.section-title{{font-size:clamp(1.6rem,4vw,2.4rem);margin-bottom:16px;}}
.section-title span{{color:var(--orange);}}
.section-sub{{font-size:16px;color:var(--gray-500);max-width:720px;line-height:1.75;margin-bottom:36px;}}
.section-dark{{background:var(--dark);}}
.section-dark .section-title{{color:white;}}
.section-dark .section-sub{{color:rgba(255,255,255,0.5);}}
.section-steel{{background:var(--steel);}}
.section-steel .section-title{{color:white;}}
.section-steel .section-sub{{color:rgba(255,255,255,0.5);}}
.why-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:2px;}}
.why-card{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);padding:32px 28px;transition:all 0.25s;}}
.why-card:hover{{background:rgba(232,82,10,0.08);border-color:rgba(232,82,10,0.25);transform:translateY(-3px);}}
.why-icon{{font-size:30px;margin-bottom:14px;}}
.why-card h3{{font-size:17px;color:white;margin-bottom:10px;}}
.why-card p{{font-size:14px;color:rgba(255,255,255,0.5);line-height:1.6;}}
.sizes-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;}}
.size-card{{background:white;border:2px solid #edebe7;border-radius:var(--radius);padding:28px 18px;text-align:center;transition:all 0.2s;position:relative;}}
.size-card:hover{{border-color:var(--orange);transform:translateY(-4px);box-shadow:0 12px 40px rgba(232,82,10,0.15);}}
.size-card.popular{{border-color:var(--orange);}}
.popular-tag{{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:var(--orange);color:white;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;padding:3px 12px;border-radius:20px;white-space:nowrap;}}
.size-num{{font-family:'Oswald',sans-serif;font-size:52px;font-weight:700;color:var(--orange);line-height:1;}}
.size-yd{{font-family:'Oswald',sans-serif;font-size:16px;color:var(--gray-500);text-transform:uppercase;}}
.size-name{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--gray-500);margin:8px 0;}}
.size-uses{{font-size:13px;color:var(--gray-700);line-height:1.5;margin-bottom:16px;}}
.size-cta{{display:inline-block;background:var(--orange);color:white;padding:9px 18px;border-radius:4px;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:13px;text-transform:uppercase;letter-spacing:0.04em;transition:all 0.2s;}}
.size-cta:hover{{background:var(--orange-bright);}}
.location-grid{{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:start;}}
.location-facts{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
.fact-box{{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:var(--radius);padding:18px;}}
.fact-label{{font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:var(--orange);font-weight:700;margin-bottom:6px;}}
.fact-val{{font-family:'Oswald',sans-serif;font-size:16px;color:white;font-weight:600;}}
.faq-item{{border-bottom:1px solid rgba(255,255,255,0.08);}}
.faq-q{{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px 0;cursor:pointer;font-family:'Barlow Condensed',sans-serif;font-size:17px;font-weight:700;text-transform:uppercase;letter-spacing:0.03em;color:white;transition:color 0.2s;user-select:none;}}
.faq-q:hover{{color:var(--orange);}}
.faq-arrow{{font-size:24px;color:var(--orange);transition:transform 0.3s;flex-shrink:0;font-family:monospace;font-weight:300;}}
.faq-a{{max-height:0;overflow:hidden;transition:max-height 0.35s ease;}}
.faq-a-inner{{padding:0 0 18px;font-size:15px;color:rgba(255,255,255,0.55);line-height:1.7;}}
.faq-item.open .faq-arrow{{transform:rotate(45deg);}}
.faq-item.open .faq-a{{max-height:300px;}}
.cta-banner{{background:var(--orange);padding:56px 24px;text-align:center;}}
.cta-banner h2{{font-size:clamp(1.8rem,4vw,2.8rem);color:white;margin-bottom:12px;}}
.cta-banner p{{font-size:16px;color:rgba(255,255,255,0.85);margin-bottom:28px;}}
.phone-big{{font-family:'Oswald',sans-serif;font-size:clamp(2rem,6vw,3.8rem);color:white;font-weight:700;display:block;margin-bottom:20px;text-decoration:none;}}
.cta-note{{font-size:13px;color:rgba(255,255,255,0.65);margin-top:16px;}}
footer{{background:#0a0a0a;padding:52px 24px 24px;color:rgba(255,255,255,0.35);}}
.footer-inner{{max-width:1200px;margin:0 auto;}}
.footer-grid{{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:40px;margin-bottom:36px;}}
.footer-brand h4{{font-family:'Oswald',sans-serif;font-size:18px;font-weight:700;color:white;text-transform:uppercase;margin-bottom:10px;}}
.footer-brand p{{font-size:13px;line-height:1.65;margin-bottom:14px;}}
.footer-phone{{color:var(--orange);font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;text-decoration:none;}}
.footer-col h5{{font-family:'Oswald',sans-serif;font-size:13px;text-transform:uppercase;letter-spacing:0.08em;color:rgba(255,255,255,0.45);margin-bottom:12px;}}
.footer-col ul{{list-style:none;}}
.footer-col li{{margin-bottom:7px;font-size:13px;}}
.footer-col a{{color:rgba(255,255,255,0.35);text-decoration:none;transition:color 0.2s;}}
.footer-col a:hover{{color:var(--orange);}}
.disclaimer{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:4px;padding:14px;font-size:11px;line-height:1.6;margin-bottom:20px;}}
.footer-bottom{{border-top:1px solid rgba(255,255,255,0.07);padding-top:18px;display:flex;justify-content:space-between;align-items:center;font-size:12px;flex-wrap:wrap;gap:10px;}}
@media(max-width:900px){{.hero-inner{{grid-template-columns:1fr;}}.call-card{{display:none;}}.footer-grid{{grid-template-columns:1fr 1fr;}}.location-grid{{grid-template-columns:1fr;}}.hero-stats{{grid-template-columns:repeat(2,1fr);}}}}
@media(max-width:600px){{.hero{{padding:40px 20px 50px;}}.topbar{{font-size:11px;}}.footer-grid{{grid-template-columns:1fr;}}.location-facts{{grid-template-columns:1fr;}}}}
@media print{{header,footer,.cta-banner,.topbar{{display:none;}}body{{color:black;}}}}
</style>
</head>
<body>
<a href="#main-content" class="skip-nav">Skip to main content</a>
<div class="topbar" role="complementary">
  <span>📞 <a href="tel:+16197596533" style="color:white;font-weight:700;">(619) 759-6533</a> — Commercial &amp; Construction Only</span>
  <span>Hours: <span class="hours">Mon–Fri 8AM–8PM EST</span> &nbsp;|&nbsp; 🇺🇸 Nationwide USA</span>
</div>
<header role="banner">
  <div class="header-inner">
    <div class="logo" aria-label="Pro Dumpster Rental">
      <div class="logo-icon" aria-hidden="true">🗑️</div>
      <div>
        <div class="logo-text">Pro <span>Dumpster</span> Rental</div>
        <div class="logo-sub">Commercial &amp; Construction Only</div>
      </div>
    </div>
    <a href="tel:+16197596533" class="cta-call" aria-label="Call for free quote: (619) 759-6533">
      <div class="pulse" aria-hidden="true"></div>📞 (619) 759-6533
    </a>
  </div>
</header>
<nav aria-label="Breadcrumb" class="breadcrumb-bar">
  <ol class="breadcrumb" itemscope itemtype="https://schema.org/BreadcrumbList">
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem"><a href="https://produmpsterrental.blogspot.com/" itemprop="item"><span itemprop="name">Home</span></a><meta itemprop="position" content="1"></li>
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem"><a href="https://produmpsterrental.blogspot.com/locations/" itemprop="item"><span itemprop="name">Locations</span></a><meta itemprop="position" content="2"></li>
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem"><a href="https://produmpsterrental.blogspot.com/locations/{state_abbr.lower()}/" itemprop="item"><span itemprop="name">{state}</span></a><meta itemprop="position" content="3"></li>
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem"><span itemprop="name">{city}, {state_abbr}</span><meta itemprop="position" content="4"></li>
  </ol>
</nav>
<section class="hero" aria-labelledby="hero-h1">
  <div class="hero-inner">
    <div>
      <div class="hero-badge" aria-label="Service location">📍 Serving {city}, {state_abbr} {zip_code}</div>
      <h1 id="hero-h1">{h1_display}</h1>
      <p class="hero-subtitle">{content['hero_subtitle']}</p>
      <div class="hero-actions">
        <a href="tel:+16197596533" class="btn-primary" aria-label="Call (619) 759-6533 for free quote">📞 Call (619) 759-6533</a>
        <a href="#sizes" class="btn-outline">View Sizes ↓</a>
      </div>
      <div class="hero-stats" aria-label="Key statistics">
        <div class="stat"><div class="stat-num">4</div><div class="stat-lbl">Sizes</div></div>
        <div class="stat"><div class="stat-num">48</div><div class="stat-lbl">States</div></div>
        <div class="stat"><div class="stat-num">B2B</div><div class="stat-lbl">Only</div></div>
        <div class="stat"><div class="stat-num">24h</div><div class="stat-lbl">Delivery</div></div>
      </div>
    </div>
    <div class="call-card" role="complementary" aria-label="Call us now">
      <h3>Get A Free Quote</h3>
      <p style="font-size:13px;color:rgba(255,255,255,0.4);">Live dispatcher — under 60 seconds</p>
      <a href="tel:+16197596533" class="call-phone" aria-label="Call (619) 759-6533">(619) 759-6533</a>
      <a href="tel:+16197596533" class="btn-primary" style="width:100%;justify-content:center;">📞 Tap to Call Now</a>
      <p class="call-note">✅ Commercial &amp; Construction Only<br>✅ Mon–Fri 8AM–8PM EST<br>✅ Flat-rate quotes · No hidden fees</p>
    </div>
  </div>
</section>
<main id="main-content" role="main">
<section aria-labelledby="intro-h2">
  <div class="section-inner">
    <div class="section-tag">About Our {city} Service</div>
    <h2 class="section-title" id="intro-h2">Dumpster Rental Built for <span>{city} Contractors</span></h2>
    <p class="section-sub">{content['intro_paragraph']}</p>
  </div>
</section>
<section class="section-dark" aria-labelledby="why-h2">
  <div class="section-inner">
    <div class="section-tag">Why Choose Us</div>
    <h2 class="section-title" id="why-h2">The <span>{city} Commercial</span> Standard</h2>
    <div class="why-grid" role="list">{why_html}</div>
  </div>
</section>
<section id="sizes" aria-labelledby="sizes-h2">
  <div class="section-inner">
    <div class="section-tag">Container Options</div>
    <h2 class="section-title" id="sizes-h2">Dumpster Sizes for <span>{city}, {state_abbr}</span> Projects</h2>
    <p class="section-sub">Every construction job in {city} is different. Choose the right roll-off container for your project scope and budget.</p>
    <div class="sizes-grid">
      <div class="size-card"><div class="size-num">10</div><div class="size-yd">Yard</div><div class="size-name">Roll-Off Dumpster</div><div class="size-uses">Small commercial cleanouts, minor office renovations, landscaping debris removal</div><a href="tel:+16197596533" class="size-cta">Get Quote</a></div>
      <div class="size-card"><div class="size-num">20</div><div class="size-yd">Yard</div><div class="size-name">Roll-Off Dumpster</div><div class="size-uses">Mid-size renovations, roofing tear-offs, flooring removal, small demolition jobs</div><a href="tel:+16197596533" class="size-cta">Get Quote</a></div>
      <div class="size-card popular"><div class="popular-tag">Most Popular in {city}</div><div class="size-num">30</div><div class="size-yd">Yard</div><div class="size-name">Roll-Off Dumpster</div><div class="size-uses">Large commercial renovations, major construction projects, property cleanouts</div><a href="tel:+16197596533" class="size-cta">Get Quote</a></div>
      <div class="size-card"><div class="size-num">40</div><div class="size-yd">Yard</div><div class="size-name">Roll-Off Dumpster</div><div class="size-uses">Major demolition, industrial projects, bulk concrete &amp; large-scale debris removal</div><a href="tel:+16197596533" class="size-cta">Get Quote</a></div>
    </div>
  </div>
</section>
<section class="section-steel" aria-labelledby="location-h2">
  <div class="section-inner">
    <div class="section-tag">Service Coverage</div>
    <h2 class="section-title" id="location-h2">Serving <span>{city}</span> &amp; {county_short} Area</h2>
    <div class="location-grid">
      <div><p class="section-sub">{content['service_area_paragraph']}</p></div>
      <div class="location-facts">
        <div class="fact-box"><div class="fact-label">City</div><div class="fact-val">{city}</div></div>
        <div class="fact-box"><div class="fact-label">State</div><div class="fact-val">{state_abbr}</div></div>
        <div class="fact-box"><div class="fact-label">ZIP Code</div><div class="fact-val">{zip_code}</div></div>
        <div class="fact-box"><div class="fact-label">County</div><div class="fact-val">{county_short}</div></div>
      </div>
    </div>
  </div>
</section>
<section class="section-dark" aria-labelledby="faq-h2" itemscope itemtype="https://schema.org/FAQPage">
  <div class="section-inner">
    <div class="section-tag">FAQ</div>
    <h2 class="section-title" id="faq-h2">Common Questions — <span>{city}, {state_abbr}</span></h2>
    <div class="faq-list">{faq_html}</div>
  </div>
</section>
</main>
<section class="cta-banner" aria-labelledby="cta-h2">
  <h2 id="cta-h2">{content['cta_headline']}</h2>
  <p>Speak with a live dispatcher — commercial &amp; construction clients only. Mon–Fri 8AM–8PM EST.</p>
  <a href="tel:+16197596533" class="phone-big" aria-label="Call (619) 759-6533">(619) 759-6533</a>
  <a href="tel:+16197596533" class="btn-primary" style="font-size:18px;padding:16px 32px;">📞 Call Now — Free Quote</a>
  <p class="cta-note">✅ No obligation &nbsp;·&nbsp; ✅ Flat-rate pricing &nbsp;·&nbsp; ✅ {city}, {state_abbr} {zip_code}</p>
</section>
<footer role="contentinfo">
  <div class="footer-inner">
    <div class="disclaimer"><strong>Disclaimer:</strong> This site connects customers with commercial dumpster rental providers. All providers are independent operators. Verify that providers furnish necessary licenses and insurance. Coverage: Continental USA only (excluding Alaska &amp; Hawaii). Commercial and construction clients only — homeowners are not accepted.</div>
    <div class="footer-grid">
      <div class="footer-brand"><h4>🗑️ Pro Dumpster Rental</h4><p>Commercial and construction roll-off dumpster rental across the continental US. Serving {city}, {state_abbr} {zip_code} and all of {county}.</p><a href="tel:+16197596533" class="footer-phone">(619) 759-6533</a></div>
      <div class="footer-col"><h5>Services</h5><ul>
        <li><a href="tel:+16197596533">Construction Dumpsters</a></li>
        <li><a href="tel:+16197596533">Commercial Waste Removal</a></li>
        <li><a href="tel:+16197596533">Roll-Off Containers</a></li>
        <li><a href="tel:+16197596533">Demolition Cleanup</a></li>
        <li><a href="tel:+16197596533">Roofing Debris Removal</a></li>
      </ul></div>
      <div class="footer-col"><h5>Service Area</h5><ul>
        <li><a href="https://produmpsterrental.blogspot.com/locations/{state_abbr.lower()}/">{state} Locations</a></li>
        <li><a href="{blogspot_url}">{city}, {state_abbr}</a></li>
        <li><a href="https://produmpsterrental.blogspot.com/locations/">{county}</a></li>
        <li><a href="{blogspot_url}">ZIP {zip_code}</a></li>
        <li><a href="https://produmpsterrental.blogspot.com/">All 48 States</a></li>
      </ul></div>
      <div class="footer-col"><h5>Hours</h5><ul>
        <li style="color:rgba(255,255,255,0.5);">Mon–Fri</li>
        <li style="color:var(--orange);font-weight:600;">8:00 AM – 8:00 PM EST</li>
        <li style="color:rgba(255,255,255,0.5);margin-top:8px;">Saturday–Sunday</li>
        <li>Closed</li>
      </ul></div>
    </div>
    <div class="footer-bottom"><div>&copy; {year} Pro Dumpster Rental — {city}, {state_abbr} {zip_code}</div><div style="display:flex;gap:16px;"><a href="https://produmpsterrental.blogspot.com/privacy-policy/" style="color:rgba(255,255,255,0.2);font-size:12px;">Privacy Policy</a><a href="https://produmpsterrental.blogspot.com/terms/" style="color:rgba(255,255,255,0.2);font-size:12px;">Terms of Service</a></div></div>
  </div>
</footer>
<script>
function toggleFaq(el){{const item=el.parentElement;const isOpen=item.classList.contains('open');document.querySelectorAll('.faq-item').forEach(f=>f.classList.remove('open'));if(!isOpen)item.classList.add('open');el.setAttribute('aria-expanded',!isOpen);}}
document.querySelectorAll('a[href="tel:+16197596533"]').forEach(el=>{{el.addEventListener('click',function(){{if(typeof gtag!=='undefined')gtag('event','phone_call',{{'event_category':'CTA','event_label':'{city} {state_abbr}'}});}});}});
</script>
</body>
</html>"""


def save_page_to_db(city, state, state_abbr, zip_code, county, filename, blogspot_url, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR REPLACE INTO generated_pages
            (state,city,zip_code,county,filename,blogspot_url,title,meta_description,primary_keyword,long_tail_keywords,ai_provider)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
            (state,city,zip_code,county,filename,blogspot_url,
             content.get('meta_title',''),content.get('meta_description',''),
             content.get('primary_keyword',''),json.dumps(content.get('long_tail_keywords',[])),
             content.get('ai_provider','fallback')))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()

def generate_sitemap():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT blogspot_url, created_at FROM generated_pages WHERE blogspot_url IS NOT NULL ORDER BY created_at DESC')
    pages = c.fetchall(); conn.close()
    urls = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, created in pages:
        d = created[:10] if created else datetime.now().strftime('%Y-%m-%d')
        urls.append(f'  <url>\n    <loc>{url}</loc>\n    <lastmod>{d}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>')
    urls.append('</urlset>')
    return '\n'.join(urls)

@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM generated_pages')
    total = c.fetchone()[0]
    c.execute('SELECT state,city,zip_code,primary_keyword,filename,ai_provider,blogspot_url FROM generated_pages ORDER BY created_at DESC LIMIT 30')
    recent = c.fetchall()
    conn.close()
    existing_keys = get_all_keys()
    return render_template('index.html', locations=US_LOCATIONS, total_pages=total,
                           recent_pages=recent, business=BUSINESS_CONFIG,
                           ai_providers=AI_PROVIDERS, existing_keys=existing_keys)

@app.route('/api/save-key', methods=['POST'])
def save_key():
    data = request.json
    provider = data.get('provider')
    key = data.get('key','').strip()
    if not provider or provider not in AI_PROVIDERS:
        return jsonify({'error': 'Invalid provider'}), 400
    if not key:
        return jsonify({'error': 'API key is required'}), 400
    save_ai_key(provider, key)
    return jsonify({'success': True, 'message': f'{AI_PROVIDERS[provider]["name"]} key saved!'})

@app.route('/api/test-key', methods=['POST'])
def test_key():
    data = request.json
    provider = data.get('provider')
    key = data.get('key','').strip()
    if not provider or not key:
        return jsonify({'error': 'Missing data'}), 400
    try:
        test_prompt = 'Respond with exactly this JSON and nothing else: {"status":"OK"}'
        if provider == 'anthropic':
            result = call_ai_anthropic(key, test_prompt)
        else:
            result = call_ai_openai_compat(provider, key, test_prompt)
        return jsonify({'success': True, 'message': f'Key works!', 'response': result[:80]})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Key failed: {str(e)[:150]}'})

@app.route('/api/cities/<state>')
def get_cities(state):
    if state in US_LOCATIONS:
        return jsonify({'cities': US_LOCATIONS[state]['cities'], 'abbreviation': US_LOCATIONS[state]['abbreviation']})
    return jsonify({'error': 'State not found'}), 404

@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.json
    state = data.get('state')
    city_data = data.get('city_data')
    if not state or not city_data or state not in US_LOCATIONS:
        return jsonify({'error': 'Missing or invalid data'}), 400
    state_abbr = US_LOCATIONS[state]['abbreviation']
    city = city_data['name']
    zip_code = city_data['zip']
    county = city_data['county']
    blogspot_url = build_blogspot_url(city, state_abbr, zip_code)
    city_slug = city.lower().replace(' ', '').replace('.', '').replace("'", "")
    filename = f"dumpster{city_slug}{state_abbr.lower()}{zip_code}.html"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT filename FROM generated_pages WHERE filename=?', (filename,))
    existing = c.fetchone(); conn.close()
    provider, api_key = get_active_provider()
    if existing and os.path.exists(os.path.join(OUTPUT_DIR, filename)) and not provider:
        token = get_or_create_token(filename)
        generated = session.get('generated_pages', [])
        if filename not in generated:
            generated.append(filename)
            session['generated_pages'] = generated
        return jsonify({'success': True, 'filename': filename, 'cached': True, 'blogspot_url': blogspot_url,
                        'preview_url': f'/preview/{filename}?token={token}',
                        'message': 'Page already exists'})
    try:
        content = generate_seo_content(city, state, state_abbr, zip_code, county)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    html = generate_html_page(city, state, state_abbr, zip_code, county, content, blogspot_url)
    with open(os.path.join(OUTPUT_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(html)
    save_page_to_db(city, state, state_abbr, zip_code, county, filename, blogspot_url, content)
    generated = session.get('generated_pages', [])
    if filename not in generated:
        generated.append(filename)
        session['generated_pages'] = generated
    with open(os.path.join(OUTPUT_DIR, 'sitemap.xml'), 'w') as f:
        f.write(generate_sitemap())
    token = get_or_create_token(filename)
    return jsonify({'success': True, 'filename': filename, 'cached': False, 'blogspot_url': blogspot_url,
                    'preview_url': f'/preview/{filename}?token={token}',
                    'meta_title': content['meta_title'], 'primary_keyword': content['primary_keyword'],
                    'long_tail_keywords': content['long_tail_keywords'][:6],
                    'ai_provider': content.get('ai_provider','fallback'),
                    'message': f'Page generated for {city}, {state_abbr}'})

@app.route('/preview/<filename>')
def preview_page(filename):
    token = request.args.get('token', '')
    if not token or not verify_token(filename, token):
        return "Access denied. Invalid or missing token.", 403
    return send_from_directory(OUTPUT_DIR, filename)

@app.route('/download/<filename>')
def download_page(filename):
    token = request.args.get('token', '')
    if not token or not verify_token(filename, token):
        return "Access denied. Invalid or missing token.", 403
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

@app.route('/sitemap.xml')
def sitemap():
    return generate_sitemap(), 200, {'Content-Type': 'application/xml'}

@app.route('/api/pages')
def list_pages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT state,city,zip_code,county,filename,title,primary_keyword,ai_provider,blogspot_url,created_at FROM generated_pages ORDER BY created_at DESC')
    pages = c.fetchall(); conn.close()
    return jsonify([{'state':p[0],'city':p[1],'zip':p[2],'county':p[3],'filename':p[4],'title':p[5],'keyword':p[6],'provider':p[7],'blogspot_url':p[8],'created':p[9]} for p in pages])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
