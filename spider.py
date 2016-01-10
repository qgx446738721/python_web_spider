# coding=utf-8
import urllib
import re
import os
import urlparse
import hashlib
import Queue
import socket
import threading
import chardet
from bs4 import BeautifulSoup

log_file = open('../build/spider_log.txt', 'w')
error_file = open('../build/spider_error.txt', 'w')


# 存储文件池
class FileStorePool:

    def __init__(self):
        self.web_page_store_path = '../build/web_src'
        self.web_page_file_id = 0
        self.doc_store_path = '../build/document'
        self.doc_file_id = 0
        self.img_store_path = '../build/img'
        self.img_file_id = 0
        self.css_store_path = '../build/css'
        self.css_file_id = 0

        # 创建文件夹
        if not os.path.exists(self.web_page_store_path):
            os.makedirs(self.web_page_store_path)
        if not os.path.exists(self.doc_store_path):
            os.makedirs(self.doc_store_path)
        if not os.path.exists(self.img_store_path):
            os.makedirs(self.img_store_path)
        if not os.path.exists(self.css_store_path):
            os.makedirs(self.css_store_path)

        # 创建id文件
        self.web_page_id_file = open('%s/id.txt' % self.web_page_store_path, 'w')
        self.doc_id_file = open('%s/id.txt' % self.doc_store_path, 'w')
        self.img_id_file = open('%s/id.txt' % self.img_store_path, 'w')
        self.css_id_file = open('%s/id.txt' % self.css_store_path, 'w')

    # 获取文件存储路径名
    def get_store_path(self, file_name):
        res = None
        ex_name = file_name[file_name.find('.'):]
        if re.search(r'(.html)|(.htm)|(.xml)|(.php)|(.jsp)|(.asp)', file_name):
            res = '%s/%d%s' % (self.web_page_store_path, self.web_page_file_id, ex_name)
            self.web_page_file_id += 1
        elif re.search(r'(.doc)|(.xls)|(.pdf)', file_name):
            res = '%s/%d%s' % (self.doc_store_path, self.doc_file_id, ex_name)
            self.doc_file_id += 1
        elif re.search(r'(.jpg)|(.png)|(.gif)', file_name):
            res = '%s/%d%s' % (self.img_store_path, self.img_file_id, ex_name)
            self.img_file_id += 1
        elif '.css' in file_name:
            res = '%s/%d%s' % (self.css_store_path, self.css_file_id, ex_name)
            self.css_file_id += 1
        return res

    # 存储文件id和文件名和url
    def save_file_id_and_url(self, save_name, src_abs_url, title=None):
        ex_name = save_name[save_name.find('.'):]
        if re.search(r'(.html)|(.htm)|(.xml)|(.php)|(.jsp)|(.asp)', save_name):
            if title:
                self.web_page_id_file.write('%s\t\t%s\t\t' % (save_name, src_abs_url.encode('utf-8')))
                self.web_page_id_file.write(title.encode('utf-8'))
                self.web_page_id_file.write('\r\n')
            else:
                self.web_page_id_file.write('%s\t\t%s\r\n' % (save_name, src_abs_url))
        elif re.search(r'(.doc)|(.xls)|(.pdf)', save_name):
            self.doc_id_file.write('%s\t\t%s\r\n' % (save_name, src_abs_url.encode('utf-8')))
        elif re.search(r'(.jpg)|(.png)|(.gif)', save_name):
            self.img_id_file.write('%s\t\t%s\r\n' % (save_name, src_abs_url.encode('utf-8')))
        elif '.css' in save_name:
            self.css_id_file.write('%s\t\t%s\r\n' % (save_name, src_abs_url.encode('utf-8')))

store_pool = FileStorePool()


class DownloadUrl:
    filter_host_name = 'computer.hdu.edu.cn'

    def __init__(self, url, host, father_abs_path):
        if isinstance(url, unicode):
            url = url.encode('utf-8')
        self.url = url
        if isinstance(host, unicode):
            host = host.encode('utf-8')
        self.host = host
        if isinstance(father_abs_path, unicode):
            father_abs_path = father_abs_path.encode('utf-8')
        self.father_abs_path = father_abs_path

    # get the store file name
    def get_file_name(self):
        abs_url = self.get_abs_url()
        url_parse = urlparse.urlparse(abs_url)
        file_name = os.path.basename(url_parse.path)
        query = self.get_query()

        if query or not file_name or ('.' not in file_name):
            return 'index.html'
        else:
            file_name = re.sub(r'(.php)|(.aspx)|(.jsp)', '.html', file_name)
            return file_name

    # get query after md5
    def get_query(self):
        try:
            abs_url = self.get_abs_url()
            url_parse = urlparse.urlparse(abs_url)

            return url_parse.query
        except Exception, e:
            print e
        return None

    # get abs url link
    def get_abs_url(self):
        abs_url = re.sub(r'(\./)|(\.\./)', '', urlparse.urljoin(self.father_abs_path, self.url))
        abs_url = re.sub(r'(////)|(///)|(//)', '/', abs_url)
        abs_url = re.sub(r'(http:/)|(https:/)', 'http://', abs_url)
        return abs_url

    # get the md5 value of abs_url
    def get_md5(self):
        md5_builder = hashlib.md5()
        md5_builder.update(self.get_abs_url())
        return md5_builder.hexdigest()

    # get the abs path
    def get_abs_path(self):
        abs_url = self.get_abs_url()
        url_parse = urlparse.urlparse(abs_url)
        return "http://%s/%s" % (url_parse.hostname, url_parse.path)


