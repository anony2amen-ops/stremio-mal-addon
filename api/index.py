from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        path = self.path
        
        if path == "/" or path == "":
            html = """
            <h1>Malayalam Movies Addon - Basic Test</h1>
            <p>✅ Server is working!</p>
            <p><a href="/manifest.json">Test Manifest</a></p>
            """
        elif path == "/manifest.json":
            html = '{"id":"test","name":"test","version":"1.0.0","resources":["catalog"],"types":["movie"],"catalogs":[{"type":"movie","id":"test","name":"Test"}]}'
            self.send_header('Content-type', 'application/json')
        else:
            html = "<h1>404 - Not Found</h1>"
        
        self.wfile.write(html.encode())
        return
