import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,  # Allow cookies and credentials (optional)
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

def extract_reddit_info(url):
    """Retrieve the title of a Reddit post if the URL is valid."""
    try:
        # Check if the URL is a Reddit link
        if "reddit.com" not in url:
            return {"Error": "The URL is not a valid Reddit link."}

        # Append .json to the URL if not already present
        if not url.endswith(".json"):
            url = url.rstrip("/") + "/.json"

        # Fetch the JSON data
        response = requests.get(url)
        response.raise_for_status()  # Ensure the request was successful
        data = response.json()

        # Extract the title from the JSON response
        title = data[0]['data']['children'][0]['data']['title']
        return {
            "title": title or "Reddit Post",
            "icon" : "https://www.redditstatic.com/shreddit/assets/favicon/192x192.png"
          }

    except requests.RequestException as e:
        return {"Error": f"Failed to retrieve the Reddit post: {e}"}
    except (KeyError, IndexError) as e:
        return {"Error": f"Unexpected JSON structure: {e}"}


def extract_youtube_info(url):
    """Extract the title and thumbnail of a YouTube video given its URL."""
    try:
        # Parse the video ID from the URL
        parsed_url = urlparse(url)
        video_id = None

        # For standard YouTube URLs
        if "youtube.com" in url:
            query_params = parse_qs(parsed_url.query)
            video_id = query_params.get("v", [None])[0]
        # For shortened YouTube URLs (youtu.be)
        elif "youtu.be" in url:
            video_id = parsed_url.path.lstrip("/")

        if not video_id:
            return {"Error": "Invalid YouTube URL. Could not extract video ID."}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Fetch the YouTube page with headers
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Ensure the request was successful
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the title
        title_tag = soup.find('meta', attrs={'name': 'title'})
        title = title_tag['content'] if title_tag else "None"
        # title = soup.title.string.strip() if soup.title else "None"

        # Construct the thumbnail URL
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

        return {
            "title": title,
            "img": thumbnail_url or "None",
            "icon": "https://developers.google.com/static/site-assets/logo-youtube.svg"
        }
    except requests.RequestException as e:
        return {"Error": f"Failed to retrieve the YouTube URL: {e}"}


def extract_pinterest_info(url):
    """Extract the main image, title, and Pinterest logo from a Pinterest page."""
    try:
        import requests
        from bs4 import BeautifulSoup

        # Fetch the Pinterest page
        response = requests.get(url)
        response.raise_for_status()  # Ensure the request was successful
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the title
        title = soup.title.string.strip() if soup.title else "No title found"

        # Extract the main image (assumes the main image is the first <img> tag with a meaningful `src`)
        main_img = None
        img_tag = soup.find("img")
        if img_tag and img_tag.get("src"):
            main_img = img_tag["src"]

        # Extract the Pinterest logo (looks for <link> or specific attributes for favicons/logos)
        logo = None
        logo_tag = soup.find("link", rel="icon") or soup.find("link", rel="shortcut icon")
        if logo_tag and logo_tag.get("href"):
            logo = logo_tag["href"]

        return {
            "title": title,
            "img": main_img or "None",
            "icon": logo or "None"
        }
    except requests.RequestException as e:
        return {"Error": f"Failed to retrieve the Pinterest URL: {e}"}


def extract_website_info(url):
    try:
        # Handle YouTube URLs
        if "youtube.com" in url or "youtu.be" in url:
            youtube_info = extract_youtube_info(url)
            return youtube_info

        # Handle Pinterest URLs
        if "pinterest.com" in url:
            pinterest_info = extract_pinterest_info(url)
            return pinterest_info

        if "reddit.com" in url:
            reddit_info = extract_reddit_info(url)
            return reddit_info

        # Fetch the HTML content for other URLs
        response = requests.get(url)
        response.raise_for_status()  # Ensure the request was successful
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the title
        title = soup.title.string.strip() if soup.title else "No title found"

        # Extract the meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc['content'].strip() if meta_desc and meta_desc.get('content') else 'No meta description found'

        # Extract the meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        keywords = meta_keywords['content'].strip() if meta_keywords and meta_keywords.get('content') else 'No meta keywords found'

        # Extract headings
        headings = []
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
            headings.extend([heading.get_text(strip=True) for heading in soup.find_all(tag)])

        # Extract anchor texts
        anchor_texts = [a.get_text(strip=True) for a in soup.find_all('a', href=True) if a.get_text(strip=True)]

        # Extract the logo
        logo = None

        # Check for favicon in <link>
        favicon = soup.find('link', rel=lambda value: value and 'icon' in value.lower())
        if favicon and favicon.get('href'):
            logo = favicon['href']

        # Check for a possible logo in <img> tags
        if not logo:
            logo_img = soup.find('img', attrs={'class': lambda x: x and 'logo' in x.lower()})
            if logo_img and logo_img.get('src'):
                logo = logo_img['src']

        # Ensure the logo URL is complete
        if logo and not logo.startswith(('http://', 'https://')):
            from urllib.parse import urljoin
            logo = urljoin(url, logo)

        # Retrieve the first image
        first_image = None
        image_tag = soup.find('img')  # Get the first <img> tag
        if image_tag and image_tag.get('src'):
            first_image = image_tag['src']
            # Ensure the image URL is complete
            if not first_image.startswith(('http://', 'https://')):
                first_image = urljoin(url, first_image)

        # Compile the extracted information
        website_info = {
            'title': title,
            'description': description,
            'keywords': keywords,
            'headings': headings,
            'links': anchor_texts,
            'icon': logo or 'None',
            'img' : first_image or 'None'
        }
        return website_info

    except requests.RequestException as e:
        return {'Error': f'Failed to retrieve the URL: {e}'}


class URLs(BaseModel):
    urls: list

@app.post("/scrape")
async def scrape(
    urls: URLs
):
    if urls.urls is None:
        return {"error" : "Please provide a list of URLs"}

    inputs = []
    output = {}

    for url in urls.urls:
        url_stripped = url.strip()
        info = extract_website_info(url_stripped)
        print(f"URL: {url_stripped}")

        # Initialize the output dictionary for the URL
        output[url_stripped] = {}

        # Iterate over the info dictionary
        for key, value in info.items():
            print(f"{key}: {value}")
            output[url_stripped][key] = value

            # Append titles to the inputs list
            if "title" in key.lower():  # Case-insensitive match
                inputs.append(value)

    # Optional: Print captured titles
    print("Captured Titles:", inputs)
    return{
        "status" : 200,
        "output": output,
        "input": inputs,
        "message": "Scraping completed successfully"
    }



if __name__ == "__main__":
  uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
