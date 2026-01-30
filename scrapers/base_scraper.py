"""
Base Scraper Class - Interface commune pour tous les scrapers
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from datetime import datetime

class VideoQuality(Enum):
    SD_360P = "360p"
    SD_480P = "480p"
    HD_720P = "720p"
    HD_1080P = "1080p"
    FHD_1440P = "1440p"
    UHD_4K = "4k"
    UNKNOWN = "unknown"

class SourceType(Enum):
    DIRECT = "direct"
    HLS = "hls"
    DASH = "dash"
    IFRAME = "iframe"
    STREAMTAPE = "streamtape"
    DOODSTREAM = "doodstream"
    MIXDROP = "mixdrop"
    UPSTREAM = "upstream"
    VIDCLOUD = "vidcloud"
    MP4UPLOAD = "mp4upload"
    FILEMOON = "filemoon"
    EMBED = "embed"

@dataclass
class VideoSource:
    """Représente une source vidéo"""
    url: str
    type: SourceType
    quality: VideoQuality = VideoQuality.UNKNOWN
    language: str = "en"
    is_m3u8: bool = False
    headers: Dict[str, str] = field(default_factory=dict)
    subtitles: List[Dict[str, str]] = field(default_factory=list)
    referer: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "type": self.type.value,
            "quality": self.quality.value,
            "language": self.language,
            "is_m3u8": self.is_m3u8,
            "headers": self.headers,
            "subtitles": self.subtitles,
            "referer": self.referer,
        }

@dataclass
class Episode:
    """Représente un épisode d'anime ou série"""
    number: int
    title: str
    id: str
    sources: List[VideoSource] = field(default_factory=list)
    thumbnail: str = ""
    description: str = ""
    duration: str = ""
    release_date: str = ""
    download_links: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "id": self.id,
            "sources": [s.to_dict() for s in self.sources],
            "thumbnail": self.thumbnail,
            "description": self.description,
            "duration": self.duration,
            "release_date": self.release_date,
            "download_links": self.download_links,
        }

@dataclass
class Season:
    """Représente une saison"""
    number: int
    title: str
    id: str
    episodes: List[Episode] = field(default_factory=list)
    episode_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "id": self.id,
            "episodes": [e.to_dict() for e in self.episodes],
            "episode_count": len(self.episodes) or self.episode_count,
        }

@dataclass
class ScraperResult:
    """Résultat complet d'un scrap"""
    title: str
    original_title: str = ""
    id: str = ""
    type: str = ""  # anime, movie, series
    description: str = ""
    poster: str = ""
    banner: str = ""
    rating: str = ""
    release_year: str = ""
    genres: List[str] = field(default_factory=list)
    status: str = ""  # ongoing, completed, upcoming
    duration: str = ""
    country: str = ""
    language: str = ""
    
    # Pour animes
    episodes: List[Episode] = field(default_factory=list)
    episode_count: int = 0
    
    # Pour séries
    seasons: List[Season] = field(default_factory=list)
    season_count: int = 0
    
    # Pour films
    sources: List[VideoSource] = field(default_factory=list)
    
    # Métadonnées
    alternative_titles: List[str] = field(default_factory=list)
    cast: List[str] = field(default_factory=list)
    director: str = ""
    studio: str = ""
    
    # Liens de téléchargement
    download_links: List[Dict[str, Any]] = field(default_factory=list)
    
    # Source
    source_site: str = ""
    source_url: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "title": self.title,
            "original_title": self.original_title,
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "poster": self.poster,
            "banner": self.banner,
            "rating": self.rating,
            "release_year": self.release_year,
            "genres": self.genres,
            "status": self.status,
            "duration": self.duration,
            "country": self.country,
            "language": self.language,
            "episode_count": len(self.episodes) if self.episodes else self.episode_count,
            "episodes": [e.to_dict() for e in self.episodes],
            "season_count": len(self.seasons) if self.seasons else self.season_count,
            "seasons": [s.to_dict() for s in self.seasons],
            "sources": [s.to_dict() for s in self.sources],
            "alternative_titles": self.alternative_titles,
            "cast": self.cast,
            "director": self.director,
            "studio": self.studio,
            "download_links": self.download_links,
            "source_site": self.source_site,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at,
        }
        return result
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

class BaseScraper(ABC):
    """Classe de base pour tous les scrapers"""
    
    def __init__(self, base_url: str, site_name: str, language: str = "en"):
        self.base_url = base_url.rstrip('/')
        self.site_name = site_name
        self.language = language
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recherche du contenu
        
        Args:
            query: Terme de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des résultats de recherche
        """
        pass
    
    @abstractmethod
    async def get_details(self, content_id: str) -> Optional[ScraperResult]:
        """
        Récupère les détails complets d'un contenu
        
        Args:
            content_id: Identifiant du contenu
            
        Returns:
            ScraperResult ou None si non trouvé
        """
        pass
    
    @abstractmethod
    async def get_episode_sources(self, content_id: str, episode_id: str) -> List[VideoSource]:
        """
        Récupère les sources vidéo d'un épisode
        
        Args:
            content_id: Identifiant du contenu
            episode_id: Identifiant de l'épisode
            
        Returns:
            Liste des sources vidéo
        """
        pass
    
    async def get_download_links(self, content_id: str, episode_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère les liens de téléchargement
        
        Args:
            content_id: Identifiant du contenu
            episode_id: Identifiant de l'épisode (optionnel)
            
        Returns:
            Liste des liens de téléchargement
        """
        return []
    
    def generate_id(self, title: str) -> str:
        """Génère un ID unique basé sur le titre"""
        return hashlib.md5(title.encode()).hexdigest()[:12]
    
    def clean_text(self, text: str) -> str:
        """Nettoie le texte extrait"""
        if not text:
            return ""
        return ' '.join(text.replace('\n', ' ').replace('\t', ' ').split())
    
    def extract_year(self, text: str) -> str:
        """Extrait l'année d'une chaîne"""
        import re
        match = re.search(r'\b(19|20)\d{2}\b', text)
        return match.group(0) if match else ""
    
    def parse_duration(self, text: str) -> str:
        """Parse la durée en minutes"""
        import re
        match = re.search(r'(\d+)\s*min', text.lower())
        if match:
            return f"{match.group(1)} min"
        match = re.search(r'(\d+)\s*h', text.lower())
        if match:
            return f"{match.group(1)}h"
        return text
    
    def get_quality_from_text(self, text: str) -> VideoQuality:
        """Déduit la qualité vidéo du texte"""
        text_lower = text.lower()
        if '4k' in text_lower or '2160p' in text_lower:
            return VideoQuality.UHD_4K
        elif '1440p' in text_lower or '2k' in text_lower:
            return VideoQuality.FHD_1440P
        elif '1080p' in text_lower or 'full hd' in text_lower or 'fhd' in text_lower:
            return VideoQuality.HD_1080P
        elif '720p' in text_lower or 'hd' in text_lower:
            return VideoQuality.HD_720P
        elif '480p' in text_lower:
            return VideoQuality.SD_480P
        elif '360p' in text_lower:
            return VideoQuality.SD_360P
        return VideoQuality.UNKNOWN
