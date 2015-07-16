TEXT_HEIGHT = 16
BUFFER_WIDTH = 512
BUFFER_HEIGHT = 512

import PIL.ImageFont, PIL.ImageDraw, PIL.Image

FONTFILE = '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'

class Rect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.bottom - self.top

class Block:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    @property
    def width(self):
        return self.right - self.left

class Allocation:
    def __init__(self, rect, line):
        self.refcount = 1
        self.rect = rect
        self.line = line

class TextManager:
    def __init__(self, width=512, height=512, line_height=20):
        self.font = PIL.ImageFont.truetype(FONTFILE, 16, encoding='unic')
        self.allocations = {}
        self.width = width
        self.height = height
        self.line_height = line_height
        self.img = PIL.Image.new('L', (width, height), color=0)
        self.draw = PIL.ImageDraw.Draw(self.img)
        self.allocated = {}
        self.freespace = []
        self.dirty = False
        print (len(self.img.tobytes()), 512 * 512)

    def dump(self):
        self.img.save('textmanager.png')

    def _allocate(self, text):
        w, h = self.font.getsize(text)
        if h > self.line_height:
            raise Exception('text too high')
        if w > self.width:
            raise Exception('text too wide')

        for (i, line) in enumerate(self.freespace):
            for block in line:
                if block.width > w:
                    rect = Rect(block.left, i * self.line_height, block.left + w, (i + 1) * self.line_height)
                    block.left = rect.right
                    self.allocated[text] = Allocation(rect, i)
                    return rect

        i = len(self.freespace)
        if (i + 1) * self.line_height > self.height:
            raise Exception('out of image space')
        line = [Block(w, self.width)]
        self.freespace.append(line)
        rect = Rect(0, i * self.line_height, w, (i + 1) * self.line_height)
        self.allocated[text] = Allocation(rect, i)
        return rect

    def alloc(self, text):
        if text in self.allocated:
            self.allocated[text].refcount += 1
            return self.allocated[text].rect

        self.dirty = True
        rect = self._allocate(text)
        self.draw.rectangle((rect.left, rect.top, rect.right, rect.bottom), fill=0)
        self.draw.text((rect.left, rect.top), text, font=self.font, fill=255)
        return rect

    def free(self, text):
        if text not in self.allocated:
            raise Exception('double free')

        alloc = self.allocated[text]
        alloc.refcount -= 1
        if alloc.refcount <= 0:
            line = self.freespace[alloc.line]
            del self.allocated[text]
            for i, block in enumerate(line):
                if block.right == alloc.rect.left:
                    block.right = alloc.rect.right
                    if i + 1 < len(line) and line[i + 1].left == block.right:
                        block.right = line[i + 1].right
                        del line[i + 1]
                    return
                if block.left == alloc.rect.right:
                    block.left = alloc.rect.left
                    return
            line.append(Block(alloc.rect.left, alloc.rect.right))
            line.sort(key=lambda block:block.left)

