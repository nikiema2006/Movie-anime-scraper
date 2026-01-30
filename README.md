# 🎬 Universal Streaming Scraper API

API universelle et puissante pour scraper des **animes**, **films** et **séries** depuis multiples sources de streaming.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## ✨ Fonctionnalités

- 🔍 **Recherche multi-sources** - Recherche parallèle sur plusieurs sites
- 📋 **Détails complets** - Titre, description, poster, genres, cast, etc.
- 🎞️ **Sources vidéo** - HLS, MP4, embeds (Streamtape, Doodstream, etc.)
- 📥 **Liens de téléchargement** - Extraction des liens directs
- 📺 **Épisodes & Saisons** - Gestion complète des séries et animes
- 🌍 **Multi-langues** - EN, FR, ES, IT, DE, JP
- ⚡ **Rapide** - Requêtes asynchrones avec fallback
- 🔧 **Facile à utiliser** - API REST avec documentation auto-générée

## 🌐 Sources Supportées

### 🎌 Animes
| Source | Langue | URL | Status |
|--------|--------|-----|--------|
| Gogoanime | 🇬🇧 EN | anitaku.to | ✅ |
| Zoro/AniWatch | 🇬🇧 EN | aniwatch.to | ✅ |
| AnimeHeaven | 🇬🇧 EN | animeheaven.me | ✅ |
| AnimeSama | 🇫🇷 FR | anime-sama.fr | ✅ |

### 🎬 Films & Séries
| Source | Langue | URL | Status |
|--------|--------|-----|--------|
| SFlix | 🇬🇧 EN | sflix.to | ✅ |
| FMovies | 🇬🇧 EN | fmovies.to | ✅ |
| LookMovie | 🇬🇧 EN | lookmovie2.to | ✅ |
| VidSrc | 🌍 MULTI | vidsrc.to | ✅ |

## 🚀 Déploiement Rapide

### Render (Recommandé)

1. Cliquez sur le bouton **"Deploy to Render"**
2. Connectez votre compte GitHub
3. Le déploiement se fait automatiquement

### Manuel

```bash
# Cloner le repo
git clone https://github.com/yourusername/universal-scraper-api.git
cd universal-scraper-api

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'API
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📚 Documentation API

Une fois déployée, la documentation est accessible à:
- **Swagger UI**: `https://votre-url/docs`
- **ReDoc**: `https://votre-url/redoc`

## 🔌 Endpoints

### Recherche
```http
GET /api/search?q=attack+on+titan&type=anime&limit=10
```

**Paramètres:**
- `q` (required): Terme de recherche
- `type` (optional): `anime`, `movie`, `series`, `all` (défaut: `all`)
- `limit` (optional): Nombre max de résultats (1-50, défaut: 10)
- `source` (optional): Source spécifique (`gogoanime`, `sflix`, etc.)

**Réponse:**
```json
{
  "success": true,
  "message": "15 résultats trouvés",
  "data": [
    {
      "id": "shingeki-no-kyojin",
      "title": "Attack on Titan",
      "url": "https://anitaku.to/category/shingeki-no-kyojin",
      "poster": "https://...",
      "type": "anime",
      "source": "gogoanime"
    }
  ],
  "sources_used": ["gogoanime", "zoro"]
}
```

### Détails
```http
GET /api/details/gogoanime/shingeki-no-kyojin?type=anime
```

**Réponse:**
```json
{
  "success": true,
  "data": {
    "title": "Attack on Titan",
    "id": "shingeki-no-kyojin",
    "type": "anime",
    "description": "Dans un monde où l'humanité vit entourée d'immenses murs...",
    "poster": "https://...",
    "release_year": "2013",
    "genres": ["Action", "Drama", "Fantasy"],
    "status": "completed",
    "episode_count": 87,
    "episodes": [
      {
        "number": 1,
        "title": "To You, in 2000 Years",
        "id": "shingeki-no-kyojin-episode-1",
        "sources": []
      }
    ],
    "source_site": "Gogoanime",
    "source_url": "https://anitaku.to/category/shingeki-no-kyojin"
  }
}
```

### Sources Vidéo
```http
GET /api/sources/gogoanime/shingeki-no-kyojin?episode_id=shingeki-no-kyojin-episode-1
```

