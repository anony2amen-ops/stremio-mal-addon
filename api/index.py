import json, os, threading, urllib.parse,```llib.request
from http.server import BaseHTTPRequestHandler```om datetime import datetime, timedelta

# ---------- CONFIG & CACHE ----------
TMDB_BASE = "https://api.themovie```org/3"
CACHE_TTL  = timedelta(hours=3)
MOVIES     = []
CACHE_TIME = datetime.min
API_KEYS   = {}

# ---------- TMDB HELPERS -------------
def tmdb_json(endpoint: str, key: str, params: dict = None```    q = {"api_key": key, **(params or {})}
    url = f"{TMDB_BASE}/{endpoint}?{urllib.parse.urlencode(q)}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)

def fetch_malayalam(key: str):
    global MOVIES, CACHE_TIME
    today = datetime.utcnow().strftime("%Y-%m-%d")
    movies = []
    for page in range(1, 4):
        data = tmdb_json("discover/movie", key, {
            "with_original_language": "```,
            "sort_by": "release_date.desc",```          "release_date.lte": today,
            "region": "IN",
            "page": page,
        })
        for m in data.get("results", []):
            ext = tmdb_json(f"movie/{m['id']}/external_ids", key)
            imdb = ext.get("imdb_id")
            if imdb and imdb.startswith("tt"):
                movies.append({
                    "id": imdb,
                    "type": "movie",
                    "name":  m["title"],
                    "poster": f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else None,
                    "description": m.get("overview",""),
                    "releaseInfo": m.get("release_date",""),
                    "background": f"https://image.tmdb```g/t/p/w780{m['backdrop_path']}" if m.get("backdrop_path") else None,
                })
    MOVIES, CACHE_TIME = movies, datetime```cnow()

def ensure_cache(key: str):
    if datetime.utcnow() - CACHE_TIME > CACHE_TT```r not MOVIES:
        threading.Thread(target=fetch_malayalam, args=(key,), daemon=True).start()

# ---------- HTTP HANDLER with CORS -------------
class handler(BaseHTTPRequestHandler):

    def add_cors_headers(self):
        """Add CORS headers for Stremio compatibility"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def json(self, obj, code=200):
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.add_cors_headers()  # ← CRITICAL FIX!
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def html(self, html, code=200):
        self.send_response(code)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.add_cors_headers()  # ← CRITICAL FIX!
        self.end_headers()
        self.wfile.write(html.encode())

    # Handle OPTIONS requests (CORS preflight)
    def do_OPTIONS(self):
        self.send_response(200)
        self.add_cors_headers()
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", ""):
            self.home()
        elif path == "/manifest.json":
            self.manifest()
        elif path == "/catalog/movie/malayalam.json":
            self.catalog()
        elif path == "/refresh":
            self.refresh()
        elif path == "/configure":
            self.configure_form()
        else:
            self.send_error(404,"Not found")

    def do_POST(self):
        if self.path == "/configure":
            length = int(self.headers.get("Content-Length",0))
            body   = self.rfile.read(length).decode()
            key    = urllib.parse.parse_qs(body).get("api_key",[None])[0]
            if key and len(key)>=10:
                API_KEYS["default"] = key
                self.html("<h1>✅ Key saved!</h1><a href='/'>Home</a>")
            else:
                self.html("<h1>❌ Invalid key!</h1><a href='/configure'>Try again```>",400)
        else:
            self.send_error(404,"Not found")

    def home(self):
        key_set = "✅ Ready```f "default" in API_KEYS else```️ API Key Required"
        movie_count = len(MOVIES)
        self.html(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Malayalam Movies Stremio Addon</title>```          <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .status {{ background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .btn {{ background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; 
                       border-radius: 5px; margin: 5px; display: inline-block; }}
                .manifest {{ background: #f0f0f0; padding: 10px; border-radius: 5px; font-family: monospace; 
                           word-break: break-all; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>🎬 Malayalam Movies Stremio Addon</h1>
            <div class="status">
                <p><strong>Status:</strong> {key_set}</p>
                <p><strong>Movies Cached:</strong> {movie_count}</p>
            </div>
            
            <div>
                <a href="/configure```lass="btn">⚙️ Configure API```y</a>
                <a href="/refresh" class="btn">```efresh Movies</a>
                <a href="/manifest.json" class="btn"```rget="_blank">📋 View Manifest</a>
            </div>
            
            <h3>📱 Install in Stremio:```3>
            <div class="manifest">
                https://{self.headers.get('host', 'your-addon.vercel.app')}/manifest.json
            </div>
            <p><small>Copy the URL above and paste it``` Stremio →```dons → Add Addon</small></p>
        </body>
        </html>
        """)

    def configure_form(self):
        self.html("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Configure TMDB API Key</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px; }
                .form-group { margin: 15px 0; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
                .info { background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <h1>⚙️ Configure TMDB API Key</h1>
            
            <div class="info">
                <h3>How to get your TMDB API Key:</h3>
                <ol>
                    <li>Go to <a href="https://www.themoviedb.org/```nup" target="_blank">themoviedb.org</a>```d create account</li>
                    <li>Visit <a href="https://www.themoviedb.org/settings```i" target="_blank">API Settings</a>```i>
                    <li>Copy your "API Key (v3 auth)" and paste below</li>
                </ol>
            </div>
            
            <form method="post">
                <div class="form-group">
                    <label for="api_key">TMDB```I Key:</label>
                    <input name="api_key" i```api_key" placeholder="Enter your```DB API key here" required>
                </div>
                <button type="submit">```ave Key</button>
            </form>
            
            <p><a href="/">← Back to Home</a></p>```      </body>
        </html>
        """)

    def manifest(self):
        # Enhanced manifest with proper Stremio fields```      self.json({
            "id": "org.malayalam.movies.```e",
            "version": "1.0.1",
            "name": "Malayalam Movies",
            "description": "Latest Malayalam movies available on OTT platforms in```dia",
            "resources": ["catalog"],
            "types": ["movie"],
            "catalogs": [{
                "type": "movie",
                "id": "malayalam",
                "name": "Malayalam Movies",
                "extra": [{"name": "skip", "isRequired": False}]
            }],
            "idPrefixes": ["tt"],
            "background": "https://images```splash.com/photo-1489599363012-b366b67c0fe5?w=1200&q=80"
        })

    def catalog(self):
        key = API_KEYS.get("default")
        if not key:
            return self.json({"metas": [], "message": "Configure TMDB API key first"})
        
        ensure_cache(key)
        self.json({"metas": MOVIES[:100]})

    def refresh(self):
        key = API_KEYS.get("default")
        if not key:
            return self.html("""
            <h1>⚠️ API Key Required</h1>
            <p>Please configure your TMDB API key first.</p>```          <a href="/configure">Configure API```y</a>
            """, 400)
        
        # Start background refresh
        threading.Thread(target=fetch_malayalam, args=(key,), daemon=True).start()
        
        self.html(f"""
        <h1>🔄 Refresh Started!</h1>
        <p>Malayalam movies are being loaded in the background.</p>
        <p>This will take about 1-2 minutes to complete.</p>
        <p><strong>Your current cache:</strong> {len(MOVIES)} movies</p>
        <a href="/">← Back to Home</a>```      <br><br>
        <a href="/catalog/movie/malayalam.json"```rget="_blank">Check Catalog JSON</a>
        """)
