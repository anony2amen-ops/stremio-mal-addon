from fastapi import FastAPI, BackgroundTasks, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import logging
import os
from pydantic import BaseModel
import hashlib
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global configuration storage (in production, use a database)
user_configs: Dict[str, Dict] = {}

# Global movie cache with user-specific data
user_movie_caches: Dict[str, List[Dict]] = {}

TMDB_BASE_URL = "https://api.themoviedb.org/3"

class ConfigRequest(BaseModel):
    tmdb_api_key: str

def generate_user_id(api_key: str) -> str:
    """Generate a unique user ID from API key"""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]

def get_user_config(user_id: str) -> Optional[Dict]:
    """Get user configuration by user ID"""
    return user_configs.get(user_id)

async def fetch_and_cache_movies_for_user(user_id: str, api_key: str):
    """Async function to fetch and cache Malayalam movies for a specific user"""
    logger.info(f"[CACHE] Fetching Malayalam OTT movies for user {user_id}")
    
    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(1, 50):  # Reduced from 1000 to 50 for better performance
            logger.info(f"[INFO] User {user_id}: Checking page {page}")
            
            params = {
                "api_key": api_key,
                "with_original_language": "ml",
                "sort_by": "release_date.desc",
                "release_date.lte": today,
                "region": "IN",
                "page": page
            }
            
            try:
                response = await client.get(f"{TMDB_BASE_URL}/discover/movie", params=params)
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                
                if not results:
                    logger.info(f"[INFO] User {user_id}: No more results on page {page}, stopping")
                    break
                
                # Process each movie
                for movie in results:
                    movie_id = movie.get("id")
                    title = movie.get("title")
                    if not movie_id or not title:
                        continue
                    
                    try:
                        # Check OTT availability
                        providers_url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers"
                        prov_response = await client.get(providers_url, params={"api_key": api_key})
                        prov_response.raise_for_status()
                        prov_data = prov_response.json()
                        
                        if "results" in prov_data and "IN" in prov_data["results"]:
                            if "flatrate" in prov_data["results"]["IN"]:
                                # Get IMDb ID
                                ext_url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
                                ext_response = await client.get(ext_url, params={"api_key": api_key})
                                ext_response.raise_for_status()
                                ext_data = ext_response.json()
                                imdb_id = ext_data.get("imdb_id")
                                
                                if imdb_id and imdb_id.startswith("tt"):
                                    movie["imdb_id"] = imdb_id
                                    final_movies.append(movie)
                    
                    except httpx.HTTPError as e:
                        logger.warning(f"[WARNING] User {user_id}: Failed to get details for movie {movie_id}: {e}")
                        continue
                
                # Add delay to respect rate limits
                await asyncio.sleep(0.1)
                
            except httpx.HTTPError as e:
                logger.error(f"[ERROR] User {user_id}: Page {page} failed: {e}")
                # Don't break, try next page
                continue
            except Exception as e:
                logger.error(f"[ERROR] User {user_id}: Unexpected error on page {page}: {e}")
                break
    
    # Deduplicate movies
    seen_ids = set()
    unique_movies = []
    for movie in final_movies:
        imdb_id = movie.get("imdb_id")
        if imdb_id and imdb_id not in seen_ids:
            seen_ids.add(imdb_id)
            unique_movies.append(movie)
    
    # Store in user-specific cache
    user_movie_caches[user_id] = unique_movies
    logger.info(f"[CACHE] Fetched {len(unique_movies)} Malayalam OTT movies for user {user_id} ✅")

