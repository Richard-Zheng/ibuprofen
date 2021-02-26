# ibuprofen

一个轻量、快速的睿易少年派自主学习数据抓取工具

A lightweight and fast RuiYi MyiPad self-learning data crawling tool

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

之后在 Actions 这个 tab 中选择 Generate HTMLs and upload ，然后 run workflow 即可。最后生成的HTML在 Artifacts 中。

### 警告

secrets 中设置的账号信息是不会公开的，但是 Actions 生成的HTML是**对所有人可见的**。因此，您应该在每次生成后手动点击 output 右侧的垃圾桶图标删除它！否则任何人都有通过您的班级信息推测出您的身份的能力，且您自主学习中的隐私信息也将被泄露。若您没有手动删除，则 Artifacts 将在 1 天后自动删除。

由于这些缺点，使用 Actions 生成HTML将在不久后废除，替代方案在不久后可用。
