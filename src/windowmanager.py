"""
The window manager for the Open Park project

The window manager uses a coordinate system where the top left corner of the
application window has coordinates (0,0).

@author: Leonhard Vogt
"""
import logging
from ctypes import pointer, sizeof
import ctypes

from graphix import GlProgram
import shaders

from pyglet import gl
import pyglet.window.mouse
from textmanager import TextManager

class Window:
    '''
    The window class is the base class for all windows and controls.
    '''
    def __init__(self, parent, left, top, width, height):
        '''
        Initialize a new window.
        
        parent -- the parent window, this instance self-registers with the parent.
        left -- the x-position of the left edge of the window with respect to the parent.
        top -- the y-position of the top edge of the window.
        width -- the width of the window.
        height -- the height of the window.
        '''
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.children = []
        self.parent = parent
        if parent:
            self.manager = parent.manager
            self.parent.add(self)

    @property
    def right(self):
        ''' the x-position of the right edge of the window (exclusive) '''
        return self.left + self.width

    @property
    def bottom(self):
        ''' the y-position of the bottom edge of the window (exclusive) '''
        return self.top + self.height

    def own_data(self, x, y):
        '''
        Iterate over all the vertex data needed for rendering this window.
        
        A flat iterable of floats that are passed in the vertex buffer.
        '''
        yield from (x, y, 0.0, 0.0)
        yield from (x, y + self.height, 0.0, 0.0)
        yield from (x + self.width, y + self.height, 1.0, 0.0)
        yield from (x + self.width, y, 1.0, 0.0)

    def get_data(self, x, y):
        '''
        Iterate over vertex data for this and all child windows
        '''
        x += self.left
        y += self.top

        if self.parent:
            # this excludes the invisible root window
            yield from self.own_data(x, y)

        for child in self.children:
            yield from child.get_data(x, y)

    def add(self, child):
        '''
        Add a child window. The child should be a Window object.
        '''
        if child in self.children:
            raise Exception('child already registered')
        self.children.append(child)

    def remove(self, child):
        '''
        Remove a child window.
        '''
        self.children.remove(child)

    def close(self):
        '''
        Close this window and unregister it from its parent. 
        '''
        if self.parent:
            self.parent.remove(self)
        for child in self.children:
            child.close()

    def on_click(self):
        '''
        Overwrite this method to register for click events.
        '''
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        '''
        Handle the mouse_press event and pass it to the appropriate child windows.
        
        In case the left mouse button is pressed the on_click method is called.
        '''
        for child in reversed(self.children):
            if child.left <= x < child.right and child.top <= y < child.bottom:
                child.on_mouse_press(x - child.left, y - child.top, button, modifiers)
        if button == pyglet.window.mouse.LEFT:
            self.on_click()


class Label(Window):
    '''
    The label window is used for showing text. When text is set its size changes to fit.
    '''
    def __init__(self, parent, text, left, top):
        '''
        Initialize the label window.
        
        parent -- the parent window
        text -- the text contents shown by the label
        left -- the x-position of the left edge of the window with respect to the parent.
        top -- the y-position of the top edge of the window.
        '''
        Window.__init__(self, parent, left, top, 0, 0)
        self._text = None
        self.text = text

    @property
    def text(self):
        '''the text contents of the label. This attribute can be set to change the text'''
        return self._text

    @text.setter
    def text(self, text):
        if self._text == text:
            return
        tm = self.manager.textmanager
        if self._text is not None:
            tm.free(self._text)
        self._text = text

        rect = self.manager.textmanager.alloc(text)
        self.width = rect.width
        self.height = rect.height
        self.u0 = rect.left / tm.width
        self.u1 = rect.right / tm.width
        self.v0 = rect.top / tm.height
        self.v1 = rect.bottom / tm.height

    def close(self):
        '''
        Close this window and unregister it from its parent.
        Releases the text resource. 
        '''
        if self._text:
            self.manager.textmanager.free(self._text)
        Window.close(self)

    def own_data(self, x, y):
        '''
        Iterate over all the vertex data needed for rendering this window.
        
        A flat iterable of floats that are passed in the vertex buffer.
        '''
        yield from (x, y, self.u0, self.v0)
        yield from (x, y + self.height, self.u0, self.v1)
        yield from (x + self.width, y + self.height, self.u1, self.v1)
        yield from (x + self.width, y, self.u1, self.v0)


class WindowManager():
    '''
    The window manager is responsible for drawing the windows and
    for forwarding events to the windows.
    
    It uses a TextManager object to manage the texture resources used by the Label objects.
    
    The window manager creates an invisible root window which is the ancestor to all windows managed.  
    '''
    def __init__(self):
        '''initialize the WindowManager'''
        self.textmanager = TextManager()
        self.root = Window(None, 0, 0, 1, 1)
        self.root.manager = self
        self.init_gl()

    def init_gl(self):
        '''initialize the opengl resources needed for presenting windows
        
        * a shader program
        * a vertex buffer
        * a texture for Label windows
        '''
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
        '''
        Draw the windows.
        '''
        self.program.use()

        data = list(self.root.get_data(0, 0))
        data = (gl.GLfloat * len(data))(*data)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.buffer)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, sizeof(data), data, gl.GL_DYNAMIC_DRAW)

        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture)
        if self.textmanager.dirty:
            # only upload the texture to the GPU if it has actually changed
            gl.glTexImage2D(gl.GL_TEXTURE_2D,
                     0,  # level
                     gl.GL_R8,
                     self.textmanager.width,
                     self.textmanager.height,
                     0,
                     gl.GL_RED,
                     gl.GL_UNSIGNED_BYTE,
                     ctypes.create_string_buffer(self.textmanager.img.tobytes()))
            self.textmanager.dirty = False
        self.program.uniform1i(b"tex", 0)  # set to 0 because the texture is bound to GL_TEXTURE0

        self.program.vertex_attrib_pointer(self.buffer, b"position", 4)
        # self.program.vertex_attrib_pointer(self.buffer, b"texcoord", 2, stride=4 * sizeof(gl.GLfloat), offset=2 * sizeof(gl.GLfloat))
        gl.glDrawArrays(gl.GL_QUADS, 0, len(data) // 4)

    def on_mouse_press(self, x, y, button, modifiers):
        '''forward the event to the root window'''
        self.root.on_mouse_press(x, y, button, modifiers)

    def on_resize(self, x, y):
        '''update the window manager when the opengl viewport is resized'''
        self.program.uniform2f(b'window_size', x, -y)
