"""
Jamaica Relief Map STL Generator - Flask Web App
"""

import os
import uuid
import tempfile
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Max upload size: 200MB
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    # ── Validate file upload ──────────────────────────────────────
    if 'tif_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    tif_file = request.files['tif_file']
    if tif_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # ── Read parameters ───────────────────────────────────────────
    try:
        width_mm        = float(request.form.get('width_mm',        250.0))
        relief_depth_mm = float(request.form.get('relief_depth_mm', 15.0))
        base_thick_mm   = float(request.form.get('base_thick_mm',   6.0))
        resolution      = int(request.form.get('resolution',        500))
    except ValueError:
        return jsonify({'error': 'Invalid parameter values'}), 400

    # Clamp resolution to safe range
    resolution = max(100, min(resolution, 1000))

    # ── Save uploaded file to temp location ───────────────────────
    tmp_dir = tempfile.mkdtemp()
    tif_path = os.path.join(tmp_dir, 'input.tif')
    stl_path = os.path.join(tmp_dir, 'output.stl')
    tif_file.save(tif_path)

    # ── Run STL generation ────────────────────────────────────────
    try:
        from jamaica_relief_stl import load_and_normalize, build_mesh

        height_grid, aspect = load_and_normalize(tif_path, resolution)
        relief_mesh = build_mesh(
            height_grid, width_mm, relief_depth_mm, base_thick_mm, aspect
        )
        relief_mesh.save(stl_path)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Clean up the uploaded tif
        if os.path.exists(tif_path):
            os.remove(tif_path)

    # ── Return STL file as download ───────────────────────────────
    return send_file(
        stl_path,
        as_attachment=True,
        download_name='jamaica_relief.stl',
        mimetype='application/octet-stream'
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
