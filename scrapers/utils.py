"""
Utilitaires pour le scraping
"""

import asyncio
import re
import json
import base64
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse, parse_qs
import aiohttp
from bs4 import BeautifulSoup
import cloudscraper
from fake_useragent import UserAgent
import httpx

try:
    ua = UserAgent()
    DEFAULT_USER_AGENT = ua.random
except:
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_random_headers():
    """Génère des headers aléatoires"""
    return {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",  # Removed 'br' to avoid brotli dependency
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

import requests

def fetch_page_sync(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Optional[str]:
    """Récupère le contenu d'une page (synchrone avec requests)"""
    if headers is None:
        headers = get_random_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def fetch_json_sync(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Optional[Dict]:
    """Récupère du JSON depuis une URL (synchrone avec requests)"""
    if headers is None:
        headers = get_random_headers()
        headers["Accept"] = "application/json"
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error fetching JSON {url}: {e}")
        return None

async def fetch_page(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Optional[str]:
    """Récupère le contenu d'une page (async avec aiohttp, fallback sur requests)"""
    if headers is None:
        headers = get_random_headers()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    return await response.text()
                return None
    except Exception as e:
        # Fallback sur requests synchrone
        return fetch_page_sync(url, headers, timeout)

async def fetch_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Optional[Dict]:
    """Récupère du JSON depuis une URL (async avec aiohttp, fallback sur requests)"""
    if headers is None:
        headers = get_random_headers()
        headers["Accept"] = "application/json"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return None
    except Exception as e:
        # Fallback sur requests synchrone
        return fetch_json_sync(url, headers, timeout)

def bypass_cloudflare(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Contourne la protection Cloudflare avec cloudscraper"""
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, headers=headers or get_random_headers(), timeout=30)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Cloudflare bypass error: {e}")
        return None

def retry_request(func, max_retries: int = 3, delay: float = 1.0):
    """Décorateur pour réessayer une requête"""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                if result:
                    return result
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(delay * (attempt + 1))
        return None
    return wrapper

def extract_video_url(embed_url: str) -> Optional[Dict[str, Any]]:
    """Extrait l'URL vidéo depuis un embed"""
    patterns = {
        'streamtape': r'streamtape\.com/e/(\w+)',
        'doodstream': r'dood\.[^/]+/e/(\w+)',
        'mixdrop': r'mixdrop\.[^/]+/e/(\w+)',
        'upstream': r'upstream\.to/e/(\w+)',
        'vidcloud': r'vidcloud\.[^/]+/e/(\w+)',
        'mp4upload': r'mp4upload\.com/embed-(\w+)',
        'yourupload': r'yourupload\.com/embed/(\w+)',
        'sbembed': r'sbembed\.com/embed/(\w+)',
        'filemoon': r'filemoon\.sx/e/(\w+)',
        'voe': r'voe\.sx/e/(\w+)',
    }
    
    for host, pattern in patterns.items():
        match = re.search(pattern, embed_url)
        if match:
            return {
                'host': host,
                'video_id': match.group(1),
                'embed_url': embed_url,
                'direct_url': None  # Nécessite extraction supplémentaire
            }
    return None

def decode_base64_url(encoded: str) -> str:
    """Décode une URL encodée en base64"""
    try:
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += '=' * padding
        return base64.b64decode(encoded).decode('utf-8')
    except:
        return ""

def extract_m3u8_from_script(html: str) -> List[str]:
    """Extrait les URLs m3u8 du JavaScript"""
    patterns = [
        r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
        r'file["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'sources?["\']?\s*:\s*\[.*?["\']([^"\']+\.m3u8[^"\']*)["\']',
    ]
    
    urls = []
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
        urls.extend(matches)
    
    return list(set(urls))

def decrypt_aes(encrypted: str, key: str, iv: str) -> str:
    """Déchiffre du texte AES (pour certains sites)"""
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import unpad
        
        key_bytes = key.encode('utf-8')
        iv_bytes = iv.encode('utf-8')
        encrypted_bytes = base64.b64decode(encrypted)
        
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception as e:
        print(f"AES decryption error: {e}")
        return ""

def parse_embed_page(html: str, referer: str = "") -> List[Dict[str, Any]]:
    """Parse une page d'embed et extrait les sources vidéo"""
    sources = []
    
    # Chercher les sources m3u8
    m3u8_urls = extract_m3u8_from_script(html)
    for url in m3u8_urls:
        sources.append({
            'url': url,
            'type': 'hls',
            'quality': 'auto',
            'is_m3u8': True
        })
    
    # Chercher les sources mp4
    mp4_pattern = r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']'
    mp4_urls = re.findall(mp4_pattern, html, re.IGNORECASE)
    for url in mp4_urls:
        sources.append({
            'url': url,
            'type': 'mp4',
            'quality': 'unknown',
            'is_m3u8': False
        })
    
    return sources

def extract_poster_url(soup: BeautifulSoup, base_url: str = "") -> str:
    """Extrait l'URL du poster"""
    # Meta og:image
    meta = soup.find('meta', property='og:image')
    if meta:
        return meta.get('content', '')
    
    # Meta twitter:image
    meta = soup.find('meta', property='twitter:image')
    if meta:
        return meta.get('content', '')
    
    # Image avec classe poster
    img = soup.find('img', class_=re.compile('poster', re.I))
    if img:
        return urljoin(base_url, img.get('src', ''))
    
    return ""

def extract_description(soup: BeautifulSoup) -> str:
    """Extrait la description"""
    # Meta description
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta:
        return meta.get('content', '')
    
    meta = soup.find('meta', property='og:description')
    if meta:
        return meta.get('content', '')
    
    # Div avec classe description/synopsis
    for class_name in ['description', 'synopsis', 'summary', 'plot']:
        div = soup.find(['div', 'p'], class_=re.compile(class_name, re.I))
        if div:
            return div.get_text(strip=True)
    
    return ""

def clean_title(title: str) -> str:
    """Nettoie un titre"""
    if not title:
        return ""
    # Enlever les espaces multiples
    title = re.sub(r'\s+', ' ', title)
    # Enlever les caractères spéciaux au début/fin
    title = title.strip(' -:|•')
    return title.strip()

def normalize_search_query(query: str) -> str:
    """Normalise une requête de recherche"""
    # Remplacer les espaces par des +
    query = re.sub(r'\s+', '+', query.strip())
    # Enlever les caractères spéciaux
    query = re.sub(r'[^\w\s\-+]', '', query)
    return query.lower()

class AsyncRequestPool:
    """Pool de requêtes asynchrones avec limitation"""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch(self, url: str, headers: Optional[Dict] = None) -> Optional[str]:
        async with self.semaphore:
            return await fetch_page(url, headers)
    
    async def fetch_multiple(self, urls: List[str], headers: Optional[Dict] = None) -> List[Optional[str]]:
        tasks = [self.fetch(url, headers) for url in urls]
        return await asyncio.gather(*tasks)
