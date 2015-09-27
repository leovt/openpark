vertex_scene = b'''
#version 130
attribute vec4 position;
attribute vec4 texcoord;
attribute int object_id;

varying vec4 texcoord_;

uniform vec2 window_size;
uniform vec2 screen_origin;

const float VOXEL_HEIGHT = 24.0;
const float VOXEL_Y_SIDE = 24.0;
const float VOXEL_X_SIDE = 48.0;

flat out int object_id_;

void main()
{
    vec2 world;
    world = vec2(VOXEL_X_SIDE * (position.x - position.y), VOXEL_Y_SIDE * (position.x + position.y) + VOXEL_HEIGHT * position.z);
    world = world + screen_origin;
    world = 2.0 * world / window_size - vec2(1.0, -1.0);
    texcoord_ = texcoord;
    gl_Position = vec4(world, position.w, 1.0); 
    object_id_ = object_id;
}
'''

fragment_scene = b'''
#version 130

uniform sampler2D tex;
varying vec4 texcoord_;

flat in int object_id_;

out vec4 FragColor;
out int ObjectID;

void main()
{
    vec4 bottom = texture2D(tex, texcoord_.xy);
    vec4 top = texture2D(tex, texcoord_.zw);
    FragColor = mix(bottom, top, top.a);
    ObjectID = object_id_;
}
'''

fragment_sprite = b'''
#version 130
uniform sampler2D tex;
uniform sampler2D palette;
varying vec4 texcoord_;

flat in int object_id_;

out vec4 FragColor;
out int ObjectID;

void main()
{
    float index = texture2D(tex, texcoord_.xy).r * 255.0;
    if (index == 0.0)
        discard;
    // index = 5.0;
    float pal = texcoord_.z;
    FragColor = texture2D(palette, vec2((index+0.5) / 32.0, (pal+0.5) / 32.0));
    ObjectID = object_id_;
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

vertex_copy = b'''
attribute vec4 position;
varying vec2 texcoord;
void main()
{
    texcoord = position.zw;
    gl_Position = vec4(position.xy, 0.0, 1.0);
}
'''

fragment_copy = b'''
uniform sampler2D tex;
varying vec2 texcoord;

void main()
{
    gl_FragColor = texture2D(tex, texcoord);
}
'''
