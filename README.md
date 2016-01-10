# python_web_spider
基于python的网络爬虫  

运行`python run.py` 开始计算机学院的爬虫  

未修复`BUG`  
>中文路径`md5 build error`

# 网络爬虫 设计
[TOC]

## 一、实验要求
网络爬虫是一款自动收集网络信息的应用程序，要求用`python`实现一个可以爬取一个完整网站的应用程序

## 二、系统设计
### 1. 概述
整个系统采用`python`实现，引用的第三方库有:  
1. `chardet`：用于编码检测，在 `python`中经常出现`ascii`转换的编码错误，需要用这个库来检测，`decode`和`encode`
2. `BeautifulSoup`：用于`HTML`页面的解析操作，主要获取内部的`url`地址  


### 2. 程序流程
程序主要从一个根`url`·开始获取网页，利用广度优先算法`Bfs`来爬取接下来的网页，并且把资源进行分类，分为4部分（网页，文档资源，图片，css文件）。  
**流程：**
```
1. 将根url加入访问队列
2. 访问资源是否有资源
3. 从访问队列获取一个url
4. 判断url是否未处理
5. 是够是css或者html 如果是 分析资源，获取内部链接加入访问队列
6. 存储下载资源到对应文件夹（web_page, img, css, doc）
7. 重复步骤2
```

### 3. id资源文件存储
保存到本地的是`id.后缀`格式，所以需要一个`id.txt`文件保存里面的`id -> url`的内容。

## 三、详细设计
本程序是多线程，面向对象的程序，程序中总共有4个类，它们是:  
1. `Spider`运行的主要类，所有爬虫都由他处理
2. `DownloadThread`管理下载线程的类
3. `DownloadUrl` 网页地址存储类
4. `FileStorePool`文件存储管理类

### 1. `FileStorePool`实现
先初始化路径变量
```python
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
```
> 保存的目录建立在当前运行路径的前一层文件夹下，所以如果放在根目录的话需要改路径  

开放两个接口，用于存储文件和写入id文件
```python
# 获取文件存储路径名
def get_store_path(self, file_name):

# 存储文件id和文件名和url
def save_file_id_and_url(self, save_name, src_abs_url, title=None):
```
存储文件的区分根据正则表达式对文件名识别，例如对网页的区分
```python
if re.search(r'(.html)|(.htm)|(.xml)|(.php)|(.jsp)|(.asp)', file_name):
	...
```

### 2. `DownloadUrl`的实现
`DownloadUrl`是一个存储网页url相关的类，比如绝对路径和相对路径...  
#### python中的编码问题
在编写程序的时候经常碰见一种错误

> UnicodeEncodeError: 'ascii' codec can't encode characters in position 0-1: ordinal not in range(128)  

`python`中在内存中处理字符串都为`unicode`编码，文件中的编码五花八本，例如：`GBK`、`UTF-8`...  
因此，在做编码转换时，通常需要以`unicode`作为中间编码，即先将其他编码的字符串解码（`decode`）成`unicode`，再从`unicode`编码（`encode`）成另一种编码  

`decode`的作用是将其他编码的字符串转换成`unicode`编码，如`str1.decode('gb2312')`，表示将`gb2312`编码的字符串`str1`转换成`unicode`编码

`encode`的作用是将`unicode`编码转换成其他编码的字符串，如`str2.encode('gb2312')`，表示将`unicode`编码的字符串`str2`转换成`gb2312`编码  

------
解决了编码问题后，接下来就是存储和处理网址的`url`，网页中的链接有些是绝对路径（直接相对于服务器的`host`的路径），还有一些是相对于当前网页的相对路径。  

设当前网页的**父网页**是在宽度优先遍历过程中，当前节点的父亲节点。

那么一张网页的`DownloadUrl`需要有以下信息来初始化:
1. 网站的`hostname`
2. **父网站**的访问绝对路径
3. 当前网站的路径（可以相对，也可以绝对）

因为本程序是对一个网站来爬取的，所以`hostname`是一样的，为了节省内存起见，`hostname`就设成`DownloadUrl`的静态成员
```python
class DownloadUrl:
    filter_host_name = 'computer.hdu.edu.cn'
```
#### 接口设计
设计好数据结构后，之后就是数据的处理，需要将获取到的路径和父网页合并处理，得到当前网页的访问绝对路径  

