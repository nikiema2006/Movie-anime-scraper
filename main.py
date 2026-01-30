"""
Universal Streaming Scraper API
API universelle pour scraper des animes, films et séries
"""

import os
import asyncio
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

from config import SITES_CONFIG, ContentType, Language, DEFAULT_SITES
from scrapers import (
    GogoanimeScraper, ZoroScraper, AnimeHeavenScraper, AnimeSamaScraper,
    SFlixScraper, FMoviesScraper, LookMovieScraper, VidSrcScraper
)

# ==================== MODÈLES PYDANTIC ====================

class SearchResult(BaseModel):
    id: str
    title: str
    url: str
    poster: str = ""
    type: str
    source: str
    year: str = ""

class VideoSourceResponse(BaseModel):
    url: str
    type: str
    quality: str = "unknown"
    language: str = "en"
    is_m3u8: bool = False
    referer: str = ""
    headers: Dict[str, str] = {}

class EpisodeResponse(BaseModel):
    number: int
    title: str
    id: str
    thumbnail: str = ""
    description: str = ""
    duration: str = ""
    release_date: str = ""
    sources: List[VideoSourceResponse] = []
    download_links: List[Dict[str, str]] = []

class SeasonResponse(BaseModel):
    number: int
    title: str
    id: str
    episode_count: int
    episodes: List[EpisodeResponse] = []

class ContentDetails(BaseModel):
    title: str
    original_title: str = ""
    id: str
    type: str
    description: str = ""
    poster: str = ""
    banner: str = ""
    rating: str = ""
    release_year: str = ""
    genres: List[str] = []
    status: str = ""
    duration: str = ""
    country: str = ""
    language: str = ""
    episode_count: int = 0
    episodes: List[EpisodeResponse] = []
    season_count: int = 0
    seasons: List[SeasonResponse] = []
    sources: List[VideoSourceResponse] = []
    alternative_titles: List[str] = []
    cast: List[str] = []
    director: str = ""
    studio: str = ""
    download_links: List[Dict[str, Any]] = []
    source_site: str = ""
    source_url: str = ""
    scraped_at: str = ""

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Terme de recherche")
    type: str = Field(default="all", description="Type: anime, movie, series, all")
    limit: int = Field(default=10, ge=1, le=50, description="Nombre max de résultats")
    sources: List[str] = Field(default=[], description="Sources spécifiques à utiliser")

class ApiResponse(BaseModel):
    success: bool
    message: str = ""
    data: Any = None
    sources_used: List[str] = []

# ==================== INSTANCES DES SCRAPERS ====================

scrapers = {
    # Animes
    "gogoanime": GogoanimeScraper(),
    "zoro": ZoroScraper(),
    "animeheaven": AnimeHeavenScraper(),
    "animesama": AnimeSamaScraper(),
    # Films/Séries
    "sflix": SFlixScraper(),
    "fmovies": FMoviesScraper(),
    "lookmovie": LookMovieScraper(),
    "vidsrc": VidSrcScraper(),
}

# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    print("🚀 Universal Scraper API démarré")
    print(f"📊 {len(scrapers)} scrapers disponibles")
    yield
    print("👋 Universal Scraper API arrêté")

# ==================== APP FASTAPI ====================

