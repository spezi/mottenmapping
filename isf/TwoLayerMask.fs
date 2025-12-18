/*{
    "DESCRIPTION": "Layer1 covers Layer2. Mesh has brightness, background is black.",
    "CREDIT": "Layer Over",
    "ISFVSN": "2",
    "CATEGORIES": ["Compositing"],
    "INPUTS": [
        {"NAME": "layer1", "TYPE": "image", "LABEL": "Layer 1 (Top)"},
        {"NAME": "layer2", "TYPE": "image", "LABEL": "Layer 2 (Bottom)"},
        {"NAME": "threshold", "TYPE": "float", "DEFAULT": 0.01, "MIN": 0.0, "MAX": 0.5, "LABEL": "Black Threshold"}
    ]
}*/

void main() {
    vec2 uv = isf_FragNormCoord;
    
    // Sample both layers
    vec4 c1 = IMG_NORM_PIXEL(layer1, uv);
    vec4 c2 = IMG_NORM_PIXEL(layer2, uv);
    
    // Layer1: Mesh has brightness > 0, background is black (= 0)
    float brightness = max(max(c1.r, c1.g), c1.b);
    
    // meshMask: 1 where mesh (bright), 0 where background (black)
    float meshMask = step(threshold, brightness);
    
    // Show layer1 only where mesh is (strips away black background)
    vec3 masked1 = c1.rgb * meshMask;
    
    // Show layer2 only where layer1 has no mesh (punch hole for mesh)
    vec3 masked2 = c2.rgb * (1.0 - meshMask);
    
    // Combine: layer1 mesh on top of layer2
    vec3 result = masked1 + masked2;
    
    gl_FragColor = vec4(result, 1.0);
}
