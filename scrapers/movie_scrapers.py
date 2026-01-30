"""
Scrapers pour sites de films et séries
"""

import re
import json
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
import aiohttp

from .base_scraper import BaseScraper, ScraperResult, Episode, Season, VideoSource, VideoQuality, SourceType
from .utils import fetch_page, fetch_json, bypass_cloudflare, get_random_headers

class SFlixScraper(BaseScraper):
    """Scraper pour SFlix"""
    
    def __init__(self):
        super().__init__("https://sflix.to", "SFlix", "en")
        self.api_url = "https://sflix.to/ajax"
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche sur SFlix"""
        search_url = f"{self.base_url}/search/{quote(query)}"
        html = await fetch_page(search_url, self.headers)
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        items = soup.find_all('div', class_='flw-item')
        
        for item in items[:limit]:
            link = item.find('a', class_='film-poster-ahref')
            img = item.find('img')
            title_elem = item.find('h2', class_='film-name')
            
            if link:
                href = link.get('href', '')
                title = title_elem.get_text(strip=True) if title_elem else (img.get('alt', '') if img else '')
                content_id = href.split('/')[-1].split('?')[0] if '/' in href else href
                
                # Déterminer le type
                content_type = 'movie' if '/movie/' in href else 'series'
                
                results.append({
                    'id': content_id,
                    'title': title,
                    'url': urljoin(self.base_url, href),
                    'poster': img.get('data-src', img.get('src', '')) if img else '',
                    'type': content_type,
                    'source': self.site_name
                })
        
        return results
    
    async def get_details(self, content_id: str, content_type: str = "movie") -> Optional[ScraperResult]:
        """Récupère les détails"""
        detail_url = f"{self.base_url}/{content_type}/{content_id}"
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
        
        # Infos
        info_div = soup.find('div', class_='elements')
        year = ""
        duration = ""
        if info_div:
            text = info_div.get_text()
            year_match = re.search(r'(\d{4})', text)
            if year_match:
                year = year_match.group(1)
            duration_match = re.search(r'(\d+)\s*min', text, re.I)
            if duration_match:
                duration = f"{duration_match.group(1)} min"
        
        result = ScraperResult(
            title=title,
            id=content_id,
            type=content_type,
            description=description,
            poster=poster,
            release_year=year,
            duration=duration,
            genres=list(set(genres)),
            source_site=self.site_name,
            source_url=detail_url
        )
        
        # Si c'est une série, récupérer les saisons
        if content_type == "series":
            result.seasons = await self._get_seasons(content_id)
            result.season_count = len(result.seasons)
        else:
            # Pour les films, récupérer les sources directement
            result.sources = await self._get_movie_sources(content_id)
        
        return result
    
    async def _get_seasons(self, series_id: str) -> List[Season]:
        """Récupère les saisons d'une série"""
        seasons = []
        
        # API pour les saisons
        seasons_url = f"{self.api_url}/season/list/{series_id}"
        data = await fetch_json(seasons_url, self.headers)
        
        if data and 'data' in data:
            seasons_html = data['data']
            soup = BeautifulSoup(seasons_html, 'lxml')
            
            season_items = soup.find_all('a', class_='dropdown-item')
            
            for i, season_item in enumerate(season_items, 1):
                season_title = season_item.get_text(strip=True)
                season_data_id = season_item.get('data-id', '')
                
                # Récupérer les épisodes de cette saison
                episodes = await self._get_episodes(series_id, season_data_id)
                
                seasons.append(Season(
                    number=i,
                    title=season_title,
                    id=season_data_id,
                    episodes=episodes,
                    episode_count=len(episodes)
                ))
        
        return seasons
    
    async def _get_episodes(self, series_id: str, season_id: str) -> List[Episode]:
        """Récupère les épisodes d'une saison"""
        episodes = []
        
        episodes_url = f"{self.api_url}/season/episodes/{season_id}"
        data = await fetch_json(episodes_url, self.headers)
        
        if data and 'data' in data:
            episodes_html = data['data']
            soup = BeautifulSoup(episodes_html, 'lxml')
            
            ep_items = soup.find_all('a', class_='episode-item')
            
            for ep in ep_items:
                ep_title = ep.get('title', '')
                ep_data_id = ep.get('data-id', '')
                ep_number = ep.find('span', class_='episode-number')
                ep_num = int(ep_number.get_text(strip=True)) if ep_number else 0
                
                episodes.append(Episode(
                    number=ep_num,
                    title=ep_title,
                    id=ep_data_id
                ))
        
        return episodes
    
    async def _get_movie_sources(self, movie_id: str) -> List[VideoSource]:
        """Récupère les sources d'un film"""
        sources = []
        
        # Récupérer les serveurs
        servers_url = f"{self.api_url}/movie/servers/{movie_id}"
        data = await fetch_json(servers_url, self.headers)
        
        if data and 'data' in data:
            servers_html = data['data']
            soup = BeautifulSoup(servers_html, 'lxml')
            
            server_items = soup.find_all('a', class_='server-item')
            
            for server in server_items:
                server_id = server.get('data-id', '')
                server_name = server.get('data-server', '')
                
                # Récupérer la source
                source_url = f"{self.api_url}/movie/sources/{server_id}"
                source_data = await fetch_json(source_url, self.headers)
                
                if source_data and 'data' in source_data:
                    for src in source_data['data']:
                        link = src.get('link', '')
                        if link:
                            sources.append(VideoSource(
                                url=link,
                                type=SourceType.HLS if '.m3u8' in link else SourceType.DIRECT,
                                is_m3u8='.m3u8' in link,
                                referer=self.base_url
                            ))
        
        return sources
    
    async def get_episode_sources(self, content_id: str, episode_id: str) -> List[VideoSource]:
        """Récupère les sources d'un épisode"""
        sources = []
        
        # Récupérer les serveurs pour l'épisode
        servers_url = f"{self.api_url}/episode/servers/{episode_id}"
        data = await fetch_json(servers_url, self.headers)
        
        if data and 'data' in data:
            servers_html = data['data']
            soup = BeautifulSoup(servers_html, 'lxml')
            
            server_items = soup.find_all('a', class_='server-item')
            
            for server in server_items:
                server_id = server.get('data-id', '')
                
                # Récupérer la source
                source_url = f"{self.api_url}/episode/sources/{server_id}"
                source_data = await fetch_json(source_url, self.headers)
                
                if source_data and 'data' in source_data:
                    for src in source_data['data']:
                        link = src.get('link', '')
                        if link:
                            sources.append(VideoSource(
                                url=link,
                                type=SourceType.HLS if '.m3u8' in link else SourceType.DIRECT,
                                is_m3u8='.m3u8' in link,
                                referer=self.base_url
                            ))
        
        return sources

