import math
import numpy as np
from typing import Dict, Any, List, Tuple
from .types import Point, TransformMatrix


def to_pdf_scale_from_meta(page_meta: Dict[str, Any]) -> float:
    """Factor para convertir coordenadas de plantilla a PDF."""
    rw = float(page_meta.get("renderWidth") or 600.0)
    pw = float(page_meta.get("pdfWidthBase") or rw)
    return pw / rw


def apply_affine(T: TransformMatrix, x: float, y: float) -> Point:
    """Aplica transformacion afin a un punto."""
    X = np.array([x, y, 1.0], dtype=float)
    u, v = (T @ X)
    return float(u), float(v)


def fit_affine(src: List[Point], dst: List[Point]) -> TransformMatrix:
    """Calcula transformacion afin por minimos cuadrados."""
    n = len(src)
    A = np.zeros((2*n, 6), dtype=float)
    b = np.zeros((2*n,), dtype=float)

    for i, ((x, y), (u, v)) in enumerate(zip(src, dst)):
        A[2*i, :] = [x, y, 1, 0, 0, 0]
        A[2*i+1, :] = [0, 0, 0, x, y, 1]
        b[2*i] = u
        b[2*i+1] = v

    params, *_ = np.linalg.lstsq(A, b, rcond=None)
    a, b1, c, d, e, f = params
    return np.array([[a, b1, c], [d, e, f]], dtype=float)


def fit_similarity(p1: Point, p2: Point, q1: Point, q2: Point) -> TransformMatrix:
    """Calcula transformacion de similitud  (escala + rotacion + translacion)"""
    vx_p = p2[0] - p1[0]; vy_p = p2[1] - p1[1]
    vx_q = q2[0] - q1[0]; vy_q = q2[1] - q1[1]
    
    norm_p = math.hypot(vx_p, vy_p) or 1.0
    norm_q = math.hypot(vx_q, vy_q)
    s = norm_q / norm_p
    
    ang_p = math.atan2(vy_p, vx_p)
    ang_q = math.atan2(vy_q, vx_q)
    theta = ang_q - ang_p
    
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    a = s * cos_t; b1 = s * (-sin_t)
    d = s * sin_t; e = s * cos_t
    c = q1[0] - (a * p1[0] + b1 * p1[1])
    f = q1[1] - (d * p1[0] + e * p1[1])
    
    return np.array([a, b1, c], [d, e, f], dtype=float)

def transform_box(T: TransformMatrix, box: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """Transforma un box de plantilla a coordenadas PDF."""
    x, y, w, h = float(box["x"]), float(box["y"]), float(box["w"]), float(box["h"])
    corners = [(x,y), (x+w,y), (x+w, y+h), (x, y+h)]
    transformed = [apply_affine(T, px, py) for (px, py) in corners]
    
    xs = [u for (u, _) in transformed]
    ys = [v for (_, v) in transformed]
    
    return (min(xs), min(ys), max(xs), max(ys))
