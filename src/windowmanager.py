import logging
from ctypes import pointer, sizeof
import ctypes

from graphix import GlProgram
import shaders

from pyglet import gl
import pyglet.window.mouse
from textmanager import TextManager

class Window:
    def __init__(self, left, top, width, height):
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.is_root = False
        self.children = []

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height

    def own_data(self, x, y):
        yield from (x, y, 0.0, 0.0)
        yield from (x, y + self.height, 0.0, 0.0)
        yield from (x + self.width, y + self.height, 1.0, 0.0)
        yield from (x + self.width, y, 1.0, 0.0)

    def get_data(self, x, y):
        x += self.left
        y += self.top

        if not self.is_root:
            yield from self.own_data(x, y)

        for child in self.children:
            yield from child.get_data(x, y)

    def add(self, child):
        self.children.append(child)

    def close(self):
        for child in self.children:
            child.close()

    def on_click(self):
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        for child in reversed(self.children):
            if child.left <= x < child.right and child.top <= y < child.bottom:
                child.on_mouse_press(x - child.left, y - child.top, button, modifiers)
        if button == pyglet.window.mouse.LEFT:
            self.on_click()


class Label(Window):
    def __init__(self, tm, text, left, top):
        self.tm = tm
        self.left = left
        self.top = top
        self.text = None
        self.set(text)
        self.is_root = False
        self.children = []

    def set(self, text):
        if self.text:
            self.tm.free(self.text)

        if text:
            rect = self.tm.alloc(text)
            self.text = text
            self.width = rect.width
            self.height = rect.height
            self.u0 = rect.left / self.tm.width
            self.u1 = rect.right / self.tm.width
            self.v0 = rect.top / self.tm.height
            self.v1 = rect.bottom / self.tm.height

    def close(self):
        if self.text:
            self.tm.free(self.text)

    def own_data(self, x, y):
        yield from (x, y, self.u0, self.v0)
        yield from (x, y + self.height, self.u0, self.v1)
        yield from (x + self.width, y + self.height, self.u1, self.v1)
        yield from (x + self.width, y, self.u1, self.v0)

class WindowManager():
    '''
    classdocs
    '''

    def __init__(self):
        self.root = Window(0, 0, 1, 1)
        self.root.is_root = True
        self.textmanager = TextManager()
        self.init_gl()

    def init_gl(self):
        self.program = GlProgram(shaders.vertex_flat, shaders.fragment_flat)
        self.buffer = gl.GLuint(0)
        gl.glGenBuffers(1, pointer(self.buffer))
        self.texture = gl.GLuint(0)
        gl.glGenTextures(1, pointer(self.texture))
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)


    def draw(self):
        self.program.use()

        data = list(self.root.get_data(0, 0))
        data = (gl.GLfloat * len(data))(*data)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)
        gl.glTexImage2D(gl.GL_TEXTURE_2D,
                 0,  # level
                 gl.GL_R8,
                 self.textmanager.width,
                 self.textmanager.height,
                 0,
                 gl.GL_RED,
                 gl.GL_UNSIGNED_BYTE,
                 ctypes.create_string_buffer(self.textmanager.img.tobytes()))
        self.program.uniform1i(b"tex", 0)  # set to 0 because the texture is bound to GL_TEXTURE0

        self.program.vertex_attrib_pointer(self.buffer, b"position", 4)
        # self.program.vertex_attrib_pointer(self.buffer, b"texcoord", 2, stride=4 * sizeof(gl.GLfloat), offset=2 * sizeof(gl.GLfloat))
        gl.glDrawArrays(gl.GL_QUADS, 0, len(data) // 4)

    def on_mouse_press(self, x, y, button, modifiers):
        self.root.on_mouse_press(x, y, button, modifiers)

    def on_resize(self, x, y):
        self.program.uniform2f(b'window_size', x, -y)
