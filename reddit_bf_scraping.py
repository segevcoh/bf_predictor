import argparse
import datetime
import os
import re
import shutil
import statistics

import numpy as np
import pandas as pd
import praw
from matplotlib import pyplot as plt

from image_parsing_utils import get_photos_from_post

CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
USER_AGENT = os.environ['USER_AGENT']
SCRAPED_DATA_CSV_PATH = 'raw_comments_bf.csv'
SUBREDDIT = "guessmybf"

HIGH_BF_TH = 60
LOW_BF_TH = 4
LOW_COMMENT_SCORE_TH = -1

BF_BIN_SIZE = 3.9
NUMBER_OF_BINS_FOR_HIST = 15


def scrape_from_reddit(time_frame, photos_output_dir):
    """ Scrapes the top posts of param: times_frame, downloads photos of users into PHOTOS_PATH and saves all comment
        information into a csv file  - INITIAL_RAW_DATA_CSV."""
    reddit = praw.Reddit(client_id=CLIENT_ID,
                         client_secret=CLIENT_SECRET,
                         user_agent=USER_AGENT,
                         check_for_async=False)

    subreddit = reddit.subreddit(SUBREDDIT)

    print("Display Name:", subreddit.display_name)
    print("Title:", subreddit.title)
    print("Description:", subreddit.description)

    # Scraping the top posts
    posts = subreddit.top(time_frame, limit=None)
    output_df = pd.DataFrame(columns=["title",
                                      "post_text",
                                      "id",
                                      "score",
                                      "comment_id",
                                      "comment_body",
                                      "comment_score",
                                      "comment_author_id",
                                      "comment_author_karma",
                                      "post_url",
                                      "permalink",
                                      "post_date",
                                      "image_paths"])
    i = 0
    for post in posts:
        if post.num_comments == 0:  # The post has no comments
            continue

        status, paths = get_photos_from_post(post, photos_output_dir)  # download all photos in the post to a given folder
        if not status:  # something went wrong and the photos in the post were not downloaded
            continue
        for j, comment in enumerate(post.comments):
            try:  # the following 2 attributes were added not too long ago (some posts do not contain them)
                comment_karma = comment.author.comment_karma
                comment_author_id = comment.author.id,
            except AttributeError:
                comment_karma = None
                comment_author_id = None

            output_df.loc[i] = [post.title,
                                post.selftext,
                                post.id,
                                post.score,
                                j,
                                comment.body,
                                comment.score,
                                comment_author_id,
                                comment_karma,
                                post.url,
                                post.permalink,
                                str(datetime.datetime.fromtimestamp(post.created)),
                                paths]
            i += 1
            output_df.to_csv(SCRAPED_DATA_CSV_PATH)


def filter_comments_with_low_score(csv_file):
    """ Deletes odd data values e.g. comments with to low of scores, can be extended later. """
    df = pd.read_csv(csv_file)
    df.drop(df[df['comment_score'] < LOW_COMMENT_SCORE_TH].index, inplace=True)
    df.to_csv(csv_file, index=False)


def process_csv_for_image_prediction(csv_file):
    """Adds columns---'comment_bf', 'bf_est' and 'bf_bin' to the given csv_file.
    comment_bf is an estimation extracted from each comment, 'bf_est' is the mean of all comments estimations, and
    'bf_bin' is the value that a given picture falls into, i.e. in the range of 4-7.9%, 8-11% and so on..."""
    df = pd.read_csv(csv_file)

    # adds a column with the bf% estimates of a particular comment
    df["comment_bf"] = df.apply(lambda row: get_comment_bf_est(row.comment_body), axis=1)

    # Group the DataFrame by user ID and calculate the mean of the "bf" column for each group
    grouped = df.groupby("id")["comment_bf"].mean()

    # Add the result as a new column to the original DataFrame
    df["bf_est"] = df["id"].map(grouped)

    # Adds 2 columns meant for classifying in which range of bf% a given user is in (i.e. in a 3-7%, 7-11%, 11-15% and
    # so on)

    # Calculate the lower bound of the range for each "bf" value
    df["range_start"] = np.floor((df["bf_est"] // BF_BIN_SIZE) * BF_BIN_SIZE)

    # Calculate the upper bound of the range for each "bf" value
    df["range_end"] = df["range_start"] + BF_BIN_SIZE

    # Create a string representation of the range for each "bf" value
    df["bf_bin"] = df.apply(lambda row: f"{row['range_start']}-{row['range_end']}", axis=1)
    df.to_csv(csv_file, index=False)


def get_comment_bf_est(comment):
    """ Extract a bf% estimate from a given comment """
    pattern = r'\b\d+\.\d|\b\d\'?\d?\b'
    comment_est = re.findall(pattern, comment)
    # remove numbers with inches (e.g., 5'7) and numbers which are too large or too small (probably not bf)
    comment_est = [float(m) for m in comment_est if "'" not in m and HIGH_BF_TH > float(m) > LOW_BF_TH]
    return statistics.median(comment_est) if comment_est else None


def create_folder_bin(raw_data, photos_path):
    """ Divides all the pictures into folders, based on which bin does the picture falls in. (i.e. in the range of
    4-7.9%, 8-11% and so on)... """
    df = pd.read_csv(raw_data)
    # Group the DataFrame by picture name
    grouped = df.groupby("id")
    # Get the unique folder names
    folder_names = df['bf_bin'].unique()
    # Create the folders if they do not exist
    for folder_name in folder_names:
        os.makedirs(folder_name, exist_ok=True)

    # Iterate over the photos names in the DataFrame
    for photo_name in grouped.groups.keys():
        photo_df = grouped.get_group(photo_name)
        photo_folder_name = photo_df['bf_bin'].iloc[0]

        # Find the corresponding image file in the raw images folder
        for file in os.listdir(photos_path):
            if file.startswith("image_" + photo_name) and file.endswith(".jpg"):
                source_path = os.path.join(photos_path, file)
                destination_path = os.path.join(photo_folder_name, file)
                shutil.move(source_path, destination_path)


def get_bf_hist(csv_path):
    df = pd.read_csv(csv_path)
    df['bf_est'].hist(bins=NUMBER_OF_BINS_FOR_HIST)
    plt.title('BF% Histogram')
    plt.savefig(csv_path.replace(".csv", "_histogram.jpg"))
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--time_frames', type=str, default="day", help="This accepts day/week/month/year")
    parser.add_argument('--photos_output_dir', type=str, default="raw_photos")
    args = parser.parse_args()

    scrape_from_reddit(args.time_frames, args.photos_output_dir)
    filter_comments_with_low_score(SCRAPED_DATA_CSV_PATH)
    process_csv_for_image_prediction(SCRAPED_DATA_CSV_PATH)
    create_folder_bin(SCRAPED_DATA_CSV_PATH, photos_path=args.photos_output_dir)

    get_bf_hist(csv_path=SCRAPED_DATA_CSV_PATH)
