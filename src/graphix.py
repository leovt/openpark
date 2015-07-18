import ctypes
import logging
from ctypes import byref, POINTER, pointer
import PIL.Image
from pyglet import gl

def shader(stype, src):
    handle = gl.glCreateShader(stype)
    buffer = ctypes.create_string_buffer(src)
    buf_pointer = ctypes.cast(ctypes.pointer(ctypes.pointer(buffer)), POINTER(POINTER(ctypes.c_char)))
    length = ctypes.c_int(len(src) + 1)
    gl.glShaderSource(handle, 1, buf_pointer, byref(length))
    gl.glCompileShader(handle)
    success = gl.GLint(0)
    gl.glGetShaderiv(handle, gl.GL_COMPILE_STATUS, pointer(success))
    length = gl.GLint(0)
    gl.glGetShaderiv(handle, gl.GL_INFO_LOG_LENGTH, pointer(length))
    buffer = ctypes.create_string_buffer(length.value)
    gl.glGetShaderInfoLog(handle, length, None, buffer)
    log = buffer.value[:length.value].decode('ascii')
    for line in log.splitlines():
        logging.debug('GLSL: ' + line)

    if not success:
        raise Exception('Compiling of the shader failed.')
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
        self.use()
        loc = gl.glGetAttribLocation(self.handle, ctypes.create_string_buffer(name))
        if loc < 0:
            logging.warning('Attribute {} is not in the shader.'.format(name))
            return
        gl.glEnableVertexAttribArray(loc)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, buffer)
        gl.glVertexAttribPointer(loc, size, type, normalized, stride, ctypes.c_void_p(offset))

    def uniform1i(self, name, value):
        self.use()
        loc = gl.glGetUniformLocation(self.handle, ctypes.create_string_buffer(name))
        gl.glUniform1i(loc, value);

    def uniform2f(self, name, v0, v1):
        self.use()
        loc = gl.glGetUniformLocation(self.handle, ctypes.create_string_buffer(name))
        gl.glUniform2f(loc, v0, v1);


def make_texture(filename):
    name = gl.GLuint(0)
    gl.glGenTextures(1, pointer(name))
    gl.glBindTexture(gl.GL_TEXTURE_2D, name)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

    image = PIL.Image.open(filename)
    image = image.convert('RGBA')
    logging.debug(image.mode)

    width, height = image.size
    assert len(image.tobytes()) == width * height * 4
    gl.glTexImage2D(gl.GL_TEXTURE_2D,
             0,  # level
             gl.GL_RGBA8,
             width,
             height,
             0,
             gl.GL_RGBA,
             gl.GL_UNSIGNED_BYTE,
             ctypes.create_string_buffer(image.tobytes()))
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
    return name
