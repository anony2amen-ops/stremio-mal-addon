from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Create the most basic FastAPI app possible
app = FastAPI()

@app.get("/")
async def home():
    return {"message": "FastAPI is working!"}

@app.get("/test")  
async def test():
    return JSONResponse({"status": "success", "framework": "FastAPI"})

# Export handler for Vercel
handler = app
