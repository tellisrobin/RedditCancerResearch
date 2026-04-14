import praw
import csv
import time
import os
from collections import defaultdict

# Subreddit list
subreddits = [
    "ChronicPain", 
    "backpain", 
    "back_pain",
    "pain",
    "lowerbackpain",
    "ChronicAustralianPain",
    "ChronicPainSpouses",
    "kneepain",
    "PelvicPain",
    "TendonPain",
    "UntreatedPain",
    "StomachPain",
    "migraine",
    "Chronicillness",
    "chronicpainrelief",
    "ChronicHeadache",
    "ChronicPain234",
    "chronicpelvicpain",
    "chronicfatigue",
    "ChronicPancreatitis",
    "Sinusitis",
    "PiriformisChronicPain",
    "TrueChronicIllness",
    "ChronicTeens",
    "Fibromyalgia",
    "ibs",
    "ibs_data",
    "IBSHelp",
    "Endo",
    "endometriosis",
    "endometriosis_corner",
    "endometriosis_stage4",
    "vulvodynia",
    "cfs",
    "Interstitialcystitis",
    "Arthritis",
    "HeadachesandMigraines"
]

# Directory to store CSV and ID files
output_directory = "Final_Data_Collection2"

# Create the directory if it doesn't exist
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# Initialize Reddit API client
reddit = praw.Reddit(
    client_id='te0wH-xpM88HVvIABR5P0g', 
    client_secret='K42r4W_dLEOmz4uuUFSoh3FdBTRfvg', 
    user_agent='Scraper'
)

# Function to process each subreddit
def process_subreddit(subreddit_name):
    id_file = os.path.join(output_directory, f"{subreddit_name}_ids.txt")
    output_file = os.path.join(output_directory, f"{subreddit_name}.csv")

    try:
        with open(id_file, 'r') as f:
            pulled_ids = set(f.read().splitlines())
    except FileNotFoundError:
        pulled_ids = set()

    subreddit = reddit.subreddit(subreddit_name)

    # Initialize flair count dictionary
    flair_counts = defaultdict(int)

    # Open CSV file for appending new data
    file_empty = not os.path.exists(output_file) or os.path.getsize(output_file) == 0

    with open(output_file, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        if file_empty:
            writer.writerow([
                "Entry Type",  # New column to identify post or comment
                "Post ID", 
                "Title", 
                "Author", 
                "Score", 
                "Content", 
                "Number of Comments", 
                "Link Flair"
            ])

        count_duplicates = 0
        count_posts = 0

        # Fetch posts
        for post in subreddit.new(limit=None):  
            if post.id not in pulled_ids:
                writer.writerow([
                    "Post",           # Entry Type
                    post.id, 
                    post.title, 
                    post.author, 
                    post.score, 
                    post.selftext if post.is_self else post.url,  
                    post.num_comments, 
                    post.link_flair_text
                ])

                # Fetch comments for the post
                post.comments.replace_more(limit=None)
                for comment in post.comments.list():
                    writer.writerow([
                        "Comment",       
                        post.id,      
                        post.title,
                        comment.author,  
                        comment.score,   
                        comment.body,    
                        post.num_comments,
                        post.link_flair_text
                    ])
                    
                flair_counts[post.link_flair_text] += 1

                pulled_ids.add(post.id)
                with open(id_file, 'a') as id_f:
                    id_f.write(post.id + '\n')

                count_posts += 1
                time.sleep(0.5)  # Delay between requests
                print(f"Pulled post from {subreddit_name}: {post.title}")
            else:
                count_duplicates += 1
                print(f"Already pulled post from {subreddit_name}: {post.id}")

    print(f"Total new posts for {subreddit_name}: {count_posts}")
    print(f"Duplicate posts skipped for {subreddit_name}: {count_duplicates}")
    print(f"\nPost counts per flair for {subreddit_name}:")
    for flair, count in flair_counts.items():
        print(f"{flair}: {count}")

# Process each subreddit
for subreddit_name in subreddits:
    process_subreddit(subreddit_name)
