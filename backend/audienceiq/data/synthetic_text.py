"""Compositional multilingual comment generator for the SYNTHETIC classroom corpus.

Every string produced here is invented (illustrative), never copied from real social-media comments.
Templates are combined with slot fillers, spelling variants, code-switching, emojis and noise so that
the corpus is not a handful of repeated strings; the clustering pipeline must still discover the needs.
"""

import numpy as np

ITEMS_EN = ["this suit", "this dress", "this lawn suit", "this 3 piece", "the blue one", "the printed lawn", "this kurti",
            "the maroon suit", "this unstitched lawn", "the embroidered one", "this outfit", "this article", "the 2 piece",
            "this shirt", "the pastel one", "this collection"]
ITEMS_RU = ["ye suit", "yeh dress", "ye wala", "is suit", "blue wala", "ye 3 piece", "is dress", "ye article",
            "maroon wala", "ye lawn", "yeh outfit", "pink wala", "ye kurta", "ye 2 piece"]
ITEMS_UR = ["یہ سوٹ", "یہ ڈریس", "یہ والا", "اس سوٹ", "یہ لان", "یہ تھری پیس", "نیلا والا"]
CITIES = ["Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Quetta", "Hyderabad",
          "Sialkot", "Gujranwala", "Sukkur", "Abbottabad", "Bahawalpur"]
CITIES_UR = ["کراچی", "لاہور", "اسلام آباد", "ملتان", "پشاور", "فیصل آباد", "راولپنڈی", "کوئٹہ"]
SIZES = ["S", "M", "L", "XL", "XXL", "small", "medium", "large"]
COLORS = ["black", "maroon", "sky blue", "mint green", "peach", "white", "mustard", "pink", "lilac", "olive"]
GREET_EN = ["", "", "", "Hi", "Hello", "Hey", "Dear", "Hi team", "AOA", "Salam"]
GREET_RU = ["", "", "", "AOA", "Assalam o alaikum", "Salam", "Sis", "Appi", "Bhai", "Hello"]
GREET_UR = ["", "", "السلام علیکم", "سلام"]
EMO_POS = ["", "", "❤️", "😍", "🔥", "✨", "💕", "👌", "❤️❤️", "😍😍", "💯"]
EMO_Q = ["", "", "", "🤔", "🙏"]
EMO_NEG = ["", "", "😡", "😠", "😢", "😞", "👎"]
TAGS = ["@sana_k", "@ayesha.r", "@hira_x", "@maham22", "@fatima.s", "@zoya_m", "@iqra.b", "@noor_h"]

