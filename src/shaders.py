vertex_scene = b'''
attribute vec4 position;
attribute vec2 texcoord;

varying vec2 texcoord_;

uniform vec2 window_size;

const float VOXEL_HEIGHT = 19.0;
const float VOXEL_Y_SIDE = 24.0;
const float VOXEL_X_SIDE = 48.0;

void main()
{
    vec2 world;
    world = vec2(VOXEL_X_SIDE * (position.x - position.y), VOXEL_Y_SIDE * (position.x + position.y) + VOXEL_HEIGHT * position.z);
    world = 2.0 * world / window_size;
    texcoord_ = texcoord;
    gl_Position = vec4(world, 0.0, 1.0); 
}
'''

fragment_scene = b'''
uniform sampler2D tex;
varying vec2 texcoord_;

void main()
{
    gl_FragColor = texture2D(tex, texcoord_);
}
'''


vertex_flat = b'''
attribute vec4 position;

varying vec2 texcoord;

uniform vec2 window_size;

void main()
{
    texcoord = position.zw;
    gl_Position = vec4(position.xy / window_size * 2.0 + vec2(-1,1), 0.0, 1.0); 
    //gl_Position = vec4(position, 0.0, 1.0); 
}
'''

fragment_flat = b'''
uniform sampler2D tex;
varying vec2 texcoord;

void main()
{
    vec4 lum;
    lum = texture2D(tex, texcoord);
    gl_FragColor = mix(vec4(0.7, 0.3, 0.3, 1.0), vec4(1.0, 1.0, 1.0, 1.0), lum.r);
}
'''
