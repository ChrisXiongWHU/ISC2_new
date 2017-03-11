from django.conf.urls import url,handler404,handler403
from . import views

app_name = 'duos'

urlpatterns = [
    url(r'^api-(?P<api_hostname>[a-zA-Z1-9]+)/frame/auth/$',views.auth_pre,name='pre_auth'),
    url(r'^api-(?P<api_hostname>[a-zA-Z1-9]+)/(?P<iKey>[a-zA-Z1-9]{20})/frame/enroll/$',views.enroll,name='enroll'),
    url(r'^api-(?P<api_hostname>[a-zA-Z1-9]+)/(?P<identifer>[a-zA-Z1-9]{20})/frame/auth_check_ws/$',views.auth_check_ws,name='auth_check_ws'),
    url(r'^api-(?P<api_hostname>[a-zA-Z1-9]+)/(?P<identifer>[a-zA-Z1-9]{20})/frame/auth_/$',views.auth,name='auth'),
    url(r'^api-(?P<api_hostname>[a-zA-Z1-9]+)/(?P<identifer>[a-zA-Z1-9]{20})/frame/auth_redirect/$',views.auth_redirect,name='auth_redirect'),    
    url(r'^api-(?P<api_hostname>[a-zA-Z1-9]+)/(?P<identifer>[a-zA-Z1-9]{20})/frame/bind_device/$',views.bind_device,name='bind_device'),
    url(r'^api-(?P<api_hostname>[a-zA-Z1-9]+)/(?P<identifer>[a-zA-Z1-9]{20})/frame/check_bind/$',views.check_bind,name='check_bind'),    
]



