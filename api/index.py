from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        
        if path == "/" or path == "":
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            html = """
            <h1>🎬 Malayalam Movies Addon - Working!</h1>
            <p>✅ Server is working perfectly!</p>
            <p><a href="/manifest.json">Test Manifest JSON</a></p>
            <p><strong>Manifest URL for Stremio:</strong></p>
            <code>https://stremio-mal-addon-dqlsbjqx6-amenafsal1-6352s-projects.vercel.app/manifest.json</code>
            """
            self.wfile.write(html.encode())
            
        elif path == "/manifest.json":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')  # ← FIXED: Set JSON header first
            self.send_header('Access-Control-Allow-Origin', '*')   # ← CRITICAL: CORS for manifest
            self.end_headers()
            
            # Simple manifest JSON as string (no import needed)
            manifest_json = '{"id":"org.malayalam.test","version":"1.0.0","name":"Malayalam Movies Test","description":"Test Malayalam addon","resources":["catalog"],"types":["movie"],"catalogs":[{"type":"movie","id":"malayalam","name":"Malayalam Movies"}],"idPrefixes":["tt"]}'
            self.wfile.write(manifest_json.encode())
            
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b"<h1>404 - Not Found</h1>")