**Réponse:**
```json
{
  "success": true,
  "data": [
    {
      "url": "https://streamtape.com/e/...",
      "type": "streamtape",
      "quality": "unknown",
      "language": "en",
      "is_m3u8": false,
      "referer": "https://anitaku.to/...",
      "headers": {},
      "subtitles": []
    },
    {
      "url": "https://.../playlist.m3u8",
      "type": "hls",
      "quality": "720p",
      "is_m3u8": true
    }
  ]
}
```

### Épisode Spécifique
```http
GET /api/episode/gogoanime/shingeki-no-kyojin/shingeki-no-kyojin-episode-1
```

### Liste des Sources
```http
GET /api/sources
```

### Multi-Search (Toutes les sources)
```http
GET /api/multi-search?q=demon+slayer&limit=5
```

## 💻 Exemples d'Utilisation

### cURL
```bash
# Recherche
curl "https://votre-api.com/api/search?q=one+piece&type=anime"

# Détails
curl "https://votre-api.com/api/details/gogoanime/one-piece"

# Sources vidéo
curl "https://votre-api.com/api/sources/gogoanime/one-piece?episode_id=one-piece-episode-1"
```

### Python
```python
import requests

# Recherche
response = requests.get("https://votre-api.com/api/search", params={
    "q": "Attack on Titan",
    "type": "anime",
    "limit": 10
})
results = response.json()

# Détails
details = requests.get("https://votre-api.com/api/details/gogoanime/shingeki-no-kyojin").json()

# Sources vidéo
sources = requests.get(
    "https://votre-api.com/api/episode/gogoanime/shingeki-no-kyojin/shingeki-no-kyojin-episode-1"
).json()
```

### JavaScript
```javascript
// Recherche
const search = async (query) => {
  const response = await fetch(`https://votre-api.com/api/search?q=${query}&type=anime`);
  return await response.json();
};

// Détails
const getDetails = async (source, id) => {
  const response = await fetch(`https://votre-api.com/api/details/${source}/${id}`);
  return await response.json();
};
```

## 🔧 Configuration Environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `PORT` | Port du serveur | `8000` |
| `DEBUG` | Mode debug | `false` |
| `PYTHON_VERSION` | Version Python | `3.11.0` |

## 📁 Structure du Projet

```
universal-scraper-api/
├── main.py                 # Point d'entrée FastAPI
├── config.py              # Configuration des sources
├── requirements.txt       # Dépendances
├── render.yaml           # Configuration Render
├── Procfile              # Configuration Heroku/Render
├── runtime.txt           # Version Python
├── README.md             # Documentation
└── scrapers/
    ├── __init__.py
    ├── base_scraper.py    # Classe de base
    ├── anime_scrapers.py  # Scrapers animes
    ├── movie_scrapers.py  # Scrapers films/séries
    └── utils.py           # Utilitaires
```

## 🛠️ Développement

### Ajouter un Nouveau Scraper

1. Créer une classe héritant de `BaseScraper`:

```python
from scrapers.base_scraper import BaseScraper, ScraperResult, Episode, VideoSource

class MonScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://monsite.com", "MonSite", "en")
    
    async def search(self, query: str, limit: int = 10):
        # Implémenter la recherche
        pass
    
    async def get_details(self, content_id: str):
        # Implémenter les détails
        pass
    
    async def get_episode_sources(self, content_id: str, episode_id: str):
        # Implémenter les sources
        pass
```

2. L'ajouter dans `main.py`:

```python
from scrapers import MonScraper

scrapers = {
    # ...
    "monsite": MonScraper(),
}
```

## ⚠️ Avertissement Légal

Cette API est fournie à des fins **éducatives uniquement**. Le scraping de contenu protégé par des droits d'auteur peut être illégal dans votre juridiction. L'utilisateur est responsable de:

- Respecter les lois locales sur le copyright
- Vérifier les conditions d'utilisation des sites scrapés
- Obtenir les autorisations nécessaires

Les développeurs ne sont pas responsables de l'utilisation abusive de cette API.

## 🤝 Contribution

Les contributions sont les bienvenues!

1. Fork le projet
2. Créez une branche (`git checkout -b feature/nouvelle-source`)
3. Committez vos changements (`git commit -am 'Ajout de X'`)
4. Push (`git push origin feature/nouvelle-source`)
5. Ouvrez une Pull Request

## 📄 License

MIT License - Voir [LICENSE](LICENSE)

## 🙏 Remerciements

- [FastAPI](https://fastapi.tiangolo.com/) pour le framework web
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) pour le parsing HTML
- [aiohttp](https://docs.aiohttp.org/) pour les requêtes asynchrones

---

⭐ **Star ce repo si tu le trouves utile!**
