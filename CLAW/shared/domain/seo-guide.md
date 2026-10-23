# SEO guide

For pages that must be found through search and through AI answers. Whoever writes or plans them: from § Intent to § Conversion; whoever builds the site: § Technical.

## Intent before keywords

- **One page per question the audience really asks,** in their words, with source and date. A page answering two intents ranks for neither.
- **Where a giant owns the obvious query,** take the same intent with what the giant does not answer: the long question, the comparison, the specific case. An app buried in a store is found on the web through the questions that lead to it.
- **The answer in the first lines,** the depth after. Length follows the question: Google has no preferred word count (Search Central, "Creating helpful content", 2026-10).

## The data loop

SEO done by an agent is a loop on real data, not a checklist run once.

1. **Read Search Console** (Performance, search type Web): queries and pages with impressions, clicks, position. No access → ask the user for an export; never estimate it.
2. **Pick the gap:** many impressions and few clicks → the title and description do not promise what the query wants; a position just past the first page → the page answers half the question.
3. **One change per page,** written down with the date, the query it targets and its numbers before.
4. **Linked from the pages that already have traffic** (§ Links).
5. **Measured after re-indexing,** on the same query, against the numbers written down. What did not move is recorded, not rewritten in a hurry.

A few complete pages beat many thin ones: the cadence is the one the review can keep up with.

## Pages at scale

- **Many pages from one template are legitimate when each answers a different question with its own data:** a product, a place, an integration, with facts specific to it.
- **The same text with a name swapped is scaled content abuse:** "many pages generated for the primary purpose of manipulating search rankings", generative AI included. Near-identical pages built for similar queries are doorways (Search Central, spam policies, 2026-08).
- **AI-written pages are allowed, and checked by hand before publishing,** metadata included: titles, descriptions, structured data, alt text (Search Central, "Using generative AI content", 2026-10). Where readers would expect it, the page says how it was made.

## Links

- **Internal first:** every new page receives links from related pages that already rank, with anchor text that says what it is; no page left without inbound links; nothing more than a few clicks from the home page.
- **Inbound links are earned:** the field's directories and lists people really use, being the source others cite, content written for another site's readers. Bought links, automated link building and low-quality directories are link spam (spam policies).
- **Communities count twice:** they send readers, and some AI engines cite them heavily (§ AI answers).

## Technical

- **Crawlable:** links are `<a href>`; content and links are in the HTML the server sends. Google renders JavaScript, not every crawler does: server-side rendering or pre-rendering serves both (Search Central, "JavaScript SEO basics", 2026-03).
- **One canonical URL per page,** in the original HTML, never changed by script. Missing content returns 404 or `noindex`, in single-page apps too.
- **A unique title and description per page;** `sitemap.xml` with only canonical, indexable URLs; `robots.txt` blocking nothing a page needs to render.
- **Structured data only for the features in Google's search gallery** (Article, Product, Software app, Breadcrumb, Organization, Review snippet, Video, …), matching what the page shows. FAQ and HowTo are not in it (gallery, 2026-10).
- **Speed and stability** as `design-guide.md` § Performance as aesthetics, where installed: they count for ranking and for conversion.
- **Verified, not deduced:** URL Inspection shows what Google actually received; titles, canonicals and status codes are checked on the build output.

## AI answers

- **Google's AI Overviews and AI Mode need no special optimisation:** an indexed page eligible for a snippet is eligible; no AI text file, no special markup; the traffic is counted in Search Console under Web (Search Central, "AI features", 2025-12). Search basics come first.
- **AI answers mostly cite what search already ranks:** AI Overviews link mainly to top-10 organic results, ChatGPT's searches overlap Bing's top results (secondary analyses, 2026).
- **Each engine reads different places:** few domains are cited by both ChatGPT and Perplexity, and Perplexity leans on community threads.
- **What gets quoted:** adding quotations, statistics and cited sources raised a page's share of generated answers by about 30-40%, keyword stuffing lowered it, and lower-ranked pages gained most (Aggarwal et al., "GEO", KDD 2024). The citable sentence stands alone: one fact, its number, its source.
- **Dated and current:** a page shows when it was last updated; a stale number costs more than a missing one.
- **Measured by asking:** the audience's real questions, put to the engines before and after, with who gets cited. A tool's visibility score is an estimate, not this measurement.
- **Controls:** `nosnippet`, `data-nosnippet`, `max-snippet`, `noindex` limit what is shown; `Google-Extended` governs use for training and grounding.

## Conversion

- **The action sits where the reader finishes,** and where the answer is given: one action per page, said with a verb and what is gained.
- **Measured per page:** search visits → the action. A page that ranks and does not convert has a promise mismatch, not a search problem.

## What is not done

- **No page made mainly to rank:** thin variants, doorways, padding to a length.
- **No bought or automated links,** no expired domain bought for its authority.
- **No invented authors, bylines, reviews or facts:** a fabricated creator profile is deception (helpful content).
