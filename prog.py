#!/usr/bin/python
# -*- coding: utf-8 -*-

import ConfigParser
import re
import os
import glob
import csv
import codecs
import datetime
import commands
import logging
import unicodecsv

#GLOBAL_
GAflg = 0
GAbody = ""
CDFPath=""
settingfile = 'setting.ini'
AttributePath=""
MetadataPath = ""
SkeletonPath = ""
sktPath = ""
Forcedwrite=False #強制書込モード(timeファイルに関わらず、全て書込)


#ファイルを取得後,GA属性だけを抽出する
def getfile(filename,results):
    try:
        file = open(filename,"r")
        data = file.read()
        #G属性のみを抜き出す
        #meat = G属性のみ head,tail = 先頭と末尾 body=G属性以外の本体
        head, body = data.split('#GLOBALattributes')
        meat, tail = body.split('#VARIABLEattributes')
        tmpmeat = meat.split('\n')
        for line in tmpmeat:
            tmp = line.rstrip('\n')
            #空白行は無視
            if(line != ''):
                results.append(tmp)
        file.close()
        return results
    except Exception as e:
        print  str(type(e))
        print  str(e.args)
        print  str(e)
    pass


#GAから必要項目だけを抜き出す
#r_ar .. 属性項目　r_br...属性内容
def extractGA(ar,r_ar,r_br):
    tmp = []
    for x in ar:
        #Attributeは"で始まるので(ヘッダー部分などを削除する)
        if re.search('"', x) != None:
            tmp.append(x)
    for i,y in enumerate(tmp):
        GAtext = "" #""配列の一時格納用配列
        match = re.findall(r'"((?:.).*?)"+',y) #""でくくられたもの全て
        match2 = re.findall(r'\s\s("\w+?")',y) #項目名のみ
        for n in match2:
            GAtext = n.strip('"')
        for m in match:
            global GAflg
            global GAbody
            #項目名だった場合は何もせず、フラグを初期化
            if(m==GAtext):
                r_ar.append(GAtext)
                if(GAflg == 1):
                    r_br.append(GAbody)
                    GAflg = 0
                    GAbody = ""
            #本文が空の時
            elif (m == " " or m == "-"):
                GAbody += "None"
                GAflg = 1
            #本文がある時
            else:
                GAbody += m
                GAflg = 1
                if(i == len(tmp)-1):
                    r_br.append(GAbody)
    return None

#設定ファイルから各種設定を読み出す
def getSetting(inifilename,CDFflg):
    try:
        global AttributePath
        global CDFPath
        global MetadataPath
        global SkeletonPath
        global sktPath
        global Forcedwrite
        inifile = ConfigParser.SafeConfigParser()
        inifile.read(inifilename)
        AttributePath = inifile.get("AttributeList","file")
        if(CDFflg != 0):
            CDFPath = inifile.get("CDF","file")
        MetadataPath = inifile.get("Metadata","file")
        SkeletonPath = inifile.get("Skeletontable","file")
        sktPath = inifile.get("sktPath","file")
        Forcedwrite = inifile.get("Forcedwrite","flg")
        return True
    except Exception as e:
        print  str(type(e))
        print  str(e.args)
        print  e.message
        print  str(e)
        print "Incorrect settingfile. Please check your setting.ini"
        print "you need setting the file. as follows"
        print "[Attribute]\nfile=*\n[CDF]\nfile=*[Metadata]\nfile=*[Skeletontable]\nfile=*\n[sktPath]\nfile=*\n[Forcedwrite]\nflg=False\n"
        return False
    pass

#設定ファイルから必須要素を読み出す
def getSettingAttribute(filename,att_ar,body_ar):
    #iniファイルを指定パスから読み出し
    inifile = ConfigParser.SafeConfigParser()
    inifile.read(filename)
    dic = {}
    #iniファイルから全ての項目を読み出す
    for section in inifile.sections():
        #一時的に辞書配列に格納した後、優先度順で並び替える
        dic[section] = inifile.get(section,"number")
    #i = Attribute , j = number(優先順位)
    for i,j in sorted(dic.items(), key=lambda x:x[1]):
        att_ar.append(i)
        body_ar.append(inifile.get(i,"data"))
    return None

#ファイル一覧を取得(*.cdfのみ)
#path 対象先のディレクトリ flg=0...cdf =1...skt
def getFileList(dirpath):
    filelist = []
    for root, dirs, files in os.walk(dirpath):
        for file in files:
            if os.path.splitext(file)[1] == u'.cdf':
                filelist.append(file)
    filelist.sort(cmp=None, key=None, reverse=False)
    return filelist

#skeletontableを使って、sktファイルを生成する
#SkeletonPath = /usr/cdf/bin/skeletontable など
def skeletontable(path):
    global sktPath
    if os.name == 'posix':
        try:
            print "Linux Mode"
            cmdtext = SkeletonPath + " -skeleton " +os.getcwd() + sktPath + " "+ os.path.abspath(path)
            commands.getoutput(cmdtext)
        except Exception as e:
            print  e.message
            print "skeletontableのパスか引数が違います \n"
    #Windows
#     elif os.name == 'nt':
#         print "Windows Mode"
#         #print os.path.abspath(i)
#         cmdtext = SkeletonPath + " -skeleton " + os.getcwd() +sktPath +" " + os.path.abspath(path)
#         commands.getoutput(cmdtext)
    #other
    else:
        print "This OS is not supported"
    return None

#ヘッダーを書き込む
def WriteHeader(ar):
    f=csv.writer(file(MetadataPath,'w'),lineterminator='\n',delimiter='\t')
    f.writerow(ar)
    print "Wrote Header"
    return None

