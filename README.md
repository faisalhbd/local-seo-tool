# Local SEO Page Generator — Dumpster Rental

## Overview
AI-powered local SEO HTML page generator for commercial dumpster rental businesses.
Generates unique, Lighthouse-optimized landing pages for every US city/town.

## Business Config
- **Offer:** Dumpster Rental (Commercial & Construction ONLY)
- **Phone:** (619) 759-6533
- **Hours:** Mon–Fri 8:00 AM – 8:00 PM EST
- **Coverage:** USA (Except Alaska & Hawaii)
- **Target:** Construction contractors & commercial property managers (NO homeowners)

## Features
- ✅ AI-generated unique content per location (Claude Sonnet)
- ✅ 48 states × 10+ cities = 480+ possible pages
- ✅ 20 long-tail keywords per page
- ✅ Schema.org: LocalBusiness, FAQPage, BreadcrumbList
- ✅ Open Graph + Twitter Card meta tags
- ✅ Canonical URLs + Geo meta tags
- ✅ Responsive design (Mobile-first)
- ✅ Accessibility (ARIA, skip nav, semantic HTML)
- ✅ Auto-updating sitemap.xml
- ✅ SQLite database tracking all pages
- ✅ Lighthouse 100 optimized structure

## Setup

```bash
cd local_seo_tool
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key-here"
python app.py
```

## Usage

1. Open http://localhost:5000
2. Select a State from the dropdown
3. Select a City/Town
4. View auto-generated long-tail keywords preview
5. Click "Generate SEO Page"
6. AI generates unique content, saves HTML to `generated_pages/`
7. Preview the page live
8. Sitemap auto-updates at `/sitemap.xml`

## Generated Page Includes (SEO Checklist)
- `<title>` (60 chars max with primary keyword)
- `<meta name="description">` (155 chars)
- `<meta name="keywords">` (20 long-tail keywords)
- `<meta name="geo.region">` + `<meta name="geo.placename">`
- `<link rel="canonical">`
- Open Graph (og:title, og:description, og:image, og:url)
- Twitter Card tags
- Schema.org LocalBusiness JSON-LD
- Schema.org FAQPage JSON-LD
- Schema.org BreadcrumbList (inline + JSON-LD)
- H1 → H2 → H3 heading hierarchy
- Alt tags on all images/icons
- ARIA roles + labels
- Skip navigation link
- Responsive CSS (clamp, grid, auto-fit)
- 4 FAQ items per page (location-specific)
- CTA section with phone number
- Footer with business hours
- Mobile-first design

## Long-Tail Keyword Formula
For each `City, ST ZIP`:
- `commercial dumpster rental {city} {state}`
- `construction dumpster rental {city} {state} {zip}`
- `roll off dumpster rental {city} {state}`
- `affordable construction waste removal {city} {state}`
- `best dumpster rental company {city} {zip}`
- ... (20 total per page)

## File Structure
```
local_seo_tool/
├── app.py              # Flask app + routes
├── requirements.txt
├── data/
│   ├── locations.py    # 48 states × 10 cities
│   └── pages.db        # SQLite: generated pages log
├── templates/
│   └── index.html      # Dashboard UI
└── generated_pages/    # Output HTML files + sitemap.xml
```
