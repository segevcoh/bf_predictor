import os

import requests

CLIENT_IMGUR_ID = os.environ['CLIENT_IMGUR_ID']


def get_image_from_imgur(post, path):

    album_url = post.url
    # Get the album ID from the URL
    album_id = album_url.split("/")[-1]

    # Get information about the album using the Imgur API
    response = requests.get(f"https://api.imgur.com/3/album/{album_id}", headers={
        "Authorization": f"Client-ID {CLIENT_IMGUR_ID}"
    }).json()

    # Get URLs of all images in the picture album
    image_urls = [item["link"] for item in response["data"]["images"]]

    # Download images
    paths = []
    for i, url in enumerate(image_urls):
        image = requests.get(url).content
        with open(f"{path}/image_{post.id}_{i}.jpg", "wb") as f:
            f.write(image)
            paths.append(f"{path}/image_{post.id}_{i}.jpg")
    print("Images downloaded successfully!")
    return True, paths


def get_photos_from_post(post, path):
    """Downloads the images inside a given post and returns a boolean - status indicating whether the download was
    successful and a list paths which contain the paths in which the pictures in the post were downloaded to."""
    at_least_one_image = False
    paths = []

    if post.is_self:
        print("This post doesn't have any images.")
        print(post.url)  # for checking purposes
        return False, paths
    try:
        if post.url.endswith(('.jpg', '.jpeg', '.png')):
            image = requests.get(post.url).content
            with open(f"{path}/image_{post.id}.jpg", "wb") as f:
                f.write(image)
            print("Image downloaded successfully!")
            return True, [f"{path}/image_{post.id}.jpg"]
        elif 'imgur.com' in post.url:
            return get_image_from_imgur(post, path)
        elif "gallery" in post.url:
            gallery = []
            for i in post.media_metadata.items():
                url = i[1]['p'][0]['u']
                url = url.split("?")[0].replace("preview", "i")
                gallery.append(url)
            for i, img in enumerate(gallery):
                image = requests.get(img).content
                with open(f"{path}/image_{post.id}_{i}.jpg", "wb") as f:
                    f.write(image)
                    paths.append(f"{path}/image_{post.id}_{i}.jpg")
                print("Image downloaded successfully!")
                at_least_one_image = True
            return True, paths
        else:
            print("The post doesn't contain a direct link to an image.")
            print(post.url)
            return False, paths
    except Exception as e:
        print(f"An error occurred: {e}")
        return at_least_one_image, paths
