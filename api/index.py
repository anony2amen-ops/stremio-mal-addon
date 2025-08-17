import asyncio
import aiohttp
from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Dict, Optional
import json

# Create FastAPI app
app = FastAPI(title="Malayalam Movies Stremio Addon")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration storage (in-memory)
config_storage: Dict[str, str] = {}
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Global movie cache
all_movies_cache = []

def get_api_key(user_id: str = "default") -> Optional[str]:
    """Get API key for a user"""
    return config_storage.get(f"api_key_{user_id}")

def set_api_key(api_key: str, user_id: str = "default"):
    """Set API key for a user"""
    config_storage[f"api_key_{user_id}"] = api_key

async def fetch_movies_from_tmdb(api_key: str) -> list:
    """Fetch Malayalam movies from TMDB - simplified version"""
    if not api_key or api_key == "YOUR TMDB API KEY":
        return []
    
    movies = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            # Fetch only first 3 pages to avoid timeouts
            for page in range(1, 4):
                params = {
                    "api_key": api_key,
                    "with_original_language": "ml",
                    "sort_by": "release_date.desc",
                    "release_date.lte": today,
                    "region": "IN",
                    "page": page
                }
                
                async with session.get(f"{TMDB_BASE_URL}/discover/movie", params=params) as response:
                    if response.status != 200:
                        break
                    
                    data = await response.json()
                    results = data.get("results", [])
                    
                    if not results:
                        break
                    
                    for movie in results:
                        movie_id = movie.get("id")
                        title = movie.get("title")
                        
                        if not movie_id or not title:
                            continue
                        
                        # Get IMDb ID
                        try:
                            ext_url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
                            async with session.get(ext_url, params={"api_key": api_key}) as ext_response:
                                if ext_response.status == 200:
                                    ext_data = await ext_response.json()
                                    imdb_id = ext_data.get("imdb_id")
                                    
                                    if imdb_id and imdb_id.startswith("tt"):
                                        movie["imdb_id"] = imdb_id
                                        movies.append(movie)
                        except:
                            continue
                            
    except Exception as e:
        print(f"Error fetching movies: {e}")
        return []
    
    return movies

def to_stremio_meta(movie: dict) -> Optional[dict]:
    """Convert movie data to Stremio format"""
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
    except:
        return None

