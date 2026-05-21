# Site Optimization Tasks
## schoolofcriticalthinking.org

What needs to be added or changed on the site to support the marketing strategy. Curriculum page content changes are covered separately in `curriculum_page_optimization.md` and are excluded here. Implementation method is left to the developer.

---

## 1. Email Capture & Sequence

**Connect the sample lesson download form to an email service provider (ESP)**
Currently the form collects email addresses but does nothing with them automatically. Connect it to an ESP (ConvertKit recommended) so that every person who downloads the sample lesson is automatically enrolled in a pre-written email sequence. The sequence delivers the lesson and sends follow-up emails over 3 weeks, building toward a book purchase. This is the highest-ROI marketing change on the list.

**Add a persistent email capture strip to every page**
The sample lesson CTA only appears on the curriculum page and homepage. Add a slim, unobtrusive email capture strip to the footer of every page — same offer, same form, same sequence. Anyone who arrives via an article or the About page currently has no way to enter the funnel.

**Create a thank-you page after form submission**
After a visitor submits their email, redirect them to a dedicated `/thank-you/` page. The page should confirm the lesson is on its way, set expectations (check your inbox), and offer three suggested next steps: read an article, explore the curriculum, learn about the book.

---

## 2. SEO Foundations

**Add unique meta titles and meta descriptions to every page**
Each page needs its own specific title tag and meta description written for the search query that page is meant to capture. This is the single highest-ROI SEO change — it costs nothing and increases click-through rate from Google immediately.

Suggested descriptions:
- **Home:** A structured critical thinking curriculum for homeschool families. Teaching children how the world actually works. Ages 8–16.
- **Seeing Patterns:** A 52-lesson critical thinking curriculum for ages 8–11. Secular, parent-led, no specialist background needed.
- **Curriculum:** Nine modules across three levels, ages 8–16. Patterns, causality, uncertainty, models, decisions.
- **About:** Founded by a philosopher and parent. The School fills the gap schools don't: teaching children how reality actually works.
- **Articles:** Writing on thinking, learning, and how the mind makes sense of the world. Practical guidance for parents.
- **Books:** Books from the School of Critical Thinking — curriculum companions, illustrated stories, and advanced study.

**Add Open Graph tags to every page**
When pages are shared on Facebook, Pinterest, or Reddit, Open Graph tags control what image, title, and description appear in the preview card. Without them, shared links look broken or generic. Each page needs `og:title`, `og:description`, `og:image`, and `og:url` tags. Articles should use their cover image as the OG image. Create a default OG image (1200×630px, book cover or logo on white background) for pages without a specific image.

**Submit the sitemap to Google Search Console**
The sitemap already exists. Set up Google Search Console if not already done, verify ownership of the domain, and submit the sitemap URL. Search Console shows exactly which queries bring visitors to the site and is essential for tracking whether SEO articles are working.

**Add Book structured data to the Seeing Patterns page**
Structured data (JSON-LD schema) on the Seeing Patterns page tells Google it's a book page, enabling enhanced search result displays. Include: book title, author, ISBN, publisher, age range, and a link to the Amazon purchase page.

**Add FAQ structured data to the Seeing Patterns page**
Alongside the FAQ section (see section 4 below), add FAQ schema markup. This can generate expanded FAQ answers directly in Google search results, increasing visibility for high-intent queries.

---

## 3. Article Infrastructure

**Add a "related articles" section at the bottom of each article**
A reader who finishes an article is the warmest possible audience. Nothing currently guides them to another article or to the curriculum. Add 2–3 related article links at the bottom of each article page.

**Add an email capture CTA at the end of every article**
Below the related articles, add a short CTA offering the free sample lesson — one sentence and an email field. A reader who reaches the end of an article is highly engaged and is exactly the right person to enter the funnel.

**Add an author bio block at the bottom of each article**
Your credibility — philosopher, parent, ten years of university teaching — is a key purchase driver. Readers who find an article via Google may never visit the About page. A short bio (photo, name, 2–3 sentences, link to About) at the bottom of every article closes that gap.

---

## 4. Seeing Patterns Page — Conversion

**Add a testimonials section**
Prepare a "What families say" section between the "How it works" block and the book/buy block. It can be empty or placeholder initially — fill it with genuine quotes from pilot families as feedback arrives. Even two or three quotes significantly increase conversion on a purchase page.

**Add a FAQ section**
A collapsible FAQ section answering the questions parents ask before buying:
1. Is this curriculum religious?
2. Does this replace our existing curriculum?
3. How much preparation does each lesson require?
4. Can my child work through this independently?
5. What age range is this designed for?
6. What format is the book available in?
7. Is there a way to try it before buying?

---

## 5. Social Sharing

**Add social sharing buttons to articles**
A Pinterest "Save" button on each article cover image and Twitter/Facebook share links at the bottom of each article. Pinterest is a major discovery channel for homeschool curriculum — a pin from one reader can drive traffic for years.

---

## 6. Analytics

**Verify Google Analytics is installed and tracking key conversions**
Confirm GA4 is installed and firing on all pages. Set up conversion events for: sample lesson form submissions, and Amazon buy button clicks. Without this, there is no way to know which marketing activities are driving traffic and purchases.

---

## Priority Order

1. Google Search Console setup + sitemap submission
2. Meta titles and descriptions
3. Open Graph tags
4. Connect email form to ESP / email sequence
5. Footer email capture strip
6. Thank-you page
7. Article email CTA
8. Related articles section
9. Author bio on articles
10. FAQ section on Seeing Patterns page
11. Testimonials slot
12. Book structured data
13. FAQ structured data
14. Social sharing buttons
15. Analytics conversion events
