import json, os, threading, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta

# ---------- CONFIG & CACHE ----------
TMDB_BASE = "https://api.themoviedb.org/3"
CACHE_TTL  = timedelta(hours=3)          # refresh every 3 h
MOVIES     = []                          # cached list
CACHE_TIME = datetime.min               # last refresh time
API_KEYS   = {}                          # in-memory user keys

# ---------- TMDB HELPERS -------------
def tmdb_json(endpoint: str, key: str, params: dict = None):
    q = {"api_key": key, **(params or {})}
    url = f"{TMDB_BASE}/{endpoint}?{urllib.parse.urlencode(q)}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)

def fetch_malayalam(key: str):
    global MOVIES, CACHE_TIME
    today = datetime.utcnow().strftime("%Y-%m-%d")
    movies = []
    for page in range(1, 4):                     # 3 pages ≈ 60 films
        data = tmdb_json("discover/movie", key, {
            "with_original_language": "ml",
            "sort_by": "release_date.desc",
            "release_date.lte": today,
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
                    "background": f"https://image.tmdb.org/t/p/w780{m['backdrop_path']}" if m.get("backdrop_path") else None,
                })
    MOVIES, CACHE_TIME = movies, datetime.utcnow()

def ensure_cache(key: str):
    if datetime.utcnow() - CACHE_TIME > CACHE_TTL or not MOVIES:
        threading.Thread(target=fetch_malayalam, args=(key,), daemon=True).start()

# ---------- HTTP HANDLER -------------
class handler(BaseHTTPRequestHandler):

    # ---- routing helpers ----
    def json(self, obj, code=200):
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def html(self, html, code=200):
        self.send_response(code)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    # ---- GET requests ----
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

    # ---- POST (save API key) ----
    def do_POST(self):
        if self.path == "/configure":
            length = int(self.headers.get("Content-Length",0))
            body   = self.rfile.read(length).decode()
            key    = urllib.parse.parse_qs(body).get("api_key",[None])[0]
            if key and len(key)>=10:
                API_KEYS["default"] = key
                self.html("<h1>✅ Key saved!</h1><a href='/'>Home</a>")
            else:
                self.html("<h1>❌ Invalid key!</h1><a href='/configure'>Try again</a>",400)
        else:
            self.send_error(404,"Not found")

    # ---- page handlers ----
    def home(self):
        key_set = "✅ Ready" if "default" in API_KEYS else "⚠️ API Key Required"
        self.html(f"""
        <h1>🎬 Malayalam Movies Addon</h1>
        <p>Status: {key_set}</p>
        <a href='/configure'>Configure API Key</a> ·
        <a href='/refresh'>Refresh</a> ·
        <a href='/manifest.json'>Manifest</a>
        """)

    def configure_form(self):
        self.html("""
        <h1>Enter TMDB API Key</h1>
        <form method='post'>
            <input name='api_key' placeholder='TMDB API Key' required style='width:300px'>
            <button>Save</button>
        </form>
        """)

    def manifest(self):
        self.json({
            "id":"org.malayalam.simple",
            "version":"1.0.0",
            "name":"Malayalam Movies (Pure Python)",
            "description":"Latest Malayalam movies available on OTT",
            "resources":["catalog"],
            "types":["movie"],
            "catalogs":[{"type":"movie","id":"malayalam","name":"Malayalam"}],
            "idPrefixes":["tt"]
        })

    def catalog(self):
        key = API_KEYS.get("default")
        if not key:
            return self.json({"metas":[],"message":"Configure TMDB API key first"})
        ensure_cache(key)
        self.json({"metas":MOVIES[:100]})    # serve up to 100 items

    def refresh(self):
        key = API_KEYS.get("default")
        if not key:
            return self.html("<h1>⚠️ Set API key first!</h1><a href='/configure'>Configure</a>",400)
        threading.Thread(target=fetch_malayalam, args=(key,), daemon=True).start()
        self.html("<h1>🔄 Refresh started!</h1><p>Come back in ~1 min.</p><a href='/'>Home</a>")
