import os
import channels.asgi

os.environ.setdefault("DJANGOs_SETTINGS_MODULE", "whu_isc.settings")
channel_layer = channels.asgi.get_channel_layer()