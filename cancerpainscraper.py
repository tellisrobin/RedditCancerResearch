import praw
import csv
import time
import os
import re
from collections import defaultdict

# ─────────────────────────────────────────────
# CANCER SUBREDDIT LIST
# ─────────────────────────────────────────────
subreddits = [
    # General cancer
    "cancer",
    "CancerFamilySupport",
    "cancersurvivors",
    "youngandhealthyish",
    "CancerCaregivers",
    "oncology",

    # # Breast & gynecologic
    "breastcancer",
    "BRCA",
    "ovariancancer",
    "cervicalcancer",
    "uterinecancer",
    "endometrialcancer",
    "triplenegative",

    # # GI cancers
    "colonoscopy",
    "colorectalcancer",
    "pancreaticcancer",
    "stomachcancer",
    "livercancer",
    "esophagealcancer",
    "cholangiocarcinoma",
    "coloncancer",

    # # Lung & thoracic
    "lungcancer",
    "mesothelioma",

    # # Blood cancers
    "leukemia",
    "lymphoma",
    "hodgkinslymphoma",
    "multiplemyeloma",
    "myeloma",
    "mds",                  # myelodysplastic syndromes
    "CML",                  # chronic myeloid leukemia
    "ALL",                  # acute lymphoblastic leukemia

    # # Brain & CNS
    "braintumor",
    "glioblastoma",
    "glioma",
    "Meningioma",

    # # Head & neck / skin
    "thyroidcancer",
    "headandneckcancer",
    "melanoma",
    "skincancer",

    # # Urologic & prostate
    "prostatecancer",
    "bladdercancer",
    "kidneycancer",
    "testicularcancer",

    # # Bone & soft tissue
    "sarcoma",

    # # Other / rarer
    "neuroendocrinetumors",
    "carcinoid",
    # "adrenalcancer",
    "appendixcancer",
    "peritonealcancer",
    "smallcelllungcancer",

    # # Palliative / pain-focused
    "palliativecare",
    "cancerpain",
    "opiates",              # many cancer pain patients discuss here
    "ChronicPain",          # overlaps heavily with cancer pain
    
    # #other Cancer related 
    "CancerCoven",
    "Fuckcancer",
    "AskDocs",
    "doihavebreastcancer",
    "braincancer",
    "ISurvivedCancer",
    "medical",
    "TNBCstage4"

]

# ─────────────────────────────────────────────
# MEDICATION KEYWORD LISTS
# ─────────────────────────────────────────────

OPIOIDS = [
    "morphine", "oxycodone", "oxycontin", "hydrocodone", "vicodin",
    "fentanyl", "dilaudid", "hydromorphone", "methadone", "tramadol",
    "codeine", "buprenorphine", "suboxone", "percocet", "norco",
    "opioid", "opiate", "narcotic", "pain patch", "pain pump",
    "palliative", "ms contin", "opana", "oxymorphone"
]

NSAIDS_ADJUVANTS = [
    "ibuprofen", "naproxen", "aspirin", "celecoxib", "meloxicam",
    "gabapentin", "neurontin", "pregabalin", "lyrica", "amitriptyline",
    "duloxetine", "cymbalta", "ketamine", "lidocaine", "dexamethasone",
    "prednisone", "steroid", "corticosteroid"
]

CHEMO_DRUGS = [
    "chemotherapy", "chemo", "cisplatin", "carboplatin", "oxaliplatin",
    "paclitaxel", "taxol", "docetaxel", "taxotere", "doxorubicin",
    "adriamycin", "cyclophosphamide", "cytoxan", "vincristine",
    "gemcitabine", "fluorouracil", "5-fu", "capecitabine", "xeloda",
    "irinotecan", "etoposide", "methotrexate", "pemetrexed",
    "immunotherapy", "pembrolizumab", "keytruda", "nivolumab", "opdivo",
    "checkpoint inhibitor", "targeted therapy", "radiation", "radiotherapy"
]

TRANSITIONS = [
    "switched to", "changed to", "started", "stopped", "increased dose",
    "dose increase", "dose escalation", "tolerance", "dependence",
    "addiction", "withdrawal", "taper", "wean", "rotating", "rotation",
    "no longer working", "stopped working", "breakthrough pain",
    "rescue dose", "palliative", "hospice", "end of life"
]

ALL_MED_KEYWORDS = OPIOIDS + NSAIDS_ADJUVANTS + CHEMO_DRUGS + TRANSITIONS

# ─────────────────────────────────────────────
# SORT METHODS
# Each method pulls a different ~1000 posts,
# giving up to ~4000 unique posts per subreddit.
# Duplicate post IDs are skipped automatically.
# ─────────────────────────────────────────────
SORT_METHODS = [
    ("new",           lambda sr: sr.new(limit=1000)),
    ("top_alltime",   lambda sr: sr.top(time_filter="all", limit=1000)),
    ("hot",           lambda sr: sr.hot(limit=1000)),
    ("controversial", lambda sr: sr.controversial(limit=1000)),
]


