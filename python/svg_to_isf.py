#!/usr/bin/env python3
"""
SVG to ISF Shader Generator for OSSIA Score
Parses SVG polygons and generates an ISF shader with individual alpha control

Usage:
  python3 svg_to_isf.py <input.svg> [--glsl|--isf]
  python3 svg_to_isf.py low_poly_dragonfly.svg         # outputs low_poly_dragonfly.glsl
  python3 svg_to_isf.py low_poly_dragonfly.svg --isf   # outputs low_poly_dragonfly.isf
"""

import xml.etree.ElementTree as ET
import re
import sys
from pathlib import Path

# Register namespace to handle SVG properly
ET.register_namespace('svg', 'http://www.w3.org/2000/svg')

def parse_svg_points(points_str):
    """Parse SVG points string into list of (x, y) tuples"""
    coords = re.findall(r'[-+]?[\d.]+', points_str)
    points = []
    for i in range(0, len(coords), 2):
        if i + 1 < len(coords):
            points.append((float(coords[i]), float(coords[i+1])))
    return points

def parse_svg(svg_path):
    """Parse SVG file and extract all polygons"""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    
    # Get SVG dimensions
    width = float(root.get('width', '1920'))
    height = float(root.get('height', '1080'))
    
    polygons = []
    
    # Handle namespace
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    
    # Try with namespace first
    for polygon in root.findall('.//svg:polygon', ns):
        points_str = polygon.get('points', '')
        if points_str:
            points = parse_svg_points(points_str)
            if len(points) >= 3:
                polygons.append(points)
    
    # If no results, try without namespace
    if not polygons:
        for polygon in root.findall('.//polygon'):
            points_str = polygon.get('points', '')
            if points_str:
                points = parse_svg_points(points_str)
                if len(points) >= 3:
                    polygons.append(points)
    
    return polygons, width, height

def polygon_to_triangles(points):
    """Convert polygon to triangles using fan triangulation"""
    triangles = []
    for i in range(1, len(points) - 1):
        triangles.append((points[0], points[i], points[i+1]))
    return triangles

