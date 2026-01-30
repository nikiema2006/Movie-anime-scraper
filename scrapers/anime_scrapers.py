"""
Scrapers pour sites d'anime
"""

import re
import json
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
import aiohttp

from .base_scraper import BaseScraper, ScraperResult, Episode, VideoSource, VideoQuality, SourceType
from .utils import fetch_page, fetch_json, bypass_cloudflare, extract_m3u8_from_script, get_random_headers

class GogoanimeScraper(BaseScraper):
    """Scraper pour Gogoanime (Anitaku)"""
    
    def __init__(self):
        super().__init__("https://anitaku.to", "Gogoanime", "en")
        self.ajax_url = "https://ajax.gogocdn.net/ajax"
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche sur Gogoanime"""
        search_url = f"{self.base_url}/search.html?keyword={quote(query)}"
        html = await fetch_page(search_url, self.headers)
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Les résultats sont dans des div avec classe "img"
        items = soup.find_all('div', class_='img')
        
        for item in items[:limit]:
            link = item.find('a')
            if not link:
                continue
            
            title_elem = link.find('img')
            title = title_elem.get('alt', '') if title_elem else link.get('title', '')
            href = link.get('href', '')
            
            if href:
                content_id = href.split('/')[-1] if '/' in href else href
                results.append({
                    'id': content_id,
                    'title': title,
                    'url': urljoin(self.base_url, href),
                    'poster': title_elem.get('src', '') if title_elem else '',
                    'type': 'anime',
                    'source': self.site_name
                })
        
        return results
    
    async def get_details(self, content_id: str) -> Optional[ScraperResult]:
        """Récupère les détails d'un anime"""
        detail_url = f"{self.base_url}/category/{content_id}"
        html = await fetch_page(detail_url, self.headers)
        
        if not html:
            # Essayer avec bypass
            html = bypass_cloudflare(detail_url, self.headers)
            if not html:
                return None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Titre
        title_elem = soup.find('div', class_='anime_info_body')
        title = ""
        if title_elem:
            h1 = title_elem.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        
        # Image
        poster = ""
        img = soup.find('div', class_='anime_info_body').find('img') if soup.find('div', class_='anime_info_body') else None
        if img:
            poster = img.get('src', '')
        
        # Description
        description = ""
        desc_div = soup.find('div', class_='description')
        if desc_div:
            description = desc_div.get_text(strip=True)
        
        # Genres
        genres = []
        genre_links = soup.find_all('a', href=re.compile(r'/genre/'))
        for link in genre_links:
            genres.append(link.get_text(strip=True))
        
        # Année et autres infos
        year = ""
        status = ""
        type_info = soup.find('div', class_='anime_info_body')
        if type_info:
            text = type_info.get_text()
            year_match = re.search(r'Released:\s*(\d{4})', text)
            if year_match:
                year = year_match.group(1)
            status_match = re.search(r'Status:\s*(\w+)', text)
            if status_match:
                status = status_match.group(1)
        
        # Récupérer les épisodes
        episodes = await self._get_episodes(content_id, soup)
        
        result = ScraperResult(
            title=title,
            id=content_id,
            type="anime",
            description=description,
            poster=poster,
            release_year=year,
            genres=list(set(genres)),
            status=status.lower(),
            episodes=episodes,
            episode_count=len(episodes),
            source_site=self.site_name,
            source_url=detail_url
        )
        
        return result
    
    async def _get_episodes(self, content_id: str, soup: BeautifulSoup) -> List[Episode]:
        """Récupère la liste des épisodes"""
        episodes = []
        
        # Trouver l'ID de la série pour l'API
        movie_id = ""
        input_id = soup.find('input', {'id': 'movie_id'})
        if input_id:
            movie_id = input_id.get('value', '')
        
        if not movie_id:
            # Essayer de trouver dans le script
            scripts = soup.find_all('script')
            for script in scripts:
                text = script.string if script else ""
                if text and 'movie_id' in text:
                    match = re.search(r'movie_id\s*=\s*["\']?(\d+)', text)
                    if match:
                        movie_id = match.group(1)
                        break
        
        if movie_id:
            # Utiliser l'API pour récupérer les épisodes
            episode_list_url = f"{self.ajax_url}/load-list-episode?ep_start=0&ep_end=9999&id={movie_id}"
            episode_html = await fetch_page(episode_list_url, self.headers)
            
            if episode_html:
                ep_soup = BeautifulSoup(episode_html, 'lxml')
                ep_links = ep_soup.find_all('a', class_='active')
                
                for i, link in enumerate(reversed(ep_links), 1):
                    ep_href = link.get('href', '').strip()
                    ep_title = link.get_text(strip=True)
                    ep_id = ep_href.split('/')[-1].replace('.html', '') if ep_href else f"ep{i}"
                    
                    episodes.append(Episode(
                        number=i,
                        title=ep_title or f"Episode {i}",
                        id=ep_id,
                        sources=[]  # Sera rempli à la demande
                    ))
        
        return episodes
    
    async def get_episode_sources(self, content_id: str, episode_id: str) -> List[VideoSource]:
        """Récupère les sources vidéo d'un épisode"""
        episode_url = f"{self.base_url}/{episode_id}"
        html = await fetch_page(episode_url, self.headers)
        
        if not html:
            return []
        
        sources = []
        
        # Chercher les iframes d'embed
        soup = BeautifulSoup(html, 'lxml')
        iframes = soup.find_all('iframe')
        
        for iframe in iframes:
            src = iframe.get('src', '')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                
                # Détecter le type d'embed
                if 'streamtape' in src:
                    sources.append(VideoSource(
                        url=src,
                        type=SourceType.STREAMTAPE,
                        referer=episode_url
                    ))
                elif 'dood' in src:
                    sources.append(VideoSource(
                        url=src,
                        type=SourceType.DOODSTREAM,
                        referer=episode_url
                    ))
                elif 'mixdrop' in src:
                    sources.append(VideoSource(
                        url=src,
                        type=SourceType.MIXDROP,
                        referer=episode_url
                    ))
                else:
                    sources.append(VideoSource(
                        url=src,
                        type=SourceType.IFRAME,
                        referer=episode_url
                    ))
        
        # Chercher les liens de téléchargement
        download_div = soup.find('div', class_='favorites_book')
        if download_div:
            links = download_div.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if 'download' in href.lower():
                    sources.append(VideoSource(
                        url=href,
                        type=SourceType.DIRECT,
                        referer=episode_url
                    ))
        
        return sources

