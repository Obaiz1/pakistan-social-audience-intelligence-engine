"""Controlled vocabularies shared by the data model, pipelines, API and tests."""

PROJECT_TITLE = "Project 3: Pakistan Social Audience & Campaign Intelligence Engine (Clustering Based)"
PRODUCT_NAME = "Pakistan Audience & Campaign Intelligence"
SHORT_NAME = "AudienceIQ PK"

SYNTHETIC_DISCLAIMER = "SYNTHETIC DEMO — NOT REAL SOCIAL MEDIA OBSERVATIONS"
OBSERVED_DISCLAIMER = (
    "OBSERVED — public YouTube Data API v3 statistics for Pakistan-related brand channels. "
    "Audience location is not verified; comment text is not redistributed."
)
IMPORTED_DISCLAIMER = "IMPORTED — user-supplied CSV; provenance as attested by the uploader."

DATASET_MODES = ("synthetic", "observed", "imported")
PLATFORMS = ("Instagram", "TikTok", "Facebook", "YouTube", "Other")
CONTENT_TYPES = (
    "reel", "video", "product_photo", "influencer_post", "styling_video", "sale_announcement", "other", "unknown",
)
CONTENT_TYPE_LABELS = {
    "reel": "Reel",
    "video": "Video",
    "product_photo": "Product photo",
    "influencer_post": "Influencer post",
    "styling_video": "Styling video",
    "sale_announcement": "Sale announcement",
    "other": "Other",
    "unknown": "Unknown",
}
LANGUAGES = ("english", "roman_urdu", "urdu", "mixed", "other", "unknown")
LANGUAGE_LABELS = {
    "english": "English",
    "roman_urdu": "Roman Urdu",
    "urdu": "Urdu (script)",
    "mixed": "Mixed / code-switched",
    "other": "Other / emoji-only",
    "unknown": "Unknown",
}

# Audience needs used ONLY by the reference labeller (cluster naming + audit), never as cluster membership.
NEEDS = (
    "price", "discount", "delivery", "availability", "size_fit", "fabric_quality",
    "purchase_inquiry", "order_issue", "compliment", "other",
)
NEED_LABELS = {
    "price": "Price / cost",
    "discount": "Discount & sale",
    "delivery": "Delivery & shipping",
    "availability": "Availability & stock",
    "size_fit": "Size & fit",
    "fabric_quality": "Fabric & quality",
    "purchase_inquiry": "Purchase / inbox inquiry",
    "order_issue": "Order problem / complaint",
    "compliment": "Compliments & praise",
    "other": "Other / unclear",
}
PURCHASE_INTENT = ("strong_intent", "possible_inquiry", "none", "unknown")
SENTIMENTS = ("positive", "neutral", "negative", "unknown")
TEXT_PERMISSIONS = ("full", "illustrative", "withheld")