class FMoviesScraper(BaseScraper):
    """Scraper pour FMovies"""
    
    def __init__(self):
        super().__init__("https://fmovies.to", "FMovies", "en")
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche sur FMovies"""
        search_url = f"{self.base_url}/search?keyword={quote(query)}"
        html = await fetch_page(search_url, self.headers)
        
        if not html:
            html = bypass_cloudflare(search_url, self.headers)
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        items = soup.find_all('div', class_='item')
        
        for item in items[:limit]:
            link = item.find('a', class_='poster')
            if link:
                href = link.get('href', '')
                title = link.get('title', '')
                content_id = href.split('/')[-1].split('?')[0] if '/' in href else href
                
                img = link.find('img')
                poster = img.get('src', '') if img else ''
                
                content_type = 'movie' if '/movie/' in href else 'series'
                
                results.append({
                    'id': content_id,
                    'title': title,
                    'url': urljoin(self.base_url, href),
                    'poster': poster,
                    'type': content_type,
                    'source': self.site_name
                })
        
        return results
    
    async def get_details(self, content_id: str, content_type: str = "movie") -> Optional[ScraperResult]:
        """Récupère les détails"""
        detail_url = f"{self.base_url}/{content_type}/{content_id}"
        html = await fetch_page(detail_url, self.headers)
        
        if not html:
            html = bypass_cloudflare(detail_url, self.headers)
            if not html:
                return None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Titre
        title = ""
        title_elem = soup.find('h1', class_='title')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # Description
        description = ""
        desc_div = soup.find('div', class_='desc')
        if desc_div:
            description = desc_div.get_text(strip=True)
        
        # Poster
        poster = ""
        img = soup.find('img', class_='poster')
        if img:
            poster = img.get('src', '')
        
        # Genres
        genres = []
        meta_div = soup.find('div', class_='meta')
        if meta_div:
            for link in meta_div.find_all('a', href=re.compile(r'/genre/')):
                genres.append(link.get_text(strip=True))
        
        # Infos
        year = ""
        duration = ""
        if meta_div:
            text = meta_div.get_text()
            year_match = re.search(r'(\d{4})', text)
            if year_match:
                year = year_match.group(1)
            duration_match = re.search(r'(\d+)\s*min', text, re.I)
            if duration_match:
                duration = f"{duration_match.group(1)} min"
        
        result = ScraperResult(
            title=title,
            id=content_id,
            type=content_type,
            description=description,
            poster=poster,
            release_year=year,
            duration=duration,
            genres=list(set(genres)),
            source_site=self.site_name,
            source_url=detail_url
        )
        
        if content_type == "series":
            result.seasons = await self._get_seasons(soup, content_id)
            result.season_count = len(result.seasons)
        else:
            result.sources = await self._get_movie_sources(soup, content_id)
        
        return result
    
    async def _get_seasons(self, soup: BeautifulSoup, series_id: str) -> List[Season]:
        """Récupère les saisons"""
        seasons = []
        
        # Chercher les options de saison
        season_select = soup.find('select', {'id': 'season'})
        if season_select:
            options = season_select.find_all('option')
            for opt in options:
                season_num = opt.get('value', '')
                season_title = opt.get_text(strip=True)
                
                # Récupérer les épisodes
                episodes = await self._get_episodes(series_id, season_num)
                
                seasons.append(Season(
                    number=int(season_num) if season_num.isdigit() else 0,
                    title=season_title,
                    id=f"{series_id}-s{season_num}",
                    episodes=episodes,
                    episode_count=len(episodes)
                ))
        
        return seasons
    
    async def _get_episodes(self, series_id: str, season_num: str) -> List[Episode]:
        """Récupère les épisodes"""
        episodes = []
        
        # L'URL change avec la saison
        url = f"{self.base_url}/ajax/season/episodes/{series_id}?season={season_num}"
        data = await fetch_page(url, self.headers)
        
        if data:
            soup = BeautifulSoup(data, 'lxml')
            ep_items = soup.find_all('a', class_='episode')
            
            for ep in ep_items:
                ep_num = ep.get('data-num', '')
                ep_title = ep.get('title', '')
                ep_id = ep.get('data-id', '')
                
                episodes.append(Episode(
                    number=int(ep_num) if ep_num.isdigit() else 0,
                    title=ep_title,
                    id=ep_id
                ))
        
        return episodes
    
    async def _get_movie_sources(self, soup: BeautifulSoup, movie_id: str) -> List[VideoSource]:
        """Récupère les sources d'un film"""
        sources = []
        
        # Chercher les iframes ou les liens directs
        watch_div = soup.find('div', class_='watch')
        if watch_div:
            iframes = watch_div.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src', '')
                if src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    sources.append(VideoSource(
                        url=src,
                        type=SourceType.IFRAME,
                        referer=self.base_url
                    ))
        
        return sources
    
    async def get_episode_sources(self, content_id: str, episode_id: str) -> List[VideoSource]:
        """Récupère les sources d'un épisode"""
        sources = []
        
        url = f"{self.base_url}/ajax/episode/sources/{episode_id}"
        data = await fetch_json(url, self.headers)
        
        if data and 'data' in data:
            for src in data['data']:
                link = src.get('link', '')
                if link:
                    sources.append(VideoSource(
                        url=link,
                        type=SourceType.IFRAME,
                        referer=self.base_url
                    ))
        
        return sources