@app.get("/")
async def home():
    """Home page"""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Malayalam Movies Stremio Addon</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .container {{ text-align: center; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .btn {{ background-color: #4CAF50; color: white; padding: 12px 20px; 
                  text-decoration: none; border-radius: 6px; display: inline-block; margin: 10px; font-weight: bold; }}
            .btn:hover {{ background-color: #45a049; }}
            .info {{ background-color: #e8f4fd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2196F3; }}
            .status {{ background-color: #d4edda; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745; }}
            h1 {{ color: #333; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 Malayalam Movies Stremio Addon</h1>
            <p style="font-size: 18px; color: #666;">Latest Malayalam Movies from TMDB</p>
            
            <div class="status">
                <p><strong>📊 Status:</strong> {'✅ Ready' if get_api_key() else '⚠️ API Key Required'}</p>
                <p><strong>🎭 Movies Cached:</strong> {len(all_movies_cache)}</p>
            </div>
            
            <div class="info">
                <h3>🚀 Quick Setup:</h3>
                <ol style="text-align: left; max-width: 500px; margin: 0 auto;">
                    <li><strong>Get TMDB API Key:</strong> <a href="https://www.themoviedb.org/settings/api" target="_blank">Free at TMDB</a></li>
                    <li><strong>Configure:</strong> Click "Configure API Key" below</li>
                    <li><strong>Refresh:</strong> Let it load Malayalam movies</li>
                    <li><strong>Install:</strong> Add to Stremio using manifest</li>
                </ol>
            </div>
            
            <a href="/configure" class="btn">⚙️ Configure API Key</a>
            <a href="/manifest.json" class="btn">📋 View Manifest</a>
            <a href="/refresh" class="btn">🔄 Refresh Movies</a>
        </div>
    </body>
    </html>
    """)

@app.get("/configure")
async def configure_page():
    """Configuration page for API key"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Configure TMDB API Key</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 8px; font-weight: bold; color: #333; }
            input[type="text"] { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 6px; font-size: 16px; }
            input[type="text"]:focus { border-color: #4CAF50; outline: none; }
            .btn { background-color: #4CAF50; color: white; padding: 12px 30px; border: none; 
                  border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; }
            .btn:hover { background-color: #45a049; }
            .info { background-color: #e8f4fd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2196F3; }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚙️ Configure TMDB API Key</h1>
            
            <div class="info">
                <h3>📝 How to get your TMDB API Key:</h3>
                <ol>
                    <li>Create free account at <a href="https://www.themoviedb.org/signup" target="_blank"><strong>TMDB</strong></a></li>
                    <li>Go to <a href="https://www.themoviedb.org/settings/api" target="_blank"><strong>API Settings</strong></a></li>
                    <li>Copy your <strong>"API Key (v3 auth)"</strong> and paste below</li>
                    <li>Save and refresh movies!</li>
                </ol>
            </div>
            
            <form method="post" action="/configure">
                <div class="form-group">
                    <label for="api_key">🔑 TMDB API Key:</label>
                    <input type="text" id="api_key" name="api_key" required 
                           placeholder="Enter your TMDB API key here" />
                </div>
                
                <div class="form-group">
                    <label for="user_id">👤 User ID (optional):</label>
                    <input type="text" id="user_id" name="user_id" value="default" 
                           placeholder="default" />
                </div>
                
                <button type="submit" class="btn">💾 Save Configuration</button>
            </form>
            
            <p style="margin-top: 30px;"><a href="/">← Back to Home</a></p>
        </div>
    </body>
    </html>
    """)

@app.post("/configure")
async def configure_api_key(api_key: str = Form(...), user_id: str = Form("default")):
    """Save API key configuration"""
    if not api_key or len(api_key) < 10:
        return HTMLResponse(content="""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1 style="color: red;">❌ Invalid API Key</h1>
        <p>Please enter a valid TMDB API key.</p>
        <a href="/configure" style="color: #4CAF50;">🔄 Try again</a>
        </body></html>
        """, status_code=400)
    
    set_api_key(api_key, user_id)
    
    return HTMLResponse(content="""
    <html>
    <head><title>Configuration Saved</title>
    <style>
        body { font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; }
        .btn { background: #4CAF50; color: white; padding: 12px 20px; text-decoration: none; 
              border-radius: 6px; margin: 10px; display: inline-block; }
    </style>
    </head>
    <body>
        <div class="container">
            <h1>✅ Configuration Saved!</h1>
            <p>Your TMDB API key has been saved successfully.</p>
            <a href="/" class="btn">🏠 Home</a>
            <a href="/refresh" class="btn">🔄 Refresh Movies</a>
        </div>
    </body>
    </html>
    """)

@app.get("/manifest.json")
async def manifest():
    """Stremio addon manifest"""
    return JSONResponse({
        "id": "org.malayalam.movies.addon",
        "version": "2.0.0",
        "name": "Malayalam Movies",
        "description": "Latest Malayalam Movies from TMDB - sorted by release date",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [{
            "type": "movie",
            "id": "malayalam",
            "name": "Malayalam Movies",
            "extra": [{"name": "skip", "isRequired": False}]
        }],
        "idPrefixes": ["tt"],
        "background": "https://images.unsplash.com/photo-1489599363012-b366b67c0fe5?w=1200&q=80"
    })

@app.get("/catalog/movie/malayalam.json")
async def catalog():
    """Movie catalog for Stremio"""
    try:
        # Return cached movies if available
        if all_movies_cache:
            metas = [to_stremio_meta(m) for m in all_movies_cache]
            metas = [m for m in metas if m]  # Filter None
            return JSONResponse({"metas": metas[:100]})  # Limit to 100 movies
        
        # If no cache, return empty but suggest refresh
        return JSONResponse({
            "metas": [],
            "message": "No movies cached. Visit /refresh to load movies."
        })
        
    except Exception as e:
        print(f"Catalog error: {e}")
        return JSONResponse({"metas": []})

@app.get("/refresh")
async def refresh():
    """Refresh movie catalog"""
    api_key = get_api_key()
    
    if not api_key:
        return HTMLResponse(content="""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>⚠️ API Key Required</h1>
        <p>Please configure your TMDB API key first.</p>
        <a href="/configure" style="color: #4CAF50;">⚙️ Configure API Key</a>
        </body></html>
        """, status_code=400)
    
    # Fetch movies in background
    try:
        global all_movies_cache
        movies = await fetch_movies_from_tmdb(api_key)
        all_movies_cache = movies
        
        return HTMLResponse(content=f"""
        <html>
        <head><title>Refresh Complete</title>
        <style>
            body {{ font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; display: inline-block; }}
            .btn {{ background: #4CAF50; color: white; padding: 12px 20px; text-decoration: none; 
                  border-radius: 6px; margin: 10px; display: inline-block; }}
        </style>
        </head>
        <body>
            <div class="container">
                <h1>🔄 Refresh Complete!</h1>
                <p><strong>✅ Loaded {len(movies)} Malayalam movies successfully!</strong></p>
                <p>Movies are now available in your Stremio catalog.</p>
                <a href="/" class="btn">🏠 Home</a>
                <a href="/catalog/movie/malayalam.json" class="btn" target="_blank">📋 View Catalog</a>
            </div>
        </body>
        </html>
        """)
        
    except Exception as e:
        return HTMLResponse(content=f"""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1 style="color: red;">❌ Refresh Failed</h1>
        <p>Error: {str(e)}</p>
        <a href="/" style="color: #4CAF50;">🏠 Back to Home</a>
        </body></html>
        """, status_code=500)

# Export handler for Vercel
handler = app
