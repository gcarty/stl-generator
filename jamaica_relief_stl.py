"""
Jamaica Relief Map STL Generator
=================================
Converts a GeoTIFF elevation file (.tif) into a 3D STL file
suitable for CNC machining.

Settings:
  - Width:          250mm
  - Relief depth:   15mm
  - Base thickness: 6mm
  - Sea level:      Flat at base surface

Usage:
  1. Place this script in the same folder as your .tif file
  2. Update INPUT_TIF below with your filename
  3. Run:  python jamaica_relief_stl.py
  4. Output STL will be saved alongside this script
"""

import numpy as np
import rasterio
from rasterio.enums import Resampling
from stl import mesh

# ─────────────────────────────────────────────
#  DEFAULT SETTINGS (used when run directly)
# ─────────────────────────────────────────────
INPUT_TIF       = "jamaica.tif"
OUTPUT_STL      = "jamaica_relief.stl"

WIDTH_MM        = 250.0
RELIEF_DEPTH_MM = 15.0
BASE_THICK_MM   = 6.0
RESOLUTION      = 500
# ─────────────────────────────────────────────


def load_and_normalize(tif_path, resolution):
    """Load GeoTIFF, resample to target resolution, normalize elevation."""
    print(f"Loading {tif_path} ...")
    with rasterio.open(tif_path) as src:
        # Calculate height to maintain aspect ratio
        orig_w = src.width
        orig_h = src.height
        aspect = orig_h / orig_w
        res_w = resolution
        res_h = max(1, int(resolution * aspect))

        print(f"  Original size : {orig_w} x {orig_h} pixels")
        print(f"  Resampled to  : {res_w} x {res_h} pixels")

        # Read and resample the first band (elevation)
        data = src.read(
            1,
            out_shape=(res_h, res_w),
            resampling=Resampling.bilinear
        ).astype(np.float32)

        # Handle no-data values (mark as sea level)
        nodata = src.nodata
        if nodata is not None:
            data[data == nodata] = 0.0

    # Clamp anything below 0 to 0 (sea = flat base)
    data = np.clip(data, 0, None)

    # Flip north/south — GeoTIFF row 0 is north, but mesh builds top-to-bottom
    data = np.flipud(data)

    # Normalize: highest point → RELIEF_DEPTH_MM, sea level → 0
    max_elev = data.max()
    if max_elev > 0:
        data = (data / max_elev) * RELIEF_DEPTH_MM
    else:
        raise ValueError("Elevation data appears to be all zeros or invalid.")

    print(f"  Elevation range: 0 to {max_elev:.1f}m → mapped to 0 to {RELIEF_DEPTH_MM}mm")
    return data, aspect


