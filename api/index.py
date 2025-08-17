from bottle import Bottle, run, request, response, abort
import json
import urllib.request
import urllib.parse
from datetime import datetime
import threading

# Create Bottle app
app = Bottle()

# In-memory storage
API_KEYS = {}
MOVIES_CACHE = []
CACHE_TIME = datetime.min

# TMDB Configuration
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Enable CORS for all routes
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With'

app.install(enable_cors)

# Helper function to call TMDB API
def tmdb_request(endpoint, api_key, params=None):
    """Make request to TMDB API"""
    if not params:
        params = {}
    params['api_key'] = api_key
    
    url = f"{TMDB_BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"TMDB API error: {e}")
        return None

def fetch_malayalam_movies(api_key):
    """Fetch Malayalam movies from TMDB"""
    global MOVIES_CACHE, CACHE_TIME
    
    print("🎬 Starting Malayalam movie fetch...")
    movies = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Fetch from multiple pages
    for page in range(1, 6):  # 5 pages = ~100 movies
        print(f"📄 Fetching page {page}...")
        
        params = {
            "with_original_language": "ml",
            "sort_by": "release_date.desc", 
            "release_date.lte": today,
            "region": "IN",
            "page": page
        }
        
        data = tmdb_request("discover/movie", api_key, params)
        if not data or not data.get("results"):
            break
            
        for movie in data["results"]:
            movie_id = movie.get("id")
            title = movie.get("title")
            
            if not movie_id or not title:
                continue
                
            # Get IMDb ID
            ext_data = tmdb_request(f"movie/{movie_id}/external_ids", api_key)
            if ext_data:
                imdb_id = ext_data.get("imdb_id")
                if imdb_id and imdb_id.startswith("tt"):
                    # Check if available on OTT (simplified check)
                    providers_data = tmdb_request(f"movie/{movie_id}/watch/providers", api_key)
                    if (providers_data and 
                        providers_data.get("results", {}).get("IN", {}).get("flatrate")):
                        
                        movies.append({
                            "id": imdb_id,
                            "type": "movie",
                            "name": title,
                            "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else None,
                            "description": movie.get("overview", ""),
                            "releaseInfo": movie.get("release_date", ""),
                            "background": f"https://image.tmdb.org/t/p/w780{movie['backdrop_path']}" if movie.get('backdrop_path') else None
                        })
    
    MOVIES_CACHE = movies
    CACHE_TIME = datetime.now()
    print(f"✅ Cached {len(movies)} Malayalam movies!")

