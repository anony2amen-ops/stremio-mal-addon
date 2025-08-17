from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse

# Create FastAPI app
app = FastAPI(title="Malayalam Movies Test")

@app.get("/")
async def root():
    """Simple test endpoint"""
    return HTMLResponse(content="""
    <html>
    <body>
        <h1>🎬 Malayalam Movies Addon - TEST</h1>
        <p>If you see this, FastAPI is working!</p>
        <a href="/manifest.json">Test Manifest</a>
    </body>
    </html>
    """)

@app.get("/manifest.json")  
async def manifest():
    """Simple manifest test"""
    return JSONResponse({
        "id": "test.malayalam.addon",
        "version": "1.0.0", 
        "name": "Malayalam Test",
        "description": "Test addon",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [{"type": "movie", "id": "test", "name": "Test"}]
    })

# CRITICAL: Export handler for Vercel
handler = app
