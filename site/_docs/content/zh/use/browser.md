---
title: 内置浏览器
description: 让 Coscribe 在一个你看得见的浏览器里使用网站，你随时可以接手，并逐个网站控制权限。
---

桌面应用有自己的浏览器，显示在 **Browser** 面板里。Coscribe 当着你的面使用它：打开网页、填完整张表单、上传和下载文件、把表格（跨多页）存成 CSV、把网页存成 PDF。登录状态会保留，所以一个网站只需登录一次。

> [!NOTE]
> 浏览器是桌面应用的一部分。如果你在自己的网页浏览器里使用 Coscribe，就没有 Browser 面板。

## 允许一个网站 {#allow-a-site}

Coscribe 第一次要用某个网站时，Browser 面板会问你：

- **Allow for this chat** 允许在这个对话里使用这个网站。
- **Always allow** 把这个网站加到工作区，之后使用时不再询问。
- **Don't allow** 拒绝。

每个工作区在 **Edit workspace › Sites** 里为每个网站保存一个级别：**Use without asking**、**Ask each time** 或 **Not in the browser**。最具体的条目优先，所以可以允许 `example.com`，同时把 `admin.example.com` 挡在外面。

## 接手 {#take-over}

点 **Take over** 自己操作页面，Coscribe 会等着。点 **Allow AI** 交还给它。

网站要求输入密码、一次性验证码或人机验证时，Coscribe 会停下来请你处理。它从不输入你没有给它的密码或验证码。

## 指给它看 {#point-at-something}

- **Select element** 让你点选页面的某个部分，发送到对话里。
- **Annotate** 给页面截一张图，你可以在上面标注，再用 **Add to chat** 发送。
