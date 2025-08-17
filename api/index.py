from http.server import BaseHTTPRequestHandler
import json
import urllib.parse

# Simple storage
API_KEYS = {}

class handler(BaseHTTPRequestHandler):
    
    def add_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.add_cors_headers()
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        
        if path == "/" or path == "":
            self.home_page()
        elif path == "/manifest.json":
            self.manifest()
        elif path == "/catalog/movie/malayalam.json":
            self.catalog()
        elif path == "/configure":
            self.configure_page()
        elif path == "/refresh":
            self.refresh_page()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/configure":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode()
                
                # Parse form data
                parsed_data = urllib.parse.parse_qs(body)
                api_key = parsed_data.get("api_key", [None])[0]
                
                if api_key and len(api_key) > 10:
                    API_KEYS["default"] = api_key
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.add_cors_headers()
                    self.end_headers()
                    self.wfile.write(b"<h1>\\xe2\\x9c\\x85 API Key Saved!</h1><a href='/'>Home</a>")
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html")
                    self.add_cors_headers()
                    self.end_headers()
                    self.wfile.write(b"<h1>\\xe2\\x9d\\x8c Invalid API Key</h1><a href='/configure'>Try Again</a>")
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/html")
                self.add_cors_headers()
                self.end_headers()
                self.wfile.write(f"<h1>Error: {str(e)}</h1>".encode())
        else:
            self.send_error(404, "Not Found")

    def home_page(self):
        status = "Ready" if "default" in API_KEYS else "API Key Required"
        host = self.headers.get("Host", "your-addon.vercel.app")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Malayalam Movies Addon</title>
            <style>
                body {{ font-family: Arial; max-width: 600px; margin: 20px auto; padding: 20px; }}
                .status {{ background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .btn {{ background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; 
                       border-radius: 5px; margin: 5px; display: inline-block; }}
                .manifest {{ background: #f0f0f0; padding: 10px; border-radius: 5px; font-family: monospace; 
                           word-break: break-all; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>🎬 Malayalam Movies Addon (Pure Python)</h1>
            
            <div class="status">
                <p><strong>Status:</strong> {status}</p>
                <p><strong>Framework:</strong> Pure Python (Ultra Stable)</p>
            </div>
            
            <div>
                <a href="/configure" class="btn">Configure API Key</a>
                <a href="/refresh" class="btn">Refresh Movies</a>
                <a href="/manifest.json" class="btn" target="_blank">View Manifest</a>
            </div>
            
            <h3>Stremio Manifest URL:</h3>
            <div class="manifest">https://{host}/manifest.json</div>
            <p><small>Copy and paste in Stremio</small></p>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.add_cors_headers()
        self.end_headers()
        self.wfile.write(html.encode())

    def configure_page(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Configure API Key</title>
            <style>
                body { font-family: Arial; max-width: 500px; margin: 20px auto; padding: 20px; }
                .form-group { margin: 15px 0; }
                input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
                button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; }
                .info { background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <h1>Configure TMDB API Key</h1>
            
            <div class="info">
                <h3>How to get API Key:</h3>
                <ol>
                    <li>Go to <a href="https://www.themoviedb.org/signup" target="_blank">TMDB.org</a></li>
                    <li>Visit <a href="https://www.themoviedb.org/settings/api" target="_blank">API Settings</a></li>
                    <li>Copy "API Key (v3 auth)" and paste below</li>
                </ol>
            </div>
            
            <form method="post">
                <div class="form-group">
                    <input name="api_key" placeholder="Paste TMDB API key here" required>
                </div>
                <button type="submit">Save Key</button>
            </form>
            
            <p><a href="/">Back to Home</a></p>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.add_cors_headers()
        self.end_headers()
        self.wfile.write(html.encode())

    def manifest(self):
        manifest_data = {
            "id": "org.malayalam.pure.addon",
            "version": "1.0.0",
            "name": "Malayalam Movies (Pure Python)",
            "description": "Malayalam movies from TMDB - Pure Python for maximum stability",
            "resources": ["catalog"],
            "types": ["movie"],
            "catalogs": [{
                "type": "movie",
                "id": "malayalam",
                "name": "Malayalam Movies"
            }],
            "idPrefixes": ["tt"]
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.add_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(manifest_data).encode())

    def catalog(self):
        if "default" not in API_KEYS:
            catalog_data = {"metas": [], "message": "Configure API key first"}
        else:
            # Return test movie for now
            catalog_data = {
                "metas": [{
                    "id": "tt1234567",
                    "type": "movie",
                    "name": "Test Malayalam Movie",
                    "description": "Test movie - real TMDB fetching will be added next"
                }]
            }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.add_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(catalog_data).encode())

    def refresh_page(self):
        if "default" not in API_KEYS:
            html = """
            <h1>API Key Required</h1>
            <p>Please configure your TMDB API key first.</p>
            <a href="/configure">Configure API Key</a>
            """
        else:
            html = """
            <h1>Refresh Ready!</h1>
            <p>API key is configured. Real movie fetching will be added in next version.</p>
            <p>For now, catalog shows test movie to verify everything works.</p>
            <a href="/">Back to Home</a> | <a href="/catalog/movie/malayalam.json" target="_blank">View Catalog</a>
            """
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.add_cors_headers()
        self.end_headers()
        self.wfile.write(html.encode())
