import sys
import logging, logging.config

import pyglet
from pyglet import gl
from pyglet.window import key

import application

window = pyglet.window.Window(resizable=True)

def initialize_gl():
    logging.info('OpenGL Version {}'.format(window.context.get_info().get_version()))
    gl.glClearColor(0.5, 0.5, 0.35, 1)

def main():
    logging.config.fileConfig('logging.conf')
    try:
        initialize_gl()
        app = application.Application(window)
        window.push_handlers(app)

        pyglet.clock.schedule_interval(app.update, 0.01)
        pyglet.app.run()
    except:
        logging.exception('Uncaught Exception')
        sys.exit(1)

if __name__ == '__main__':
    main()
