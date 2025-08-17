from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from typing import Dict, Optional

# Create FastAPI app
app = FastAPI(title="Malayalam Movies Stremio Addon")

# Add CORS middleware - CRITICAL for Stremio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (serverless compatible)
api_keys: Dict[str, str] = {}
movies_cache: list = []

# TMDB Configuration
TMDB_BASE_URL = "https://api.themoviedb.org/3"

async def tmdb_request(endpoint: str, api_key: str, params: dict = None):
    """Make async request to TMDB API"""
    if not params:
        params = {}
    params["api_key"] = api_key
    
    url = f"{TMDB_BASE_URL}/{endpoint}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"TMDB API error: {e}")
        return None

async def fetch_malayalam_movies(api_key: str) -> list:
    """Fetch Malayalam movies from TMDB - simplified for serverless"""
    movies = []
    
    try:
        # Fetch only first 2 pages to avoid timeout
        for page in range(1, 3):
            params = {
                "with_original_language": "ml",
                "sort_by": "release_date.desc", 
                "region": "IN",
                "page": page
            }
            
            data = await tmdb_request("discover/movie", api_key, params)
            if not data or not data.get("results"):
                break
                
            for movie in data["results"]:
                if not movie.get("id") or not movie.get("title"):
                    continue
                    
                # Get IMDb ID
                ext_data = await tmdb_request(f"movie/{movie['id']}/external_ids", api_key)
                if ext_data and ext_data.get("imdb_id"):
                    imdb_id = ext_data["imdb_id"]
                    if imdb_id.startswith("tt"):
                        movies.append({
                            "id": imdb_id,
                            "type": "movie",
                            "name": movie["title"],
                            "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else None,
                            "description": movie.get("overview", ""),
                            "releaseInfo": movie.get("release_date", ""),
                            "background": f"https://image.tmdb.org/t/p/w780{movie['backdrop_path']}" if movie.get('backdrop_path') else None
                        })
                        
        return movies[:50]  # Limit to 50 movies for performance
        
    except Exception as e:
        print(f"Error fetching movies: {e}")
        return []

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    status = "✅ Ready" if api_keys.get("default") else "⚠️ API Key Required"
    movie_count = len(movies_cache)
    host = request.headers.get("host", "your-addon.vercel.app")
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Malayalam Movies Stremio Addon</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 700px; margin: 20px auto; padding: 20px; background: #f8f9fa;
            }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .status {{ 
                background: linear-gradient(135deg, #e8f5e8, #d4edda); 
                padding: 20px; border-radius: 12px; margin: 20px 0; 
                border-left: 4px solid #28a745;
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
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎬 Malayalam Movies Stremio Addon</h1>
            <p style="color: #6c757d; font-size: 16px;">Powered by FastAPI - High Performance & Modern</p>
        </div>
        
        <div class="status">
            <p><strong>📊 Status:</strong> {status}</p>
            <p><strong>🎭 Movies Cached:</strong> {movie_count}</p>
            <p><strong>⚡ Framework:</strong> FastAPI (High Performance)</p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="/configure" class="btn">⚙️ Configure API Key</a>
            <a href="/refresh" class="btn">🔄 Refresh Movies</a>
            <a href="/manifest.json" class="btn" target="_blank">📋 View Manifest</a>
        </div>
        
        <div style="background: white; padding: 20px; border-radius: 12px; margin: 20px 0;">
            <h3>📱 Add to Stremio:</h3>
            <p>Copy this URL and paste in Stremio → Addons → Add Addon:</p>
            <div class="manifest">https://{host}/manifest.json</div>
        </div>
        
        <div style="background: white; padding: 20px; border-radius: 12px; margin: 20px 0;">
            <h4>🚀 FastAPI Benefits:</h4>
            <ul>
                <li>⚡ High performance async operations</li>
                <li>🎯 Built-in API documentation</li>
                <li>📝 Automatic request validation</li>
                <li>🔄 Modern Python async/await support</li>
            </ul>
        </div>
    </body>
    </html>
    """

@app.get("/configure", response_class=HTMLResponse)
async def configure_get():
    """Configuration page"""
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
                    <li>Click Save and then refresh your movies!</li>
                </ol>
            </div>
            
            <form method="post" action="/configure">
                <div class="form-group">
                    <label for="api_key">🔑 TMDB API Key:</label>
                    <input type="text" id="api_key" name="api_key" 
                           placeholder="Enter your TMDB API key (32+ characters)" 
                           required minlength="20">
                </div>
                <button type="submit">💾 Save Configuration</button>
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
    """Save API key configuration"""
    api_key = api_key.strip()
    
    if not api_key or len(api_key) < 15:
        return """
        <html><body style="font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa;">
        <div style="background: #fff; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <h1 style="color: #dc3545;">❌ Invalid API Key</h1>
            <p>Please enter a valid TMDB API key (at least 15 characters).</p>
            <a href="/configure" style="color: #28a745; text-decoration: none; font-weight: 600;">🔄 Try Again</a>
        </div>
        </body></html>
        """
    
    # Test the API key with a simple request
    test_data = await tmdb_request("configuration", api_key)
    if not test_data:
        return """
        <html><body style="font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa;">
        <div style="background: #fff; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <h1 style="color: #dc3545;">❌ API Key Test Failed</h1>
            <p>The API key appears to be invalid or there was a connection error.</p>
            <a href="/configure" style="color: #28a745; text-decoration: none; font-weight: 600;">🔄 Try Again</a>
        </div>
        </body></html>
        """
    
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
            <h1 style="color: #28a745;">✅ Configuration Saved Successfully!</h1>
            <p>Your TMDB API key is now configured and tested.</p>
            <p>You can now refresh movies to populate your catalog.</p>
            
            <a href="/" class="btn">🏠 Go to Home</a>
            <a href="/refresh" class="btn" style="background: #007bff;">🔄 Refresh Movies Now</a>
        </div>
    </body>
    </html>
    """

@app.get("/manifest.json")
async def manifest():
    """Stremio addon manifest"""
    return {
        "id": "org.malayalam.fastapi.movies",
        "version": "1.0.0",
        "name": "Malayalam Movies (FastAPI)",
        "description": "Latest Malayalam movies from TMDB - High performance FastAPI addon",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [{
            "type": "movie",
            "id": "malayalam",
            "name": "Malayalam Movies",
            "extra": [{"name": "skip", "isRequired": False}]
        }],
        "idPrefixes": ["tt"],
        "background": "https://images.unsplash.com/photo-1489599363012-b366b67c0fe5?w=1200&q=80",
        "logo": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=200&q=80"
    }

@app.get("/catalog/movie/malayalam.json")
async def catalog():
    """Movie catalog for Stremio"""
    if not api_keys.get("default"):
        return {
            "metas": [], 
            "message": "Please configure your TMDB API key first at the addon homepage"
        }
    
    # Return cached movies (limit to first 100 for performance)
    return {
        "metas": movies_cache[:100] if movies_cache else [],
        "cacheMaxAge": 3600  # Cache for 1 hour
    }

@app.get("/refresh", response_class=HTMLResponse)
async def refresh():
    """Refresh movie catalog"""
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
    
    # Fetch movies in background (simplified for serverless)
    try:
        api_key = api_keys["default"]
        new_movies = await fetch_malayalam_movies(api_key)
        movies_cache.clear()
        movies_cache.extend(new_movies)
        
        movie_count = len(movies_cache)
        
        return f"""
        <html>
        <head>
            <title>Refresh Complete</title>
            <style>
                body {{ font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa; }}
                .container {{ background: #fff; padding: 40px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .btn {{ background: #28a745; color: white; padding: 12px 24px; text-decoration: none; 
                      border-radius: 8px; margin: 10px; display: inline-block; font-weight: 600; }}
                .success {{ background: #d4edda; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔄 Refresh Complete!</h1>
                <div class="success">
                    <p><strong>✅ Successfully fetched {movie_count} Malayalam movies!</strong></p>
                    <p>Movies are now available in your Stremio catalog.</p>
                </div>
                
                <p>Your addon is ready to use with the latest Malayalam movies from TMDB.</p>
                
                <a href="/" class="btn">🏠 Back to Home</a>
                <a href="/catalog/movie/malayalam.json" class="btn" target="_blank" style="background: #007bff;">📋 View Catalog</a>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
        <div style="background: #fff; padding: 30px; border-radius: 12px; display: inline-block;">
            <h1 style="color: red;">❌ Refresh Failed</h1>
            <p>Error: {str(e)}</p>
            <a href="/" style="color: #4CAF50;">🏠 Back to Home</a>
        </div>
        </body></html>
        """

# Export the app for Vercel (CRITICAL!)
handler = app