def build_mesh(height_grid, width_mm, relief_mm, base_mm, aspect):
    """Build a solid closed STL mesh from a 2D height grid."""
    rows, cols = height_grid.shape
    height_mm = width_mm * aspect

    # Pixel spacing in mm
    dx = width_mm / (cols - 1)
    dy = height_mm / (rows - 1)

    print(f"Building mesh ({cols} x {rows} grid) ...")
    print(f"  Physical size : {width_mm:.1f}mm x {height_mm:.1f}mm")

    # Total Z: base bottom is at 0, base top at base_mm,
    # terrain surface at base_mm + height_grid value
    z_surface = base_mm + height_grid  # shape (rows, cols)

    # ── Count triangles ──────────────────────────────────────────
    # Top surface:  2 triangles per quad cell
    n_top = 2 * (rows - 1) * (cols - 1)
    # Bottom face:  2 triangles per quad cell
    n_bot = 2 * (rows - 1) * (cols - 1)
    # Four walls (left, right, front, back): 2 triangles per edge segment
    n_walls = 2 * (2 * (cols - 1) + 2 * (rows - 1))
    n_total = n_top + n_bot + n_walls

    relief_mesh = mesh.Mesh(np.zeros(n_total, dtype=mesh.Mesh.dtype))
    tri_idx = 0

    # ── Top surface (terrain) ────────────────────────────────────
    for r in range(rows - 1):
        for c in range(cols - 1):
            x0, x1 = c * dx, (c + 1) * dx
            y0, y1 = r * dy, (r + 1) * dy
            z00 = z_surface[r,   c]
            z10 = z_surface[r,   c+1]
            z01 = z_surface[r+1, c]
            z11 = z_surface[r+1, c+1]

            # Triangle 1
            relief_mesh.vectors[tri_idx] = [
                [x0, y0, z00],
                [x1, y0, z10],
                [x0, y1, z01],
            ]
            tri_idx += 1
            # Triangle 2
            relief_mesh.vectors[tri_idx] = [
                [x1, y0, z10],
                [x1, y1, z11],
                [x0, y1, z01],
            ]
            tri_idx += 1

    # ── Bottom face (flat at z=0) ────────────────────────────────
    for r in range(rows - 1):
        for c in range(cols - 1):
            x0, x1 = c * dx, (c + 1) * dx
            y0, y1 = r * dy, (r + 1) * dy

            # Reversed winding for downward-facing normal
            relief_mesh.vectors[tri_idx] = [
                [x0, y1, 0],
                [x1, y0, 0],
                [x0, y0, 0],
            ]
            tri_idx += 1
            relief_mesh.vectors[tri_idx] = [
                [x0, y1, 0],
                [x1, y1, 0],
                [x1, y0, 0],
            ]
            tri_idx += 1

    total_w = (cols - 1) * dx
    total_h = (rows - 1) * dy

    # ── Front wall (y=0) ─────────────────────────────────────────
    for c in range(cols - 1):
        x0, x1 = c * dx, (c + 1) * dx
        z0 = z_surface[0, c]
        z1 = z_surface[0, c+1]
        relief_mesh.vectors[tri_idx] = [
            [x0, 0, 0],
            [x1, 0, 0],
            [x0, 0, z0],
        ]
        tri_idx += 1
        relief_mesh.vectors[tri_idx] = [
            [x1, 0, 0],
            [x1, 0, z1],
            [x0, 0, z0],
        ]
        tri_idx += 1

    # ── Back wall (y=total_h) ────────────────────────────────────
    for c in range(cols - 1):
        x0, x1 = c * dx, (c + 1) * dx
        z0 = z_surface[rows-1, c]
        z1 = z_surface[rows-1, c+1]
        relief_mesh.vectors[tri_idx] = [
            [x0, total_h, z0],
            [x1, total_h, 0],
            [x0, total_h, 0],
        ]
        tri_idx += 1
        relief_mesh.vectors[tri_idx] = [
            [x0, total_h, z0],
            [x1, total_h, z1],
            [x1, total_h, 0],
        ]
        tri_idx += 1

    # ── Left wall (x=0) ─────────────────────────────────────────
    for r in range(rows - 1):
        y0, y1 = r * dy, (r + 1) * dy
        z0 = z_surface[r,   0]
        z1 = z_surface[r+1, 0]
        relief_mesh.vectors[tri_idx] = [
            [0, y0, z0],
            [0, y1, 0],
            [0, y0, 0],
        ]
        tri_idx += 1
        relief_mesh.vectors[tri_idx] = [
            [0, y0, z0],
            [0, y1, z1],
            [0, y1, 0],
        ]
        tri_idx += 1

    # ── Right wall (x=total_w) ───────────────────────────────────
    for r in range(rows - 1):
        y0, y1 = r * dy, (r + 1) * dy
        z0 = z_surface[r,   cols-1]
        z1 = z_surface[r+1, cols-1]
        relief_mesh.vectors[tri_idx] = [
            [total_w, y0, 0],
            [total_w, y1, z1],
            [total_w, y0, z0],
        ]
        tri_idx += 1
        relief_mesh.vectors[tri_idx] = [
            [total_w, y0, 0],
            [total_w, y1, 0],
            [total_w, y1, z1],
        ]
        tri_idx += 1

    print(f"  Triangles built: {n_total:,}")
    return relief_mesh


def main():
    print("=" * 50)
    print("  Jamaica Relief Map STL Generator")
    print("=" * 50)

    height_grid, aspect = load_and_normalize(INPUT_TIF, RESOLUTION)
    relief_mesh = build_mesh(height_grid, WIDTH_MM, RELIEF_DEPTH_MM, BASE_THICK_MM, aspect)

    print(f"Saving {OUTPUT_STL} ...")
    relief_mesh.save(OUTPUT_STL)
    print(f"Done! STL saved as: {OUTPUT_STL}")
    print()
    print("Next steps:")
    print("  1. Import the STL into your CAM software (Fusion 360, VCarve, Easel, etc.)")
    print("  2. Set your tool, stepover, and feed rates")
    print("  3. Generate gcode and send to your CNC")


if __name__ == "__main__":
    main()
