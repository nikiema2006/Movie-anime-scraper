"""
Universal Scraper Package
Supports: Anime, Movies, Series from multiple sources
"""

from .base_scraper import BaseScraper, ScraperResult, Episode, Season, VideoSource
from .anime_scrapers import GogoanimeScraper, ZoroScraper, AnimeHeavenScraper, AnimeSamaScraper
from .movie_scrapers import SFlixScraper, FMoviesScraper, LookMovieScraper, VidSrcScraper
from .utils import retry_request, bypass_cloudflare, extract_video_url

__all__ = [
    'BaseScraper',
    'ScraperResult', 
    'Episode',
    'Season',
    'VideoSource',
    'GogoanimeScraper',
    'ZoroScraper',
    'AnimeHeavenScraper',
    'AnimeSamaScraper',
    'SFlixScraper',
    'FMoviesScraper',
    'LookMovieScraper',
    'VidSrcScraper',
    'retry_request',
    'bypass_cloudflare',
    'extract_video_url',
]
