from http.```ver import Base```PRequestHandler
import json

# Simple in```mory storage
API_KEYS = {}

class handler```seHTTPRequestHandler):
    
    def add_cors```aders(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST```PTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def send_json```lf, data, code```0):
        self.send_response```de)
        self.send_header```ontent-Type", "application/json```        self.add_cors_headers()
        self.end_headers()
        self.wfile.```te(json.dumps(data).encode())

    def send_html```lf, html, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html```        self.add_cors_headers```        self.end_headers()
        self.wfile.write(html.encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.add_cors_headers()
        self.end_headers()

    def do_GET(self):
        path = self.path.```it("?")[0]
        
        if path == "/" or path == "":```          self.home_page()
        elif path == "/```ifest.json":
            self.manifest()
        elif path == "/catalog```vie/malayalam.json":
            self.catalog()
        elif path == "/configure```            self.configure_```e()
        elif path == "/refresh```            self.refresh_page()
        else:
            self.send_error```4, "Not Found")

    def do_POST(self):
        if self.path == "/```figure":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile```ad(length).decode()
                # Simple form```rsing
                if "api```y=" in body:
                    api```y = body.split("api_key=")[1].split("&")
                    api```y = api_key.replace("+```" ").replace("%20", " ")
                    if len(api_key) > 10:
                        API_KEYS["default"] = api_key
                        self.send_html```h1>✅ API Key```ved!</h1><a href='/'>```e</a>")
                    else:
                        self.send_html("<h1>❌ Invali```PI Key</h1><a href='/configure```ry Again</a>",```0)
                else:
                    self.send_html("<h1>❌ No API Key Foun```h1><a href='/configure'>Try```ain</a>", 400)
            except Exception as e:```              self.send_html(f"<h1>❌ Error```str(e)}</h1><a href='/configure'>``` Again</a>```500)
        else:
            self.send_error```4, "Not Found")

    def home_page(self):
        status = "```eady" if "```ault" in API_```S else "⚠️ API Key Required"
        host = self.headers.```("Host", "your-addon.vercel.app")
        
        html = f"""
        <!DOCTYPE html>```      <html>
        <head>
            <title>Malayalam Movies Addon```itle>
            <style>
                body {{ font-family: Arial; max-width: 600px; margin: ```x auto; padding: 20px; }}
                .status {{ background: #e8f5e8; padding: 15px; border-radius: 8px; margin: ```x 0; }}
                .btn {{ background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; 
                       border-radius: 5px; margin: 5px; display: inline```ock; }}
                .manifest {{ background: #f0f0f0; padding: 10px; border-radius: 5px; font```mily: monospace; ```                         wor```reak: break-all; margin```0px 0; }}
            </style>
        </head>
        <body>
            <h1>🎬 Malayalam Movies```remio Addon```1>
            
            <div class="status">
                <p```trong>Status:</strong> {status}</p>
            </div>
            
            <div>
                <a href="/```figure" class="btn">```Configure API Key</a>```              <a href="/refresh```lass="btn">```efresh Movies```>
                <a href="/manifest```on" class="```" target="_blank">📋 View Manifest```>
            </div>
            
            <h3>```tremio Manifest```L:</h3>
            <div```ass="manifest">```              https://{host}/manifest.json
            </div>
            <p```mall>Copy this URL and add it``` Stremio</small></p>
            
            <hr>
            <p><strong```rking Features:</strong></p>```          <ul>
                <li>✅ Basic```ges and CORS headers```i>
                <li>✅```nifest for```remio</li>
                <li>✅```I key configuration```i>
                <li>```ovie fetching (coming next```li>
            </ul>
        </body>
        </html>
        """
        self.send_html(html)

    def configure_page(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Configure API Key```itle>
            <style>
                body { font-family: Arial; max-width: 500px; margin: ```x auto; padding: 20px; }
                .form-group { margin: 15px 0; }
                label { display: block; margin-bottom: 5px; font```ight: bold; }
                input { width: 100%; padding: 10px; border: ``` solid #ddd; border-radius: 5px; }
                button```background: #4CAF50; color: white; padding:```px 20px; border: none```order-radius: 5px; }
                .info { background: #e```fd; padding: 15px; border-radius: 5px; margin: ```x 0; }
            </style>
        </head>
        <body>
            <h1>```Configure TMDB API Key```1>
            
            <div class="info">```              <h3>How to get API```y:</h3>
                <ol>
                    <li>Go to ```href="https://```.themoviedb.org/signup```arget="_blank">```B.org</a></li>
                    <li>Visit``` href="https```www.themoviedb.org/settings/api" target```blank">API Settings```></li>
                    <li>Copy```PI Key (v3 auth)" and paste below```i>
                </ol>
            </div>
            
            <form method="post```                <div class="form-group">
                    <label>```B API Key:</label>
                    <input name```pi_key" placeholder```aste your TMDB API key```re" require```                </div>
                <button type="submit">```ave Key</button>
            </form>
            
            <p>```href="/">← Back to Home```></p>
        </body>
        </html>
        """
        self.send_html(html)

    def manifest(self):
        manifest```ta = {
            "id": "org```layalam.simple.v2", 
            "version": "1.0.2",
            "name": "Malayalam Movies (Simple)",
            "description": "Malayalam```vies from TMDB - Pure```thon version```            "resources": ["catalog"],
            "types": ["movie"],
            "catalogs": [{
                "type": "movie",
                "id": "malayalam", 
                "name": "Malayalam Movies"
            }],
            "idP```ixes": ["tt"]
        }
        self.send_json(manifest_data)

    def catalog(self):
        # For```w, return a```mple test catalog```      test_movies = [
            {
                "id": "tt1234567",
                "type": "movie", 
                "name": "Test Malayalam Movie",
                "poster": None,
                "description": "This is a test movie to verify the catalog works"
            }
        ]
        
        if "default" not``` API_KEYS:
            self.send_json```metas": [], "message```"Please configure API key first"```        else:
            self.send_json({"metas": test```vies})

    def refresh_page(self):
        if "default" not in API_KEYS:```          html = """
            <h1>⚠️ API Key```quired</h1>
            <p>Please configure your```DB API key first```p>
            <a href="/configure```onfigure API Key```>
            """
            self.send_html(html, 400)
        else:
            html = """
            <h1>🔄 Refresh```ature</h1>
            <p>API```y is configure```Movie fetching will be adde```n next version```p>
            <p>For now, the```talog shows a```st movie to```rify everything```rks.</p>
            <a href="/">← Back to Home```>
            <br><br>
            <a href="/catalog```vie/malayalam.json" target="_blank">View```st Catalog</a>```          """
            self.send_html(html)

