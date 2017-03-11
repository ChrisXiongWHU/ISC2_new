from channels import route

from .consumers import ws_connect
from .consumers import ws_message
from .consumers import ws_disconnect


mychannel_routing = [
    route("websocket.connect",ws_connect,path=r"^/api-(?P<api_hostname>[a-zA-Z1-9]+)/(?P<identifer>[a-zA-Z1-9]{20})$"),
    route("websocket.receive",ws_message,path=r"^/api-(?P<api_hostname>[a-zA-Z1-9]+)/(?P<identifer>[a-zA-Z1-9]{20})$"),
    route("websocket.disconnect",ws_disconnect,path=r"^/api-(?P<api_hostname>[a-zA-Z1-9]+)/(?P<identifer>[a-zA-Z1-9]{20})$"),
]