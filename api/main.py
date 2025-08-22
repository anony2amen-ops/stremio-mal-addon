from fastapi import FastAPI, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
import json
import os
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import time

# Create FastAPI app with optimized settings
app = FastAPI(
    title="Malayalam Movies Stremio Addon",
    version="1.0.0",
    description="High-performance Malayalam movies addon for Stremio"
)

# CORS middleware - CRITICAL for Stremio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (serverless compatible with persistence fallback)
api_keys: Dict[str, str] = {}
movies_cache: List[dict] = []
cache_timestamp: Optional[datetime] = None
refresh_status = {"in_progress": False, "last_update": None, "error": None}

# Configuration
TMDB_BASE_URL = "https://api.themoviedb.org/3"
CACHE_DURATION_HOURS = 12
MAX_MOVIES_PER_REQUEST = 20
REQUEST_DELAY = 0.25  # 4 requests per second to respect TMDB limits
MAX_PAGES = 3  # Limit for serverless constraints
VERCEL_TIMEOUT_BUFFER = 5  # seconds buffer before timeout

class TMDBClient:
    """Optimized TMDB API client with rate limiting"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.last_request_time = 0
        
    async def _rate_limited_request(self, url: str, params: dict) -> Optional[dict]:
        """Make rate-limited request to TMDB"""
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < REQUEST_DELAY:
            await asyncio.sleep(REQUEST_DELAY - elapsed)
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                self.last_request_time = time.time()
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            print(f"Timeout error for URL: {url}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"HTTP error {e.response.status_code} for URL: {url}")
            return None
        except Exception as e:
            print(f"Unexpected error for URL {url}: {e}")
            return None

    async def discover_movies(self, page: int = 1) -> Optional[dict]:
        """Discover Malayalam movies with optimized parameters"""
        params = {
            "api_key": self.api_key,
            "with_original_language": "ml",
            "sort_by": "release_date.desc",
            "region": "IN",
            "page": page,
            "include_adult": "false",
            "include_video": "false",
            "vote_count.gte": 1  # Filter out movies with no votes
        }
        
        url = f"{TMDB_BASE_URL}/discover/movie"
        return await self._rate_limited_request(url, params)
    
    async def get_external_ids(self, movie_id: int) -> Optional[dict]:
        """Get external IDs for a movie"""
        params = {"api_key": self.api_key}
        url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
        return await self._rate_limited_request(url, params)
    
    async def test_api_key(self) -> bool:
        """Test if API key is valid"""
        params = {"api_key": self.api_key}
        url = f"{TMDB_BASE_URL}/configuration"
        result = await self._rate_limited_request(url, params)
        return result is not None

async def fetch_malayalam_movies_optimized(api_key: str, start_time: float) -> List[dict]:
    """
    Optimized movie fetching with timeout awareness and batching
    """
    client = TMDBClient(api_key)
    movies = []
    processed_ids = set()
    
    try:
        # Fetch movies page by page with timeout checking
        for page in range(1, MAX_PAGES + 1):
            # Check if we're approaching timeout (keep 5 second buffer)
            elapsed = time.time() - start_time
            if elapsed > (45):  # 45 seconds for hobby plan with buffer
                print(f"Approaching timeout, stopping at page {page}")
                break
                
            print(f"Fetching page {page}...")
            discover_data = await client.discover_movies(page)
            
            if not discover_data or not discover_data.get("results"):
                print(f"No more results at page {page}")
                break
            
            # Process movies in batches to avoid memory issues
            movie_batch = []
            for movie in discover_data["results"][:MAX_MOVIES_PER_REQUEST]:
                if not movie.get("id") or movie["id"] in processed_ids:
                    continue
                    
                processed_ids.add(movie["id"])
                
                # Check timeout again
                if time.time() - start_time > 45:
                    break
                
                # Get IMDb ID
                ext_data = await client.get_external_ids(movie["id"])
                if ext_data and ext_data.get("imdb_id"):
                    imdb_id = ext_data["imdb_id"]
                    if imdb_id and imdb_id.startswith("tt"):
                        movie_obj = {
                            "id": imdb_id,
                            "type": "movie",
                            "name": movie.get("title", "Unknown"),
                            "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else None,
                            "description": movie.get("overview", "")[:200] + "..." if len(movie.get("overview", "")) > 200 else movie.get("overview", ""),
                            "releaseInfo": movie.get("release_date", ""),
                            "background": f"https://image.tmdb.org/t/p/w780{movie['backdrop_path']}" if movie.get('backdrop_path') else None,
                            "imdbRating": movie.get("vote_average", 0),
                            "genre": movie.get("genre_ids", [])
                        }
                        movie_batch.append(movie_obj)
                        
                        # Yield control periodically
                        if len(movie_batch) % 5 == 0:
                            await asyncio.sleep(0.01)
            
            movies.extend(movie_batch)
            print(f"Page {page} processed: {len(movie_batch)} movies added (total: {len(movies)})")
            
            # Limit total movies for performance
            if len(movies) >= 100:
                movies = movies[:100]
                break
                
    except Exception as e:
        print(f"Error in fetch_malayalam_movies_optimized: {e}")
        # Return whatever we managed to fetch
        
    # Sort by release date (newest first)
    movies.sort(key=lambda x: x.get("releaseInfo", ""), reverse=True)
    
    print(f"Final movie count: {len(movies)}")
    return movies

async def refresh_movies_background(api_key: str):
    """Background task to refresh movie catalog"""
    global movies_cache, cache_timestamp, refresh_status
    
    start_time = time.time()
    refresh_status["in_progress"] = True
    refresh_status["error"] = None
    
    try:
        print("Starting background movie refresh...")
        new_movies = await fetch_malayalam_movies_optimized(api_key, start_time)
        
        if new_movies:
            movies_cache.clear()
            movies_cache.extend(new_movies)
            cache_timestamp = datetime.now()
            refresh_status["last_update"] = cache_timestamp.isoformat()
            print(f"Successfully refreshed {len(new_movies)} movies in {time.time() - start_time:.2f} seconds")
        else:
            refresh_status["error"] = "No movies fetched"
            
    except Exception as e:
        print(f"Background refresh error: {e}")
        refresh_status["error"] = str(e)
    finally:
        refresh_status["in_progress"] = False

def is_cache_valid() -> bool:
    """Check if cache is still valid"""
    if not cache_timestamp or not movies_cache:
        return False
    return datetime.now() - cache_timestamp < timedelta(hours=CACHE_DURATION_HOURS)

# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "movies_cached": len(movies_cache),
        "cache_valid": is_cache_valid(),
        "api_configured": bool(api_keys.get("default"))
    }

@app.get("/ping")
async def ping():
    """Lightweight ping endpoint for keep-alive"""
    return {"pong": True, "timestamp": datetime.now().isoformat()}

@app.get("/status")
async def get_status():
    """Get refresh status"""
    return {
        "refresh_in_progress": refresh_status["in_progress"],
        "last_update": refresh_status["last_update"],
        "error": refresh_status["error"],
        "movies_count": len(movies_cache),
        "cache_valid": is_cache_valid(),
        "api_configured": bool(api_keys.get("default"))
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Enhanced home page with status"""
    api_configured = bool(api_keys.get("default"))
    movie_count = len(movies_cache)
    cache_valid = is_cache_valid()
    host = request.headers.get("host", "your-addon.vercel.app")
    
    status_color = "#28a745" if api_configured and cache_valid else "#ffc107"
    status_text = "✅ Ready" if api_configured and cache_valid else "⚠️ Needs Setup/Refresh"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Malayalam Movies Stremio Addon</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 700px; margin: 20px auto; padding: 20px; background: #f8f9fa;
            }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .status {{ 
                background: linear-gradient(135deg, #e8f5e8, #d4edda); 
                padding: 20px; border-radius: 12px; margin: 20px 0; 
                border-left: 4px solid {status_color};
            }}
            .btn {{ 
                background: linear-gradient(135deg, #28a745, #20c997); 
                color: white; padding: 12px 24px; text-decoration: none; 
                border-radius: 8px; margin: 8px; display: inline-block; 
                font-weight: 600; transition: transform 0.2s;
            }}
            .btn:hover {{ transform: translateY(-2px); }}
            .manifest {{ 
                background: #f8f9fa; padding: 15px; border-radius: 8px; 
                font-family: 'Monaco', 'Menlo', monospace; font-size: 14px;
                word-break: break-all; margin: 15px 0; border: 1px solid #dee2e6;
            }}
            .refresh-status {{ 
                font-size: 12px; color: #6c757d; margin-top: 10px;
                {'animation: pulse 1.5s infinite;' if refresh_status['in_progress'] else ''}
            }}
            @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} 100% {{ opacity: 1; }} }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎬 Malayalam Movies Stremio Addon</h1>
            <p style="color: #6c757d; font-size: 16px;">Optimized FastAPI - Production Ready</p>
        </div>
        
        <div class="status">
            <p><strong>📊 Status:</strong> {status_text}</p>
            <p><strong>🎭 Movies Cached:</strong> {movie_count}</p>
            <p><strong>⏰ Cache Valid:</strong> {'✅ Yes' if cache_valid else '❌ No'}</p>
            <p><strong>⚡ Framework:</strong> FastAPI (Optimized)</p>
            <div class="refresh-status">
                {'🔄 Refresh in progress...' if refresh_status['in_progress'] else 
                 f"Last update: {refresh_status['last_update'] or 'Never'}"}<br>
                {f"⚠️ Error: {refresh_status['error']}" if refresh_status['error'] else ''}
            </div>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="/configure" class="btn">⚙️ Configure API Key</a>
            <a href="/refresh" class="btn" {'style="opacity:0.5;pointer-events:none;"' if refresh_status['in_progress'] else ''}>
                🔄 {'Refreshing...' if refresh_status['in_progress'] else 'Refresh Movies'}
            </a>
            <a href="/manifest.json" class="btn" target="_blank">📋 View Manifest</a>
            <a href="/status" class="btn" target="_blank" style="background: #6c757d;">📈 Status API</a>
        </div>
        
        <div style="background: white; padding: 20px; border-radius: 12px; margin: 20px 0;">
            <h3>📱 Add to Stremio:</h3>
            <p>Copy this URL and paste in Stremio → Addons → Add Addon:</p>
            <div class="manifest">https://{host}/manifest.json</div>
        </div>
        
        <div style="background: white; padding: 20px; border-radius: 12px; margin: 20px 0;">
            <h4>🚀 Optimizations Applied:</h4>
            <ul>
                <li>⚡ Async operations with timeout handling</li>
                <li>🎯 TMDB rate limiting (4 requests/sec)</li>
                <li>📝 Background task processing</li>
                <li>🔄 Smart caching with 12-hour expiry</li>
                <li>🛡️ Error handling and recovery</li>
                <li>📊 Health monitoring endpoints</li>
            </ul>
        </div>
    </body>
    </html>
    """

@app.get("/configure", response_class=HTMLResponse)
async def configure_get():
    """Configuration page with better UX"""
    current_key = "✅ Configured" if api_keys.get("default") else "❌ Not Set"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Configure TMDB API Key</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 600px; margin: 20px auto; padding: 20px; background: #f8f9fa;
            }}
            .form-container {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            .form-group {{ margin: 20px 0; }}
            label {{ display: block; margin-bottom: 8px; font-weight: 600; color: #495057; }}
            input {{ 
                width: 100%; padding: 12px; border: 2px solid #dee2e6; border-radius: 8px; 
                font-size: 16px; transition: border-color 0.3s; box-sizing: border-box;
            }}
            input:focus {{ border-color: #28a745; outline: none; box-shadow: 0 0 0 3px rgba(40,167,69,0.1); }}
            button {{ 
                background: linear-gradient(135deg, #28a745, #20c997); color: white; 
                padding: 14px 28px; border: none; border-radius: 8px; font-size: 16px; 
                font-weight: 600; cursor: pointer; width: 100%; transition: transform 0.2s;
            }}
            button:hover {{ transform: translateY(-2px); }}
            .info {{ 
                background: linear-gradient(135deg, #e8f4fd, #cce7ff); 
                padding: 20px; border-radius: 8px; margin: 20px 0; 
                border-left: 4px solid #007bff;
            }}
            .status {{ 
                background: #f8f9fa; padding: 15px; border-radius: 8px; 
                text-align: center; margin: 20px 0; font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="form-container">
            <h1 style="text-align: center; color: #495057;">⚙️ Configure TMDB API Key</h1>
            
            <div class="status">
                Current Status: {current_key}
            </div>
            
            <div class="info">
                <h3>📝 How to get your TMDB API Key:</h3>
                <ol>
                    <li>Create a free account at <a href="https://www.themoviedb.org/signup" target="_blank">themoviedb.org</a></li>
                    <li>Verify your email and log in</li>
                    <li>Go to <a href="https://www.themoviedb.org/settings/api" target="_blank">Settings → API</a></li>
                    <li>Copy your <strong>"API Key (v3 auth)"</strong> and paste below</li>
                    <li>Click Save - the system will test your key automatically</li>
                    <li>Then refresh your movies to populate the catalog!</li>
                </ol>
                <p><strong>Note:</strong> Your API key is stored only in memory and reset on each deployment for security.</p>
            </div>
            
            <form method="post" action="/configure">
                <div class="form-group">
                    <label for="api_key">🔑 TMDB API Key:</label>
                    <input type="text" id="api_key" name="api_key" 
                           placeholder="Enter your TMDB API key (32 characters)" 
                           required minlength="20" maxlength="50">
                </div>
                <button type="submit">💾 Save & Test Configuration</button>
            </form>
            
            <p style="text-align: center; margin-top: 30px;">
                <a href="/" style="color: #007bff; text-decoration: none; font-weight: 600;">← Back to Home</a>
            </p>
        </div>
    </body>
    </html>
    """

