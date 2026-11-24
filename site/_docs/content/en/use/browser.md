---
title: The built-in browser
description: Let Coscribe use websites in a browser you can watch, take over and control site by site.
---

The desktop app has its own browser, shown in the **Browser** panel. Coscribe uses it in front of you: it opens pages, fills in whole forms, uploads and downloads files, saves tables (across several pages) as CSV files and pages as PDF. Sign-ins are kept between sessions, so you sign in to a site once.

> [!NOTE]
> The browser is part of the desktop app. If you run Coscribe in your own web browser instead, there is no Browser panel.

## Allow a site

The first time Coscribe wants to use a site, the Browser panel asks you:

- **Allow for this chat** lets it use the site in this conversation.
- **Always allow** adds the site to the workspace, so it is used without asking from then on.
- **Don't allow** refuses.

Each workspace keeps a level per site under **Edit workspace › Sites**: **Use without asking**, **Ask each time** or **Not in the browser**. The most specific entry wins, so `admin.example.com` can stay out while `example.com` is allowed.

## Take over

Click **Take over** to use the page yourself; Coscribe waits. Click **Allow AI** to hand it back.

When a site asks for a password, a one-time code or a captcha, Coscribe stops and asks you to deal with it. It never types a password or code you didn't give it.

## Point at something

- **Select element** lets you click a part of the page to send to the conversation.
- **Annotate** takes a picture of the page that you can mark up and send with **Add to chat**.