def to_stremio_meta(movie: Dict) -> Optional[Dict]:
    """Convert TMDB movie to Stremio metadata format"""
    try:
        imdb_id = movie.get("imdb_id")
        title = movie.get("title")
        if not imdb_id or not title:
            return None
        
        return {
            "id": imdb_id,
            "type": "movie",
            "name": title,
            "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
            "description": movie.get("overview", ""),
            "releaseInfo": movie.get("release_date", ""),
            "background": f"https://image.tmdb.org/t/p/w780{movie['backdrop_path']}" if movie.get("backdrop_path") else None
        }
    except Exception as e:
        logger.error(f"[ERROR] to_stremio_meta failed: {e}")
        return None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page explaining the addon"""
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/configure", response_class=HTMLResponse) 
@app.post("/configure", response_class=HTMLResponse)
async def configure(request: Request, tmdb_api_key: str = Form(None)):
    """Configuration page for users to enter their TMDB API key"""
    if request.method == "GET":
        return templates.TemplateResponse("configure.html", {
            "request": request,
            "success": False,
            "error": None,
            "user_id": None
        })
    
    # POST request - process the form
    if not tmdb_api_key or not tmdb_api_key.strip():
        return templates.TemplateResponse("configure.html", {
            "request": request,
            "success": False,
            "error": "Please enter a valid TMDB API key",
            "user_id": None
        })
    
    try:
        # Validate API key by making a test request
        async with httpx.AsyncClient(timeout=10.0) as client:
            test_response = await client.get(
                f"{TMDB_BASE_URL}/configuration",
                params={"api_key": tmdb_api_key.strip()}
            )
            test_response.raise_for_status()
        
        # Generate user ID and store config
        user_id = generate_user_id(tmdb_api_key.strip())
        user_configs[user_id] = {
            "api_key": tmdb_api_key.strip(),
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"[CONFIG] New user configured: {user_id}")
        
        return templates.TemplateResponse("configure.html", {
            "request": request,
            "success": True,
            "error": None,
            "user_id": user_id
        })
        
    except httpx.HTTPError:
        return templates.TemplateResponse("configure.html", {
            "request": request,
            "success": False,
            "error": "Invalid TMDB API key. Please check your key and try again.",
            "user_id": None
        })
    except Exception as e:
        logger.error(f"[ERROR] Configuration failed: {e}")
        return templates.TemplateResponse("configure.html", {
            "request": request,
            "success": False,
            "error": "An error occurred while configuring. Please try again.",
            "user_id": None
        })

@app.get("/{user_id}/manifest.json")
async def get_manifest(user_id: str):
    """Get addon manifest for specific user"""
    config = get_user_config(user_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found. Please configure the addon first.")
    
    return {
        "id": f"org.malayalam.catalog.{user_id}",
        "version": "1.0.0",
        "name": "Malayalam Movies",
        "description": "Latest Malayalam Movies on OTT platforms",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [{
            "type": "movie",
            "id": "malayalam",
            "name": "Malayalam Movies"
        }],
        "idPrefixes": ["tt"],
        "behaviorHints": {
            "configurable": True,
            "configurationRequired": True
        }
    }

@app.get("/catalog/movie/{user_id}.json")
async def get_catalog(user_id: str):
    """Get movie catalog for specific user"""
    logger.info(f"[INFO] Catalog requested for user: {user_id}")
    
    config = get_user_config(user_id)
    if not config:
        logger.warning(f"[WARNING] No configuration found for user: {user_id}")
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    try:
        # Check if we have cached movies for this user
        if user_id not in user_movie_caches or not user_movie_caches[user_id]:
            logger.info(f"[INFO] No cached movies for user {user_id}, fetching...")
            # Start background task to fetch movies
            asyncio.create_task(fetch_and_cache_movies_for_user(user_id, config["api_key"]))
            return {"metas": []}
        
        # Convert cached movies to Stremio format
        movies = user_movie_caches[user_id]
        metas = []
        for movie in movies:
            meta = to_stremio_meta(movie)
            if meta:
                metas.append(meta)
        
        logger.info(f"[INFO] Returning {len(metas)} movies for user {user_id} ✅")
        return {"metas": metas}
        
    except Exception as e:
        logger.error(f"[ERROR] Catalog error for user {user_id}: {e}")
        return {"metas": []}

@app.get("/refresh/{user_id}")
async def refresh_user_cache(user_id: str, background_tasks: BackgroundTasks):
    """Refresh movie cache for specific user"""
    config = get_user_config(user_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    background_tasks.add_task(fetch_and_cache_movies_for_user, user_id, config["api_key"])
    return {"status": f"Cache refresh started for user {user_id}"}

@app.get("/health")
async def health_check():
    """Health check endpoint for cron jobs"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "configured_users": len(user_configs),
        "cached_users": len(user_movie_caches)
    }

@app.get("/stats")
async def get_stats():
    """Get addon statistics"""
    stats = {
        "total_users": len(user_configs),
        "users_with_cache": len(user_movie_caches),
        "cache_sizes": {uid: len(cache) for uid, cache in user_movie_caches.items()}
    }
    return stats

# Startup event to initialize any necessary components
@app.on_event("startup")
async def startup_event():
    logger.info("[STARTUP] Malayalam Movies Stremio Addon started")
    logger.info("[STARTUP] FastAPI server ready")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7000))
    uvicorn.run(app, host="0.0.0.0", port=port)
