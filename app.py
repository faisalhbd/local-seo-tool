"""
Local SEO Page Generator — Dumpster Rental
Multi-AI Support: Anthropic, Groq, Together AI, OpenRouter
Blogspot URL Structure: dumpsterCityStateZip.blogspot.com
"""

import os, json, sqlite3, re, requests
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
        "model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        "free": True,
        "signup": "https://console.groq.com",
        "header_key": "Authorization",
        "header_format": "Bearer {key}",
    },
    "together": {
        "name": "Together AI (FREE $25 credit)",
        "url": "https://api.together.xyz/v1/chat/completions",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
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
        "model": "claude-3-5-haiku-20241022",
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


def get_geo_position(zip_code):
    """Return lat;lon string for geo.position meta tag via zippopotam.us API."""
    try:
        r = requests.get(f"https://api.zippopotam.us/us/{zip_code}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            lat = data["places"][0]["latitude"]
            lon = data["places"][0]["longitude"]
            return f"{lat};{lon}"
    except Exception:
        pass
    return ""
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

def call_ai_openai_compat(provider_name, api_key, prompt, retries=3):
    cfg = AI_PROVIDERS[provider_name]
    headers = {"Content-Type": "application/json", cfg["header_key"]: cfg["header_format"].format(key=api_key)}
    if provider_name == "openrouter":
        headers["HTTP-Referer"] = "https://produmpsterrental.com"
    models = cfg.get("models") or ([cfg["model"]] if cfg.get("model") else [])
    if not models:
        raise RuntimeError(f"No model configured for {provider_name}")
    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert local SEO copywriter. Always respond with valid JSON only, no markdown, no extra text."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7, "max_tokens": 1500,
        }
        for attempt in range(retries):
            try:
                r = requests.post(cfg["url"], headers=headers, json=payload, timeout=60)
                if r.status_code == 429:
                    wait = 15 * (attempt + 1)
                    print(f"Rate limit hit on {provider_name} ({model}), waiting {wait}s (attempt {attempt+1}/{retries})")
                    import time; time.sleep(wait)
                    continue
                r.raise_for_status()
                response_json = r.json()
                return response_json["choices"][0]["message"]["content"].strip()
            except requests.exceptions.Timeout:
                print(f"Timeout on {provider_name} ({model}) attempt {attempt+1}/{retries}")
                if attempt == retries - 1:
                    continue  # try next model
            except Exception as e:
                print(f"AI Error ({provider_name}, {model}, attempt {attempt+1}): {e}")
                if attempt == retries - 1:
                    continue  # try next model
                import time; time.sleep(2)
    raise RuntimeError(f"{provider_name} failed after trying all models and {retries} attempts per model")

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


def build_meta_title(city, state_abbr, zip_code):
    """Generate a meta title strictly between 50-60 chars."""
    candidates = [
        f"Dumpster Rental {city}, {state_abbr} {zip_code} | Pro Dumpster Rental",
        f"Dumpster Rental {city}, {state_abbr} | Pro Dumpster Rental",
        f"Commercial Dumpster Rental {city}, {state_abbr} {zip_code}",
        f"Commercial Dumpster Rental {city}, {state_abbr}",
        f"Roll-Off Dumpster Rental {city}, {state_abbr} {zip_code}",
        f"Roll-Off Dumpster Rental {city}, {state_abbr}",
    ]
    for c in candidates:
        if 50 <= len(c) <= 60:
            return c
    valid = [c for c in candidates if len(c) <= 60]
    return max(valid, key=len) if valid else candidates[-1][:60]


def build_meta_desc(city, state_abbr, zip_code):
    """Generate a meta description strictly between 140-155 chars."""
    core = (
        f"Commercial dumpster rental in {city}, {state_abbr} {zip_code}. "
        f"10–40 yard containers for contractors. "
        f"Call (619) 759-6533 Mon–Fri 8AM–8PM EST."
    )
    if 140 <= len(core) <= 155:
        return core
    if len(core) > 155:
        return core[:152] + "..."
    # Too short — pad with city-specific suffix
    pad = f" Serving {city} commercial job sites."
    result = core + pad
    if len(result) > 155:
        result = result[:152] + "..."
    return result


def generate_seo_content(city, state, state_abbr, zip_code, county):
    saved_keys = get_saved_provider_keys()
    if not saved_keys:
        raise RuntimeError('No AI provider key found. Please save a valid Groq, Together, OpenRouter, or Anthropic key before generating pages.')
    providers_to_try = [p for p in ["groq","together","openrouter","anthropic"] if p in saved_keys]
    keywords = get_long_tail_keywords(city, state_abbr, zip_code, county)
    primary_kw = f"commercial dumpster rental {city} {state_abbr}"
    county_short = county.replace(" County", "").replace(" Parish", "")

    # ---------------------------------------------------------------
    # CONVERSION-OPTIMIZED PROMPT — SEO + Pay-Per-Call focused
    # ---------------------------------------------------------------
    prompt = f"""You are an expert direct-response copywriter AND local SEO specialist writing for a commercial dumpster rental pay-per-call campaign.

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
- Target Clients: Licensed contractors, GCs, construction companies, commercial property managers ONLY. NO homeowners accepted.

SEO RULES:
1. meta_title MUST be 50-60 characters exactly — count every character
2. meta_description MUST be 140-155 characters exactly — include phone (619) 759-6533
3. H1 MUST be under 65 characters — city + keyword only, punchy
4. Every section must mention {city} or {county} naturally — no keyword stuffing
5. NEVER start intro_paragraph with "As a leading", "Located in the heart of", "Are you looking for"

CONVERSION RULES (CRITICAL — this page must make contractors call):
6. hero_subtitle: Must create URGENCY — mention same-day/next-day delivery availability + {county}
7. qualifier_checklist: Write exactly 4 short bullet items that help a contractor self-identify as the RIGHT customer (they are: licensed contractor or GC, managing active job sites, needing 10-40 yard containers, NOT a homeowner). Make them feel seen and welcome.
8. qualifier_reject: Write 1 short sentence politely turning away homeowners and redirecting them
9. intro_paragraph: Start by stating WHO this service is for (contractors, not homeowners). Then 3 more sentences with local {city}/{county} construction context. Must feel human, not AI-generated.
10. why_us_points: Each must address a contractor PAIN POINT (not generic features). Pain points: job site delays, wrong container size, hidden fees, slow response time.
11. cta_headline: Must include urgency trigger — "This Week", "Today", "Before 8PM", "Spots Fill Fast", or "Next-Day Available"
12. trust_bar: Write exactly 3 short trust signals (e.g. "500+ Job Sites Served", "Flat-Rate No Hidden Fees", "Next-Day Delivery Available") — make them feel credible
13. size_qualifiers: For each dumpster size (10, 20, 30, 40 yard), write a 1-sentence "Best for:" description targeting contractor use cases ONLY (no residential examples)
14. faq answers must always end with a call-to-action to phone (619) 759-6533

Respond ONLY with this exact JSON (no markdown, no preamble, no extra text):
{{"meta_title":"[50-60 chars]","meta_description":"[140-155 chars with phone]","h1":"[under 65 chars — MUST include the word Rental e.g. Commercial Dumpster Rental {city}]","hero_subtitle":"[urgency + next-day/same-day + {county} contractors]","trust_bar":["[trust signal 1]","[trust signal 2]","[trust signal 3]"],"qualifier_checklist":["[✅ contractor self-qualifier 1]","[✅ contractor self-qualifier 2]","[✅ contractor self-qualifier 3]","[✅ contractor self-qualifier 4]"],"qualifier_reject":"[1 polite sentence for homeowners]","intro_paragraph":"[4 sentences: who it's for + {city}/{county} local context]","why_us_points":[{{"title":"[contractor pain point title]","desc":"[2 sentences — solve the pain, mention {city} or {county}]"}},{{"title":"[pain point 2]","desc":"[2 sentences]"}},{{"title":"[pain point 3]","desc":"[2 sentences mentioning {city}]"}},{{"title":"[pain point 4]","desc":"[2 sentences]"}}],"size_qualifiers":{{"10":"[Best for: commercial use case only]","20":"[Best for: commercial use case only]","30":"[Best for: commercial use case only]","40":"[Best for: commercial use case only]"}},"service_area_paragraph":"[3+ sentences — {city}, {county}, ZIP {zip_code}, nearby areas]","cta_headline":"[urgency headline with {city} {state_abbr} — must have time trigger]","faq":[{{"q":"[contractor-specific FAQ about renting in {city}]","a":"[answer ending with call to (619) 759-6533]"}},{{"q":"[FAQ about acceptable waste types for construction in {city}]","a":"[answer ending with call prompt]"}},{{"q":"[FAQ about choosing right size for {city} job sites]","a":"[answer ending with call prompt]"}},{{"q":"[FAQ about service area coverage near {city} and {county}]","a":"[answer ending with call to (619) 759-6533]"}}],"schema_description":"[2-3 sentences for LocalBusiness schema — {city}, {state_abbr}]","og_description":"[1-2 sentence social share — {city} commercial focus]"}}"""

    raw = None
    used_provider = None
    errors = []

    for provider in providers_to_try:
        api_key = saved_keys.get(provider)
        for attempt in range(2):  # retry once per provider
            try:
                if provider == "anthropic":
                    raw = call_ai_anthropic(api_key, prompt)
                else:
                    raw = call_ai_openai_compat(provider, api_key, prompt)
                used_provider = provider
                import time; time.sleep(3)  # 3s delay to avoid rate limit
                break
            except Exception as e:
                print(f"AI Error ({provider}, attempt {attempt+1}): {e}")
                if attempt == 1:
                    errors.append(f"{provider}: {e}")
                raw = None
        if raw:
            break

    if raw:
        try:
            # Aggressive JSON cleaning
            cleaned = raw.strip()
            # Remove markdown code fences
            cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()
            # If model added preamble text, extract JSON object only
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                cleaned = json_match.group(0)
            data = json.loads(cleaned)
            data['long_tail_keywords'] = keywords
            data['primary_keyword'] = primary_kw
            data['ai_provider'] = used_provider or 'unknown'
            return data
        except Exception as e:
            print(f"JSON parse error: {e}\nRaw response: {raw[:500]}")
            # Don't raise — fall through to fallback below

    # All providers failed or JSON invalid — use fallback static content
    print(f"Using fallback content. Provider errors: {errors}")
    return {
        "meta_title": build_meta_title(city, state_abbr, zip_code),
        "meta_description": build_meta_desc(city, state_abbr, zip_code),
        "h1": f"Commercial Dumpster Rental {city}, {state_abbr}",
        "hero_subtitle": f"Same-Day & Next-Day Roll-Off Delivery for Active Job Sites in {county} — Contractors Only.",
        "trust_bar": [
            "500+ Commercial Job Sites Served",
            "Flat-Rate Pricing — No Hidden Fees",
            "Next-Day Delivery Available"
        ],
        "qualifier_checklist": [
            "✅ You're a licensed contractor, GC, or site manager",
            "✅ You have an active commercial or construction job site",
            "✅ You need a 10, 20, 30, or 40-yard roll-off container",
            "✅ You need reliable, on-schedule waste removal"
        ],
        "qualifier_reject": f"We serve commercial and construction clients only — homeowners should contact a local residential waste service.",
        "intro_paragraph": f"Pro Dumpster Rental is built exclusively for contractors, general contractors, and commercial property managers in {city}, {state_abbr} {zip_code} — not homeowners. If you're managing an active job site in {county} and need a roll-off container delivered on schedule, we're the crew for you. From demolition cleanups to major commercial renovations, our 10 to 40-yard containers handle the heaviest construction debris. Call (619) 759-6533 and our dispatcher will have your container on site — often next business day.",
        "why_us_points": [
            {"title": "No Job Site Delays", "desc": f"A late dumpster can halt your entire crew in {city}. We deliver on the schedule you need — next-day in most {county} locations — so your project keeps moving."},
            {"title": "Right Size, First Time", "desc": f"Ordering the wrong size wastes money and time on {city} job sites. Our dispatchers match your container to your project scope before we confirm the order."},
            {"title": "Zero Hidden Fees", "desc": f"You'll get a flat-rate quote before your container ships to {city}. The price you hear on the phone is the price you pay — no surprise charges at pickup."},
            {"title": "Contractor-Dedicated Service", "desc": f"We don't mix homeowner calls with contractor jobs. Every {county} commercial client gets a dedicated dispatcher who understands job site logistics, not residential cleanup."}
        ],
        "size_qualifiers": {
            "10": f"Best for: Small commercial cleanouts, office gut renovations, retail fixture removal in {city}",
            "20": f"Best for: Roofing tear-offs, flooring removal, mid-size structural demo on {county} job sites",
            "30": f"Best for: Full commercial gut remodels, major construction debris, multi-trade renovation projects in {city}",
            "40": f"Best for: Large-scale demolition, industrial teardowns, bulk concrete and slab removal in {county}"
        },
        "service_area_paragraph": f"We serve all active commercial and construction job sites in {city}, {state_abbr} {zip_code} and throughout {county}. Our delivery zone covers surrounding communities near {city}, including other commercial corridors and active build areas in the region. Call (619) 759-6533 to confirm next-day availability at your specific {city} worksite — our dispatcher can lock in your delivery window in under 60 seconds.",
        "cta_headline": f"Need a Dumpster on Your {city} Job Site This Week?",
        "faq": [
            {"q": f"How do I rent a commercial dumpster in {city}, {state_abbr}?", "a": f"Call (619) 759-6533 Mon–Fri 8AM–8PM EST — our dispatcher confirms availability in {city} and gives you a flat-rate quote in under 60 seconds. We serve {county} contractors only, no homeowner requests accepted."},
            {"q": f"What types of construction waste can I dispose of in {city}?", "a": f"Our {city} containers accept concrete, roofing shingles, drywall, lumber, demolition debris, commercial renovation waste, metal scraps, and bulk construction materials. Hazardous materials are not accepted — call (619) 759-6533 if you're unsure about specific materials."},
            {"q": f"What dumpster size do I need for my {city} job site?", "a": f"10-yard for small commercial cleanouts; 20-yard for roofing and mid-size renovations; 30-yard for major commercial builds; 40-yard for full demolition and industrial projects in {county}. Not sure? Call (619) 759-6533 and our dispatcher will size it for you."},
            {"q": f"Does Pro Dumpster Rental deliver to areas near {city}, {state_abbr}?", "a": f"Yes — we cover {city}, all of {county}, and surrounding communities. Call (619) 759-6533 to confirm next-day or same-week availability at your exact worksite location."}
        ],
        "schema_description": f"Pro Dumpster Rental provides commercial and construction roll-off dumpster rental in {city}, {state_abbr} {zip_code} and throughout {county}. Serving licensed contractors and commercial property managers with 10 to 40-yard containers. Call (619) 759-6533.",
        "og_description": f"Commercial roll-off dumpster rental in {city}, {state_abbr}. Serving {county} contractors and construction job sites. Flat-rate pricing. Call (619) 759-6533.",
        "long_tail_keywords": keywords,
        "primary_keyword": primary_kw,
        "ai_provider": "fallback"
    }


def generate_html_page(city, state, state_abbr, zip_code, county, content, blogspot_url):
    kw_str = ", ".join(content['long_tail_keywords'][:12])
    county_short = county.replace(" County", "").replace(" Parish", "")

    # ── Auto-sanitize all SEO fields ──────────────────────────────
    # Title: must be 50-60 chars
    meta_title = content['meta_title']
    if not (50 <= len(meta_title) <= 60):
        meta_title = build_meta_title(city, state_abbr, zip_code)

    # H1: hard cap 65 chars + must contain "Rental"
    h1_raw = content['h1']
    if len(h1_raw) > 65 or "rental" not in h1_raw.lower():
        h1_raw = f"Commercial Dumpster Rental {city}, {state_abbr}"
        if len(h1_raw) > 65:
            h1_raw = f"Dumpster Rental {city}, {state_abbr}"

    # Meta description: must be 140-155 chars
    meta_desc = content['meta_description']
    if not (140 <= len(meta_desc) <= 155):
        meta_desc = build_meta_desc(city, state_abbr, zip_code)

    # CTA Headline: hard cap 70 chars — trim if AI returned too long
    cta_headline = content.get('cta_headline', f"Need a Dumpster on Your {city} Job Site This Week?")
    if len(cta_headline) > 70:
        cta_headline = f"Need a Dumpster on Your {city} Job Site This Week?"
    content['cta_headline'] = cta_headline

    schema = {
        "@context": "https://schema.org", "@type": "LocalBusiness",
        "name": f"Pro Dumpster Rental - {city}",
        "url": blogspot_url,
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
    icons = ["⚡","🛡️","🏗️","💰"]
    why_html = "".join([f'<div class="why-card"><div class="why-icon" aria-hidden="true">{icons[i%4]}</div><h3>{p["title"]}</h3><p>{p["desc"]}</p></div>' for i,p in enumerate(content['why_us_points'])])
    faq_html = "".join([f'<div class="faq-item" itemscope itemprop="mainEntity" itemtype="https://schema.org/Question"><div class="faq-q" onclick="toggleFaq(this)" role="button" aria-expanded="false"><span itemprop="name">{f["q"]}</span><div class="faq-arrow" aria-hidden="true">+</div></div><div class="faq-a" itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer"><div class="faq-a-inner" itemprop="text">{f["a"]}</div></div></div>' for f in content['faq']])
    h1_display = h1_raw.replace(city, f'<span>{city}</span>', 1)
    year = datetime.now().year
    geo_position = get_geo_position(zip_code)
    og_image = f"{blogspot_url}og-image.jpg"

    # Trust bar HTML
    trust_bar_items = content.get('trust_bar', ["500+ Job Sites Served", "Flat-Rate — No Hidden Fees", "Next-Day Delivery Available"])
    trust_bar_html = "".join([f'<div class="trust-item"><span class="trust-check">✔</span>{t}</div>' for t in trust_bar_items])

    # Qualifier checklist HTML
    qualifiers = content.get('qualifier_checklist', [
        "✅ You're a licensed contractor or general contractor",
        "✅ You manage active commercial or construction job sites",
        "✅ You need 10, 20, 30, or 40-yard roll-off containers",
        "✅ You need reliable, on-schedule waste removal"
    ])
    qualifier_html = "".join([f'<li class="qual-item">{q}</li>' for q in qualifiers])
    qualifier_reject = content.get('qualifier_reject', f'We serve commercial and construction clients only — homeowners should contact a local residential waste service.')

    # Size qualifiers
    sq = content.get('size_qualifiers', {
        "10": f"Best for: Small commercial cleanouts, office renovations, retail fixture removal",
        "20": f"Best for: Roofing tear-offs, flooring removal, mid-size structural demo",
        "30": f"Best for: Full commercial gut remodels, major construction debris",
        "40": f"Best for: Large-scale demolition, industrial teardowns, bulk concrete removal"
    })

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
<meta name="geo.position" content="{geo_position}">
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
:root{{--black:#111010;--dark:#1c1c1c;--steel:#2b2b2b;--orange:#e8520a;--orange-bright:#ff6b1a;--yellow:#f5a623;--white:#ffffff;--gray-500:#888070;--gray-700:#4a4540;--green:#2a7d46;--radius:6px;}}
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
.trust-bar{{background:var(--green);padding:10px 24px;}}
.trust-bar-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:center;align-items:center;gap:32px;flex-wrap:wrap;}}
.trust-item{{color:white;font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;display:flex;align-items:center;gap:7px;}}
.trust-check{{color:var(--yellow);font-size:16px;}}
.breadcrumb-bar{{background:var(--steel);padding:10px 24px;}}
.breadcrumb{{list-style:none;display:flex;align-items:center;flex-wrap:wrap;gap:6px;font-size:12px;color:rgba(255,255,255,0.4);max-width:1200px;margin:0 auto;}}
.breadcrumb li+li::before{{content:"›";margin-right:6px;}}
.breadcrumb a{{color:rgba(255,255,255,0.5);transition:color 0.2s;}}
.breadcrumb a:hover{{color:var(--orange);}}
.breadcrumb li:last-child{{color:var(--orange);}}
.hero{{background:var(--black);position:relative;overflow:hidden;padding:72px 24px 80px;}}
.hero::before{{content:'';position:absolute;inset:0;background:repeating-linear-gradient(45deg,transparent,transparent 40px,rgba(255,255,255,0.012) 40px,rgba(255,255,255,0.012) 80px);pointer-events:none;}}
.hero-inner{{max-width:1200px;margin:0 auto;position:relative;display:grid;grid-template-columns:1fr 340px;gap:56px;align-items:center;}}
.hero-badge{{display:inline-flex;align-items:center;gap:8px;background:rgba(232,82,10,0.15);border:1px solid rgba(232,82,10,0.4);color:var(--orange);padding:6px 16px;border-radius:4px;font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:20px;}}
.hero h1{{font-size:clamp(2rem,5vw,3.2rem);font-weight:700;color:white;line-height:1.1;margin-bottom:10px;}}
.hero h1 span{{color:var(--orange);}}
.hero-subtitle{{font-size:17px;color:rgba(255,255,255,0.75);margin-bottom:14px;line-height:1.5;font-weight:500;}}
.b2b-tag{{display:inline-flex;align-items:center;gap:6px;background:rgba(42,125,70,0.2);border:1px solid rgba(42,125,70,0.5);color:#5dba80;padding:5px 14px;border-radius:4px;font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:28px;}}
.hero-actions{{display:flex;flex-wrap:wrap;gap:14px;align-items:center;}}
.btn-primary{{background:var(--orange);color:white;border:none;border-radius:4px;padding:16px 28px;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:18px;cursor:pointer;display:inline-flex;align-items:center;gap:10px;text-decoration:none;transition:all 0.2s;box-shadow:0 6px 24px rgba(232,82,10,0.45);text-transform:uppercase;letter-spacing:0.04em;}}
.btn-primary:hover{{background:var(--orange-bright);transform:translateY(-2px);}}
.btn-outline{{background:transparent;color:white;border:2px solid rgba(255,255,255,0.3);border-radius:4px;padding:14px 24px;font-family:'Barlow Condensed',sans-serif;font-weight:600;font-size:16px;cursor:pointer;display:inline-flex;align-items:center;gap:8px;text-decoration:none;transition:all 0.2s;text-transform:uppercase;}}
.btn-outline:hover{{border-color:var(--orange);color:var(--orange);}}
.hero-stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:32px;}}
.stat{{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:var(--radius);padding:14px;text-align:center;}}
.stat-num{{font-family:'Oswald',sans-serif;font-size:1.8rem;font-weight:700;color:var(--orange);line-height:1;}}
.stat-lbl{{font-size:10px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.06em;margin-top:4px;}}
.call-card{{background:var(--steel);border:2px solid rgba(232,82,10,0.4);border-radius:8px;padding:28px 24px;text-align:center;}}
.call-card-tag{{display:inline-block;background:rgba(42,125,70,0.25);border:1px solid rgba(42,125,70,0.5);color:#5dba80;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;padding:3px 12px;border-radius:20px;margin-bottom:12px;}}
.call-card h3{{font-size:18px;color:white;margin-bottom:4px;font-family:'Oswald',sans-serif;text-transform:uppercase;}}
.call-card-sub{{font-size:12px;color:rgba(255,255,255,0.4);margin-bottom:4px;}}
.call-phone{{font-family:'Oswald',sans-serif;font-size:28px;color:var(--orange);font-weight:700;display:block;margin:14px 0 16px;text-decoration:none;}}
.call-note{{font-size:11px;color:rgba(255,255,255,0.35);margin-top:14px;line-height:1.8;text-align:left;}}
.call-note span{{color:var(--yellow);}}
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
.qual-wrapper{{background:#f5fbf7;padding:0 24px 40px;}}
.qual-box{{max-width:1200px;margin:0 auto;background:white;border:2px solid rgba(42,125,70,0.25);border-radius:8px;padding:32px;}}
.qual-title{{font-family:'Oswald',sans-serif;font-size:20px;font-weight:700;text-transform:uppercase;color:var(--dark);margin-bottom:20px;display:flex;align-items:center;gap:10px;}}
.qual-list{{list-style:none;display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px;}}
.qual-item{{font-size:14px;font-weight:600;color:#1a4d2e;padding:10px 14px;background:rgba(42,125,70,0.07);border-radius:var(--radius);border-left:3px solid var(--green);}}
.qual-reject{{font-size:13px;color:#999;font-style:italic;padding-top:14px;border-top:1px solid rgba(42,125,70,0.15);}}
.why-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:2px;}}
.why-card{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);padding:32px 28px;transition:all 0.25s;}}
.why-card:hover{{background:rgba(232,82,10,0.08);border-color:rgba(232,82,10,0.25);transform:translateY(-3px);}}
.why-icon{{font-size:30px;margin-bottom:14px;}}
.why-card h3{{font-size:17px;color:white;margin-bottom:10px;}}
.why-card p{{font-size:14px;color:rgba(255,255,255,0.55);line-height:1.65;}}
.sizes-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:20px;}}
.size-card{{background:white;border:2px solid #edebe7;border-radius:var(--radius);padding:28px 18px 22px;text-align:center;transition:all 0.2s;position:relative;}}
.size-card:hover{{border-color:var(--orange);transform:translateY(-4px);box-shadow:0 12px 40px rgba(232,82,10,0.15);}}
.size-card.popular{{border-color:var(--orange);}}
.popular-tag{{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:var(--orange);color:white;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;padding:3px 12px;border-radius:20px;white-space:nowrap;}}
.size-num{{font-family:'Oswald',sans-serif;font-size:52px;font-weight:700;color:var(--orange);line-height:1;}}
.size-yd{{font-family:'Oswald',sans-serif;font-size:16px;color:var(--gray-500);text-transform:uppercase;}}
.size-name{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:var(--gray-500);margin:8px 0 6px;}}
.size-qualifier{{font-size:12px;color:#2a7d46;font-weight:600;background:#f0faf4;border:1px solid rgba(42,125,70,0.2);border-radius:4px;padding:7px 10px;margin-bottom:14px;line-height:1.4;text-align:left;}}
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
.faq-item.open .faq-a{{max-height:320px;}}
.cta-banner{{background:var(--orange);padding:60px 24px;text-align:center;}}
.cta-banner h2{{font-size:clamp(1.8rem,4vw,2.8rem);color:white;margin-bottom:10px;}}
.cta-urgency{{display:inline-block;background:rgba(0,0,0,0.15);border:1px solid rgba(255,255,255,0.3);color:white;font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;padding:5px 16px;border-radius:20px;margin-bottom:18px;}}
.cta-banner p{{font-size:16px;color:rgba(255,255,255,0.9);margin-bottom:24px;}}
.phone-big{{font-family:'Oswald',sans-serif;font-size:clamp(2rem,6vw,3.8rem);color:white;font-weight:700;display:block;margin-bottom:20px;text-decoration:none;}}
.cta-note{{font-size:13px;color:rgba(255,255,255,0.75);margin-top:16px;}}
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
.legal-modal-overlay{{position:fixed;inset:0;background:rgba(0,0,0,0.82);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px;opacity:0;pointer-events:none;transition:opacity 0.25s;}}
.legal-modal-overlay.open{{opacity:1;pointer-events:all;}}
.legal-modal{{background:#1c1c1c;border:1px solid rgba(255,255,255,0.1);border-radius:10px;max-width:760px;width:100%;max-height:85vh;display:flex;flex-direction:column;transform:translateY(20px);transition:transform 0.25s;}}
.legal-modal-overlay.open .legal-modal{{transform:translateY(0);}}
.legal-modal-header{{display:flex;align-items:center;justify-content:space-between;padding:20px 24px;border-bottom:1px solid rgba(255,255,255,0.08);flex-shrink:0;}}
.legal-modal-header h3{{font-family:'Oswald',sans-serif;font-size:20px;color:white;text-transform:uppercase;letter-spacing:0.04em;margin:0;}}
.legal-modal-close{{background:rgba(255,255,255,0.08);border:none;color:rgba(255,255,255,0.6);width:34px;height:34px;border-radius:50%;cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center;transition:all 0.2s;flex-shrink:0;}}
.legal-modal-close:hover{{background:var(--orange);color:white;}}
.legal-modal-body{{overflow-y:auto;padding:24px;flex:1;}}
.legal-modal-body h4{{font-family:'Oswald',sans-serif;font-size:15px;color:var(--orange);text-transform:uppercase;letter-spacing:0.06em;margin:22px 0 8px;}}
.legal-modal-body h4:first-child{{margin-top:0;}}
.legal-modal-body p{{font-size:13px;color:rgba(255,255,255,0.5);line-height:1.75;margin-bottom:10px;}}
.legal-modal-footer{{padding:16px 24px;border-top:1px solid rgba(255,255,255,0.08);text-align:right;flex-shrink:0;}}
.legal-modal-footer button{{background:var(--orange);color:white;border:none;padding:10px 24px;border-radius:4px;font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:14px;text-transform:uppercase;cursor:pointer;transition:background 0.2s;}}
.legal-modal-footer button:hover{{background:var(--orange-bright);}}
@media(max-width:900px){{.hero-inner{{grid-template-columns:1fr;}}.call-card{{display:none;}}.footer-grid{{grid-template-columns:1fr 1fr;}}.location-grid{{grid-template-columns:1fr;}}.hero-stats{{grid-template-columns:repeat(2,1fr);}}.qual-list{{grid-template-columns:1fr;}}.trust-bar-inner{{gap:16px;}}}}
@media(max-width:600px){{.hero{{padding:40px 20px 50px;}}.topbar{{font-size:11px;}}.footer-grid{{grid-template-columns:1fr;}}.location-facts{{grid-template-columns:1fr;}}}}
@media print{{header,footer,.cta-banner,.topbar,.trust-bar{{display:none;}}body{{color:black;}}}}
</style>
</head>
<body>
<a href="#main-content" class="skip-nav">Skip to main content</a>
<div class="topbar" role="complementary">
  <span>📞 <a href="tel:+16197596533" style="color:white;font-weight:700;">(619) 759-6533</a> — Commercial &amp; Construction Clients Only</span>
  <span>Hours: <span class="hours">Mon–Fri 8AM–8PM EST</span> &nbsp;|&nbsp; 🇺🇸 Nationwide USA</span>
</div>
<header role="banner">
  <div class="header-inner">
    <div class="logo" aria-label="Pro Dumpster Rental">
      <div class="logo-icon" aria-hidden="true">🗑️</div>
      <div>
        <div class="logo-text">Pro <span>Dumpster</span> Rental</div>
        <div class="logo-sub">Commercial &amp; Construction Job Sites Only</div>
      </div>
    </div>
    <a href="tel:+16197596533" class="cta-call" aria-label="Call (619) 759-6533 for free quote">
      <div class="pulse" aria-hidden="true"></div>📞 (619) 759-6533
    </a>
  </div>
</header>
<div class="trust-bar" role="complementary" aria-label="Trust signals">
  <div class="trust-bar-inner">{trust_bar_html}</div>
</div>
<nav aria-label="Breadcrumb" class="breadcrumb-bar">
  <ol class="breadcrumb" itemscope itemtype="https://schema.org/BreadcrumbList">
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem"><a href="{blogspot_url}" itemprop="item"><span itemprop="name">Home</span></a><meta itemprop="position" content="1"></li>
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem"><a href="{blogspot_url}locations/" itemprop="item"><span itemprop="name">Locations</span></a><meta itemprop="position" content="2"></li>
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem"><a href="{blogspot_url}locations/{state_abbr.lower()}/" itemprop="item"><span itemprop="name">{state}</span></a><meta itemprop="position" content="3"></li>
    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem"><span itemprop="name">{city}, {state_abbr}</span><meta itemprop="position" content="4"></li>
  </ol>
</nav>
<section class="hero" aria-labelledby="hero-h1">
  <div class="hero-inner">
    <div>
      <div class="hero-badge" aria-label="Service location">📍 Serving {city}, {state_abbr} {zip_code}</div>
      <h1 id="hero-h1">{h1_display}</h1>
      <p class="hero-subtitle">{content['hero_subtitle']}</p>
      <div class="b2b-tag">🏗️ For Licensed Contractors &amp; Commercial Sites — Not Homeowners</div>
      <div class="hero-actions">
        <a href="tel:+16197596533" class="btn-primary" aria-label="Call (619) 759-6533 for free quote">📞 Call (619) 759-6533</a>
        <a href="#sizes" class="btn-outline">View Sizes ↓</a>
      </div>
      <div class="hero-stats" aria-label="Key statistics">
        <div class="stat"><div class="stat-num">500+</div><div class="stat-lbl">Job Sites Served</div></div>
        <div class="stat"><div class="stat-num">48</div><div class="stat-lbl">States</div></div>
        <div class="stat"><div class="stat-num">B2B</div><div class="stat-lbl">Only</div></div>
        <div class="stat"><div class="stat-num">24h</div><div class="stat-lbl">Delivery</div></div>
      </div>
    </div>
    <div class="call-card" role="complementary" aria-label="Call us now">
      <div class="call-card-tag">✔ Contractors Only</div>
      <h3>Get a Free Quote Now</h3>
      <p class="call-card-sub">Live dispatcher — under 60 seconds</p>
      <a href="tel:+16197596533" class="call-phone" aria-label="Call (619) 759-6533">(619) 759-6533</a>
      <a href="tel:+16197596533" class="btn-primary" style="width:100%;justify-content:center;">📞 Tap to Call Now</a>
      <p class="call-note">
        <span>✔</span> Commercial &amp; Construction Only<br>
        <span>✔</span> Mon–Fri 8AM–8PM EST<br>
        <span>✔</span> Flat-Rate · No Hidden Fees<br>
        <span>✔</span> Same-Day &amp; Next-Day Available
      </p>
    </div>
  </div>
</section>
<div class="qual-wrapper">
  <div class="qual-box">
    <div class="qual-title">✅ Is This Service Right for You?</div>
    <ul class="qual-list" role="list">{qualifier_html}</ul>
    <p class="qual-reject">⚠️ {qualifier_reject}</p>
  </div>
</div>
<main id="main-content" role="main">
<section aria-labelledby="intro-h2">
  <div class="section-inner">
    <div class="section-tag">About Our {city} Service</div>
    <h2 class="section-title" id="intro-h2">Roll-Off Dumpsters Built for <span>{city} Job Sites</span></h2>
    <p class="section-sub">{content['intro_paragraph']}</p>
  </div>
</section>
<section class="section-dark" aria-labelledby="why-h2">
  <div class="section-inner">
    <div class="section-tag">Why Contractors Choose Us</div>
    <h2 class="section-title" id="why-h2">We Solve the Problems <span>Contractors Actually Face</span></h2>
    <div class="why-grid" role="list">{why_html}</div>
  </div>
</section>
<section id="sizes" aria-labelledby="sizes-h2">
  <div class="section-inner">
    <div class="section-tag">Container Options</div>
    <h2 class="section-title" id="sizes-h2">Roll-Off Sizes for <span>{city}, {state_abbr}</span> Job Sites</h2>
    <p class="section-sub">Every commercial and construction project in {city} is different. Choose the right container — or call us and we'll pick the right size for you.</p>
    <div class="sizes-grid">
      <div class="size-card">
        <div class="size-num">10</div><div class="size-yd">Yard</div>
        <div class="size-name">Roll-Off Dumpster</div>
        <div class="size-qualifier">{sq.get("10","Best for: Small commercial cleanouts and office renovations")}</div>
        <a href="tel:+16197596533" class="size-cta">Get Quote</a>
      </div>
      <div class="size-card">
        <div class="size-num">20</div><div class="size-yd">Yard</div>
        <div class="size-name">Roll-Off Dumpster</div>
        <div class="size-qualifier">{sq.get("20","Best for: Roofing tear-offs, flooring removal, mid-size demolition")}</div>
        <a href="tel:+16197596533" class="size-cta">Get Quote</a>
      </div>
      <div class="size-card popular">
        <div class="popular-tag">Most Popular in {city}</div>
        <div class="size-num">30</div><div class="size-yd">Yard</div>
        <div class="size-name">Roll-Off Dumpster</div>
        <div class="size-qualifier">{sq.get("30","Best for: Large commercial renovations, major construction projects")}</div>
        <a href="tel:+16197596533" class="size-cta">Get Quote</a>
      </div>
      <div class="size-card">
        <div class="size-num">40</div><div class="size-yd">Yard</div>
        <div class="size-name">Roll-Off Dumpster</div>
        <div class="size-qualifier">{sq.get("40","Best for: Industrial teardowns, bulk concrete and large demolition")}</div>
        <a href="tel:+16197596533" class="size-cta">Get Quote</a>
      </div>
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
  <div class="cta-urgency">⚡ Spots Fill Fast — Call Before 8PM EST Today</div>
  <h2 id="cta-h2">{content['cta_headline']}</h2>
  <p>Speak directly with a live dispatcher — commercial &amp; construction clients only. Mon–Fri 8AM–8PM EST.</p>
  <a href="tel:+16197596533" class="phone-big" aria-label="Call (619) 759-6533">(619) 759-6533</a>
  <a href="tel:+16197596533" class="btn-primary" style="font-size:18px;padding:16px 32px;">📞 Call Now — Free Quote</a>
  <p class="cta-note">✅ No obligation &nbsp;·&nbsp; ✅ Flat-rate pricing &nbsp;·&nbsp; ✅ {city}, {state_abbr} {zip_code} &nbsp;·&nbsp; ✅ B2B Only</p>
</section>
<footer role="contentinfo">
  <div class="footer-inner">
    <div class="disclaimer"><strong>Disclaimer:</strong> This site connects commercial and construction clients with dumpster rental providers. All providers are independent operators. Verify that providers furnish necessary licenses and insurance. Coverage: Continental USA only (excluding Alaska &amp; Hawaii). Commercial and construction clients only — homeowners are not accepted.</div>
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
        <li><a href="{blogspot_url}locations/{state_abbr.lower()}/">{state} Locations</a></li>
        <li><a href="{blogspot_url}">{city}, {state_abbr}</a></li>
        <li><a href="{blogspot_url}locations/">{county}</a></li>
        <li><a href="{blogspot_url}">ZIP {zip_code}</a></li>
        <li><a href="{blogspot_url}">All 48 States</a></li>
      </ul></div>
      <div class="footer-col"><h5>Hours</h5><ul>
        <li style="color:rgba(255,255,255,0.5);">Mon–Fri</li>
        <li style="color:var(--orange);font-weight:600;">8:00 AM – 8:00 PM EST</li>
        <li style="color:rgba(255,255,255,0.5);margin-top:8px;">Saturday–Sunday</li>
        <li>Closed</li>
      </ul></div>
    </div>
    <div class="footer-bottom">
      <div>&copy; {year} Pro Dumpster Rental — {city}, {state_abbr} {zip_code}</div>
      <div style="display:flex;gap:16px;">
        <a href="#" onclick="openModal('privacy');return false;" style="color:rgba(255,255,255,0.2);font-size:12px;">Privacy Policy</a>
        <a href="#" onclick="openModal('terms');return false;" style="color:rgba(255,255,255,0.2);font-size:12px;">Terms of Service</a>
      </div>
    </div>
  </div>
</footer>
<div class="legal-modal-overlay" id="legalModal" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
  <div class="legal-modal">
    <div class="legal-modal-header">
      <h3 id="modalTitle">Policy</h3>
      <button class="legal-modal-close" onclick="closeModal()" aria-label="Close">&times;</button>
    </div>
    <div class="legal-modal-body" id="modalBody"></div>
    <div class="legal-modal-footer"><button onclick="closeModal()">Close</button></div>
  </div>
</div>
<script>
function toggleFaq(el){{const item=el.parentElement;const isOpen=item.classList.contains('open');document.querySelectorAll('.faq-item').forEach(f=>f.classList.remove('open'));if(!isOpen)item.classList.add('open');el.setAttribute('aria-expanded',!isOpen);}}
document.querySelectorAll('a[href="tel:+16197596533"]').forEach(el=>{{el.addEventListener('click',function(){{if(typeof gtag!=='undefined')gtag('event','phone_call',{{'event_category':'CTA','event_label':'{city} {state_abbr}'}});}});}});
const LEGAL_CONTENT={{privacy:{{title:"Privacy Policy",html:`<h4>Overview</h4><p>Pro Dumpster Rental operates this website to connect commercial and construction clients in {city}, {state_abbr} {zip_code} with dumpster rental services.</p><h4>Information We Collect</h4><p>We collect information you voluntarily provide when you contact us at (619) 759-6533. This may include your name, company name, phone number, and project details.</p><h4>How We Use Your Information</h4><p>Information is used exclusively to respond to your inquiry and coordinate services. We do not sell or share your personal information.</p><h4>Cookies</h4><p>This site may use basic analytics cookies. You may disable cookies in your browser settings.</p><h4>Children's Privacy</h4><p>This website is for commercial and construction businesses only.</p><h4>Contact</h4><p>Questions? Call (619) 759-6533, Mon–Fri 8AM–8PM EST.</p>`}},terms:{{title:"Terms of Service",html:`<h4>Acceptance</h4><p>By using this website you agree to these Terms. If you disagree, discontinue use immediately.</p><h4>Service Description</h4><p>This site connects commercial and construction clients in {city}, {state_abbr} {zip_code} with roll-off dumpster rental services. Call (619) 759-6533 Mon–Fri 8AM–8PM EST.</p><h4>Eligibility</h4><p>Services are for commercial and construction businesses only. Homeowner requests are not accepted.</p><h4>Limitation of Liability</h4><p>Pro Dumpster Rental shall not be liable for indirect or consequential damages from use of this site.</p><h4>Independent Operators</h4><p>Operators are solely responsible for their own licensing and insurance. Verify permits required in {city}, {state_abbr}.</p><h4>Governing Law</h4><p>These Terms are governed by the laws of {state_abbr}. Disputes resolved in courts serving {city}, {state_abbr} {zip_code}.</p><h4>Contact</h4><p>Questions? Call (619) 759-6533, Mon–Fri 8AM–8PM EST.</p>`}}}};
function openModal(type){{const data=LEGAL_CONTENT[type];if(!data)return;document.getElementById('modalTitle').textContent=data.title;document.getElementById('modalBody').innerHTML=data.html;const overlay=document.getElementById('legalModal');overlay.classList.add('open');document.body.style.overflow='hidden';overlay.querySelector('.legal-modal-close').focus();}}
function closeModal(){{document.getElementById('legalModal').classList.remove('open');document.body.style.overflow='';}}
document.getElementById('legalModal').addEventListener('click',function(e){{if(e.target===this)closeModal();}});
document.addEventListener('keydown',function(e){{if(e.key==='Escape')closeModal();}});
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
        generated = session.get('generated_pages', [])
        if filename not in generated:
            generated.append(filename)
            session['generated_pages'] = generated
        return jsonify({'success': True, 'filename': filename, 'cached': True, 'blogspot_url': blogspot_url, 'message': 'Page already exists'})
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
    return jsonify({'success': True, 'filename': filename, 'cached': False, 'blogspot_url': blogspot_url,
                    'meta_title': content['meta_title'], 'primary_keyword': content['primary_keyword'],
                    'long_tail_keywords': content['long_tail_keywords'][:6],
                    'ai_provider': content.get('ai_provider','fallback'),
                    'message': f'Page generated for {city}, {state_abbr}'})

@app.route('/preview/<filename>')
def preview_page(filename):
    safe_name = os.path.basename(filename)
    fpath = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(fpath):
        return "Page not found", 404
    return send_from_directory(OUTPUT_DIR, safe_name)

@app.route('/download/<filename>')
def download_page(filename):
    safe_name = os.path.basename(filename)
    fpath = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(fpath):
        return "File not found", 404
    return send_from_directory(OUTPUT_DIR, safe_name, as_attachment=True)

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

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT filename FROM generated_pages')
        files = c.fetchall()
        c.execute('DELETE FROM generated_pages')
        conn.commit(); conn.close()
        deleted_files = 0
        for (fname,) in files:
            fpath = os.path.join(OUTPUT_DIR, fname)
            if os.path.exists(fpath):
                os.remove(fpath)
                deleted_files += 1
        session.pop('generated_pages', None)
        return jsonify({'success': True, 'message': f'History cleared. {len(files)} records and {deleted_files} files deleted.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete-page/<filename>', methods=['POST'])
def delete_page(filename):
    try:
        safe_name = os.path.basename(filename)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT filename FROM generated_pages WHERE filename=?', (safe_name,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Page not found in database'}), 404
        c.execute('DELETE FROM generated_pages WHERE filename=?', (safe_name,))
        conn.commit(); conn.close()
        fpath = os.path.join(OUTPUT_DIR, safe_name)
        if os.path.exists(fpath):
            os.remove(fpath)
        generated = session.get('generated_pages', [])
        if safe_name in generated:
            generated.remove(safe_name)
            session['generated_pages'] = generated
        return jsonify({'success': True, 'message': f'{safe_name} deleted successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/preview-raw/<filename>')
def preview_raw(filename):
    safe_name = os.path.basename(filename)
    fpath = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(fpath):
        return "File not found", 404
    with open(fpath, 'r', encoding='utf-8') as f:
        raw_html = f.read()
    escaped = raw_html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>RAW SOURCE — {safe_name}</title>
<style>
  body {{ background: #0d0d0d; color: #c8f5c8; font-family: 'Courier New', monospace; font-size: 13px; padding: 20px; margin: 0; }}
  .toolbar {{ position: sticky; top: 0; background: #1a1a1a; border-bottom: 1px solid #333; padding: 12px 16px; display: flex; align-items: center; gap: 12px; margin-bottom: 20px; z-index: 100; }}
  .toolbar span {{ color: #ff6b2b; font-weight: bold; font-size: 14px; }}
  .toolbar a {{ background: #ff6b2b; color: white; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; }}
  .toolbar a:hover {{ background: #c44207; }}
  pre {{ white-space: pre-wrap; word-break: break-all; line-height: 1.6; margin: 0; }}
  .line-num {{ color: #555; user-select: none; display: inline-block; min-width: 40px; text-align: right; margin-right: 12px; }}
</style>
</head>
<body>
<div class="toolbar">
  <span>📄 RAW SOURCE: {safe_name}</span>
  <a href="/download/{safe_name}" download="{safe_name}">⬇ Download HTML</a>
  <a href="/preview/{safe_name}" target="_blank">👁 Live Preview</a>
</div>
<pre>"""
    for i, line in enumerate(escaped.splitlines(), 1):
        page += f'<span class="line-num">{i}</span>{line}\n'
    page += "</pre></body></html>"
    return page

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