# get all link string in a html page
def get_all_href_list(root_my_url, soup, file_encode):

    root_parse = urlparse.urlparse(root_my_url.get_abs_url())
    href_list = []

    if not root_parse.hostname:
        return href_list

    # get tags' href
    tag_list = soup.find_all(['a', 'img', 'link'])
    href_filter = r'#|\n|(mailto:)'

    for tag in tag_list:
        add_my_url = DownloadUrl(None, None, root_my_url.get_abs_path())

        if tag.get('href') and not re.search(href_filter, tag.get('href')):
            add_my_url.url = tag.get('href')
        elif tag.get('src'):
            add_my_url.url = tag.get('src')

        if add_my_url.url:
            temp_parse = urlparse.urlparse(add_my_url.url)
            if temp_parse.hostname:
                add_my_url.host = temp_parse.hostname
            else:
                add_my_url.host = root_parse.hostname
            href_list.append(add_my_url)

    return href_list


class DownloadThread(threading.Thread):

    def __init__(self, my_url, url_queue, thread_pool):
        threading.Thread.__init__(self)
        self.url_queue = url_queue
        self.my_url = my_url
        self.thread_pool = thread_pool

    def run(self):
        try:
          self.download_url(self.my_url)
        except Exception, e:
            print 'download error at: %s' % self.my_url.get_abs_url()
            error_file.write('download error at: %s\n' % self.my_url.get_abs_url())

        self.thread_pool.release()
        return

    # download page
    def download_url(self, my_url):
        root = urlparse.urlparse(my_url.get_abs_url())
        # judge if is local host
        if root.hostname and not re.search(DownloadUrl.filter_host_name, root.hostname):
            return

        # generate absolute url
        root_abs_url = my_url.get_abs_url()

        # print "start download page: %s" % root_abs_url

        # get the path and filename
        file_name = my_url.get_file_name()
        store_path = store_pool.get_store_path(file_name)

        if not store_path:
            return

        # if is picture save it
        if re.search(r'(.jpg)|(.png)|(.gif)|(.doc)|(.zip)|(.rar)|(.xls)', file_name):
            urllib.urlretrieve(root_abs_url, store_path)
            store_pool.save_file_id_and_url(os.path.basename(store_path), root_abs_url)
            return

        html = urllib.urlopen(root_abs_url).read()
        file_encode = chardet.detect(html)['encoding']
        soup = BeautifulSoup(html, "html.parser")
        title = None
        if soup.title:
            title = soup.title.string
            title
            if not isinstance(title, unicode):
                title = title.decode(file_encode)
        res_link_list = []

        # get link
        css_link_list = re.findall(r'url\([^\)]*\)', html)
        for css_link in css_link_list:
            css_link = re.sub(r'(url\()|\)', '', css_link)
            item = DownloadUrl(css_link, root.hostname, my_url.get_abs_path())
            res_link_list.append(item)
        if '.html' in file_name:
            ret_url_list = get_all_href_list(my_url, soup, file_encode)
            for ret_url in ret_url_list:
                res_link_list.append(ret_url)

        # save page
        out_file = open(store_path, "w")
        out_file.write(html)
        print 'download at: %s' % root_abs_url
        print 'store to %s' % store_path
        log_file.write('download at: %s\n' % root_abs_url)
        log_file.write('store to %s\n' % store_path)
        store_pool.save_file_id_and_url(os.path.basename(store_path), root_abs_url, title)

        for next_my_url in res_link_list:
            if DownloadUrl.filter_host_name in next_my_url.host:
                self.url_queue.put(next_my_url)

        return


class Spider:
    thread_num = 1

    def __init__(self):
        self.url_queue = Queue.Queue()
        self.thread_pool = threading.BoundedSemaphore(value=self.thread_num)
        self.visited = {}

    # 主函数开始
    def run(self, root_url, root_host):
        # 重置存储池
        global store_pool
        store_pool = FileStorePool()

        # 设置过滤路径
        DownloadUrl.filter_host_name = root_host

        socket.setdefaulttimeout(6)
        root_my_url = DownloadUrl(root_url, root_host, None)
        self.url_queue.put(root_my_url)

        # if has thread running or url_queue is not empty
        while True:
            try:
                top = self.url_queue.get(timeout=30)
            except Exception:
                print '网站爬取完成'.decode('utf-8')
                break

            abs_url = top.get_abs_url()
            try:
                md5_builder = hashlib.md5()
                md5_builder.update(abs_url)
                md5_url = md5_builder.hexdigest()
            except Exception, e:
                print 'md5 build error at: %s' % abs_url
                continue

            if self.is_visited(md5_url):
                continue

            thread = DownloadThread(top, self.url_queue, self.thread_pool)
            self.thread_pool.acquire()
            thread.start()

        error_file.close()
        log_file.close()

    def is_visited(self, md5_string):
        if not self.visited.get(md5_string):
            self.visited[md5_string] = True
            return False

        return True
