import socket
import struct
import pickle
import time
import os
import json
import pymysql
import platform
import ctypes

db = pymysql.connect("localhost","root","123456","user")
cursor = db.cursor()
server_ip = '127.0.0.1'
server_port = 9878
filedir = os.path.dirname(os.path.abspath(__file__))
header_struct = struct.Struct('1024s')
LOGIN_FLAG = 0                                                           #判断是否登录的标识

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
    a = pickle.dumps(header)
    b = header_struct.pack(a)
    return b

def senddir(client): #发送服务器目录
    a = os.listdir()
    b = json.dumps(a)
    c = b.encode()
    client.send(c)

def login(client,username,password): #判断登录
    sql="""select USERNAME,PASSWORD 
    from USER 
    where USERNAME=%s and PASSWORD=%s"""
    try:
        # 执行sql语句
        exist=cursor.execute(sql,(username,password))
        # 提交到数据库执行
        db.commit()
        if exist:
            header = {
                    'cmd' : 'L',
                    'ack' : 'Y'
                }
        else :
            header = {
                    'cmd' : 'L',
                    'ack' : 'N'
                }
            print(username)
        header = packheader(header)
        client.send(header)
        return exist
    except:
        # 如果发生错误则回滚
        db.rollback()

def dheader(filename): #生成下载数据头
    filepath = os.path.join(filedir, filename)
    header = {
           'cmd' : 'D',
           'ack' : 'Y',
           'filename' : filename,
           'filesize' : os.path.getsize(filepath),
           'filectime' : os.path.getctime(filepath),
            }
    return header

def uheader(filename,filesize): #生成上传数据头
    if(cipan(filesize)):
        header = {
                    'cmd' : 'U',
                    'ack' : 'Y',
                    'filename' : filename
                }
    else:
        header = {
                    'cmd' : 'U',
                    'ack' : 'N',
                    'filename' : filename
                }
    return header

def get(client,filename,filesize,filectime): #从客户端接收
    filepath = os.path.join(filedir, filename)
    with open(filepath, 'wb') as f:
        recv_size = 0
        while recv_size < filesize:
            res = client.recv(1024)
            f.write(res)
            recv_size += len(res)

        header ={
            'cmd' : 'U',
            'ack' : 'S',
        }
        header=packheader(header)
        client.send(header)

def send(client,filename): #发送到客户端
    filepath = os.path.join(filedir, filename)
    header = packheader(dheader(filename))
    client.send(header)
    with open(filepath, 'rb') as f:
            for line in f:
                client.send(line)

def unpackheader(client,header): #解包并判断
    header = header_struct.unpack(header)
    header = pickle.loads(*header)
    cmd = header['cmd']
    ack = header['ack']
    global LOGIN_FLAG
    if cmd == 'D':
        if LOGIN_FLAG == 0:
            login(client,'unlogin','unlogin')
            print("未登录")
        else:
            if ack == 'Y':
                filename = header['filename']
                send(client,filename)
            elif ack == 'N':
                print("磁盘不足")

    elif cmd == 'U':
        if LOGIN_FLAG == 0:
            login(client,'unlogin','unlogin')
        else:
            if ack=='Q':
                filename = header['filename']
                filesize = header['filesize']
                header = packheader(uheader(filename,filesize))
                client.send(header)
                request = client.recv(1024)
                unpackheader(client,request)
            elif ack=='Y':
                filename = header['filename']
                filesize = header['filesize']
                filectime = header['filectime']
                get(client,filename,filesize,filectime)

    elif cmd == 'L':
        username = header['username']
        password = header['password']
        if login(client,username,password):
            LOGIN_FLAG = 1

    return 

def run():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((server_ip, server_port))
    server.listen(5)
    
    print('Server start on')
    print('-> ip: %s port: %d' %(server_ip, server_port))
    while True:
        client, client_addr = server.accept()
        senddir(client)
        print("Connect from", client_addr)
        try:
            while True:
                request = client.recv(1024)
                a=unpackheader(client,request)
                if a=='E':
                    break
                print('Send %s to %s' % (request, client_addr[0]))
            
        except ConnectionResetError:
            break

if __name__ == '__main__':
    run()