def flag_medications(text):
    """
    Scans text for medication keywords.
    Returns a dict with category flags and matched terms.
    """
    if not text:
        return {
            "has_opioid": False,
            "has_nsaid_adjuvant": False,
            "has_chemo": False,
            "has_transition_language": False,
            "matched_terms": ""
        }

    text_lower = text.lower()
    matched = []

    has_opioid = any(kw in text_lower for kw in OPIOIDS)
    has_nsaid = any(kw in text_lower for kw in NSAIDS_ADJUVANTS)
    has_chemo = any(kw in text_lower for kw in CHEMO_DRUGS)
    has_transition = any(kw in text_lower for kw in TRANSITIONS)

    for kw in ALL_MED_KEYWORDS:
        if kw in text_lower:
            matched.append(kw)

    return {
        "has_opioid": has_opioid,
        "has_nsaid_adjuvant": has_nsaid,
        "has_chemo": has_chemo,
        "has_transition_language": has_transition,
        "matched_terms": "; ".join(set(matched))
    }


# ─────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────

output_directory = "Cancer_Pain_Data"

if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# Reusing credentials from original script
reddit = praw.Reddit(
    client_id='te0wH-xpM88HVvIABR5P0g',
    client_secret='K42r4W_dLEOmz4uuUFSoh3FdBTRfvg',
    user_agent='Scraper'
)

# ─────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────

def process_subreddit(subreddit_name):
    id_file = os.path.join(output_directory, f"{subreddit_name}_ids.txt")
    output_file = os.path.join(output_directory, f"{subreddit_name}.csv")

    # Load already-pulled IDs
    try:
        with open(id_file, 'r') as f:
            pulled_ids = set(f.read().splitlines())
    except FileNotFoundError:
        pulled_ids = set()

    try:
        subreddit = reddit.subreddit(subreddit_name)
        # Force a fetch to check if subreddit exists
        _ = subreddit.id
    except Exception as e:
        print(f"[SKIP] r/{subreddit_name} not accessible: {e}")
        return

    flair_counts = defaultdict(int)
    file_empty = not os.path.exists(output_file) or os.path.getsize(output_file) == 0

    with open(output_file, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        if file_empty:
            writer.writerow([
                "Entry Type",       # Post or Comment
                "Post ID",
                "Title",
                "Author",
                "Score",
                "Content",
                "Number of Comments",
                "Link Flair",
                # Medication flags
                "Has Opioid Mention",
                "Has NSAID/Adjuvant Mention",
                "Has Chemo/Treatment Mention",
                "Has Transition Language",
                "Matched Med Terms"
            ])

        total_new = 0
        total_dupes = 0

        # ── Loop over each sort method ──────────────────
        for sort_name, fetch_fn in SORT_METHODS:
            count_new = 0
            count_dupes = 0
            print(f"  → Fetching [{sort_name}] ...")
 
            try:
                posts = fetch_fn(subreddit)
            except Exception as e:
                print(f"  [ERROR] Could not fetch [{sort_name}] for r/{subreddit_name}: {e}")
                continue
 
            for post in posts:
                if post.id in pulled_ids:
                    count_dupes += 1
                    continue
 
                post_text = post.selftext if post.is_self else post.url
                post_meds = flag_medications(post.title + " " + post_text)
 
                writer.writerow([
                    "Post",
                    post.id,
                    post.title,
                    str(post.author),
                    post.score,
                    post_text,
                    post.num_comments,
                    post.link_flair_text,
                    sort_name,
                    post_meds["has_opioid"],
                    post_meds["has_nsaid_adjuvant"],
                    post_meds["has_chemo"],
                    post_meds["has_transition_language"],
                    post_meds["matched_terms"]
                ])
 
                # Fetch all comments for this post
                try:
                    post.comments.replace_more(limit=None)
                    for comment in post.comments.list():
                        comment_meds = flag_medications(comment.body)
                        writer.writerow([
                            "Comment",
                            post.id,
                            post.title,
                            str(comment.author),
                            comment.score,
                            comment.body,
                            post.num_comments,
                            post.link_flair_text,
                            sort_name,
                            comment_meds["has_opioid"],
                            comment_meds["has_nsaid_adjuvant"],
                            comment_meds["has_chemo"],
                            comment_meds["has_transition_language"],
                            comment_meds["matched_terms"]
                        ])
                except Exception as e:
                    print(f"  [COMMENT ERROR] {post.id}: {e}")
 
                flair_counts[post.link_flair_text] += 1
                pulled_ids.add(post.id)
 
                # Save ID immediately — safe to restart at any point
                with open(id_file, 'a') as id_f:
                    id_f.write(post.id + '\n')
 
                count_new += 1
                time.sleep(0.5)
                print(f"    [OK] {post.title[:75]}")
 
            print(f"  [{sort_name}] done — {count_new} new, {count_dupes} already seen")
            total_new += count_new
            total_dupes += count_dupes
 
    print(f"\n── r/{subreddit_name} complete: {total_new} new posts total, {total_dupes} skipped ──")
    print("  Flair breakdown:")
    for flair, count in flair_counts.items():
        print(f"    {flair}: {count}")
 
 
# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
 
print(f"Starting cancer pain scraper — {len(subreddits)} subreddits x {len(SORT_METHODS)} sort methods\n")
for subreddit_name in subreddits:
    print(f"\n>>> Processing r/{subreddit_name}")
    process_subreddit(subreddit_name)
 
print("\n✓ All done. Data saved to:", output_directory)