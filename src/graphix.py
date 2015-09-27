import ctypes
import logging
from ctypes import byref, POINTER, pointer, sizeof
import PIL.Image
from pyglet import gl
import shaders

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
        if loc < 0:
            logging.warning('Uniform {} is not in the shader.'.format(name))
            return
        gl.glUniform1i(loc, value);

    def uniform2f(self, name, v0, v1):
        self.use()
        loc = gl.glGetUniformLocation(self.handle, ctypes.create_string_buffer(name))
        if loc < 0:
            logging.warning('Uniform {} is not in the shader.'.format(name))
            return
        gl.glUniform2f(loc, v0, v1);


def make_texture(filename, indexed=False):
    name = gl.GLuint(0)
    gl.glGenTextures(1, pointer(name))
    gl.glBindTexture(gl.GL_TEXTURE_2D, name)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

    image = PIL.Image.open(filename)
    if indexed:
        assert image.mode == 'P'
    else:
        image = image.convert('RGBA')
    logging.debug('loading {} mode={}'.format(filename, image.mode))

    width, height = image.size
    if indexed:
        assert len(image.tobytes()) == width * height
        gl.glTexImage2D(gl.GL_TEXTURE_2D,
                 0,  # level
                 gl.GL_R8,
                 width,
                 height,
                 0,
                 gl.GL_RED,
                 gl.GL_UNSIGNED_BYTE,
                 ctypes.create_string_buffer(image.tobytes()))
    else:
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

class Framebuffer:
    ''' used for rendering to texture '''
    def __init__(self):
        self.fbo = gl.GLuint(0)
        self.rendered_texture = gl.GLuint(0)
        self.depthrenderbuffer = gl.GLuint(0)
        self.pickingbuffer = gl.GLuint(0)
        self.vertex_buffer = gl.GLuint(0)

        self.program = GlProgram(shaders.vertex_copy, shaders.fragment_copy)
        gl.glGenBuffers(1, pointer(self.vertex_buffer))
        data = (gl.GLfloat * 16)(-1, -1, 0, 0,
                                 - 1, 1, 0, 1,
                                  1, 1, 1, 1,
                                  1, -1, 1, 0)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_STATIC_DRAW)

        gl.glGenFramebuffers(1, pointer(self.fbo))
        if not self.fbo:
            logging.error('failed fbo')
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)

        gl.glGenTextures(1, pointer(self.rendered_texture))
        if not self.rendered_texture:
            logging.error('failed rendered_texture')

        gl.glGenRenderbuffers(1, pointer(self.depthrenderbuffer))
        gl.glGenRenderbuffers(1, pointer(self.pickingbuffer))

        self.resize(1, 1)

    def resize(self, width, height):
        ''' resizes the framebuffer to the given dimensions '''
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.rendered_texture)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, width, height, 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, 0)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, self.rendered_texture, 0)

        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.depthrenderbuffer)
        gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_DEPTH_COMPONENT, width, height)
        gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT, gl.GL_RENDERBUFFER, self.depthrenderbuffer)

        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.pickingbuffer)
        gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_R16UI, width, height)
        gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT1, gl.GL_RENDERBUFFER, self.pickingbuffer)

        draw_buffers = (gl.GLenum * 2)(gl.GL_COLOR_ATTACHMENT0, gl.GL_COLOR_ATTACHMENT1)
        gl.glDrawBuffers(2, draw_buffers)

        if gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER) != gl.GL_FRAMEBUFFER_COMPLETE:
            logging.error('setting up fbo failed')

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    def bind(self):
        ''' binds the framebuffer '''
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)

    def clear(self):
        gl.glClearBufferfv(gl.GL_COLOR, 0, (gl.GLfloat * 4)(0.1, 0.2, 0.3, 0.4))
        gl.glClearBufferfv(gl.GL_DEPTH, 0, (gl.GLfloat * 1)(1.0))
        gl.glClearBufferiv(gl.GL_COLOR, 1, (gl.GLint * 4)(0, 0, 0, 0))

    def copy(self):
        ''' copy the contents of the texture to full window '''
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

        self.program.use()

        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.rendered_texture)
        self.program.uniform1i(b"tex", 0)
        self.program.vertex_attrib_pointer(self.vertex_buffer, b"position", 4, stride=4 * sizeof(gl.GLfloat))
        gl.glDrawArrays(gl.GL_QUADS, 0, 4)
