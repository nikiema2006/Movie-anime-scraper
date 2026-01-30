"""
Configuration des sites de streaming supportés
Multi-langues: EN, FR, ES, IT, DE, JP
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class ContentType(Enum):
    ANIME = "anime"
    MOVIE = "movie"
    SERIES = "series"
    ALL = "all"

class Language(Enum):
    EN = "english"
    FR = "french"
    ES = "spanish"
    IT = "italian"
    DE = "german"
    JP = "japanese"
    MULTI = "multi"

@dataclass
class SiteConfig:
    name: str
    base_url: str
    content_types: List[ContentType]
    languages: List[Language]
    enabled: bool = True
    requires_proxy: bool = False
    cloudflare_protected: bool = False
    api_based: bool = False
    search_endpoint: str = ""
    details_endpoint: str = ""
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
            }

# Configuration des sites supportés
SITES_CONFIG: Dict[str, SiteConfig] = {
    # ===== ANIMES =====
    "gogoanime": SiteConfig(
        name="Gogoanime",
        base_url="https://anitaku.to",
        content_types=[ContentType.ANIME],
        languages=[Language.EN],
        cloudflare_protected=False,
        search_endpoint="/search.html?keyword={query}",
        details_endpoint="/category/{id}",
    ),
    
    "zoro": SiteConfig(
        name="Zoro/AniWatch",
        base_url="https://aniwatch.to",
        content_types=[ContentType.ANIME],
        languages=[Language.EN, Language.JP],
        cloudflare_protected=True,
        search_endpoint="/search?keyword={query}",
        details_endpoint="/anime/{id}",
    ),
    
    "animeheaven": SiteConfig(
        name="AnimeHeaven",
        base_url="https://animeheaven.me",
        content_types=[ContentType.ANIME],
        languages=[Language.EN, Language.JP],
        cloudflare_protected=False,
        search_endpoint="/search?q={query}",
        details_endpoint="/anime/{id}",
    ),
    
    "voiranime": SiteConfig(
        name="VoirAnime",
        base_url="https://v6.voiranime.com",
        content_types=[ContentType.ANIME],
        languages=[Language.FR],
        cloudflare_protected=True,
        search_endpoint="/?s={query}",
        details_endpoint="/anime/{id}",
    ),
    
    "animesama": SiteConfig(
        name="AnimeSama",
        base_url="https://anime-sama.fr",
        content_types=[ContentType.ANIME],
        languages=[Language.FR, Language.EN, Language.JP],
        cloudflare_protected=False,
        search_endpoint="/template-php/defaut/fetch.php?search={query}",
        api_based=True,
    ),
    
    # ===== FILMS & SÉRIES =====
    "fmovies": SiteConfig(
        name="FMovies",
        base_url="https://fmovies.to",
        content_types=[ContentType.MOVIE, ContentType.SERIES],
        languages=[Language.EN],
        cloudflare_protected=True,
        search_endpoint="/search?keyword={query}",
        details_endpoint="/movie/{id}",
    ),
    
    "sflix": SiteConfig(
        name="SFlix",
        base_url="https://sflix.to",
        content_types=[ContentType.MOVIE, ContentType.SERIES],
        languages=[Language.EN],
        cloudflare_protected=True,
        search_endpoint="/search/{query}",
        details_endpoint="/movie/{id}",
    ),
    
    "voirfilm": SiteConfig(
        name="VoirFilm",
        base_url="https://www.voirfilm.tv",
        content_types=[ContentType.MOVIE, ContentType.SERIES],
        languages=[Language.FR],
        cloudflare_protected=False,
        search_endpoint="/recherche?q={query}",
        details_endpoint="/film/{id}",
    ),
    
    "streamingcommunity": SiteConfig(
        name="StreamingCommunity",
        base_url="https://streamingcommunity.computer",
        content_types=[ContentType.MOVIE, ContentType.SERIES],
        languages=[Language.IT],
        cloudflare_protected=True,
        api_based=True,
        search_endpoint="/api/search?q={query}",
    ),
    
    "pelispedia": SiteConfig(
        name="Pelispedia",
        base_url="https://pelispedia.vip",
        content_types=[ContentType.MOVIE, ContentType.SERIES],
        languages=[Language.ES],
        cloudflare_protected=False,
        search_endpoint="/search/{query}",
    ),
    
    "kinox": SiteConfig(
        name="Kinox",
        base_url="https://kinox.to",
        content_types=[ContentType.MOVIE, ContentType.SERIES],
        languages=[Language.DE, Language.EN],
        cloudflare_protected=True,
        search_endpoint="/Search.html?q={query}",
    ),
    
    "lookmovie": SiteConfig(
        name="LookMovie",
        base_url="https://lookmovie2.to",
        content_types=[ContentType.MOVIE, ContentType.SERIES],
        languages=[Language.EN],
        cloudflare_protected=True,
        api_based=True,
        search_endpoint="/api/v1/movies/search/?q={query}",
    ),
    
    "vidsrc": SiteConfig(
        name="VidSrc",
        base_url="https://vidsrc.to",
        content_types=[ContentType.MOVIE, ContentType.SERIES, ContentType.ANIME],
        languages=[Language.MULTI],
        cloudflare_protected=False,
        api_based=True,
        search_endpoint="/api/search/{query}",
    ),
    
    "tmdb": SiteConfig(
        name="TMDB (Metadata)",
        base_url="https://api.themoviedb.org/3",
        content_types=[ContentType.MOVIE, ContentType.SERIES, ContentType.ANIME],
        languages=[Language.MULTI],
        api_based=True,
        enabled=True,
    ),
}

# Sites par défaut pour chaque type de contenu
DEFAULT_SITES = {
    ContentType.ANIME: ["gogoanime", "animeheaven", "animesama"],
    ContentType.MOVIE: ["sflix", "fmovies", "lookmovie"],
    ContentType.SERIES: ["sflix", "fmovies", "lookmovie"],
}

# Configuration des extracteurs vidéo
VIDEO_EXTRACTORS = {
    "streamtape": {
        "pattern": r"streamtape\.com/e/(\w+)",
        "extractor": "StreamtapeExtractor",
    },
    "doodstream": {
        "pattern": r"dood\.[^/]+/e/(\w+)",
        "extractor": "DoodStreamExtractor",
    },
    "mixdrop": {
        "pattern": r"mixdrop\.[^/]+/e/(\w+)",
        "extractor": "MixDropExtractor",
    },
    "upstream": {
        "pattern": r"upstream\.to/e/(\w+)",
        "extractor": "UpstreamExtractor",
    },
    "vidcloud": {
        "pattern": r"vidcloud\.[^/]+/e/(\w+)",
        "extractor": "VidCloudExtractor",
    },
    "mp4upload": {
        "pattern": r"mp4upload\.com/embed-(\w+)",
        "extractor": "Mp4UploadExtractor",
    },
    "yourupload": {
        "pattern": r"yourupload\.com/embed/(\w+)",
        "extractor": "YourUploadExtractor",
    },
    "sbembed": {
        "pattern": r"sbembed\.com/embed/(\w+)",
        "extractor": "SbEmbedExtractor",
    },
    "filemoon": {
        "pattern": r"filemoon\.sx/e/(\w+)",
        "extractor": "FileMoonExtractor",
    },
}

# Configuration Redis (caching)
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "password": None,
    "ttl": 3600,  # 1 heure
}

# Rate limiting
RATE_LIMIT = {
    "requests_per_minute": 60,
    "requests_per_hour": 1000,
}

# Timeouts
TIMEOUTS = {
    "connection": 10,
    "read": 30,
}