处理路径使用了`python`的`urlparse`库

```python
# 初始化函数
def __init__(self, url, host, father_abs_path):
	# 中文编码的处理
	if isinstance(url, unicode):
	    url = url.encode('utf-8')
	self.url = url
	if isinstance(host, unicode):
	    host = host.encode('utf-8')
	self.host = host
	if isinstance(father_abs_path, unicode):
	    father_abs_path = father_abs_path.encode('utf-8')
	self.father_abs_path = father_abs_path

# get the file name
def get_file_name(self):
	...
	
# get query after md5
def get_query(self):
	...

# get abs url link
def get_abs_url(self):
	abs_url = re.sub(r'(\./)|(\.\./)', '', urlparse.urljoin(self.father_abs_path, self.url))
	abs_url = re.sub(r'(////)|(///)|(//)', '/', abs_url)
	abs_url = re.sub(r'(http:/)|(https:/)', 'http://', abs_url)

 # get the md5 value of abs_url
 def get_md5(self):
	 ...

# get the abs path
def get_abs_path(self): 
```

### 3. `DownloadThread`的实现
一个`DownloadThread`就是一个下载解析线程继承自`threading.Thread`，整个应用程序总共开启了4个线程，主要考虑到一般笔记本电脑都是4核心的，当一个`DownloadThread`下载并解析完成后，就退出并销毁了，所以需要一个类或者变量来控制线程的个数。

本程序是采用生产者和消费者的模型来设计的，使用一个同步型号量来控制线程的个数，具体细节详见`Spider`的实现。

线程类的初始化需要`url`资源，访问队列，多线程控制的同步型号量。所以需要以下类：
1. 网页资源的`DownloadUrl`类实例
2. 访问队列`Queue`
3. 同步型号量`BoundedSemaphore`
```python
def __init__(self, my_url, url_queue, thread_pool):
	threading.Thread.__init__(self)
	self.url_queue = url_queue
	self.my_url = my_url
	self.thread_pool = thread_pool
```

#### 接口设计
```python
# 开始线程
def run(self):
	// 捕获到错误的时候写入错误日志文件
	
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

# get all link string in a html page
def get_all_href_list(root_my_url, soup, file_encode):
```

### 4. `Spider`的实现
`Spider`类主要用于管理各个类的资源，包括同步信号量、访问队列、线程资源...  。也是暴露给外面调用的类，实例化后只需要调用`spider.run(...)`开始下载网站

**初始化**的时候，需要初始化访问队列、线程同步型号量和访问标记表
```python
thread_num = 4

def __init__(self):
    self.url_queue = Queue.Queue()
    self.thread_pool = threading.BoundedSemaphore(value=self.thread_num)
    self.visited = {}
```

运行方法带有两个参数`(root_url, root_host)`，表示广度优先遍历的根节点信息。根据`root_url`和`root_host`初始化一个`DownloadUrl`并把它加入到访问队列`self.url_queue`中。

建立一个死循环`whilte True`，从访问队列中取出一个`url`。这里涉及到一个问题，如果直根据访问队列是否为空来判断网页是否爬取完成是不合理的。因为是多线程的程序，我有可能还有网页在下载，没有处理完。

上述问题的解决办法就是使用`python`中的队列(`Queue`)的特新。首先`Queue`是多线程安全的，访问的时候不需要加锁解锁，其次，可以给队列设置超时访问时间，也就是说调用`url_queue.get(timeout=20)`是阻塞的，当超过20秒仍没有取到元素的时候才会返回`None`。基于这个原理，我们先设置`socket`的超时时间为6秒，那么队列的超时时间应该设为 **>24秒**，安全起见取30秒。

获取到`url`后先建立`md5`数值，判断是否已经处理过这个`url`了，如果没有处理过，那么创建一个`DownloadThread`，并且执行`self.thread_pool.acquire()`。这条语句是指从同步型号量中获取一个数值，如果无法获取（同步型号量为0的时候），线程就会阻塞，只有等到其他线程处理完释放了资源才可以继续执行，这里就是线程的数量控制了。

执行分析下载，完毕。

## 四、总结
用`python`的确很方便，本次实验中主要碰到的烦人问题就是编码问题，动不动就报错。太天朝的中文编码支持真麻烦。  

进过本次实验，充分熟悉了`python`。