@app.post("/configure", response_class=HTMLResponse)
async def configure_post(api_key: str = Form(...)):
    """Save and test API key configuration"""
    api_key = api_key.strip()
    
    if not api_key or len(api_key) < 15:
        return """
        <html><body style="font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa;">
        <div style="background: #fff; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <h1 style="color: #dc3545;">❌ Invalid API Key Format</h1>
            <p>Please enter a valid TMDB API key (at least 15 characters).</p>
            <a href="/configure" style="color: #28a745; text-decoration: none; font-weight: 600;">🔄 Try Again</a>
        </div>
        </body></html>
        """
    
    # Test the API key
    client = TMDBClient(api_key)
    api_valid = await client.test_api_key()
    
    if not api_valid:
        return """
        <html><body style="font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa;">
        <div style="background: #fff; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <h1 style="color: #dc3545;">❌ API Key Test Failed</h1>
            <p>The API key appears to be invalid, expired, or there was a connection error.</p>
            <p>Please verify your key and try again.</p>
            <a href="/configure" style="color: #28a745; text-decoration: none; font-weight: 600;">🔄 Try Again</a>
        </div>
        </body></html>
        """
    
    # Save the validated API key
    api_keys["default"] = api_key
    
    return """
    <html>
    <head>
        <title>Configuration Saved</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa; }
            .success { background: #fff; padding: 40px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .btn { background: #28a745; color: white; padding: 12px 24px; text-decoration: none; 
                  border-radius: 8px; margin: 10px; display: inline-block; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="success">
            <h1 style="color: #28a745;">✅ Configuration Saved & Tested!</h1>
            <p>Your TMDB API key is now configured and validated.</p>
            <p><strong>Next step:</strong> Refresh movies to populate your catalog.</p>
            <p>This may take up to 1 minute to complete.</p>
            
            <a href="/" class="btn">🏠 Go to Home</a>
            <a href="/refresh" class="btn" style="background: #007bff;">🔄 Refresh Movies Now</a>
        </div>
    </body>
    </html>
    """

