---
title: コネクター
description: メール、カレンダー、プロジェクト管理ツールなど、使っているサービスに Coscribe をつなぎ、そこで何をしてよいかを選びます。
---

コネクターを使うと、Coscribe が別のサービスを利用できます。メールを読む、カレンダーに予定を追加する、チケットを調べる、などです。コネクターは Model Context Protocol（MCP）を使うため、Coscribe の一覧にあるものだけでなく、どの MCP サーバーでも使えます。

## コネクターを追加する {#add-a-connector}

**Settings** › **Connectors** › **Discover** を開き、サービスを選んで **Connect** をクリックします。

- ほとんどのホスト型サービスではサインインを求められます。サインインはブラウザーでサービス自身のページに開き、サインインは一度だけです。Coscribe があなたのパスワードを見ることはありません。
- **Needs setup** と表示されたサービスでは、先にそのサービスにアプリを登録する必要があります。Coscribe が手順を案内し、必要なのは一度だけです。チームの誰かがすでに設定済みなら、**Copy a message for your admin** でその人に設定ファイルを依頼できます。

依頼にまだつないでいないサービスが必要なとき、Coscribe が会話の中でコネクターを提案することもあります。カードの **Connect** をクリックすると、つながった後に Coscribe が作業を続けます。**Not now** を選ぶとそのままになります。**Settings** › **Connectors** でいつでもつなげます。

## カスタムコネクターを追加する {#add-a-custom-connector}

一覧にない MCP サーバーには、**Add** › **Add custom connector** を選び、名前を付けてから、次のどちらかを行います。

- ホスト型サーバーの **MCP server URL** と、必要なヘッダーを入力します。キーを書き出さずにヘッダーに入れるには **Insert a secret** を使います。ヘッダーは `{{secret:NAME}}` となり、値は [Secrets](../reference/settings.md#secrets) から取られます。
- または **Run a local command instead** を選び、`npx` などのコマンド、その引数、必要な環境変数を入力します。このコンピューター上のプログラムとして、あなたの権限で実行されます。

> [!WARNING]
> ローカルコマンドは、あなたの Windows アカウントができることをすべて行えます。信頼できるサーバーだけを追加してください。

## できることを選ぶ {#choose-what-it-may-do}

**Yours** でコネクターを開くと、そのツールが **Read-only tools** と **Write/delete tools** に分かれて表示されます。ツールごとに次から選びます。

| 選択 | 動作 |
|---|---|
| **Always allow** | Coscribe は確認せずに使います。 |
| **Needs approval** | Coscribe が毎回確認します。[承認と権限モード](../use/approvals.md) を参照してください。 |
| **Blocked** | Coscribe は使えません。 |

コネクターのページには、つながっているかどうかも表示されます。つながっていない場合、**Retry** で再接続し、**Sign in** でサービスのサインインページを開きます。

## 1 つのフォルダー向けのコネクター {#connectors-for-one-folder}

フォルダーは `.coscribe/mcp.json` に独自のコネクターを持てます。フォルダーの設定を受け入れると、そのフォルダーを使う会話でだけ適用されます。[フォルダー独自のメモとルール](../workspaces/folder-settings.md) を参照してください。

## ワークフローでコネクターを使う {#use-a-connector-in-a-workflow}

コネクターのツールは [ワークフロー](../workflows/workflows.md) の手順にできます。また、コネクターに何か新しいものが現れたときにワークフローを開始できます。[イベントでワークフローを開始する](../workflows/workflows.md#start-on-an-event) を参照してください。