T: dict[str, dict[str, list[str]]] = {
    "price": {
        "english": ["Price please{end}", "What is the price of {item}{end}", "How much is {item}{end}", "Price{end}",
                    "Price plz", "Rate of {item}{end}", "Kindly share the price{end}", "How much for {item} in {size}{end}",
                    "Whats the cost{end}", "Price in PKR{end}", "Too expensive for lawn honestly", "Is the price same in stores{end}",
                    "Price of {color} one{end}", "Overpriced, last year it was much cheaper", "Can you tell me the price{end}"],
        "roman_urdu": ["Price kya hai{end}", "{item} ki price kya hai{end}", "Kitne ka hai{end}", "{item} kitne ka hai{end}",
                       "Price bata dein{end}", "Price bohat zyada hai", "Qeemat kya hai{end}", "Rate kya hai iska{end}",
                       "Price batao please", "Itna mehnga kyun hai", "Price kitni hai {color} wale ki{end}", "Kitne ka mil jayega{end}",
                       "Price thori kam karein", "Kitnay ka hai yeh{end}", "Price kia hy{end}"],
        "urdu": ["قیمت کیا ہے؟", "{item_ur} کی قیمت کیا ہے؟", "یہ کتنے کا ہے؟", "قیمت بتا دیں", "بہت مہنگا ہے", "ریٹ کیا ہے؟",
                 "قیمت بتائیں پلیز"],
        "mixed": ["Price kya hai of {item}{end}", "{item} ki price please{end}", "What's the qeemat{end}", "قیمت please{end}",
                  "Price بتائیں please", "How much hai ye{end}"],
    },
    "discount": {
        "english": ["Any discount{end}", "Any discount on {item}{end}", "Is there a sale{end}", "When is the sale{end}",
                    "Discount code please{end}", "Will this be on sale{end}", "Any promo code{end}", "Is {item} included in the sale{end}",
                    "Waiting for 11.11 sale", "Any offer for 12.12{end}", "How much off{end}", "Is the 30% off on unstitched too{end}",
                    "Flat off on this{end}", "Any student discount{end}"],
        "roman_urdu": ["Discount milega{end}", "Sale kab lagegi{end}", "Koi discount hai{end}", "{item} pe discount hai{end}",
                       "Sale mein aayega{end}", "11.11 pe kitna off hai{end}", "Discount code de dein", "Offer kab tak hai{end}",
                       "Sale ka intezar hai", "12.12 sale mein milega{end}", "Kitna off hai{end}", "Koi offer chal raha hai{end}"],
        "urdu": ["کوئی ڈسکاؤنٹ ہے؟", "سیل کب لگے گی؟", "اس پر رعایت ملے گی؟", "آفر کب تک ہے؟", "ڈسکاؤنٹ کوڈ دے دیں"],
        "mixed": ["Discount ملے گا{end}", "Sale کب ہے{end}", "Any discount hai{end}", "11.11 sale mein kitna off{end}",
                  "Koi promo code{end}"],
    },
    "delivery": {
        "english": ["Delivery time to {city}{end}", "Do you deliver to {city}{end}", "How many days for delivery{end}",
                    "Delivery charges{end}", "Is cash on delivery available{end}", "Do you ship abroad{end}",
                    "Will it reach before Eid{end}", "Shipping to UK{end}", "How long does delivery take{end}",
                    "Delivery in {city} how many days{end}", "Free delivery{end}", "Which courier do you use{end}"],
        "roman_urdu": ["Delivery kitne din mein hogi{end}", "{city} mein delivery hai{end}", "Delivery {city} mein{end}",
                       "Eid se pehle mil jayega{end}", "Delivery charges kitne hain{end}", "COD hai{end}",
                       "Kitne din lagenge {city} tak{end}", "Parcel kab tak pohanchega{end}", "Delivery free hai{end}",
                       "{city} tak kitne din{end}", "Bahar mulk delivery hoti hai{end}"],
        "urdu": ["ڈیلیوری کتنے دن میں ہوگی؟", "{city_ur} میں ڈیلیوری ہے؟", "عید سے پہلے پہنچ جائے گا؟", "ڈیلیوری چارجز کتنے ہیں؟",
                 "کیش آن ڈیلیوری ہے؟"],
        "mixed": ["Delivery کتنے دن میں{end}", "{city} delivery kitne days{end}", "Delivery charges kya hain to {city}{end}",
                  "COD available hai{end}", "Eid se pehle delivery possible{end}"],
    },
    "availability": {
        "english": ["Is {item} available{end}", "Is this available in {city}{end}", "Available in {size}{end}",
                    "Is it in stock{end}", "Out of stock already{end}", "When will you restock{end}", "Available online{end}",
                    "Is {color} available{end}", "Sold out?? Please restock", "Which outlet has it{end}",
                    "Is it available in {city} store{end}", "Still available{end}"],
        "roman_urdu": ["Ye available hai{end}", "{city} mein milega{end}", "{item} stock mein hai{end}", "{color} wala milega{end}",
                       "Restock kab hoga{end}", "Outlet pe milega{end}", "Abhi available hai{end}", "{city} branch mein hai{end}",
                       "Sold out ho gaya kya{end}", "Online mil jayega{end}", "Dobara kab aayega{end}"],
        "urdu": ["کیا یہ دستیاب ہے؟", "{city_ur} میں ملے گا؟", "اسٹاک میں ہے؟", "یہ کب دوبارہ آئے گا؟", "آؤٹ لیٹ پر دستیاب ہے؟"],
        "mixed": ["{size} size دستیاب hai{end}", "Available hai {city} mein{end}", "Stock mein hai ya sold out{end}",
                  "{city} outlet par available{end}"],
    },
    "size_fit": {
        "english": ["Do you have {size}{end}", "Size chart please{end}", "Is {size} available{end}", "What size should I get{end}",
                    "Does it run small{end}", "Length of the shirt{end}", "Plus size available{end}", "Fitting is too tight",
                    "Measurements for {size}{end}", "Size guide please{end}", "Is it true to size{end}", "{size} size{end}"],
        "roman_urdu": ["{size} size hai{end}", "Size chart bhej dein{end}", "{size} available hai{end}", "Fitting kaisi hai{end}",
                       "Size chota hai ya bara{end}", "Shirt ki lambai kitni hai{end}", "Mera size {size} hai milega{end}",
                       "Size guide bata dein", "Fitting tight thi pichli dafa", "Plus size bhi banate hain{end}", "{size} mein hai{end}"],
        "urdu": ["{size} سائز ہے؟", "سائز چارٹ بھیج دیں", "فٹنگ کیسی ہے؟", "قمیض کی لمبائی کتنی ہے؟", "میرا سائز {size} ہے"],
        "mixed": ["{size} size دستیاب hai{end}", "Size chart بھیج دیں please", "Fitting kaisi hai of {size}{end}",
                  "Size {size} mil jayega{end}"],
    },
    "fabric_quality": {
        "english": ["What fabric is this{end}", "Is the fabric soft{end}", "Quality is amazing", "Is it pure lawn{end}",
                    "Does the colour fade{end}", "Fabric is too thin", "Is it see through{end}", "Quality of embroidery{end}",
                    "Is it cotton{end}", "The print quality is great", "Material looks cheap", "Is the dupatta chiffon{end}"],
        "roman_urdu": ["Fabric kaisa hai{end}", "Kapra kaisa hai{end}", "Quality achi hai{end}", "Rang to nahi jata{end}",
                       "Kapra patla hai", "Quality pehle jaisi nahi rahi", "Dupatta chiffon hai{end}", "Lawn ki quality kaisi hai{end}",
                       "Kadhai zabardast hai", "Kapra transparent to nahi{end}", "Material soft hai{end}"],
        "urdu": ["کپڑا کیسا ہے؟", "کوالٹی اچھی ہے؟", "رنگ تو نہیں اترتا؟", "کڑھائی بہت اچھی ہے", "لان کی کوالٹی کیسی ہے؟"],
        "mixed": ["Fabric کیسا hai{end}", "Quality achi hai of lawn{end}", "کپڑا soft hai{end}", "Colour fade to nahi hota{end}"],
    },
    "purchase_inquiry": {
        "english": ["Inbox please", "Check your DM", "Details please", "How to order{end}", "I want to order this",
                    "Send details on WhatsApp", "Can I order {item}{end}", "Please DM details", "Website link please{end}",
                    "I want to buy {item}", "Order number please{end}", "Contact number{end}"],
        "roman_urdu": ["Inbox me details send kar dein", "Order kaise karein{end}", "Mujhe {item} lena hai", "Details bhej dein",
                       "Order karna hai", "DM check karein", "Whatsapp number de dein", "Link bhej dein", "Mujhe ye chahiye",
                       "Book kar dein mera", "Inbox check karo please"],
        "urdu": ["ان باکس میں تفصیلات بھیج دیں", "آرڈر کیسے کریں؟", "مجھے یہ لینا ہے", "رابطہ نمبر دیں", "مجھے یہ چاہیے"],
        "mixed": ["Order kaise karein on website{end}", "Inbox میں details bhej dein", "I want this lena hai", "DM کر دیں please"],
    },
    "order_issue": {
        "english": ["Ordered last week, still waiting", "I haven't received my order", "Order not delivered yet",
                    "Wrong size received", "Still waiting for my parcel {emo_neg}", "No response on DM", "Received damaged item",
                    "Refund please, it has been 2 weeks", "Delivery delayed again", "Wrong colour sent", "Worst service, no reply",
                    "Where is my order{end}"],
        "roman_urdu": ["Order kiya tha abhi tak nahi mila", "Parcel abhi tak nahi aaya", "Ghalat size bhej diya",
                       "Reply nahi kar rahe", "2 hafte ho gaye order nahi mila", "Refund kab milega{end}", "Delivery late hai bohat",
                       "Order cancel kar dein", "Kharab piece aaya hai", "Complaint ki thi koi jawab nahi"],
        "urdu": ["آرڈر کیا تھا ابھی تک نہیں ملا", "غلط سائز بھیج دیا", "ریفنڈ کب ملے گا؟", "کوئی جواب نہیں دے رہا", "شکایت کی تھی"],
        "mixed": ["Order kiya tha still waiting", "Abhi tak parcel not received", "آرڈر نہیں ملا please check",
                  "Refund kab milega its been 2 weeks"],
    },
    "compliment": {
        "english": ["Beautiful {emo_pos}", "Very beautiful dress!", "Gorgeous colours", "Love it {emo_pos}", "So elegant",
                    "Stunning collection {emo_pos}", "This is so pretty", "Amazing", "Lovely print", "Classy as always",
                    "Wow {emo_pos}", "Best collection this year", "Obsessed with {item}", "{emo_pos}"],
        "roman_urdu": ["Bohat khubsurat {emo_pos}", "Zabardast collection", "Kamal ka design hai", "Masha Allah bohat pyara",
                       "Bohat pyari dress hai", "Kya baat hai {emo_pos}", "Zabardast {emo_pos}", "Rang bohat pyare hain",
                       "Bohat acha laga", "Ye wala bohat pyara hai"],
        "urdu": ["بہت خوبصورت", "زبردست", "ماشاءاللہ بہت پیارا", "کمال کا ڈیزائن ہے", "بہت پیاری ڈریس ہے"],
        "mixed": ["Beautiful hai {emo_pos}", "Bohat gorgeous", "So pretty yaar", "خوبصورت dress {emo_pos}", "Amazing collection hai"],
    },
    "other": {
        "english": ["Song name{end}", "Who is the model{end}", "First", "Which song is this{end}", "Nice music", "Follow back",
                    "Eid Mubarak 🌙", "Hmm", "Ok", "Happy Friday", "Me {emo_pos}", "Ameen"],
        "roman_urdu": ["Gana konsa hai{end}", "Model kaun hai{end}", "Pehla comment", "Eid Mubarak sab ko", "Jumma Mubarak",
                       "Acha", "Theek hai"],
        "urdu": ["عید مبارک", "گانا کونسا ہے؟", "جمعہ مبارک", "آمین"],
        "mixed": ["Song ka naam{end}", "Eid Mubarak sab ko 🌙", "Model ka naam{end}"],
    },
    "giveaway": {
        "english": ["Done {tag} {tag2}", "Participated! {tag}", "Done ✅ {tag}", "Count me in {tag}", "Done sis {emo_pos} {tag}",
                    "Entered {tag} {tag2}", "Done 🤞 {tag}"],
        "roman_urdu": ["Done kar diya {tag}", "Mai bhi participate {tag}", "Done {tag} {tag2} umeed hai jeet jaon"],
        "urdu": ["ڈن {tag}"],
        "mixed": ["Done kar diya ✅ {tag}"],
    },
}