class ZoroScraper(BaseScraper):
    """Scraper pour Zoro/AniWatch"""
    
    def __init__(self):
        super().__init__("https://aniwatch.to", "AniWatch", "en")
        self.api_url = "https://aniwatch.to/ajax"
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche sur AniWatch"""
        search_url = f"{self.base_url}/search?keyword={quote(query)}"
        html = await fetch_page(search_url, self.headers)
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # Les résultats sont dans des div avec classe "film_list-wrap"
        items = soup.find_all('div', class_='flw-item')
        
        for item in items[:limit]:
            link = item.find('a', class_='film-poster-ahref')
            img = item.find('img')
            title_elem = item.find('h3', class_='film-name')
            
            if link:
                href = link.get('href', '')
                title = title_elem.get_text(strip=True) if title_elem else (img.get('alt', '') if img else '')
                content_id = href.split('/')[-1].split('?')[0] if '/' in href else href
                
                results.append({
                    'id': content_id,
                    'title': title,
                    'url': urljoin(self.base_url, href),
                    'poster': img.get('data-src', img.get('src', '')) if img else '',
                    'type': 'anime',
                    'source': self.site_name
                })
        
        return results
    
    async def get_details(self, content_id: str) -> Optional[ScraperResult]:
        """Récupère les détails d'un anime"""
        detail_url = f"{self.base_url}/anime/{content_id}"
        html = await fetch_page(detail_url, self.headers)
        
        if not html:
            html = bypass_cloudflare(detail_url, self.headers)
            if not html:
                return None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Titre
        title = ""
        title_elem = soup.find('h2', class_='film-name')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # Description
        description = ""
        desc_div = soup.find('div', class_='film-description')
        if desc_div:
            description = desc_div.get_text(strip=True)
        
        # Poster
        poster = ""
        img = soup.find('img', class_='film-poster-img')
        if img:
            poster = img.get('data-src', img.get('src', ''))
        
        # Genres
        genres = []
        genre_links = soup.find_all('a', href=re.compile(r'/genre/'))
        for link in genre_links:
            genres.append(link.get_text(strip=True))
        
        # Infos additionnelles
        info_div = soup.find('div', class_='anisc-info')
        year = ""
        status = ""
        if info_div:
            text = info_div.get_text()
            year_match = re.search(r'(\d{4})', text)
            if year_match:
                year = year_match.group(1)
            if 'ongoing' in text.lower():
                status = 'ongoing'
            elif 'completed' in text.lower():
                status = 'completed'
        
        # Récupérer les épisodes via l'API
        episodes = await self._get_episodes_api(content_id)
        
        result = ScraperResult(
            title=title,
            id=content_id,
            type="anime",
            description=description,
            poster=poster,
            release_year=year,
            genres=list(set(genres)),
            status=status,
            episodes=episodes,
            episode_count=len(episodes),
            source_site=self.site_name,
            source_url=detail_url
        )
        
        return result
    
    async def _get_episodes_api(self, content_id: str) -> List[Episode]:
        """Récupère les épisodes via l'API"""
        episodes = []
        
        # API pour récupérer les épisodes
        api_url = f"{self.api_url}/v2/episode/list/{content_id}"
        data = await fetch_json(api_url, self.headers)
        
        if data and 'data' in data:
            episodes_data = data['data'].get('episodes', [])
            for ep in episodes_data:
                episodes.append(Episode(
                    number=ep.get('number', 0),
                    title=ep.get('title', f"Episode {ep.get('number', 0)}"),
                    id=str(ep.get('id', '')),
                    sources=[],
                    thumbnail=ep.get('image', '')
                ))
        
        return episodes
    
    async def get_episode_sources(self, content_id: str, episode_id: str) -> List[VideoSource]:
        """Récupère les sources vidéo"""
        # API pour les sources
        api_url = f"{self.api_url}/v2/episode/servers?episodeId={episode_id}"
        data = await fetch_json(api_url, self.headers)
        
        sources = []
        
        if data and 'data' in data:
            servers = data['data'].get('servers', [])
            for server in servers:
                server_name = server.get('serverName', '').lower()
                server_id = server.get('serverId', '')
                
                # Récupérer l'URL de la source
                source_api = f"{self.api_url}/v2/episode/sources?serverId={server_id}"
                source_data = await fetch_json(source_api, self.headers)
                
                if source_data and 'data' in source_data:
                    source_info = source_data['data']
                    link = source_info.get('link', '')
                    
                    if link:
                        sources.append(VideoSource(
                            url=link,
                            type=SourceType.HLS if '.m3u8' in link else SourceType.DIRECT,
                            is_m3u8='.m3u8' in link,
                            referer=self.base_url
                        ))
        
        return sources