#項目を書き込む関数
#file_ar ファイル一覧 body_ar 本文
def WriteAttribute(file_ar,body_ar):
    f=csv.writer(file(MetadataPath,'a'),lineterminator='\n',delimiter='\t')
    todaydetail  =    datetime.datetime.today()
    time = todaydetail.strftime("%Y/%m/%d %H:%M")
    for i,m in enumerate(file_ar):
        writetext = []
        #print m
        for j,n in enumerate(body_ar):
            if(n == "filename"):
                writetext.append(m)
            elif(n=="time"):
                writetext.append(time)
            else:
                writetext.append(body_ar[j])
        f.writerow(writetext)
    return None

from optparse import OptionParser

usage = 'usage: %prog [options] '
parser = OptionParser(usage=usage)
(options, args) = parser.parse_args()


#ファイル更新確認関数
#path = タイムスタンプ格納用ファイルの位置
#list = CDFファイル一覧
def gettime(path,timelist,ExArray):
    global CDFPath
    tmpCDFPath = os.path.dirname(os.path.abspath(CDFPath))
    #日時を保存するファイルの存在確認
    #中身は空でタイムスタンプだけを使用する
    if(os.path.exists(path) != True):
        #ファイルが存在しない場合,新規で作成
        f=open("time","w")
        f.write("")
        f.close()
        #初回起動時(もしくはエラー)は全てのCDFに対して処理を行う
        ExArray = timelist
        return None
    time = os.path.getmtime(path)

    for i in timelist:
        timeCDFPath =tmpCDFPath + "/" + i
        #print timeCDFPath
        if(time - os.path.getmtime(timeCDFPath) < 0.0):
            #対象CDFが更新日よりも後に作成されたものについては処理する
            #print "This CDF is new  = " + timeCDFPath
            ExArray.append(i)
            pass
        else:
            #対象CDFが更新日よりも前の物については、処理しない
            #print "This CDF is old  = " + timeCDFPath
            pass
        pass
    return None

def main():
    # CDF格納用
    Array = []
    # CDF展開先
    AttributeArray = []
    BodyArray = []
    # WEKO必須属性展開先
    SAttributeArray = []
    SBodyArray = []
    CDFflg = 0

    global CDFPath
    global sktPath
    global Forcedwrite
    #args[0] = 代表cdfの名前が入る
    #正しい引数があった場合、iniファイルからの読み込みはやめる
    if not args or len(args) != 1:
        CDFflg = 1
    Settingflg = getSetting(settingfile,CDFflg)
    if(CDFPath == ""):
        CDFPath = args[0]
    FileListArray = getFileList(os.path.abspath(os.path.dirname(CDFPath)))
    skeletontable(CDFPath)
    sktPath = sktPath + ".skt"
    if(Settingflg != False):
        getfile(os.getcwd() +sktPath, Array)
        extractGA(Array, AttributeArray, BodyArray)
        getSettingAttribute(AttributePath, SAttributeArray, SBodyArray)
        # SAttribute..項目名 SBody...項目本文
        for iii in SAttributeArray:
            str = iii + " is SAttributeArray(old)"
            print str.decode('shift-jis')
        SAttributeArray.extend(AttributeArray)
        SBodyArray.extend(BodyArray)
        for iii in SAttributeArray:
            str = iii + " is SAttributeArray"
            print str.decode('shift-jis')
        for iij in SBodyArray:
            str = iij + " is SBodyArray"
            print str.decode('shift-jis')
        # ヘッダが存在するかどうかで,この後の処理を決める
        # 1.ヘッダが存在する..追加モードでCDF要素を書き込み
        # 2.ヘッダが存在しない(ファイルが存在しない)..新規書き込みモードで1から書き込む

        Headerflg = True
        try:
            # ヘッダーを読み込んで、存在するかどうかを確認
            reader = csv.reader(file(MetadataPath, 'r'),lineterminator='\n', delimiter='\t')
        # 初めての作成で、Metadata.tsvというファイル自体が存在しなかった場合
        # ファイルが存在しなかった場合は1から作成
        except Exception as e:
            print  e.message
            print "初回設定のため、設定ファイルを新たに作成します\n"
            f = open(MetadataPath, "w")
            reader = csv.reader(open(MetadataPath,'r'),lineterminator='\n', delimiter='\t')
            Headerflg = False
        for n in reader:
            if(n > 0):
                break  # 一行目がヘッダーなので
            for p, m in enumerate(n):
                if(m != SAttributeArray[p]):
                    Headerflg = False
                    break
        print Headerflg
        # ヘッダー情報が存在しない or ヘッダー情報が間違っている時
        # ファイルを新規に作る
        ExecutionArray = []
        if(Headerflg != True):
            # .sktファイル分だけ回す i=index
            print "Undefined Header"
            if(Forcedwrite != True):
                gettime("time",FileListArray,ExecutionArray)
                WriteHeader(SAttributeArray)
                WriteAttribute(ExecutionArray, SBodyArray)
            else:
                WriteHeader(SAttributeArray)
                WriteAttribute(FileListArray, SBodyArray)

        # ヘッダー情報が正しい場合は,行末に追加する作業を行う
        else:
            print "Found Header"
            if(Forcedwrite != True):
                gettime("time",FileListArray,ExecutionArray)
                WriteHeader(SAttributeArray)
                WriteAttribute(ExecutionArray, SBodyArray)
            else:
                WriteHeader(SAttributeArray)
                WriteAttribute(FileListArray, SBodyArray)
        open("Metadata_utf8.tsv", 'wb').write(open(MetadataPath, 'rb').read().decode('shift-JIS').encode('utf-8'))

if __name__=='__main__':
    main()
