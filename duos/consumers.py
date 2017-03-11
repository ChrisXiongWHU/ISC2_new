#coding:utf-8
from channels import Group
from channels.asgi import get_channel_layer
from channels.sessions import channel_session,session_for_reply_channel
from django.core.cache import cache
from auth import auth
import json
from auth_tools import ws_init_auth
from .models import Device


EXPLICIT_REPLY_COMMAND = "EXPLICIT"

@channel_session
def ws_connect(message,api_hostname,identifer):
    message.reply_channel.send({'accept':True})
    #检查cache和数据库
    key = cache.get("device-%s-%s_key" %(identifer,api_hostname),None) or Device.objects.get(identifer=identifer).dKey
    #若未开始绑定，或未绑定
    if key is None:
        message.reply_channel.send({"close":True})

    random_number,code = ws_init_auth.gen_b64_random_and_code(key,ws_init_auth.CONNECTION_SETUP_PREFIX)

    message.channel_session["key"] = key
    message.channel_session["auth"] = False
    message.channel_session["setup_random"] = random_number

    message.reply_channel.send({'text':code})





@channel_session
def ws_message(message,api_hostname,identifer):
    #若已经过认证（已建立合法通道）
    if message.channel_session['auth']:
        try:
            content = json.loads(message.content['text'])
        except:
            message.reply_channel.send({"text":"Your data format should be json"})
        key = message.channel_session["key"]
        if content["action"] == EXPLICIT_REPLY_COMMAND:
            random = cache.get("device-%s-%s_explicit_random" %(identifer,api_hostname),None)

            if random is None:
                message.reply_channel.send({"text":"{'info':'The explicit auth is timeout'}"})

            try:
                prefix, = ws_init_auth.decrypt_and_validate_info(content["info"],key,random)
            except Exception,e:
                del_chanell_session(message,'key','auth')
                message.reply_channel.send({"close":True})
            else:
                if prefix == ws_init_auth.EXPLICIT_SUCCEED_PREFIX:
                    cache.set("device-%s-%s_auth" %(identifer,api_hostname),True,30)
                elif prefix == ws_init_auth.EXPLICIT_DENIED_PREFIX:
                    cache.set("device-%s-%s_auth" %(identifer,api_hostname),False,30)
        else:
            message.reply_channel.send({"text":message.content["text"]})

    else:
        key = message.channel_session['key']
        info = message.content['text']
        random = message.channel_session['setup_random']
        try:
            prefix, = ws_init_auth.decrypt_and_validate_info(info,key,random,ws_init_auth.CONNECTION_REPLY_PREFIX)
            del_chanell_session(message,'setup_random')
        except Exception,e:
            message.reply_channel.send({"text":str(e)})
            del_chanell_session(message,'key','auth')
            message.reply_channel.send({"close":True})
        else:
            #认证通过,置session位，并将其加入Group
            message.channel_session['auth'] = True
            message.reply_channel.send({"text":"Auth Passed.The connection established"})
            Group("device-%s-%s" %(identifer,api_hostname)).add(message.reply_channel)



@channel_session
def ws_disconnect(message,api_hostname,identifer):
    del_chanell_session(message,'key','auth')
    Group("device-%s-%s" %(identifer,api_hostname)).discard(message.reply_channel)



def del_chanell_session(message,*sessions):
    for session in sessions:
        if session in message.channel_session:
            del message.channel_session[session]


def get_session_from_group(group_name,session=None):
    channel_list = get_channel_layer().group_channels(group_name).keys()
    sessions = session_for_reply_channel(channel_list[0])
    if session is not None:
        sessions = sessions.get(session,None)
    return sessions

def get_session_from_channels(channels_list,session=None):
    channel_list = channels_list.keys()
    sessions = session_for_reply_channel(channel_list[0])
    if session is not None:
        sessions = sessions.get(session,None)
    return sessions
    

        
        