def generate_isf_shader(polygons, width, height, output_path):
    """Generate ISF shader from polygons with parameter-driven colors"""
    
    # Generate inputs for each polygon
    inputs_list = []
    
    for i in range(len(polygons)):
        inputs_list.append(f'''    {{
      "NAME": "poly{i}_alpha",
      "TYPE": "float",
      "DEFAULT": 1.0,
      "MIN": 0.0,
      "MAX": 1.0,
      "LABEL": "Polygon {i+1} Alpha"
    }}''')
    
    # Join inputs properly
    if inputs_list:
        inputs_str = ",\n".join(inputs_list)
        inputs_section = f",\n{inputs_str}"
    else:
        inputs_section = ""
    
    # Generate triangle checks for each polygon - NO hardcoded colors!
    checks_list = []
    triangle_counter = 0
    
    for poly_idx, polygon in enumerate(polygons):
        triangles = polygon_to_triangles(polygon)
        
        for tri_idx, (p1, p2, p3) in enumerate(triangles):
            # Flip Y coordinates (SVG top=0 to GLSL bottom=0)
            p1_flipped = (p1[0], height - p1[1])
            p2_flipped = (p2[0], height - p2[1])
            p3_flipped = (p3[0], height - p3[1])
            
            # Generate check WITHOUT hardcoded color - use else if for efficiency
            if triangle_counter == 0:
                check = f'''if (pointInTriangle(pixelCoord, vec2({p1_flipped[0]:.3f}, {p1_flipped[1]:.3f}), vec2({p2_flipped[0]:.3f}, {p2_flipped[1]:.3f}), vec2({p3_flipped[0]:.3f}, {p3_flipped[1]:.3f}))) {{ alpha = poly{poly_idx}_alpha; }}'''
            else:
                check = f'''else if (pointInTriangle(pixelCoord, vec2({p1_flipped[0]:.3f}, {p1_flipped[1]:.3f}), vec2({p2_flipped[0]:.3f}, {p2_flipped[1]:.3f}), vec2({p3_flipped[0]:.3f}, {p3_flipped[1]:.3f}))) {{ alpha = poly{poly_idx}_alpha; }}'''
            
            checks_list.append(check)
            triangle_counter += 1
    
    triangle_checks_str = "\n    ".join(checks_list)
    
    # Generate complete shader
    shader = f'''/*{{
  "DESCRIPTION": "Low Poly - Individual Polygon Alpha Control",
  "CREDIT": "Generated from SVG",
  "ISFVSN": "2",
  "INPUTS": [
    {{
      "NAME": "globalAlpha",
      "TYPE": "float",
      "DEFAULT": 1.0,
      "MIN": 0.0,
      "MAX": 1.0,
      "LABEL": "Global Alpha"
    }}{inputs_section},
    {{
      "NAME": "polygonColor",
      "TYPE": "color",
      "DEFAULT": [0.8, 0.8, 0.8, 1.0],
      "LABEL": "Polygon Color"
    }},
    {{
      "NAME": "backgroundColor",
      "TYPE": "color",
      "DEFAULT": [0.0, 0.0, 0.0, 0.0],
      "LABEL": "Background Color"
    }}
  ]
}}*/

// Point-in-triangle test using barycentric coordinates
bool pointInTriangle(vec2 p, vec2 a, vec2 b, vec2 c) {{
  vec2 v0 = c - a;
  vec2 v1 = b - a;
  vec2 v2 = p - a;
  
  float dot00 = dot(v0, v0);
  float dot01 = dot(v0, v1);
  float dot02 = dot(v0, v2);
  float dot11 = dot(v1, v1);
  float dot12 = dot(v1, v2);
  
  float denom = dot00 * dot11 - dot01 * dot01;
  if (abs(denom) < 0.0001) return false;
  
  float invDenom = 1.0 / denom;
  float u = (dot11 * dot02 - dot01 * dot12) * invDenom;
  float v = (dot00 * dot12 - dot01 * dot02) * invDenom;
  
  return (u >= -0.0001) && (v >= -0.0001) && (u + v <= 1.0001);
}}

void main() {{
  vec2 uv = isf_FragNormCoord;
  vec2 pixelCoord = uv * vec2({width:.1f}, {height:.1f});
  
  vec4 color = backgroundColor;
  float alpha = 0.0;
  
  {triangle_checks_str}
  
  // Apply color parameter based on alpha
  if (alpha > 0.0) {{
    color = polygonColor;
    color.a = alpha * globalAlpha;
  }}
  gl_FragColor = color;
}}'''
    
    with open(output_path, 'w') as f:
        f.write(shader)
    
    print(f"✓ ISF Shader generiert: {output_path}")
    print(f"  - Polygone: {len(polygons)}")
    print(f"  - Triangle-Tests: {triangle_counter}")
    print(f"  - Parameter: {len(polygons) + 3} (globalAlpha + {len(polygons)} poly-alphas + polygonColor + backgroundColor)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 svg_to_isf.py <input.svg> [--glsl|--isf]")
        print()
        print("Examples:")
        print("  python3 svg_to_isf.py low_poly_dragonfly.svg         # outputs low_poly_dragonfly.glsl")
        print("  python3 svg_to_isf.py low_poly_dragonfly.svg --isf   # outputs low_poly_dragonfly.isf")
        sys.exit(1)
    
    svg_path = Path(sys.argv[1])
    
    # Check if input file exists
    if not svg_path.exists():
        print(f"✗ SVG-Datei nicht gefunden: {svg_path}")
        sys.exit(1)
    
    # Determine output extension
    output_ext = ".glsl"  # Default
    if len(sys.argv) > 2:
        if sys.argv[2] == "--isf":
            output_ext = ".isf"
        elif sys.argv[2] == "--glsl":
            output_ext = ".glsl"
    
    # Generate output path with same name but different extension
    output_path = svg_path.with_stem(svg_path.stem).with_suffix(output_ext)
    
    print(f"SVG zu ISF Shader Generator")
    print(f"=" * 60)
    
    try:
        polygons, width, height = parse_svg(svg_path)
        print(f"✓ SVG gelesen: {len(polygons)} Polygone")
        print(f"  - Input:  {svg_path}")
        print(f"  - Output: {output_path}")
        print(f"  - Dimensionen: {width} x {height}")
        print()
        
        if polygons:
            generate_isf_shader(polygons, width, height, output_path)
            print(f"\n✓ Generierung erfolgreich!")
            return True
        else:
            print("✗ Keine Polygone in der SVG-Datei gefunden!")
            return False
    except Exception as e:
        print(f"✗ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)