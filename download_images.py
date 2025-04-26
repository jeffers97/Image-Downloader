import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import time
import re

def download_images(url, output_folder='downloaded_images'):
    """
    Download all images from a website
    
    Args:
        url: The URL of the website to download images from
        output_folder: The folder to save images to
    """
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created folder: {output_folder}")
    
    # Add http scheme if not present
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Get base URL for resolving relative links
    parsed_url = urllib.parse.urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    # Fetch the webpage
    print(f"Fetching webpage: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch the webpage: {e}")
        return
    
    # Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all image tags
    img_tags = soup.find_all('img')
    print(f"Found {len(img_tags)} image tags")
    
    # Track downloaded images to avoid duplicates
    downloaded_files = set()
    download_count = 0
    
    # Download each image
    for img in img_tags:
        # Get image URL from src or data-src attribute
        img_url = img.get('src') or img.get('data-src') or img.get('data-original')
        
        if not img_url:
            continue
        
        # Convert relative URL to absolute URL
        if not img_url.startswith(('http://', 'https://')):
            if img_url.startswith('//'):
                img_url = parsed_url.scheme + ':' + img_url
            elif img_url.startswith('/'):
                img_url = base_url + img_url
            else:
                img_url = urllib.parse.urljoin(url, img_url)
        
        # Skip SVG images, base64 encoded images, and empty URLs
        if 'data:image' in img_url or not img_url or img_url.endswith('.svg'):
            continue
        
        # Special handling for shgcdn.com URLs
        if 'shgcdn.com' in img_url:
            # Extract the UUID from the URL
            uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', img_url)
            if uuid_match:
                filename = f"image_{uuid_match.group(1)}.jpg"
            else:
                # Fallback if UUID not found
                filename = f"image_{hash(img_url) & 0xffffffff}.jpg"
        else:
            # Extract filename from URL for non-shgcdn URLs
            filename = os.path.basename(urllib.parse.urlparse(img_url).path)
            
            # Clean up filename and ensure it has an extension
            filename = re.sub(r'[^\w\-_.]', '_', filename)
            if not os.path.splitext(filename)[1]:
                # If no extension, add .jpg as default
                filename += '.jpg'
        
        # Ensure unique filenames
        base_name, ext = os.path.splitext(filename)
        counter = 1
        while filename in downloaded_files:
            filename = f"{base_name}_{counter}{ext}"
            counter += 1
        
        downloaded_files.add(filename)
        output_path = os.path.join(output_folder, filename)
        
        # Download the image
        try:
            print(f"Downloading: {img_url}")
            img_response = requests.get(img_url, headers=headers, stream=True, timeout=10)
            img_response.raise_for_status()
            
            # Check if the content type is an image
            content_type = img_response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                print(f"Skipping non-image content: {content_type}")
                continue
                
            # Save the image
            with open(output_path, 'wb') as out_file:
                for chunk in img_response.iter_content(chunk_size=8192):
                    out_file.write(chunk)
            
            download_count += 1
            print(f"Saved to: {output_path}")
            
            # Small delay to be nice to the server
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Failed to download {img_url}: {e}")
    
    print(f"\nDownload complete! Downloaded {download_count} images to {output_folder}")

if __name__ == "__main__":
    # Get the website URL from user input
    website_url = input("Enter the website URL to download images from: ")
    
    # Get optional custom output folder
    output_folder = input("Enter output folder name (or press Enter for default 'downloaded_images'): ")
    if not output_folder:
        output_folder = 'downloaded_images'
    
    # Download images
    download_images(website_url, output_folder)
