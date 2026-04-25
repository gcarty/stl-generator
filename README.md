# Jamaica Relief Map STL Generator

A web app that converts a GeoTIFF elevation file into a CNC-ready STL file.

## Files

| File | Purpose |
|---|---|
| `app.py` | Flask web server |
| `jamaica_relief_stl.py` | STL generation logic |
| `requirements.txt` | Python dependencies |
| `render.yaml` | Render.com deployment config |
| `templates/index.html` | Web UI |

## Running Locally (Mac)

1. Open Terminal
2. Navigate to this folder:
   ```
   cd path/to/stl-generator
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the app:
   ```
   python app.py
   ```
5. Open your browser to: http://localhost:5000

## Deploying to Render.com

1. Push this folder to a GitHub repository
2. Log in to render.com
3. Click "New" → "Web Service"
4. Connect your GitHub repo
5. Render will auto-detect `render.yaml` and deploy
6. Your app will be live at a `.onrender.com` URL