SECOND_PHRASES = {
    "price": {"english": "Price?", "roman_urdu": "Price kya hai?", "urdu": "قیمت؟", "mixed": "Price?"},
    "delivery": {"english": "Delivery to {city}?", "roman_urdu": "{city} delivery hai?", "urdu": "ڈیلیوری؟", "mixed": "Delivery {city}?"},
    "availability": {"english": "Available?", "roman_urdu": "Available hai?", "urdu": "دستیاب ہے؟", "mixed": "Available hai?"},
    "size_fit": {"english": "{size} size?", "roman_urdu": "{size} size hai?", "urdu": "سائز؟", "mixed": "{size} size?"},
    "compliment": {"english": "Beautiful!", "roman_urdu": "Bohat pyara!", "urdu": "خوبصورت!", "mixed": "So pretty!"},
}

RU_SPELLING = {"hai": ["hai", "hy", "he", "hay"], "kya": ["kya", "kia"], "mein": ["mein", "me", "main", "mai"],
               "nahi": ["nahi", "nai", "nhi"], "bohat": ["bohat", "bht", "bohot", "bahut"], "kitne": ["kitne", "kitnay", "kitny"],
               "please": ["please", "plz", "pls", "plzzz"], "delivery": ["delivery", "delivry", "dilivery"],
               "available": ["available", "availble", "avaliable"], "karein": ["karein", "kren", "kr dein"],
               "dein": ["dein", "dain", "do"]}