class LookMovieScraper(BaseScraper):
    """Scraper pour LookMovie"""
    
    def __init__(self):
        super().__init__("https://lookmovie2.to", "LookMovie", "en")
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche sur LookMovie"""
        search_url = f"{self.base_url}/api/v1/movies/search/?q={quote(query)}"
        data = await fetch_json(search_url, self.headers)
        
        results = []
        
        if data and 'results' in data:
            for item in data['results'][:limit]:
                results.append({
                    'id': str(item.get('id', '')),
                    'title': item.get('title', ''),
                    'url': f"{self.base_url}/movies/view/{item.get('slug', '')}",
                    'poster': item.get('poster', ''),
                    'year': str(item.get('year', '')),
                    'type': 'movie',
                    'source': self.site_name
                })
        
        # Chercher aussi dans les séries
        series_url = f"{self.base_url}/api/v1/shows/search/?q={quote(query)}"
        series_data = await fetch_json(series_url, self.headers)
        
        if series_data and 'results' in series_data:
            for item in series_data['results'][:limit]:
                results.append({
                    'id': str(item.get('id', '')),
                    'title': item.get('title', ''),
                    'url': f"{self.base_url}/shows/view/{item.get('slug', '')}",
                    'poster': item.get('poster', ''),
                    'year': str(item.get('year', '')),
                    'type': 'series',
                    'source': self.site_name
                })
        
        return results[:limit]
    
    async def get_details(self, content_id: str, content_type: str = "movie") -> Optional[ScraperResult]:
        """Récupère les détails"""
        if content_type == "movie":
            return await self._get_movie_details(content_id)
        else:
            return await self._get_series_details(content_id)
    
    async def _get_movie_details(self, movie_id: str) -> Optional[ScraperResult]:
        """Récupère les détails d'un film"""
        api_url = f"{self.base_url}/api/v1/movies/view/{movie_id}"
        data = await fetch_json(api_url, self.headers)
        
        if not data:
            return None
        
        movie_data = data.get('data', {})
        
        result = ScraperResult(
            title=movie_data.get('title', ''),
            id=movie_id,
            type="movie",
            description=movie_data.get('description', ''),
            poster=movie_data.get('poster', ''),
            banner=movie_data.get('background', ''),
            release_year=str(movie_data.get('year', '')),
            duration=f"{movie_data.get('duration', '')} min",
            genres=movie_data.get('genres', []),
            rating=str(movie_data.get('rating', '')),
            source_site=self.site_name,
            source_url=f"{self.base_url}/movies/view/{movie_data.get('slug', '')}"
        )
        
        # Récupérer les sources
        result.sources = await self._get_lookmovie_sources(movie_id, "movie")
        
        return result
    
    async def _get_series_details(self, series_id: str) -> Optional[ScraperResult]:
        """Récupère les détails d'une série"""
        api_url = f"{self.base_url}/api/v1/shows/view/{series_id}"
        data = await fetch_json(api_url, self.headers)
        
        if not data:
            return None
        
        series_data = data.get('data', {})
        
        result = ScraperResult(
            title=series_data.get('title', ''),
            id=series_id,
            type="series",
            description=series_data.get('description', ''),
            poster=series_data.get('poster', ''),
            banner=series_data.get('background', ''),
            release_year=str(series_data.get('year', '')),
            genres=series_data.get('genres', []),
            rating=str(series_data.get('rating', '')),
            source_site=self.site_name,
            source_url=f"{self.base_url}/shows/view/{series_data.get('slug', '')}"
        )
        
        # Récupérer les saisons
        seasons_data = series_data.get('seasons', [])
        seasons = []
        
        for season in seasons_data:
            season_num = season.get('season_number', 0)
            episodes_data = season.get('episodes', [])
            episodes = []
            
            for ep in episodes_data:
                episodes.append(Episode(
                    number=ep.get('episode_number', 0),
                    title=ep.get('title', f"Episode {ep.get('episode_number', 0)}"),
                    id=str(ep.get('id', ''))
                ))
            
            seasons.append(Season(
                number=season_num,
                title=season.get('title', f"Season {season_num}"),
                id=str(season.get('id', '')),
                episodes=episodes,
                episode_count=len(episodes)
            ))
        
        result.seasons = seasons
        result.season_count = len(seasons)
        
        return result
    
    async def _get_lookmovie_sources(self, content_id: str, content_type: str) -> List[VideoSource]:
        """Récupère les sources vidéo"""
        sources = []
        
        # LookMovie utilise des streams HLS protégés
        # Il faut récupérer le token d'accès
        access_url = f"{self.base_url}/api/v1/{content_type}/access/{content_id}"
        data = await fetch_json(access_url, self.headers)
        
        if data and 'data' in data:
            streams = data['data'].get('streams', [])
            for stream in streams:
                stream_url = stream.get('url', '')
                quality = stream.get('quality', 'unknown')
                
                if stream_url:
                    sources.append(VideoSource(
                        url=stream_url,
                        type=SourceType.HLS,
                        quality=VideoQuality(quality) if quality in [q.value for q in VideoQuality] else VideoQuality.UNKNOWN,
                        is_m3u8=True,
                        referer=self.base_url
                    ))
        
        return sources
    
    async def get_episode_sources(self, content_id: str, episode_id: str) -> List[VideoSource]:
        """Récupère les sources d'un épisode"""
        return await self._get_lookmovie_sources(episode_id, "episode")