app = FastAPI(
    title="Universal Streaming Scraper API",
    description="""
    API universelle pour scraper des animes, films et séries depuis multiples sources.
    
    ## Sources supportées:
    
    ### 🎌 Animes
    - **Gogoanime** (EN) - anitaku.to
    - **Zoro/AniWatch** (EN) - aniwatch.to
    - **AnimeHeaven** (EN) - animeheaven.me
    - **AnimeSama** (FR) - anime-sama.fr
    
    ### 🎬 Films & Séries
    - **SFlix** (EN) - sflix.to
    - **FMovies** (EN) - fmovies.to
    - **LookMovie** (EN) - lookmovie2.to
    - **VidSrc** (MULTI) - vidsrc.to
    
    ## Fonctionnalités:
    - 🔍 Recherche multi-sources
    - 📋 Détails complets (titre, description, poster, genres...)
    - 🎞️ Sources vidéo (HLS, MP4, embeds)
    - 📥 Liens de téléchargement
    - 📺 Liste des épisodes/saisons
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ENDPOINTS ====================

@app.get("/", tags=["Root"])
async def root():
    """Page d'accueil de l'API"""
    return {
        "name": "Universal Streaming Scraper API",
        "version": "2.0.0",
        "description": "API pour scraper animes, films et séries",
        "docs": "/docs",
        "endpoints": {
            "search": "/api/search?q={query}&type={type}",
            "details": "/api/details/{source}/{content_id}?type={type}",
            "sources": "/api/sources/{source}/{content_id}?episode={episode_id}",
            "episode": "/api/episode/{source}/{content_id}/{episode_id}",
            "sources_list": "/api/sources",
            "health": "/health"
        },
        "scrapers_available": list(scrapers.keys())
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Vérification de l'état de l'API"""
    return {
        "status": "healthy",
        "scrapers": len(scrapers),
        "version": "2.0.0"
    }

@app.get("/api/sources", tags=["Sources"], response_model=List[Dict[str, Any]])
async def list_sources():
    """Liste toutes les sources disponibles"""
    sources = []
    for key, scraper in scrapers.items():
        sources.append({
            "id": key,
            "name": scraper.site_name,
            "base_url": scraper.base_url,
            "language": scraper.language,
            "types": ["anime"] if "anime" in key else (["movie", "series"] if key in ["sflix", "fmovies", "lookmovie"] else ["movie", "series", "anime"])
        })
    return sources

@app.get("/api/search", tags=["Search"], response_model=ApiResponse)
async def search_content(
    q: str = Query(..., min_length=1, description="Terme de recherche"),
    type: str = Query(default="all", description="Type: anime, movie, series, all"),
    limit: int = Query(default=10, ge=1, le=50, description="Nombre max de résultats"),
    source: Optional[str] = Query(default=None, description="Source spécifique (gogoanime, sflix, etc.)")
):
    """
    Recherche de contenu (anime, film, série)
    
    - **q**: Terme de recherche (ex: "Attack on Titan", "The Matrix")
    - **type**: Type de contenu (anime, movie, series, all)
    - **limit**: Nombre maximum de résultats (1-50)
    - **source**: Source spécifique (optionnel)
    """
    results = []
    sources_used = []
    
    # Déterminer quels scrapers utiliser
    scrapers_to_use = []
    
    if source and source in scrapers:
        scrapers_to_use = [(source, scrapers[source])]
    else:
        if type == "anime" or type == "all":
            scrapers_to_use.extend([
                ("gogoanime", scrapers["gogoanime"]),
                ("animeheaven", scrapers["animeheaven"]),
                ("animesama", scrapers["animesama"]),
            ])
        if type in ["movie", "series", "all"]:
            scrapers_to_use.extend([
                ("sflix", scrapers["sflix"]),
                ("lookmovie", scrapers["lookmovie"]),
                ("vidsrc", scrapers["vidsrc"]),
            ])
    
    # Lancer les recherches en parallèle
    async def search_with_scraper(name, scraper):
        try:
            return await scraper.search(q, limit)
        except Exception as e:
            print(f"Error with {name}: {e}")
            return []
    
    tasks = [search_with_scraper(name, scraper) for name, scraper in scrapers_to_use]
    search_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for (name, scraper), result in zip(scrapers_to_use, search_results):
        if isinstance(result, list):
            for item in result:
                item['source'] = name
            results.extend(result)
            if result:
                sources_used.append(name)
    
    # Limiter le nombre de résultats
    results = results[:limit]
    
    return ApiResponse(
        success=len(results) > 0,
        message=f"{len(results)} résultats trouvés" if results else "Aucun résultat",
        data=results,
        sources_used=sources_used
    )

@app.get("/api/details/{source}/{content_id}", tags=["Details"], response_model=ApiResponse)
async def get_details(
    source: str,
    content_id: str,
    type: Optional[str] = Query(default="movie", description="Type: movie, series, anime")
):
    """
    Récupère les détails complets d'un contenu
    
    - **source**: Source du contenu (gogoanime, sflix, etc.)
    - **content_id**: Identifiant du contenu
    - **type**: Type de contenu (movie, series, anime)
    """
    if source not in scrapers:
        raise HTTPException(status_code=400, detail=f"Source '{source}' non supportée. Sources: {list(scrapers.keys())}")
    
    scraper = scrapers[source]
    
    try:
        if hasattr(scraper, 'get_details'):
            # Certains scrapers nécessitent le type
            if source in ["sflix", "fmovies"]:
                result = await scraper.get_details(content_id, type)
            else:
                result = await scraper.get_details(content_id)
            
            if result:
                return ApiResponse(
                    success=True,
                    message="Détails récupérés avec succès",
                    data=result.to_dict(),
                    sources_used=[source]
                )
            else:
                return ApiResponse(
                    success=False,
                    message="Contenu non trouvé",
                    data=None,
                    sources_used=[source]
                )
        else:
            raise HTTPException(status_code=400, detail=f"Le scraper {source} ne supporte pas get_details")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/api/sources/{source}/{content_id}", tags=["Sources"], response_model=ApiResponse)
async def get_sources(
    source: str,
    content_id: str,
    episode_id: Optional[str] = Query(default=None, description="ID de l'épisode (pour les séries/animes)"),
    type: Optional[str] = Query(default="movie", description="Type: movie, series, anime")
):
    """
    Récupère les sources vidéo d'un contenu
    
    - **source**: Source du contenu
    - **content_id**: Identifiant du contenu
    - **episode_id**: ID de l'épisode (pour séries/animes)
    - **type**: Type de contenu
    """
    if source not in scrapers:
        raise HTTPException(status_code=400, detail=f"Source '{source}' non supportée")
    
    scraper = scrapers[source]
    
    try:
        if episode_id:
            # Récupérer les sources d'un épisode spécifique
            sources = await scraper.get_episode_sources(content_id, episode_id)
        elif type == "movie":
            # Pour les films, récupérer les détails puis les sources
            if source in ["sflix", "fmovies"]:
                details = await scraper.get_details(content_id, "movie")
            else:
                details = await scraper.get_details(content_id)
            sources = details.sources if details else []
        else:
            return ApiResponse(
                success=False,
                message="episode_id requis pour les séries/animes",
                data=None,
                sources_used=[source]
            )
        
        return ApiResponse(
            success=len(sources) > 0,
            message=f"{len(sources)} sources trouvées" if sources else "Aucune source",
            data=[s.to_dict() for s in sources],
            sources_used=[source]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/api/episode/{source}/{content_id}/{episode_id}", tags=["Episodes"], response_model=ApiResponse)
async def get_episode(
    source: str,
    content_id: str,
    episode_id: str
):
    """
    Récupère les sources vidéo d'un épisode spécifique
    
    - **source**: Source du contenu
    - **content_id**: Identifiant du contenu (série/anime)
    - **episode_id**: Identifiant de l'épisode
    """
    if source not in scrapers:
        raise HTTPException(status_code=400, detail=f"Source '{source}' non supportée")
    
    scraper = scrapers[source]
    
    try:
        sources = await scraper.get_episode_sources(content_id, episode_id)
        
        return ApiResponse(
            success=len(sources) > 0,
            message=f"{len(sources)} sources trouvées" if sources else "Aucune source",
            data=[s.to_dict() for s in sources],
            sources_used=[source]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/api/download/{source}/{content_id}", tags=["Download"], response_model=ApiResponse)
async def get_download_links(
    source: str,
    content_id: str,
    episode_id: Optional[str] = Query(default=None, description="ID de l'épisode")
):
    """
    Récupère les liens de téléchargement
    
    - **source**: Source du contenu
    - **content_id**: Identifiant du contenu
    - **episode_id**: ID de l'épisode (optionnel)
    """
    if source not in scrapers:
        raise HTTPException(status_code=400, detail=f"Source '{source}' non supportée")
    
    scraper = scrapers[source]
    
    try:
        if hasattr(scraper, 'get_download_links'):
            links = await scraper.get_download_links(content_id, episode_id)
            
            return ApiResponse(
                success=len(links) > 0,
                message=f"{len(links)} liens trouvés" if links else "Aucun lien",
                data=links,
                sources_used=[source]
            )
        else:
            return ApiResponse(
                success=False,
                message="Ce scraper ne supporte pas les liens de téléchargement",
                data=[],
                sources_used=[source]
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

# ==================== ENDPOINTS AVANCÉS ====================

@app.get("/api/multi-search", tags=["Advanced"], response_model=ApiResponse)
async def multi_search(
    q: str = Query(..., min_length=1),
    type: str = Query(default="all"),
    limit: int = Query(default=5, ge=1, le=20)
):
    """
    Recherche parallèle sur toutes les sources disponibles
    Plus lent mais plus complet
    """
    all_results = []
    sources_used = []
    
    async def search_single(name, scraper):
        try:
            results = await scraper.search(q, limit)
            for r in results:
                r['source'] = name
            return name, results
        except:
            return name, []
    
    # Lancer toutes les recherches en parallèle
    tasks = [search_single(name, scraper) for name, scraper in scrapers.items()]
    results = await asyncio.gather(*tasks)
    
    for name, result_list in results:
        if result_list:
            all_results.extend(result_list)
            sources_used.append(name)
    
    # Trier par pertinence (simple: titre contenant la requête)
    query_lower = q.lower()
    all_results.sort(key=lambda x: (
        0 if query_lower in x.get('title', '').lower() else 1,
        x.get('title', '')
    ))
    
    return ApiResponse(
        success=len(all_results) > 0,
        message=f"{len(all_results)} résultats de {len(sources_used)} sources",
        data=all_results[:limit * 3],
        sources_used=sources_used
    )

@app.get("/api/trending/{source}", tags=["Advanced"], response_model=ApiResponse)
async def get_trending(
    source: str,
    type: Optional[str] = Query(default="movie")
):
    """
    Récupère les contenus tendance (si supporté par la source)
    
    Sources supportées: lookmovie, vidsrc
    """
    if source not in scrapers:
        raise HTTPException(status_code=400, detail=f"Source '{source}' non supportée")
    
    # Pour l'instant, retourner une recherche vide ou utiliser des listes prédéfinies
    return ApiResponse(
        success=True,
        message="Utilisez /api/search pour rechercher du contenu",
        data=[],
        sources_used=[source]
    )

# ==================== POINT D'ENTRÉE ====================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("DEBUG", "false").lower() == "true"
    )
