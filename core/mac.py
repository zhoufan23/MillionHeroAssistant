# -*- coding: utf-8 -*-

"""

    capture the VM screen
    then use hanwang text recognize the text
    then use baidu to search answer

"""

import ctypes
import os
import time
import pyscreenshot
from PIL import Image, ImageGrab
from datetime import datetime


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), 
            ('top', ctypes.c_long), 
            ('right', ctypes.c_long), 
            ('bottom', ctypes.c_long)] 
    def __str__(self): 
        return str((self.left, self.top, self.right, self.bottom)) 

def analyze_current_screen_text(directory="."):
    """
    capture the VM screen now

    :return:
    """
    print("capture time: ", datetime.now().strftime("%H:%M:%S"))
    screenshot = pyscreenshot.grab(bbox=(50, 70, 600, 1050))

    save_screen_area = os.path.join(directory, "screenshot.png")
    save_text_area = os.path.join(directory, "text_area.png")
    screenshot.save(save_screen_area)
    parse_answer_area(os.path.join(directory, "screenshot.png"), save_text_area)
    return get_area_data(save_text_area)


def parse_answer_area(source_file, text_area_file):
    """
    crop the answer area

    :return:
    """

    image = Image.open(source_file)
    wide = image.size[0]
    # print("screen width: {0}, screen height: {1}".format(image.size[0], image.size[1]))

    region = image.crop((0, 100, wide, 500))
    region.save(text_area_file)


def get_area_data(text_area_file):
    """

    :param text_area_file:
    :return:
    """
    with open(text_area_file, "rb") as fp:
        image_data = fp.read()
        return image_data
    return ""