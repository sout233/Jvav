import requests
import json
import re
import time
import random
import signal
import multitasking
from urllib.parse import quote
from fake_useragent import UserAgent
from tqdm import tqdm

signal.signal(signal.SIGINT, multitasking.killall)
fake_ua = UserAgent()

FORMAT_ARR = ['30216','30232','30280','30250','30251']
COLLON_REGAX = 'https://space.bilibili.com/12355462/channel/collectiondetail?sid=12422'
COLLON_URL = 'https://api.bilibili.com/x/polymer/space/seasons_archives_list?mid={MID}&season_id={SID}&sort_reverse=false&page_num={PAGE_NUM}&page_size=30'
VIDEO_INFO_URL = 'https://api.bilibili.com/x/web-interface/view?bvid='
VIDEO_STREAM_URL = 'https://api.bilibili.com/x/player/playurl?bvid={BVID}&cid={CID}&fnval=80'

def start_process():     
    input_url = input('请输入合集url: ')
    searchObj = re.search(r'bilibili.com/[0-9]*/', input_url, re.M|re.I)
    global MID
    global SID
    MID = str(searchObj.group(0).replace('/',''))
    MID = MID.replace('bilibili.com','')
    searchObj = re.search(r'sid=[0-9]*', input_url, re.M|re.I)
    SID = str(searchObj.group(0).replace('sid=',''))
    while True:
        try:
            global THREAD_NUM
            thread_num = input("请输入下载线程数：")
            THREAD_NUM = int(thread_num)+1
            break
        except:
            print("输入内容不是数字")   
    while True:
        num = input("选择下载音频音质(1-5)：\n\t(1) 64K\n\t(2) 132K\n\t(3) 192K\n\t(4) 逗比全景声\n\t(5) Hi-Res老烧\n输入序号: ")
        try:
            num = int(num)
        except:
            print('6')
        for i in range(1,6):
            if num == i:
                print(f'已选择: {FORMAT_ARR[i-1]}')
                global AUDIO_FORMAT
                AUDIO_FORMAT = FORMAT_ARR[i-1]
                return
        print('请输入正确的序号')

def get_headers():
    headers = {'User-Agent': fake_ua.random,'Referer': 'https://www.bilibili.com'}
    return headers

def get_req_dist(url):
    req = requests.get(url,get_headers())
    req_dist = json.loads(req.text)
    return req_dist

def get_cid(bvid):
    get=VIDEO_INFO_URL + bvid
    get2=json.loads(requests.get(get,get_headers()).text)
    return(get2['data']['cid'])

def get_video_stream(bvid, cid):
    url = VIDEO_STREAM_URL.replace('{BVID}', bvid)
    url = url.replace('{CID}', str(cid))
    got_dist = json.loads(requests.get(url,get_headers()).text)
    return got_dist['data']['dash']['audio']

def list_split(items, n):
    return [items[i:i+n] for i in range(0, len(items), n)]

@multitasking.task
def sub_download(video_arr):
    print(len(video_arr))
    for video in video_arr:
        bvid = video_arr[video_arr.index(video)]['bvid']
        cid = get_cid(bvid)
        audio_list = get_video_stream(bvid,cid)
        audio_url = traverse_audio_list(audio_list,AUDIO_FORMAT)
        if audio_url == None:
            audio_url = traverse_audio_list(audio_list,'30280')

        response = requests.get(audio_url, headers=get_headers())
        content = response.content
        file_name = video['title'] + '.m4s'
        file_name = re.sub('[/:*?"<>|]','-',file_name)

        head = requests.head(audio_url, headers=get_headers())
        file_size = head.headers.get('Content-Length')
        if file_size is not None:
            file_size = int(file_size)

        chunk_size = 1024
        bar = tqdm(total=file_size, desc=file_name[:15]+'...')
        with open(file_name, mode='wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                bar.update(chunk_size)
                bar.refresh()
        bar.close()

def traverse_audio_list(audio_list,audio_format):
    for _audio in audio_list:
        if str(_audio['id']) == audio_format:
            return _audio['baseUrl']
    return None

if __name__ == "__main__":
    start_process()
    video_arr = []
    for i in range(1,99):
        collon_get = COLLON_URL.replace('{SID}',SID)
        collon_get = collon_get.replace('{MID}',MID)
        collon_get = collon_get.replace('{PAGE_NUM}',str(i))
        req_dist = get_req_dist(collon_get)
        print(f'正在获取第{i}页数据')
        req_arch = req_dist['data']['archives']
        if req_arch != []:
            for video in req_arch:
                video_arr.append(video)
        else:
            break
    print(f'已获得{len(video_arr)}个视频')
    start_time = time.time()
    _vlist = list_split(video_arr, round(len(video_arr)/THREAD_NUM))
    for _v in _vlist:
        sub_download(_v)
    multitasking.wait_for_tasks()
    end_time = time.time()
    print(f'已完成, 耗时{end_time-start_time}s')
