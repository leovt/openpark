import logging
from ctypes import pointer, sizeof

from graphix import GlProgram
import shaders

from pyglet import gl

class Window:
    def __init__(self, left, top, width, height):
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.is_root = False
        self.children = []

    def get_data(self, x, y):
        x += self.left
        y += self.top

        if not self.is_root:
            yield from (x, y)
            yield from (x, y + self.height)
            yield from (x + self.width, y + self.height)
            yield from (x + self.width, y)

        for child in self.children:
            yield from child.get_data(x, y)

    def add(self, child):
        self.children.append(child)


class WindowManager():
    '''
    classdocs
    '''

    def __init__(self):
        self.init_gl()
        self.root = Window(0, 0, 1, 1)
        self.root.is_root = True

        # test adding a window
        self.root.add(Window(10, 10, 200, 30))

    def init_gl(self):
        self.program = GlProgram(shaders.vertex_flat, shaders.fragment_flat)
        self.buffer = gl.GLuint(0)
        gl.glGenBuffers(1, pointer(self.buffer))

    def draw(self):
        self.program.use()

        data = list(self.root.get_data(0, 0))
        data = (gl.GLfloat * len(data))(*data)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)


        self.program.vertex_attrib_pointer(self.buffer, b"position", 2)
        gl.glDrawArrays(gl.GL_QUADS, 0, len(data) // 2)