class VidSrcScraper(BaseScraper):
    """Scraper pour VidSrc (multi-content)"""
    
    def __init__(self):
        super().__init__("https://vidsrc.to", "VidSrc", "multi")
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recherche sur VidSrc"""
        search_url = f"{self.base_url}/api/search/{quote(query)}"
        data = await fetch_json(search_url, self.headers)
        
        results = []
        
        if data and 'result' in data:
            for item in data['result'][:limit]:
                content_type = item.get('type', 'movie')
                results.append({
                    'id': item.get('id', ''),
                    'title': item.get('title', ''),
                    'url': f"{self.base_url}/{content_type}/{item.get('id', '')}",
                    'poster': item.get('poster', ''),
                    'year': str(item.get('year', '')),
                    'type': content_type,
                    'source': self.site_name
                })
        
        return results
    
    async def get_details(self, content_id: str, content_type: str = "movie") -> Optional[ScraperResult]:
        """Récupère les détails"""
        detail_url = f"{self.base_url}/api/{content_type}/{content_id}"
        data = await fetch_json(detail_url, self.headers)
        
        if not data or 'data' not in data:
            return None
        
        item_data = data['data']
        
        result = ScraperResult(
            title=item_data.get('title', ''),
            id=content_id,
            type=content_type,
            description=item_data.get('description', ''),
            poster=item_data.get('poster', ''),
            release_year=str(item_data.get('year', '')),
            genres=item_data.get('genres', []),
            source_site=self.site_name,
            source_url=f"{self.base_url}/{content_type}/{content_id}"
        )
        
        if content_type == "series":
            # Récupérer les saisons et épisodes
            seasons = []
            seasons_data = item_data.get('seasons', [])
            
            for season in seasons_data:
                season_num = season.get('number', 1)
                episodes_data = season.get('episodes', [])
                episodes = []
                
                for ep in episodes_data:
                    episodes.append(Episode(
                        number=ep.get('number', 0),
                        title=ep.get('title', f"Episode {ep.get('number', 0)}"),
                        id=str(ep.get('id', ''))
                    ))
                
                seasons.append(Season(
                    number=season_num,
                    title=f"Season {season_num}",
                    id=str(season.get('id', '')),
                    episodes=episodes,
                    episode_count=len(episodes)
                ))
            
            result.seasons = seasons
            result.season_count = len(seasons)
        else:
            # Sources directes pour les films
            sources_data = item_data.get('sources', [])
            for src in sources_data:
                result.sources.append(VideoSource(
                    url=src.get('url', ''),
                    type=SourceType.HLS if '.m3u8' in src.get('url', '') else SourceType.DIRECT,
                    is_m3u8='.m3u8' in src.get('url', ''),
                    referer=self.base_url
                ))
        
        return result
    
    async def get_episode_sources(self, content_id: str, episode_id: str) -> List[VideoSource]:
        """Récupère les sources d'un épisode"""
        sources = []
        
        api_url = f"{self.base_url}/api/episode/{episode_id}"
        data = await fetch_json(api_url, self.headers)
        
        if data and 'data' in data:
            sources_data = data['data'].get('sources', [])
            for src in sources_data:
                sources.append(VideoSource(
                    url=src.get('url', ''),
                    type=SourceType.HLS if '.m3u8' in src.get('url', '') else SourceType.IFRAME,
                    is_m3u8='.m3u8' in src.get('url', ''),
                    referer=self.base_url
                ))
        
        return sources
