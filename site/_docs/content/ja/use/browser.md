---
title: 内蔵ブラウザー
description: 目の前のブラウザーで coscribe に Web サイトを使わせ、いつでも操作を代わり、サイトごとに管理します。
---

デスクトップアプリには独自のブラウザーがあり、**Browser** パネルに表示されます。coscribe はあなたの目の前でこれを使います。ページを開き、フォーム全体に入力し、ファイルをアップロード・ダウンロードし、（複数ページにわたる）表を CSV ファイルに、ページを PDF に保存します。ログイン状態は保たれるので、サイトへのログインは一度だけです。

> [!NOTE]
> ブラウザーはデスクトップアプリの一部です。自分の Web ブラウザーで coscribe を使っている場合、Browser パネルはありません。

## サイトを許可する {#allow-a-site}

coscribe があるサイトを初めて使おうとすると、Browser パネルが尋ねます。

- **Allow for this chat** はこの会話でそのサイトを使うことを許可します。
- **Always allow** はそのサイトをワークスペースに追加し、以後は確認なしで使います。
- **Don't allow** は拒否します。

各ワークスペースは、**Edit workspace › Sites** にサイトごとのレベルを持ちます。**Use without asking**、**Ask each time**、**Not in the browser** のいずれかです。いちばん具体的な項目が優先されるので、`example.com` を許可しつつ `admin.example.com` を外しておけます。

## 操作を代わる {#take-over}

**Take over** をクリックすると、自分でページを操作できます。coscribe は待ちます。**Allow AI** をクリックすると戻します。

サイトがパスワード、ワンタイムコード、CAPTCHA を求めると、coscribe は止まってあなたに対応を頼みます。渡されていないパスワードやコードを入力することはありません。

## 指し示す {#point-at-something}

- **Select element** で、ページの一部をクリックして会話に送れます。
- **Annotate** はページの画像を撮り、印を付けて **Add to chat** で送れます。
