from fractions import Fraction

import gi
from pydantic import AnyHttpUrl
from toml.encoder import TomlEncoder

gi.require_version('Gio', '2.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Rsvg', '2.0')
gi.require_version('Gst', '1.0')
from gi.repository import GdkPixbuf, Gst


class MyTomlEncoder(TomlEncoder):
    def __init__(self, _dict=dict, preserve=False):
        super().__init__(_dict, preserve)
        self.dump_funcs[AnyHttpUrl] = lambda x: str(x)


def get_device_path(device: Gst.Device):
    type_name = device.__class__.__name__
    # GstPipeWireDevice doesn't have dedicated GIR binding yet,
    # so we have to access its "device.path" in general GStreamer way
    if type_name == 'GstPipeWireDevice':
        properties = device.get_properties()
        return properties['device.path']
    # Assume GstV4l2Device
    return device.get_property('device_path')


def scale_pixbuf(pixbuf: GdkPixbuf.Pixbuf, outer_width: int, outer_height):
    # Get original size
    ow = pixbuf.get_width()
    oh = pixbuf.get_height()
    # Get aspect ration
    ratio = Fraction(ow, oh)
    # Try scaling to outer_height
    scaled_height = outer_height
    scaled_width = int(ratio * outer_height)
    # If it is larger than outer_width, fixed by width
    if scaled_width > outer_width:
        scaled_width = outer_width
        scaled_height = int(scaled_width / ratio)
    # Now scale with calculated size
    return pixbuf.scale_simple(scaled_width, scaled_height, GdkPixbuf.InterpType.BILINEAR)
