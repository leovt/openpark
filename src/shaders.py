vertex_scene = b'''
attribute vec2 position;
void main()
{
    gl_Position = vec4(position, 0.0, 1.0);
}
'''

fragment_scene = b'''
void main()
{
    gl_FragColor = vec4(0.3, 0.7, 0.3, 1.0);
}
'''


vertex_flat = b'''
attribute vec2 position;
//uniform vec2 window_size;
const vec2 window_size = vec2(640, -480);
void main()
{
    gl_Position = vec4(position / window_size * 2.0 + vec2(-1,1), 0.0, 1.0); 
    //gl_Position = vec4(position, 0.0, 1.0); 
}
'''

fragment_flat = b'''
void main()
{
    gl_FragColor = vec4(0.7, 0.3, 0.3, 1.0);
}
'''
