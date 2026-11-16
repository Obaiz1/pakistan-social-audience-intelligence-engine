# Project 3 — requirement checklist (transcribed from the assignment)

**Source:** `Project 3 (1).docx` (four pages), supplied by the course instructor and read directly on 2026-11-15. The original document is **not** committed to this repository; this file is a requirement-by-requirement transcription so each sentence can be traced to an implementation (`docs/TRACEABILITY_MATRIX.md`).

**Official title:** *Project 3: Pakistan Social Audience & Campaign Intelligence Engine (Clustering Based)*

## Business problem (verbatim intent)

A Lahore-based online brand (clothing, perfume, etc.) runs Instagram, TikTok and Facebook campaigns (e.g. its 11.11 or 12.12 collection) and receives thousands of comments such as "Price please?", "Is this available in Karachi?", "Very beautiful dress!", "Price bohat zyada hai.", "Delivery kitne din mein hogi?", "Any discount on this suit?", "Ordered last week, still waiting.", "Inbox me details send kar dein." It has engagement data, comments, campaign metrics and product information but does not know which customer needs or content patterns are hidden in them.

| ID | Requirement (from the document) |
|---|---|
| R-TASK-1 | Build an engine that **groups similar audience behaviours**. |
| R-TASK-2 | **Identifies unusual patterns**. |
| R-TASK-3 | **Converts those discoveries into practical marketing decisions**. |
| R-TASK-4 | The goal is **not merely positive/negative classification**; the project concentrates on discovering audience segments and campaign opportunities (Project 1 covers content analysis). |
| R-APP | Build **a small web application that answers five marketing questions**. |
| R-Q1 | **Which content attracts attention?** Compare reels, product photos, influencer posts, styling videos, sale announcements and Eid campaigns using likes, comments, shares and views **where publicly available**. |
| R-Q2 | **What does the audience want?** Group comments around price, fabric quality, sizing, delivery, discounts, availability and purchase interest. |
| R-Q3 | **Which marketing patterns are unusual?** Identify posts whose engagement or comment patterns differ substantially from **comparable posts**, for further investigation. |
| R-Q4 | **Which audience needs should the brand address?** Discover groups such as discount-focused commenters, delivery-concerned shoppers and customers asking about product availability. |
| R-Q5 | **What should the marketing team do next?** Generate **evidence-based recommendations** for content, promotions, customer service and campaign testing. |
| R-DATA-1 | Start with **a single product category**, such as women's lawn suits. |
| R-DATA-2 | Collect or prepare **approximately 2,000–5,000 public post records and associated comments** for a class demonstration (may extend if suitable access exists). |
| R-DATA-3 | Public posts from Sapphire, Khaadi, Gul Ahmed are a useful starting point; **use permitted access methods and follow each platform's terms; do not assume all comments or analytics are publicly downloadable.** |
| R-DATA-A | Table A (posts): `post_id, brand, platform, campaign, content_type, product_category, likes, comments_count, shares (if available), views (if available), days_since_post`. |
| R-DATA-B | Table B (comments): `post_id, comment_text, language_type (English / Roman Urdu / Urdu), topic, sentiment, purchase_intent`. |
| R-DATA-4 | The table examples are **illustrative, not actual measurements** from those brands. |
| R-DATA-5 | For a research-oriented version, **keep the source URL, collection date, data provenance and applicable reuse permissions**. |
| R-DATA-6 | **Separate actual observations from generated or simulated records.** |
| R-SRC-1 | 2026 paper (10,602 observations, 17 brands, 7 platforms): **check the paper and its materials for actual dataset and code availability before planning to reuse it**. |
| R-SRC-2 | Pakistan's largest e-commerce dataset: transaction data, **not a social-media comments dataset**; check reuse permissions before distributing. |
| R-SRC-3 | Pakistani Fashion Catalogue (75 products, 5 retailers, PKR prices): product context only, **not a substitute for real audience-engagement data**. |

## Findings recorded for the data-source requirements (checked 2026-11-15)

| ID | What was checked | Result |
|---|---|---|
| R-SRC-1 | Article page `thesesjournal.com/index.php/1/article/view/3247` (Horrara et al., *Spectrum of Engineering Sciences* 4(6), 2026) | No dataset or code link (no GitHub/Kaggle/Zenodo/"on request"). Site content licence CC BY-NC-ND 4.0 covers the article, not data. **Not reused.** |
| R-SRC-2 | `opendata.com.pk/dataset/pakistan-largest-ecommerce-dataset` | Order/transaction records (2016–2018); no licence field shown. **Not used as comments; not redistributed.** |
| R-SRC-3 | `huggingface.co/datasets/Osama-Ansar/pakistani-fashion-catalogue` | 75 rows, licence "other" (users must check source-site terms), retailers Breakout/Charcoal/Cougar/Engine/Outfitters (casual/menswear, not lawn). **Not used** (licence unclear, category mismatch). |