ENDS = ["?", "?", "??", " ?", "", " please?", " plz", "?!"]


def _pick(rng: np.random.Generator, seq):
    return seq[int(rng.integers(len(seq)))]


def _fill(rng: np.random.Generator, template: str) -> str:
    tag, tag2 = _pick(rng, TAGS), _pick(rng, TAGS)
    return (template.replace("{item}", _pick(rng, ITEMS_EN if rng.random() < 0.6 else ITEMS_RU))
            .replace("{item_ur}", _pick(rng, ITEMS_UR))
            .replace("{city}", _pick(rng, CITIES)).replace("{city_ur}", _pick(rng, CITIES_UR))
            .replace("{size}", _pick(rng, SIZES)).replace("{color}", _pick(rng, COLORS))
            .replace("{emo_pos}", _pick(rng, EMO_POS)).replace("{emo_neg}", _pick(rng, EMO_NEG))
            .replace("{tag}", tag).replace("{tag2}", tag2 if tag2 != tag else "")
            .replace("{end}", _pick(rng, ENDS)))


def _noise(rng: np.random.Generator, text: str, language: str) -> str:
    if language in {"roman_urdu", "mixed"}:
        words = text.split(" ")
        for i, w in enumerate(words):
            core = w.lower().strip("?!.,")
            if core in RU_SPELLING and rng.random() < 0.45:
                words[i] = w.lower().replace(core, _pick(rng, RU_SPELLING[core]))
        text = " ".join(words)
    r = rng.random()
    if r < 0.40:
        text = text.lower()
    elif r < 0.43:
        text = text.upper()
    if rng.random() < 0.15:
        text = text.rstrip("?!. ")
    if rng.random() < 0.18:
        text = f"{text} {_pick(rng, EMO_Q if '?' in text else EMO_POS)}".strip()
    return " ".join(text.split())


def make_comment(rng: np.random.Generator, need: str, language: str) -> tuple[str, str | None, int]:
    """Returns (text, secondary_need, template_index) for a latent need and language."""
    bank = T[need].get(language) or T[need]["english"]
    idx = int(rng.integers(len(bank)))
    body = _fill(rng, bank[idx])
    secondary = None
    if need not in {"giveaway", "other"} and rng.random() < 0.12:
        options = [n for n in SECOND_PHRASES if n != need]
        secondary = _pick(rng, options)
        phrase = _fill(rng, SECOND_PHRASES[secondary][language if language in SECOND_PHRASES[secondary] else "english"])
        body = f"{phrase} {body}" if secondary == "compliment" else f"{body} {phrase}"
    greet_bank = GREET_UR if language == "urdu" else GREET_RU if language in {"roman_urdu", "mixed"} else GREET_EN
    greet = _pick(rng, greet_bank)
    if greet and need not in {"compliment", "giveaway", "other"} and rng.random() < 0.5:
        body = f"{greet} {body}" if language != "urdu" else f"{greet}، {body}"
    return _noise(rng, body, language), secondary, idx
