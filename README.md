# ibuprofen

轻量、快速的少年派自主学习资源抓取工具

## 特点

* 快如闪电：抓取上千条记录快至1分钟以内
* 简洁：核心代码不过百行
* 持久化缓存：除第一次抓取，其余抓取操作都只需10秒以下

## 使用方法

需安装 Python 3.7 及以上版本

```
pip install -r requirements.txt
python user.py -p 123456 100000@xxx.lexuewang.cn:8003
```

## 为什么这么快？

使用了 Python 原生协程实现 asyncio 及第三方网络库 aiohttp ，充分发挥异步 I/O 优势。

## 应用

我写了一个简单的静态HTML生成器，并且在 Github Actions 中抓取数据、生成HTML并上传。

要使用，请 Fork 此 repo ，然后在 Settings/secrets 中设置 Name 为 `ARGS` ，Value 为 `-p 密码 账号` 的 Repository secret。