@app.get("/manifest.json")
async def manifest():
    """Optimized Stremio addon manifest"""
    return {
        "id": "org.malayalam.optimized.movies",
        "version": "1.2.0",
        "name": "Malayalam Movies (Optimized)",
        "description": "Latest Malayalam movies from TMDB with high-performance caching and rate limiting",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [{
            "type": "movie",
            "id": "malayalam",
            "name": "Malayalam Movies",
            "extra": [
                {"name": "skip", "isRequired": False},
                {"name": "genre", "isRequired": False}
            ]
        }],
        "idPrefixes": ["tt"],
        "background": "https://images.unsplash.com/photo-1489599363012-b366b67c0fe5?w=1200&q=80",
        "logo": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=200&q=80",
        "behaviorHints": {
            "configurable": True,
            "configurationRequired": False
        }
    }

@app.get("/catalog/movie/malayalam.json")
async def catalog(skip: int = 0):
    """Optimized movie catalog with pagination"""
    if not api_keys.get("default"):
        return JSONResponse({
            "metas": [], 
            "cacheMaxAge": 300  # 5 minutes for error states
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    if not movies_cache:
        return JSONResponse({
            "metas": [],
            "cacheMaxAge": 300  # 5 minutes when empty
        }, headers={"Access-Control-Allow-Origin": "*"})
    
    # Pagination
    end_idx = skip + 100
    paginated_movies = movies_cache[skip:end_idx]
    
    cache_max_age = 3600 if is_cache_valid() else 300  # 1 hour if valid, 5 min if stale
    
    return JSONResponse({
        "metas": paginated_movies,
        "cacheMaxAge": cache_max_age
    }, headers={"Access-Control-Allow-Origin": "*"})

@app.get("/refresh", response_class=HTMLResponse)
async def refresh(background_tasks: BackgroundTasks):
    """Initiate movie refresh with background processing"""
    if not api_keys.get("default"):
        return """
        <html><body style="font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa;">
        <div style="background: #fff; padding: 30px; border-radius: 12px; display: inline-block;">
            <h1 style="color: #ffc107;">⚠️ API Key Required</h1>
            <p>Please configure your TMDB API key first.</p>
            <a href="/configure" style="color: #007bff; text-decoration: none; font-weight: 600;">⚙️ Configure API Key</a>
        </div>
        </body></html>
        """
    
    if refresh_status["in_progress"]:
        return """
        <html>
        <head>
            <title>Refresh In Progress</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa; }
                .container { background: #fff; padding: 40px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
                .spinner { animation: spin 1s linear infinite; display: inline-block; margin-right: 10px; }
                @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            </style>
        </head>
        <body>
            <div class="container">
                <h1><span class="spinner">🔄</span>Refresh In Progress</h1>
                <p>Please wait while we fetch the latest Malayalam movies...</p>
                <p>This page will refresh automatically every 5 seconds.</p>
                <p><a href="/status" target="_blank">📊 View Status API</a></p>
            </div>
        </body>
        </html>
        """
    
    # Start background refresh
    api_key = api_keys["default"]
    background_tasks.add_task(refresh_movies_background, api_key)
    
    return """
    <html>
    <head>
        <title>Refresh Started</title>
        <meta http-equiv="refresh" content="3;url=/">
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa; }
            .container { background: #fff; padding: 40px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .btn { background: #28a745; color: white; padding: 12px 24px; text-decoration: none; 
                  border-radius: 8px; margin: 10px; display: inline-block; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Refresh Started!</h1>
            <p>Movie refresh is now running in the background.</p>
            <p>You'll be redirected to the home page automatically.</p>
            <p>Check the status there for progress updates.</p>
            
            <a href="/" class="btn">🏠 Go to Home Now</a>
            <a href="/status" class="btn" target="_blank" style="background: #007bff;">📊 View Status</a>
        </div>
    </body>
    </html>
    """

# Cron endpoint for automated refresh
@app.post("/api/cron/refresh")
async def cron_refresh(background_tasks: BackgroundTasks):
    """Cron endpoint for automated daily refresh"""
    if not api_keys.get("default"):
        return {"error": "API key not configured", "status": "skipped"}
    
    if refresh_status["in_progress"]:
        return {"error": "Refresh already in progress", "status": "skipped"}
    
    # Check if cache is still relatively fresh (less than 6 hours old)
    if cache_timestamp and datetime.now() - cache_timestamp < timedelta(hours=6):
        return {"message": "Cache still fresh", "status": "skipped"}
    
    # Start background refresh
    api_key = api_keys["default"]
    background_tasks.add_task(refresh_movies_background, api_key)
    
    return {
        "message": "Background refresh started", 
        "status": "started",
        "timestamp": datetime.now().isoformat()
    }

# Export for Vercel - CRITICAL!
handler = app

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
