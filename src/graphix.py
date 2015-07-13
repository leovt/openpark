import ctypes
from ctypes import byref, POINTER

from pyglet import gl

def shader(stype, src):
    handle = gl.glCreateShader(stype)
    buffer = ctypes.create_string_buffer(src)
    pointer = ctypes.cast(ctypes.pointer(ctypes.pointer(buffer)), POINTER(POINTER(ctypes.c_char)))
    length = ctypes.c_int(len(src) + 1)
    gl.glShaderSource(handle, 1, pointer, byref(length))
    gl.glCompileShader(handle)
    return handle

class GlProgram:
    def __init__(self, vertex_shader, fragment_shader):
        self.handle = gl.glCreateProgram()
        gl.glAttachShader(self.handle, shader(gl.GL_VERTEX_SHADER, vertex_shader))
        gl.glAttachShader(self.handle, shader(gl.GL_FRAGMENT_SHADER, fragment_shader))
        gl.glLinkProgram(self.handle)
        self.use()  # early error

    def use(self):
        gl.glUseProgram(self.handle)

    def vertex_attrib_pointer(self, buffer, name, size, type=gl.GL_FLOAT, normalized=False, stride=0, offset=0):
        loc = gl.glGetAttribLocation(self.handle, ctypes.create_string_buffer(name))
        gl.glEnableVertexAttribArray(loc)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, buffer)
        gl.glVertexAttribPointer(loc, size, type, normalized, stride, ctypes.c_void_p(offset))

    def uniform1i(self, name, value):
        loc = gl.glGetUniformLocation(self.handle, ctypes.create_string_buffer(name))
        gl.glUniform1i(loc, value);
