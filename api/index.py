
import asyncio
import aiohttp
from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn
from typing import Dict, Optional
import threading
from urllib.parse import quote

app = FastAPI(title="Malayalam Movies Stremio Addon")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration storage (in-memory for Vercel compatibility)
config_storage: Dict[str, str] = {}
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Global movie cache
all_movies_cache = []
cache_lock = asyncio.Lock()

def get_api_key(user_id: str = "default") -> Optional[str]:
    """Get API key for a user (defaults to 'default' user)"""
    return config_storage.get(f"api_key_{user_id}")

def set_api_key(api_key: str, user_id: str = "default"):
    """Set API key for a user"""
    config_storage[f"api_key_{user_id}"] = api_key

async def fetch_and_cache_movies(api_key: str):
    """Fetch Malayalam OTT movies asynchronously"""
    global all_movies_cache

    if not api_key or api_key == "YOUR TMDB API KEY":
        print("[ERROR] No valid API key provided")
        return

    async with cache_lock:
        print("[CACHE] Fetching Malayalam OTT movies...")

        today = datetime.now().strftime("%Y-%m-%d")
        final_movies = []

        async with aiohttp.ClientSession() as session:
            for page in range(1, 500):  # Reduced from 1000 to 500 for better performance
                print(f"[INFO] Checking page {page}")
                params = {
                    "api_key": api_key,
                    "with_original_language": "ml",
                    "sort_by": "release_date.desc",
                    "release_date.lte": today,
                    "region": "IN",
                    "page": page
                }

                try:
                    async with session.get(f"{TMDB_BASE_URL}/discover/movie", params=params) as response:
                        data = await response.json()
                        results = data.get("results", [])

                        if not results:
                            print(f"[INFO] No more results at page {page}")
                            break

                        # Process movies concurrently
                        movie_tasks = []
                        for movie in results:
                            movie_id = movie.get("id")
                            title = movie.get("title")
                            if movie_id and title:
                                movie_tasks.append(process_movie(session, movie, api_key))

                        if movie_tasks:
                            processed_movies = await asyncio.gather(*movie_tasks, return_exceptions=True)
                            for movie_data in processed_movies:
                                if movie_data and not isinstance(movie_data, Exception):
                                    final_movies.append(movie_data)

                except Exception as e:
                    print(f"[ERROR] Page {page} failed: {e}")
                    break

        # Deduplicate
        seen_ids = set()
        unique_movies = []
        for movie in final_movies:
            imdb_id = movie.get("imdb_id")
            if imdb_id and imdb_id not in seen_ids:
                seen_ids.add(imdb_id)
                unique_movies.append(movie)

        all_movies_cache = unique_movies
        print(f"[CACHE] Fetched {len(all_movies_cache)} Malayalam OTT movies ✅")

async def process_movie(session: aiohttp.ClientSession, movie: dict, api_key: str) -> Optional[dict]:
    """Process a single movie to check OTT availability and get IMDb ID"""
    movie_id = movie.get("id")

    try:
        # Check OTT availability
        providers_url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers"
        async with session.get(providers_url, params={"api_key": api_key}) as prov_response:
            prov_data = await prov_response.json()

            if ("results" in prov_data and 
                "IN" in prov_data["results"] and 
                "flatrate" in prov_data["results"]["IN"]):

                # Get IMDb ID
                ext_url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
                async with session.get(ext_url, params={"api_key": api_key}) as ext_response:
                    ext_data = await ext_response.json()
                    imdb_id = ext_data.get("imdb_id")

                    if imdb_id and imdb_id.startswith("tt"):
                        movie["imdb_id"] = imdb_id
                        return movie
    except Exception as e:
        print(f"[ERROR] Processing movie {movie_id} failed: {e}")

    return None

def to_stremio_meta(movie: dict) -> Optional[dict]:
    """Convert movie data to Stremio metadata format"""
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
        print(f"[ERROR] to_stremio_meta failed: {e}")
        return None

@app.get("/")
async def root():
    """Root endpoint with information about the addon"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Malayalam Movies Stremio Addon</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { text-align: center; }
            .btn { background-color: #4CAF50; color: white; padding: 12px 20px; 
                  text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px; }
            .btn:hover { background-color: #45a049; }
            .info { background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Malayalam Movies Stremio Addon</h1>
            <p>Latest Malayalam Movies available on OTT platforms</p>

            <div class="info">
                <h3>Setup Instructions:</h3>
                <ol style="text-align: left;">
                    <li>Get your free TMDB API key from <a href="https://www.themoviedb.org/settings/api" target="_blank">themoviedb.org</a></li>
                    <li>Configure your API key using the link below</li>
                    <li>Install the addon in Stremio using the manifest URL</li>
                </ol>
            </div>

            <a href="/configure" class="btn">Configure API Key</a>
            <a href="/manifest.json" class="btn">View Manifest</a>
            <a href="/refresh" class="btn">Refresh Movies</a>

            <div class="info">
                <p><strong>Movies Cached:</strong> {movies_count}</p>
                <p><strong>Status:</strong> {status}</p>
            </div>
        </div>
    </body>
    </html>
    """.format(
        movies_count=len(all_movies_cache),
        status="Ready" if get_api_key() else "API Key Required"
    ))

