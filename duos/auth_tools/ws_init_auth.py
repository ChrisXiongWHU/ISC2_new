#coding:utf-8

from duos.duoTools import encrypt,decrypt
import base64
import random

choice = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456789'

def createRandomFields(size):
    ret = []
    for i in xrange(size):
        ret.append(random.choice(choice))
    return ''.join(ret)


CONNECTION_SETUP_PREFIX = "SYN"
CONNECTION_REPLY_PREFIX = "ACK"
EXPLICIT_SUCCEED_PREFIX = "SUCCEED"
EXPLICIT_DENIED_PREFIX = "FAILED"
EXPLICIT_AUTH_PREFIX = "AUTH"

class AuthFailedError(Exception):
    pass

def gen_b64_random_and_code(key,prefix,data=None):
    '''
    生成服务器认证码（BASE64）
    '''
    random_number = createRandomFields(20)
    cookie = prefix
    if data is not None:
        cookie += "\0%s" %(data)    
    cookie += "\0%s" %(random_number)   
    e = encrypt(key,cookie)
    return random_number,base64.b64encode(e)





def decrypt_and_validate_info(e,key,random_number,prefix=None):
    '''
    解密客户端回传信息，检验其随机数及前缀合法性，并返回除验证随机数以外的内容
    '''
    info = decrypt(key,base64.b64decode(e)).split('\0')
    random_number = random_number[::-1]
    if random_number != info[-1]:
        raise AuthFailedError()
    if prefix is not None:
        if info[0] != prefix:
            raise AuthFailedError(info)
    info.pop()
    return info
    



    




    

