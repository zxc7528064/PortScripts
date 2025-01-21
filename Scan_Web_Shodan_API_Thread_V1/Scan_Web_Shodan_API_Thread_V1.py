# -*- coding: utf-8 -*-
"""
Created on Tue Dec  3 10:42:35 2019

@author: user
"""
import click
import time
import os
import sys
import win32com.client
import requests
import re
from shodan import Shodan
from multiprocessing import Process,Queue
#--------------------------------------------------------------
@click.command()
@click.option('-ip', help = 'Scan IP',default='127.0.0.1', show_default=True)
@click.option('-t', help = '.Txt file storage Scan IP',default='Path/.txt', show_default=True)
def Start(ip,t):
    #print(f'IP is :',ip or "IPERROR")
    #print(f'File Path is :',t or "PathERROR")
    Chick_IP = IP_test()#檢查IP
    if Chick_IP == False:
        print(time.strftime('%Y.%m.%d-%H:%M:%S', time.localtime()) + "\t|IP ADDRESS ERROR!")
        sys.exit(0)
    elif Chick_IP == True:    
        api_key_box = File_load('Path/API_KEY.txt')
        excel = win32com.client.Dispatch('Excel.Application')
        workBook1 = excel.Workbooks.Open(os.path.abspath('DeBug\log.xlsx'))
        #--------------------------------------------參數設定
        if ip != "127.0.0.1":
            try:
                print(time.strftime('%Y.%m.%d-%H:%M:%S', time.localtime()) + "\t|URL:" + ip + "\t|START FIND TITLE|")  
                Scan_Start_IP(ip,api_key_box[0])
            except:
                print('error')  
        elif ip == "127.0.0.1" and t != 'Path/.txt':
            Url_box = File_load(t)#掃描文檔檔案路徑
            for x in range(0,len(Url_box),len(api_key_box)):
                try:
                    q = Queue()
                    
                    print(time.strftime('%Y.%m.%d-%H:%M:%S', time.localtime()) + "\t|URL:" + Url_box[x] + "\t|START FIND TITLE|")  
                    ch1 = Process(target = Scan_Start,args = (Url_box[x],api_key_box[0],q,)) 
                    print(time.strftime('%Y.%m.%d-%H:%M:%S', time.localtime()) + "\t|URL:" + Url_box[x+1] + "\t|START FIND TITLE|")
                    ch2 = Process(target = Scan_Start,args = (Url_box[x+1],api_key_box[1],q,))
                    
                    ch1.start()
                    ch2.start()
                    ch1.join()
                    ch2.join()
                    for z in range(0,len(api_key_box)):
                        print(z)
                        Excel_File_write(workBook1,time.strftime('%Y.%m.%d-%H:%M:%S', time.localtime()) ,  Url_box[x+z] ,  q.get())
                        workBook1.Save()
                except:
                    print('error')   
    workBook1.Close(SaveChanges=1)

#-ip 指定單一IP搜尋
#-t  指定.txt搜尋多筆IP
#-path 秀出輸出檔案的路徑位置
#--------------------------------------------------------------
def IP_test():
    if re.search('<img src="/images/flags/tw.gif',requests.get('https://www.whois365.com/tw').text):
        return True
    else:
        return True
#--------------------------------------------txt檔案讀取
def File_load(file_path):
    File_box =[]
    with open(file_path, 'r', encoding='utf-8') as f:
        data = f.readlines()
    for x in range(len(data)):
        data_box = data[x].strip('\n')
        File_box.append(data_box)
    f.close()
    return File_box
#--------------------------------------------excel檔案寫錄
def Excel_File_write(workBook_box,text_box1,text_box2,text_box3):
    excel.Visible = -1
    workSheet = workBook_box.Sheets(1)
    last_Row_NB = workSheet.usedrange.rows.count
    workSheet.Activate
    workSheet.Cells((last_Row_NB+1), 1).Value = text_box1
    workSheet.Cells((last_Row_NB+1), 2).Value = text_box2
    workSheet.Cells((last_Row_NB+1), 3).Value = text_box3
    workBook_box.Save()
#--------------------------------------------掃描Quene版
def Scan_Start(ip_box,api_box,q):
    try:
         #country_code[country_code]
         #country_name[country_name]
         #hostnames[hostnames]
         #org[org]
        title_box = Shodan(api_box).host(ip_box)['data'][0]['http']['title']
        print(time.strftime('%Y.%m.%d-%H:%M:%S', time.localtime()) + "\t|URL:" + ip_box + "\t|Title:" + title_box + "|")
        q.put(title_box)
    except:
        print(time.strftime('%Y.%m.%d-%H:%M:%S', time.localtime()) + "\t|URL:" + ip_box + "\t|Title:Can't Find Title|")
        q.put("Can't Find Title")
#--------------------------------------------掃描IP版
def Scan_Start_IP(ip_box,api_box):
    try:
         #country_code[country_code]
         #country_name[country_name]
         #hostnames[hostnames]
         #org[org]
        title_box = Shodan(api_box).host(ip_box)['data'][0]['http']['title']
        print(time.strftime('%Y.%m.%d-%H:%M:%S', time.localtime()) + "\t|URL:" + ip_box + "\t|Title:" + title_box + "|")
    except:
        print(time.strftime('%Y.%m.%d-%H:%M:%S', time.localtime()) + "\t|URL:" + ip_box + "\t|Title:Can't Find Title|")
#--------------------------------------------主程式
if __name__=='__main__':
    Start()
