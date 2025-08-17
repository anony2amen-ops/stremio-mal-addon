# Malayalam Movies Stremio Addon - FastAPI Version

## Overview
This is a FastAPI-based Stremio addon that displays Malayalam movies available on OTT platforms in India, sorted by release date (latest first).

## Key Features
- ✅ **FastAPI with async/await** - Better performance than Flask
- ✅ **User-configurable TMDB API keys** - No hardcoded keys
- ✅ **Web-based configuration page** - Easy setup for users
- ✅ **Background refresh functionality** - Update movie catalog
- ✅ **Vercel deployment ready** - Serverless deployment
- ✅ **CORS enabled** - Works with Stremio
- ✅ **In-memory storage** - No database required

## Files Structure
```
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel deployment configuration
└── README.md             # This file
```

## Local Development

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
# or
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access the Application
- Home: http://localhost:8000/
- Configure API Key: http://localhost:8000/configure
- Manifest: http://localhost:8000/manifest.json
- Refresh: http://localhost:8000/refresh

## Deployment to Vercel

### 1. Prerequisites
- GitHub account
- Vercel account (free)
- TMDB API key

### 2. Deploy Steps
1. **Push code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Vercel will auto-detect the Python project

3. **Deploy**:
   - Click "Deploy"
   - Wait for deployment to complete
   - Note your deployment URL (e.g., `your-addon.vercel.app`)

### 3. Post-Deployment Setup
1. Visit `https://your-addon.vercel.app/configure`
2. Enter your TMDB API key
3. Click "Refresh Movies" to populate the catalog
4. Use `https://your-addon.vercel.app/manifest.json` in Stremio

## How Users Will Use Your Addon

### Step 1: Get TMDB API Key
Users need to:
1. Create free account at [themoviedb.org](https://www.themoviedb.org/signup)
2. Go to [API Settings](https://www.themoviedb.org/settings/api)
3. Copy the "API Key (v3 auth)"

### Step 2: Configure the Addon
1. Visit `https://your-addon.vercel.app/configure`
2. Enter their TMDB API key
3. Click "Save Configuration"

### Step 3: Install in Stremio
1. Open Stremio
2. Go to Addons section
3. Click "Add Addon"
4. Enter: `https://your-addon.vercel.app/manifest.json`
5. Install the addon

### Step 4: Enjoy Malayalam Movies
- Browse "Malayalam Movies" catalog in Stremio
- Movies are sorted by release date (newest first)
- Only shows movies available on OTT platforms in India

## API Endpoints

### Public Endpoints
- `GET /` - Home page with setup instructions
- `GET /configure` - Configuration page for API key
- `POST /configure` - Save API key configuration
- `GET /manifest.json` - Stremio addon manifest
- `GET /catalog/movie/malayalam.json` - Movie catalog
- `GET /refresh` - Refresh movie catalog

### Configuration Storage
- API keys are stored in memory per deployment
- Each user can have their own API key using user_id parameter
- Default user_id is "default"

## Technical Details

### Performance Improvements over Flask
- **Async I/O**: Non-blocking HTTP requests using aiohttp
- **Concurrent Processing**: Multiple movie API calls processed simultaneously
- **Background Tasks**: Refresh operations don't block user requests
- **Better Resource Usage**: More efficient memory and CPU utilization

### Vercel Compatibility
- **Serverless Functions**: Each request is handled independently
- **No Persistent Storage**: Uses in-memory storage for simplicity
- **Cold Start Optimization**: Fast initialization with cached imports
- **Automatic Scaling**: Handles traffic spikes automatically

### Security Features
- **No Hardcoded Keys**: Users provide their own TMDB API keys
- **Input Validation**: API key format validation
- **Error Handling**: Graceful handling of API failures
- **CORS Protection**: Configured for Stremio compatibility

## Troubleshooting

### Common Issues
1. **"API Key Required" Error**:
   - Visit `/configure` and enter a valid TMDB API key

2. **Empty Movie Catalog**:
   - Check if API key is valid
   - Visit `/refresh` to manually refresh catalog
   - Check Vercel function logs for errors

3. **Stremio Can't Load Addon**:
   - Ensure the manifest URL is correct
   - Check if CORS is working (should be automatic)
   - Verify the deployment is live

### Getting Help
1. Check Vercel function logs for errors
2. Test API endpoints individually
3. Verify TMDB API key is working: `https://api.themoviedb.org/3/configuration?api_key=YOUR_KEY`

## Contributing
Feel free to submit issues and enhancement requests!

## License
This project is open source and available under the MIT License.