class AnimeHeavenScraper(BaseScraper):
    """Scraper pour AnimeHeaven"""
    
    def __init__(self):
        super().__init__("https://animeheaven.me", "AnimeHeaven", "en")
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche sur AnimeHeaven"""
        search_url = f"{self.base_url}/search?q={quote(query)}"
        html = await fetch_page(search_url, self.headers)
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        items = soup.find_all('div', class_='condd')
        
        for item in items[:limit]:
            link = item.find('a')
            if link:
                href = link.get('href', '')
                title_elem = link.find('div', class_='condd')
                title = title_elem.get_text(strip=True) if title_elem else href
                
                content_id = href.split('/')[-1] if '/' in href else href
                
                results.append({
                    'id': content_id,
                    'title': title,
                    'url': urljoin(self.base_url, href),
                    'type': 'anime',
                    'source': self.site_name
                })
        
        return results
    
    async def get_details(self, content_id: str) -> Optional[ScraperResult]:
        """Récupère les détails"""
        detail_url = f"{self.base_url}/anime/{content_id}"
        html = await fetch_page(detail_url, self.headers)
        
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Titre
        title = ""
        title_elem = soup.find('div', class_='infoboxc')
        if title_elem:
            h1 = title_elem.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        
        # Description
        description = ""
        desc = soup.find('div', class_='infodes')
        if desc:
            description = desc.get_text(strip=True)
        
        # Poster
        poster = ""
        img = soup.find('div', class_='infoboxc').find('img') if soup.find('div', class_='infoboxc') else None
        if img:
            poster = urljoin(self.base_url, img.get('src', ''))
        
        # Épisodes
        episodes = []
        ep_links = soup.find_all('a', href=re.compile(r'/episode/'))
        
        for link in ep_links:
            href = link.get('href', '')
            ep_text = link.get_text(strip=True)
            ep_match = re.search(r'Episode\s*(\d+)', ep_text, re.I)
            ep_num = int(ep_match.group(1)) if ep_match else 0
            
            ep_id = href.split('/')[-1] if '/' in href else href
            
            episodes.append(Episode(
                number=ep_num,
                title=ep_text,
                id=ep_id
            ))
        
        # Trier par numéro d'épisode
        episodes.sort(key=lambda x: x.number)
        
        result = ScraperResult(
            title=title,
            id=content_id,
            type="anime",
            description=description,
            poster=poster,
            episodes=episodes,
            episode_count=len(episodes),
            source_site=self.site_name,
            source_url=detail_url
        )
        
        return result
    
    async def get_episode_sources(self, content_id: str, episode_id: str) -> List[VideoSource]:
        """Récupère les sources"""
        episode_url = f"{self.base_url}/episode/{episode_id}"
        html = await fetch_page(episode_url, self.headers)
        
        if not html:
            return []
        
        sources = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Chercher les iframes
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                sources.append(VideoSource(
                    url=src,
                    type=SourceType.IFRAME,
                    referer=episode_url
                ))
        
        return sources

class AnimeSamaScraper(BaseScraper):
    """Scraper pour AnimeSama (FR)"""
    
    def __init__(self):
        super().__init__("https://anime-sama.fr", "AnimeSama", "fr")
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche sur AnimeSama"""
        search_url = f"{self.base_url}/template-php/defaut/fetch.php?search={quote(query)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    
                    for item in data[:limit]:
                        results.append({
                            'id': item.get('url', '').split('/')[-1],
                            'title': item.get('title', ''),
                            'url': urljoin(self.base_url, item.get('url', '')),
                            'poster': item.get('image', ''),
                            'type': 'anime',
                            'source': self.site_name
                        })
                    
                    return results
                return []
    
    async def get_details(self, content_id: str) -> Optional[ScraperResult]:
        """Récupère les détails"""
        detail_url = f"{self.base_url}/anime/{content_id}"
        html = await fetch_page(detail_url, self.headers)
        
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Titre
        title = ""
        title_elem = soup.find('h1')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # Description
        description = ""
        desc = soup.find('div', class_='synopsis')
        if desc:
            description = desc.get_text(strip=True)
        
        # Poster
        poster = ""
        img = soup.find('img', class_='cover')
        if img:
            poster = img.get('src', '')
        
        # Genres
        genres = []
        genre_div = soup.find('div', class_='genres')
        if genre_div:
            for link in genre_div.find_all('a'):
                genres.append(link.get_text(strip=True))
        
        # Épisodes - AnimeSama a une structure spéciale avec saisons
        episodes = []
        ep_list = soup.find_all('a', class_='episode')
        
        for i, ep in enumerate(ep_list, 1):
            ep_href = ep.get('href', '')
            ep_title = ep.get_text(strip=True)
            ep_id = ep_href.split('/')[-1] if '/' in ep_href else str(i)
            
            episodes.append(Episode(
                number=i,
                title=ep_title,
                id=ep_id
            ))
        
        result = ScraperResult(
            title=title,
            id=content_id,
            type="anime",
            description=description,
            poster=poster,
            genres=genres,
            episodes=episodes,
            episode_count=len(episodes),
            source_site=self.site_name,
            source_url=detail_url
        )
        
        return result
    
    async def get_episode_sources(self, content_id: str, episode_id: str) -> List[VideoSource]:
        """Récupère les sources"""
        episode_url = f"{self.base_url}/anime/{content_id}/{episode_id}"
        html = await fetch_page(episode_url, self.headers)
        
        if not html:
            return []
        
        sources = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Chercher les lecteurs vidéo
        players = soup.find_all('div', class_='player')
        for player in players:
            iframe = player.find('iframe')
            if iframe:
                src = iframe.get('src', '')
                if src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    sources.append(VideoSource(
                        url=src,
                        type=SourceType.IFRAME,
                        referer=episode_url
                    ))
        
        return sources