@app.get("/configure")
async def configure_page():
    """Configuration page for API key"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Configure TMDB API Key</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input[type="text"] { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
            .btn { background-color: #4CAF50; color: white; padding: 12px 20px; border: none; 
                  border-radius: 4px; cursor: pointer; }
            .btn:hover { background-color: #45a049; }
            .success { color: green; font-weight: bold; }
            .error { color: red; font-weight: bold; }
            .info { background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>Configure TMDB API Key</h1>

        <div class="info">
            <h3>How to get your TMDB API Key:</h3>
            <ol>
                <li>Go to <a href="https://www.themoviedb.org/signup" target="_blank">TMDB</a> and create a free account</li>
                <li>Navigate to <a href="https://www.themoviedb.org/settings/api" target="_blank">API Settings</a></li>
                <li>Copy your "API Key (v3 auth)" and paste it below</li>
            </ol>
        </div>

        <form method="post" action="/configure">
            <div class="form-group">
                <label for="api_key">TMDB API Key:</label>
                <input type="text" id="api_key" name="api_key" required 
                       placeholder="Enter your TMDB API key here" />
            </div>

            <div class="form-group">
                <label for="user_id">User ID (optional):</label>
                <input type="text" id="user_id" name="user_id" value="default" 
                       placeholder="default" />
            </div>

            <button type="submit" class="btn">Save Configuration</button>
        </form>

        <p><a href="/">← Back to Home</a></p>
    </body>
    </html>
    """)

@app.post("/configure")
async def configure_api_key(api_key: str = Form(...), user_id: str = Form("default")):
    """Save API key configuration"""
    if not api_key or len(api_key) < 10:
        return HTMLResponse(content="""
        <html><body>
        <h1>Error</h1>
        <p style="color: red;">Invalid API key provided!</p>
        <a href="/configure">Try again</a>
        </body></html>
        """, status_code=400)

    set_api_key(api_key, user_id)

    return HTMLResponse(content="""
    <html>
    <head>
        <title>Configuration Saved</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
            .success { color: green; font-weight: bold; }
            .btn { background-color: #4CAF50; color: white; padding: 12px 20px; 
                  text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px; }
        </style>
    </head>
    <body>
        <h1>Configuration Saved!</h1>
        <p class="success">Your TMDB API key has been saved successfully.</p>
        <p>You can now refresh the movie catalog and use the addon.</p>

        <a href="/" class="btn">Go to Home</a>
        <a href="/refresh" class="btn">Refresh Movies Now</a>
    </body>
    </html>
    """)

@app.get("/manifest.json")
async def manifest():
    """Stremio addon manifest"""
    return JSONResponse({
        "id": "org.malayalam.catalog",
        "version": "2.0.0",
        "name": "Malayalam Movies OTT",
        "description": "Latest Malayalam Movies available on OTT platforms in India",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [{
            "type": "movie",
            "id": "malayalam",
            "name": "Malayalam Movies",
            "extra": [{"name": "skip", "isRequired": False}]
        }],
        "idPrefixes": ["tt"]
    })

@app.get("/catalog/movie/malayalam.json")
async def catalog():
    """Stremio catalog endpoint"""
    print("[INFO] Catalog requested")
    try:
        if not all_movies_cache:
            api_key = get_api_key()
            if api_key:
                print("[INFO] Cache empty, fetching movies...")
                await fetch_and_cache_movies(api_key)

        metas = [meta for meta in (to_stremio_meta(m) for m in all_movies_cache) if meta]
        print(f"[INFO] Returning {len(metas)} total movies ✅")
        return JSONResponse({"metas": metas})
    except Exception as e:
        print(f"[ERROR] Catalog error: {e}")
        return JSONResponse({"metas": []})

@app.get("/refresh")
async def refresh():
    """Refresh movie catalog"""
    api_key = get_api_key()
    if not api_key:
        return HTMLResponse(content="""
        <html><body>
        <h1>API Key Required</h1>
        <p>Please configure your TMDB API key first.</p>
        <a href="/configure">Configure API Key</a>
        </body></html>
        """, status_code=400)

    # Start background refresh
    asyncio.create_task(fetch_and_cache_movies(api_key))

    return HTMLResponse(content="""
    <html>
    <head>
        <title>Refresh Started</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
            .info { background-color: #e7f3ff; padding: 15px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>Refresh Started</h1>
        <div class="info">
            <p>Movie catalog refresh has been started in the background.</p>
            <p>This may take a few minutes to complete.</p>
        </div>
        <a href="/">← Back to Home</a>
    </body>
    </html>
    """)

@app.on_event("startup")
async def startup_event():
    """Initialize the app on startup"""
    print("[STARTUP] Malayalam Movies Stremio Addon starting...")
    api_key = get_api_key()
    if api_key and api_key != "YOUR TMDB API KEY":
        print("[STARTUP] API key found, pre-loading movies...")
        asyncio.create_task(fetch_and_cache_movies(api_key))
    else:
        print("[STARTUP] No API key configured. Please visit /configure")

# For Vercel deployment
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


# Export handler for Vercel
handler = app

