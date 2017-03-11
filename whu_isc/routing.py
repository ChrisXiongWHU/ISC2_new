from channels import include


channel_routing = [
    include("duos.routing.mychannel_routing",path=r"^"),
]