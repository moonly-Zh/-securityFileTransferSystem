import socket
import struct
import pickle
import time
import os
import json
import platform
import ctypes

server_ip = '127.0.0.1'  
server_port = 9878                                                  #服务器的ip和端口    
filedir = os.path.dirname(os.path.abspath(__file__))                #此文件当前目录
header_struct = struct.Struct('1024s')                              #以1024长度的字节流作为数据头的格式
LOGIN_FLAG = 0                                                      #判断是否登录的标识

'''def sturcts:                                                     #数据头的结构
    cmd                                                             #操作符
    分为D下载 U上传 L登录 E退出
    
    ack                                                             #状态标识符
    cmd=D时 {ack=Y,yes,ack=N,no}
    cmd=U时 {ack=Q，客户端发送一条确认消息，ack=S,服务器回复上传完，ack=Y，服务器同意上传，ack=N，no}
    cmd=L时 {ack=Y,yes,ack=N,no}
    username                                                        #登录账号    
    password                                                        #密码
    
    元数据：
    filename                                                        #上传或下载的数据名称
    filesize                                                        #文件大小 磁盘剩余空间判断要用
    filectime                                                       #文件创建时间
'''


def cipan(filesize): #检查磁盘剩余空间是否够用
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p('C:\\'), None, None, ctypes.pointer(free_bytes))
        if free_bytes.value>filesize+1000:
            return 1
        else:
            return 0
    else:
        st = os.statvfs('/home/')
        if ((st.f_bavail * st.f_frsize)*1024)>filesize+100000:
            return 1
        else:
            return 0

def packheader(header): #打包数据头
    a = pickle.dumps(header)                                       #序列化
    b = header_struct.pack(a)                                      #结构体打包
    return b

def getdir(): #获取客户端目录
    a = os.listdir(filedir)
    print("客户端文件目录")
    print("-"*80)
    print(a)
    print("-"*80)
    return a

def getserverdir(client): #获取服务器目录

    a=client.recv(1024)
    b=a.decode()
    c=json.loads(b)
    print("服务器文件目录")
    print("-"*80)
    print(c)
    print("-"*80)
    return c

def login(client,username,password): #登录
    header = {
           'cmd' : 'L',
           'ack' : 'Y',
           'username' : username,
           'password' : password
        }

    headerstr = packheader(header)

    client.send(headerstr)
    
def dheader(filename,filesize): #生成下载数据头
    if cipan(filesize):
        
        header = {
                    'cmd' : 'D',
                    'ack' : 'Y',    
                    'filename' : filename
                }
        return header
    else:
        header = {
                    'cmd' : 'D',
                    'ack' : 'N',
                    'filename' : filename
                }
        return header

def uheader(filename,ack): #生成上传数据头
    filepath = os.path.join(filedir, filename)   
    header =    {
                    'cmd' : 'U',
                    'ack' : ack,
                    'filename' : filename,
                    'filesize' : os.path.getsize(filepath),
                    'filectime' : os.path.getctime(filepath),
                }
    return header

def eheader(): #生成退出数据头
    header =    {
                    'cmd' : 'E',
                    'ack' : 'Y',
                }
    return header

def get(client,filename,filesize,filectime): #下载
    with open('%s\\%s' % (filedir, filename), 'wb') as f:
        recv_size = 0
        while recv_size < filesize:
            res = client.recv(1024)
            f.write(res)
            recv_size += len(res)
        print("下载完成!")    
        print("元数据：")
        print('文件名：%s' % filename)
        print('文件大小：%s' % filesize)
        print('文件创建时间：%s' % time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(filectime)))

    return True
    
def send(client,filename): #上传
    filepath = os.path.join(filedir, filename)
    header = packheader(uheader(filename,'Y'))
    client.send(header)
    with open(filepath, 'rb') as f:
            for line in f:
                client.send(line)
    
    unpackheader(client,client.recv(1024))

def unpackheader(client,header): #解包并判断
    header = header_struct.unpack(header)
    header = pickle.loads(*header)
    cmd = header['cmd']
    ack = header['ack']
    global LOGIN_FLAG
    if cmd == 'D':
        if ack == 'N':
            print("要下载的文件不存在!")

        elif ack == 'Y':
            filename = header['filename']
            filesize = header['filesize']
            filectime = header['filectime']
            if (packheader(dheader(filename,filesize))):
                get(client,filename,filesize,filectime)

    elif cmd == 'U':
        if ack == 'N':
            print("服务器磁盘空间不足！")

        elif ack == 'Y':
            filename = header['filename']
            send(client,filename)
        
        elif ack == 'S':
            print("上传完成！")

    elif cmd == 'L':
        if ack == 'N':  
            print("登陆失败！")
            print(header['cmd'])

        elif ack == 'Y':
            print("登陆成功！")
            LOGIN_FLAG = 1
    
    else:
        print("未知错误")

def run(): #运行程序
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server_ip, server_port))
    b=getdir()
    a=getserverdir(client)
    while True:
        if LOGIN_FLAG == 0:
            print("请先登录：")
            username = input("请输入账号：")
            password = input("请输入密码：")
            login(client,username,password)
            unpackheader(client,client.recv(1024))
        else:
            cz = input("请选择操作：（dl|up|exit）")

            if cz == "dl":
                while True:
                    filename = input("请从上述列表中选择要下载的文件：")
                    if filename not in a:
                        print("不存在")
                        print(filename)
                    elif filename in a:

                        header = packheader(dheader(filename,filesize=0))
                        client.send(header)
                        unpackheader(client,client.recv(1024))
                        break

            elif cz == "up":
                while True:
                    filename = input("请从上述列表中选择要上传的文件：")
                    if filename not in b:
                        print("不存在")
                        print(filename)
                    elif filename in b:
                        header = packheader(uheader(filename,'Q'))
                        client.send(header)
                        unpackheader(client,client.recv(1024))
                        break
            
            elif cz == "exit":
                header = packheader(eheader())
                break

if __name__ == '__main__':
    run()



        



