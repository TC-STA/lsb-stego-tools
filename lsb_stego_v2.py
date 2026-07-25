#!/usr/bin/env python3
"""
LSB 隐写 V2 - AES加密 + 文件嵌入 + 纠错编码
"""
import os,sys,struct
import numpy as np
from PIL import Image
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC=b'LSB2';VER=0x02;EOF=bytes(8)
F_ENCRYPT=0x01;F_FILE=0x02;F_ECC=0x04;ECC_RPT=3
SALT=b'LSB_STEGO_V2';PBKDF2_ITER=200000
NL=12;TL=16;KL=32

def derkey(pw):
    return PBKDF2HMAC(hashes.SHA256(),KL,SALT,PBKDF2_ITER).derive(pw.encode())

def ecc_enc(b):
    return ''.join(c*ECC_RPT for c in b)
def ecc_dec(b):
    return ''.join('1' if b[i:i+ECC_RPT].count('1')>ECC_RPT//2 else '0' for i in range(0,len(b)-ECC_RPT+1,ECC_RPT))

def build_pkt(data,is_file,fname,encrypt,pw,ecc):
    fn=fname.encode() if is_file else b''
    assert len(fn)<=255
    nonce=b'';tag=b'';pl=data
    if encrypt:
        aes=AESGCM(derkey(pw));nonce=os.urandom(NL)
        ct=aes.encrypt(nonce,pl,None);tag=ct[-TL:];pl=ct[:-TL]
    fl=(F_ENCRYPT if encrypt else 0)|(F_FILE if is_file else 0)|(F_ECC if ecc else 0)
    hdr=struct.pack('>4s B B I B',MAGIC,VER,fl,len(data),len(fn))+fn
    if encrypt:hdr+=nonce+tag
    bits=''.join(format(b,'08b') for b in hdr+pl+EOF)
    return ecc_enc(bits) if ecc else bits

def parse_pkt(bits,pw=''):
    for em in[False,True]:
        b=bits
        try:
            if em:b=ecc_dec(b)
        except:continue
        mi=-1
        for off in range(0,len(b)-32,8):
            try:
                if int(b[off:off+32],2).to_bytes(4,'big')==MAGIC:mi=off;break
            except:continue
        if mi<0:continue
        pos=mi
        def rb(n):nonlocal pos;v=int(b[pos:pos+n],2);pos+=n;return v
        def rbs(n):return bytes(rb(8) for _ in range(n))
        try:
            mg=rbs(4);assert mg==MAGIC
            ver=rb(8);fl=rb(8);olen=rb(32);nlen=rb(8)
            fn=rbs(nlen).decode('utf-8',errors='replace')
            enc=bool(fl&F_ENCRYPT);isf=bool(fl&F_FILE);hecc=bool(fl&F_ECC)
            if hecc!=em:continue
            no=rbs(NL) if enc else b'';tg=rbs(TL) if enc else b''
            if enc:pl=AESGCM(derkey(pw)).decrypt(no,rbs(olen)+tg,None)
            else:pl=rbs(olen)
            rbs(8)
            return{'ok':True,'data':pl,'file':fn,'isfile':isf}
        except:continue
    return{'ok':False,'err':'not found'}

def encode(img_path,out_path,msg,is_file=False,pw='',ecc=False):
    if is_file:
        with open(msg,'rb')as f:data=f.read()
        fn=os.path.basename(msg)
    else:data=msg.encode('utf-8');fn=''
    bits=build_pkt(data,is_file,fn,bool(pw),pw,ecc)
    im=Image.open(img_path).convert('RGB')
    px=np.array(im,dtype=np.uint8);h,w,_=px.shape
    total=h*w*3
    if len(bits)>total:
        cap=(total-1024)//8
        if ecc:cap//=ECC_RPT
        raise ValueError(f'图片太小, 最多{cap}字节, 需要{len(bits)//8}字节')
    fl=px.ravel()
    for i,b in enumerate(bits):fl[i]=(fl[i]&0xFE)|int(b)
    Image.fromarray(fl.reshape(h,w,3),'RGB').save(out_path,'PNG')
    print(f'OK {out_path} ({os.path.getsize(out_path)//1024}KB)')
    print(f'数据:{len(data)}B 加密:{"是"if pw else"否"} 纠错:{"是"if ecc else"否"}')

def decode(img_path,pw='',odir=''):
    im=Image.open(img_path).convert('RGB')
    b=''.join(str(p&1) for p in np.array(im,dtype=np.uint8).ravel())
    r=parse_pkt(b,pw)
    if not r['ok']:print(f'FAIL {r["err"]}');return
    d=r['data']
    if r['isfile'] and r['file']:
        op=(odir or os.path.dirname(img_path))+"/"+r['file']
        with open(op,'wb')as f:f.write(d)
        print(f'FILE -> {op} ({len(d)}B)')  
    else:print(f'TEXT: {d.decode("utf-8",errors="replace")}')

def demo():
    import time
    print('='*50)
    print('LSB V2 DEMO')
    print('='*50)
    d=os.path.dirname(os.path.abspath(__file__))or'/sdcard/星宝阁'
    print(f'\n[1] 生成测试图...')
    im=Image.new('RGB',(400,300))
    for x in range(400):
        for y in range(300):
            im.putpixel((x,y),(int(255*x/400),int(255*y/300),int(255*(x+y)/700)))
    orig=d+'/v2_orig.png';im.save(orig,'PNG')
    print(f'OK {orig}')
    print(f'\n[2] 文本+加密...')
    st1=d+'/v2_enc.png'
    encode(orig,st1,'密码666隐藏的消息!',pw='666')
    print(f'\n[3] 文件嵌入+纠错...')
    tf=d+'/secret.txt'
    with open(tf,'w')as f:f.write('Hidden file content!\nLine2\nLine3')
    st2=d+'/v2_file.png'
    encode(orig,st2,tf,is_file=True,pw='key',ecc=True)
    print(f'\n[4] 错误密码解码...')
    decode(st1,pw='wrong')
    print(f'\n[5] 正确密码解码...')
    decode(st1,pw='666')
    print(f'\n[6] 文件解码...')
    decode(st2,pw='key',odir=d)
    print(f'\n{"="*50}\nDONE\n{"="*50}')

if __name__=='__main__':
    if len(sys.argv)<2:
        print('用法:\n  encode <原图> <输出> <文本> [--password P] [--ecc]\n  encode <原图> <输出> <文件> --file [--password P] [--ecc]\n  decode <图> [--password P] [--output-dir D]\n  demo')
    elif sys.argv[1]=='demo':demo()
    elif sys.argv[1]=='encode'and len(sys.argv)>=5:
        isf='--file'in sys.argv;pw='';ec=False
        for i,a in enumerate(sys.argv):
            if a=='--password'and i+1<len(sys.argv):pw=sys.argv[i+1]
            if a=='--ecc':ec=True
        encode(sys.argv[2],sys.argv[3],sys.argv[4],isf,pw,ec)
    elif sys.argv[1]=='decode'and len(sys.argv)>=3:
        pw='';od=''
        for i,a in enumerate(sys.argv):
            if a=='--password'and i+1<len(sys.argv):pw=sys.argv[i+1]
            if a=='--output-dir'and i+1<len(sys.argv):od=sys.argv[i+1]
        decode(sys.argv[2],pw,od)
    else:print('参数错误')