@app.route('/')
def home():
    """Home page"""
    status = "✅ Ready" if "default" in API_KEYS else "⚠️ API Key Required"
    movie_count = len(MOVIES_CACHE)
    host = request.environ.get('HTTP_HOST', 'your-addon.vercel.app')
    
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
            .features {{ 
                display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 15px; margin: 20px 0; 
            }}
            .feature {{ 
                background: white; padding: 15px; border-radius: 8px; 
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .emoji {{ font-size: 24px; margin-right: 8px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎬 Malayalam Movies Stremio Addon</h1>
            <p style="color: #6c757d; font-size: 16px;">Powered by Bottle Framework - Ultra Lightweight & Fast</p>
        </div>
        
        <div class="status">
            <p><span class="emoji">📊</span><strong>Status:</strong> {status}</p>
            <p><span class="emoji">🎭</span><strong>Movies Cached:</strong> {movie_count}</p>
            <p><span class="emoji">⚡</span><strong>Framework:</strong> Bottle (Ultra Fast)</p>
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
        
        <div class="features">
            <div class="feature">
                <h4>🚀 Ultra Fast</h4>
                <p>Bottle framework with minimal overhead for lightning-fast responses</p>
            </div>
            <div class="feature">
                <h4>🎯 OTT Focus</h4>
                <p>Shows only Malayalam movies available on streaming platforms in India</p>
            </div>
            <div class="feature">
                <h4>📅 Latest First</h4>
                <p>Movies sorted by release date with newest releases appearing first</p>
            </div>
            <div class="feature">
                <h4>🔄 Auto Refresh</h4>
                <p>Smart caching with background updates to keep content fresh</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/configure', method='GET')
def configure_get():
    """Configuration page"""
    current_key = "✅ Configured" if "default" in API_KEYS else "❌ Not Set"
    
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
                font-size: 16px; transition: border-color 0.3s;
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
            ol {{ text-align: left; }}
            a {{ color: #007bff; text-decoration: none; font-weight: 600; }}
            a:hover {{ text-decoration: underline; }}
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
                           pattern="[a-zA-Z0-9]{{20,}}" required>
                </div>
                <button type="submit">💾 Save Configuration</button>
            </form>
            
            <p style="text-align: center; margin-top: 30px;">
                <a href="/">← Back to Home</a>
            </p>
        </div>
    </body>
    </html>
    """

@app.route('/configure', method='POST')
def configure_post():
    """Save API key"""
    api_key = request.forms.get('api_key', '').strip()
    
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
    
    # Test the API key
    test_data = tmdb_request("configuration", api_key)
    if not test_data:
        return """
        <html><body style="font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa;">
        <div style="background: #fff; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <h1 style="color: #dc3545;">❌ API Key Test Failed</h1>
            <p>The API key appears to be invalid or expired.</p>
            <a href="/configure" style="color: #28a745; text-decoration: none; font-weight: 600;">🔄 Try Again</a>
        </div>
        </body></html>
        """
    
    API_KEYS["default"] = api_key
    
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

@app.route('/manifest.json')
def manifest():
    """Stremio addon manifest"""
    response.content_type = 'application/json'
    
    return json.dumps({
        "id": "org.malayalam.bottle.movies",
        "version": "1.0.0",
        "name": "Malayalam Movies",
        "description": "Latest Malayalam movies available on OTT platforms in India - Ultra fast Bottle-powered addon",
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
    })

@app.route('/catalog/movie/malayalam.json')
def catalog():
    """Movie catalog for Stremio"""
    response.content_type = 'application/json'
    
    if "default" not in API_KEYS:
        return json.dumps({
            "metas": [], 
            "message": "Please configure your TMDB API key first at the addon homepage"
        })
    
    # Return cached movies (limit to first 150 for performance)
    metas = MOVIES_CACHE[:150] if MOVIES_CACHE else []
    
    return json.dumps({
        "metas": metas,
        "cacheMaxAge": 3600  # Cache for 1 hour
    })

@app.route('/refresh')
def refresh():
    """Refresh movie catalog"""
    if "default" not in API_KEYS:
        return """
        <html><body style="font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa;">
        <div style="background: #fff; padding: 30px; border-radius: 12px; display: inline-block;">
            <h1 style="color: #ffc107;">⚠️ API Key Required</h1>
            <p>Please configure your TMDB API key first.</p>
            <a href="/configure" style="color: #007bff; text-decoration: none; font-weight: 600;">⚙️ Configure API Key</a>
        </div>
        </body></html>
        """
    
    # Start background refresh
    api_key = API_KEYS["default"]
    threading.Thread(target=fetch_malayalam_movies, args=(api_key,), daemon=True).start()
    
    current_count = len(MOVIES_CACHE)
    
    return f"""
    <html>
    <head>
        <title>Refresh Started</title>
        <style>
            body {{ font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa; }}
            .container {{ background: #fff; padding: 40px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            .btn {{ background: #28a745; color: white; padding: 12px 24px; text-decoration: none; 
                  border-radius: 8px; margin: 10px; display: inline-block; font-weight: 600; }}
            .progress {{ background: #e9ecef; border-radius: 8px; padding: 15px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔄 Refresh Started!</h1>
            <p>Malayalam movies are being fetched from TMDB in the background.</p>
            
            <div class="progress">
                <p><strong>Current cache:</strong> {current_count} movies</p>
                <p><strong>Estimated time:</strong> 2-3 minutes</p>
                <p><strong>Progress:</strong> Fetching from 5 pages of TMDB results</p>
            </div>
            
            <p>The page will update automatically. You can check the catalog after a few minutes.</p>
            
            <a href="/" class="btn">🏠 Back to Home</a>
            <a href="/catalog/movie/malayalam.json" class="btn" target="_blank" style="background: #007bff;">📋 Check Catalog</a>
        </div>
        
        <script>
            // Auto refresh page every 30 seconds to show progress
            setTimeout(() => location.reload(), 30000);
        </script>
    </body>
    </html>
    """

# Handle CORS preflight requests
@app.route('/<path:path>', method='OPTIONS')
def options_handler(path=None):
    """Handle CORS preflight requests"""
    return ""

# Export application for Vercel
application = app

# For local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
