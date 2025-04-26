import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import time
import re
import hashlib
from collections import defaultdict

def download_images(url, output_folder='downloaded_images'):
    """
    Download all images from a website and organize them by similar names
    
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
    
    # Collect image information
    image_info = []
    
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
            
        # Try to get alt text and title for better naming
        alt_text = img.get('alt', '')
        title = img.get('title', '')
        
        # Extract original filename parts for shgcdn.com URLs
        original_name = ""
        
        if 'shgcdn.com' in img_url:
            # Extract the UUID from the URL
            uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', img_url)
            
            # Try to extract original filename if present in the URL or path
            orig_name_match = re.search(r'/([^/]+?)(?:-/|-)?(?:format|preview|quality)', img_url)
            if orig_name_match:
                original_name = orig_name_match.group(1)
                # Clean up the original name
                original_name = re.sub(r'[^\w\-_.]', '_', original_name)
            
            if uuid_match:
                uuid = uuid_match.group(1)
                
                # Create a name using original name (if found) or alt/title text if available
                if original_name:
                    filename = f"{original_name}_{uuid[-8:]}.jpg"
                elif alt_text and len(alt_text) > 3:
                    # Use alt text (cleaned) with UUID suffix for uniqueness
                    clean_alt = re.sub(r'[^\w\-_]', '_', alt_text)[:30]
                    filename = f"{clean_alt}_{uuid[-8:]}.jpg"
                elif title and len(title) > 3:
                    # Use title (cleaned) with UUID suffix for uniqueness
                    clean_title = re.sub(r'[^\w\-_]', '_', title)[:30]
                    filename = f"{clean_title}_{uuid[-8:]}.jpg"
                else:
                    # Just use the UUID as filename
                    filename = f"image_{uuid}.jpg"
            else:
                # Fallback if UUID not found
                if original_name:
                    filename = f"{original_name}_{hashlib.md5(img_url.encode()).hexdigest()[:8]}.jpg"
                else:
                    filename = f"image_{hashlib.md5(img_url.encode()).hexdigest()[:12]}.jpg"
        else:
            # For non-shgcdn URLs, try to get filename from URL
            path = urllib.parse.urlparse(img_url).path
            filename = os.path.basename(path)
            
            # Add extension if missing
            if not os.path.splitext(filename)[1]:
                filename += '.jpg'
            
            # Clean up filename
            filename = re.sub(r'[^\w\-_.]', '_', filename)
            
            # If filename seems generic, try to use alt text or title
            if filename in ['image.jpg', 'img.jpg', 'picture.jpg', '.jpg'] or len(filename) < 5:
                if alt_text and len(alt_text) > 3:
                    clean_alt = re.sub(r'[^\w\-_]', '_', alt_text)[:30]
                    filename = f"{clean_alt}_{hashlib.md5(img_url.encode()).hexdigest()[:8]}.jpg"
                elif title and len(title) > 3:
                    clean_title = re.sub(r'[^\w\-_]', '_', title)[:30]
                    filename = f"{clean_title}_{hashlib.md5(img_url.encode()).hexdigest()[:8]}.jpg"
        
        # Store information for organizing later
        image_info.append({
            'url': img_url,
            'filename': filename,
            'alt_text': alt_text,
            'title': title,
            'original_name': original_name
        })
    
    # Organize images by patterns in filenames
    image_groups = defaultdict(list)
    
    for info in image_info:
        # Extract the first part of the filename before any numbers/underscores
        # This helps group similar images together
        base = re.match(r'^([a-zA-Z_]+)', info['filename'])
        if base:
            group_key = base.group(1)
        else:
            # If no match, use the first 3 characters
            group_key = info['filename'][:3]
            
        # If original name is available, prefer that for grouping
        if info['original_name']:
            # Take the first word of original name for grouping
            parts = re.split(r'[^a-zA-Z]', info['original_name'])
            if parts and parts[0]:
                group_key = parts[0]
                
        # Fallback for very short keys
        if len(group_key) < 2:
            group_key = 'misc'
            
        image_groups[group_key].append(info)
    
    # Download files by group
    download_count = 0
    
    for group, images in image_groups.items():
        # Create subdirectory for the group if it has multiple images
        group_dir = output_folder
        if len(images) > 1:
            group_dir = os.path.join(output_folder, group)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
                print(f"Created group folder: {group_dir}")
        
        # Track filenames used in this group
        used_filenames = set()
        
        # Download each image in the group
        for info in images:
            img_url = info['url']
            filename = info['filename']
            
            # Ensure unique filenames within group
            base_name, ext = os.path.splitext(filename)
            counter = 1
            while filename in used_filenames:
                filename = f"{base_name}_{counter}{ext}"
                counter += 1
            
            used_filenames.add(filename)
            output_path = os.path.join(group_dir, filename)
            
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
    print(f"Organized into {len(image_groups)} groups")

if __name__ == "__main__":
    # Get the website URL from user input
    website_url = input("Enter the website URL to download images from: ")
    
    # Get optional custom output folder
    output_folder = input("Enter output folder name (or press Enter for default 'downloaded_images'): ")
    if not output_folder:
        output_folder = 'downloaded_images'
    
    # Download images
    download_images(website_url, output_folder)
