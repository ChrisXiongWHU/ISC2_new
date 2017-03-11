#coding:utf-8

from django.shortcuts import render,get_object_or_404,redirect
from .models import Application,Account,User,Device,createRandomFields
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest,HttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from .duoTools import parseDuoSig,validateParams,checkUserEnrolled,signResponse,DuoFormatException,generate_aes_key,generate_captcha
from django.db.utils import IntegrityError

from django.urls import reverse
from channels import Group
from channels.asgi import get_channel_layer
from django.core.cache import cache
import requests
from duo import _parse_vals
import json
import time
from auth_tools.ws_init_auth import EXPLICIT_AUTH_PREFIX,gen_b64_random_and_code
from consumers import get_session_from_channels
from auth_tools.ws_init_auth import gen_b64_random_and_code,EXPLICIT_AUTH_PREFIX
# Create your views here.



@xframe_options_exempt
def auth_pre(request,api_hostname):
    '''
    接受request，request data为tx,parent
    对tx进行验证，未通过则返回错误
    检测user是否enroll，若未enroll进行enroll操作，否则进行验证或激活操作
    '''

    #若找不到对应的account,返回404
    try:
        account = Account.objects.get(api_hostname=api_hostname)
    except Account.DoesNotExist,e:
         return render(request,'duos/not_found.html')

    #检验参数是否错误，错误均返回403
    tx = request.GET['tx']
    #若sig存在格式错误，返回403
    try:
        sig = parseDuoSig(tx)
    except DuoFormatException,e:
        return render(request,'duos/dennied.html')
    #若sig中的ikey未注册于apihostname下，返回403
    iKey = sig['content'][1]
    try:
        app = Application.objects.get(iKey=iKey,account__api_hostname=api_hostname)
    except Application.DoesNotExist,e:
        return render(request,'duos/dennied.html')
    sKey = app.sKey
    #若sig存在信息错误或加密错误，返回403
    if not validateParams(sig,sKey):
        return render(request,'duos/dennied.html')


    #若user未enroll，进行enroll,若user已经enroll，但未激活设备，进行设备激活
    userName = sig['content'][0]
    user = checkUserEnrolled(userName,account)

    #保存sig_dict，parent,sKey供enroll和认证使用
    request.session['sig_dict'] = sig
    request.session['parent'] = request.GET['parent']
    request.session['sKey'] = sKey

    if user is None:
        enroll_url = reverse('duos:enroll',args=(api_hostname,iKey,))
        return redirect(enroll_url)
    else:
        #暂时只考虑一个设备
        device = user.device_set.all()[0]
        #若已激活，进行认证
        if device.is_activated:
            return render(request,'duos/auth.html',{
            'api_hostname':api_hostname,
            'identifer':device.identifer,
        })
        #未激活，则进行激活
        else:
            bind_url = reverse('duos:bind_device',args=(api_hostname,device.identifer))
            return redirect(bind_url)

@xframe_options_exempt
def bind_device(request,api_hostname,identifer):
    #生成二维码，秘钥并存入数据库。
    dkey = generate_aes_key()
    captcha = generate_captcha(api_hostname,identifer,dkey)
    #cache有效期设置比等待时间稍小
    cache.set("device-%s-%s_key" %(identifer,api_hostname),dkey,115)
    return render(request,'duos/bind_device.html',{
        'api_hostname':api_hostname,
        'identifer':identifer,
        'captcha':captcha,
    })



def check_bind(request,api_hostname,identifer):
    channel_layer = get_channel_layer()  
    #每10秒检查一次socket连接,最多不超过120秒
    for i in xrange(12):
        device_group_list = channel_layer.group_channels("device-%s-%s" %(identifer,api_hostname))
        if len(device_group_list)>0:
            #进行认证,数据库更新
            key = get_session_from_channels(device_group_list,"key")
            Device.objects.filter(identifer=identifer).update(dKey=key,is_activated=True)
            return HttpResponse(content=json.dumps({'status':'ok'}))
        else:
            time.sleep(10)
    # 120秒内未发现可用连接
    else:
        bind_url = reverse('duos:bind_device',args=(api_hostname,identifer))
        return HttpResponse(content=json.dumps({'status':'pending'}))


@xframe_options_exempt
def auth_redirect(request,api_hostname,identifer):
    return render(request,'duos/auth.html',{
        'api_hostname':api_hostname,
        'identifer':identifer,
    })


@xframe_options_exempt
def auth_check_ws(request,api_hostname,identifer):
    channel_layer = get_channel_layer()
    device_group_name = "device-%s-%s" %(identifer,api_hostname)
    # 每5秒检查一次socket连接,最多不超过60秒
    for i in xrange(12):
        device_group_list = channel_layer.group_channels(device_group_name)
        if len(device_group_list)>0:
            key = get_session_from_channels(device_group_list,"key")
            data = {"xxx":"xxx"}
            random,code = gen_b64_random_and_code(key,EXPLICIT_AUTH_PREFIX,data)
            cache.set("device-%s-%s_explicit_random" %(identifer,api_hostname),random,28)
            Group(device_group_name).send({"text":code})
            return HttpResponse(content=json.dumps({'status':'ok'}))
        else:
            time.sleep(5)
    # 60秒内未发现可用连接
    else:
        return HttpResponse(content=json.dumps({'status':'pending'}))





def auth(request,api_hostname,identifer):
    device_group_name = "device-%s-%s" %(identifer,api_hostname)
    device_group_list = get_channel_layer().group_channels(device_group_name)
    #若连接中断
    if len(device_group_list) == 0:
        return HttpResponse(content=json.dumps({'status':'pending'}))

    # 每5秒检查一次认证情况,最多不超过30秒
    for i in xrange(6):
        auth_status = cache.get("device-%s-%s_auth" %(identifer,api_hostname),None)
        # 认证成功
        if auth_status is True:
            sigDict = request.session.get('sig_dict',None)
            parent = request.session.get('parent',None)
            sKey = request.session.get('sKey',None)
            responseBody = signResponse(sigDict,sKey)
            return HttpResponse(content=json.dumps({
                'status':'ok',
                'data':responseBody,
                'parent':parent
            }))
        # 认证失败
        elif auth_status is False:
            return HttpResponse(content=json.dumps({'status':'denied'}))
        else:
            time.sleep(5)
    # 认证未进行
    else:
        return HttpResponse(content=json.dumps({'status':'pending'}))




@xframe_options_exempt
def enroll(request,api_hostname,iKey):
    #如果该请求为auth_pre发送
    if request.method == 'GET':
        return render(request,'duos/enroll.html', \
        {'api_hostname':api_hostname,'iKey':iKey})

    #若该请求为提交表单
    elif request.method =='POST':
        phone = request.POST['phone']
        userName = request.session.get('sig_dict',None)['content'][0]
        parent = request.session.get('parent',None)
        account = Account.objects.get(api_hostname=api_hostname)

        #防止重复提交表单，捕获实体完整性错误
        try:
            user = User.objects.create(user_name=userName,user_phone=phone,account=account)
            device = Device.objects.create(user=user,account=account,**Device.new_device(api_hostname))
        except IntegrityError,e:
            user = User.objects.get(user_name=userName)
            device = user.device_set.all()[0]
        return redirect(reverse('duos:bind_device',args=(api_hostname,device.identifer)))


        



    
        
    


    
    
    
    
