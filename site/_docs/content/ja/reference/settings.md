---
title: 設定
description: Coscribe の設定の各ページと、それぞれの設定の働き。
---

設定は右上の歯車から開きます。デスクトップアプリでは <kbd>Ctrl</kbd> + <kbd>,</kbd> でも開けます。上部の検索ボックスで、設定を名前で探せます。

## General {#general}

| 設定 | 働き |
|---|---|
| **Theme** | ライト、ダーク、または Windows と同じ。 |
| **Interface font** | メニュー、パネル、会話のフォント。Figtree、システムのフォント、OpenDyslexic から選びます。 |
| **Motion** | **Reduced** にすると、ストリーミング中の返答などのアニメーションを減らします。 |
| **Conversation view** | **Simple** は各返答をその裏の手順なしで表示し、Coscribe が何をしているかを 1 行で示します。**Detailed** はすべての手順を表示します。 |
| **What should Coscribe call you?** | ホーム画面のあいさつに使う名前。 |
| **Default model** | 新しい会話が最初に使うモデル。各会話は自分のモデル選択から切り替えられます。 |
| **Default mode** | 新しい会話が最初に使う [権限モード](../get-started/first-conversation.md#permission-modes)。 |
| **Global instructions** | Coscribe に常に知っておいてほしいこと。[指示](../customize/instructions.md) を参照してください。 |
| **Prompt suggestions** | 返答の後、メッセージ欄に次のメッセージを提案します。<kbd>Enter</kbd> で送信、<kbd>Tab</kbd> で欄に入れて編集できます。使用量が少し増えます。 |
| **Background agents** | あなたが会話を続ける間、バックグラウンドで動くヘルパーに Coscribe が作業を渡せるようにします。使用量を多く消費することがあります。 |
| **Archive inactive conversations** | 7 日、30 日、90 日間活動のない会話をアーカイブします。アーカイブしない設定もできます。開いている会話や作業中の会話はアーカイブされません。 |
| **Keep running in the background** | ウィンドウを閉じても Coscribe がトレイに残り、スケジュールタスクが引き続き実行されます。オフにすると、ウィンドウを閉じると終了します。 |
| **Notifications** | **All**（すべてのタスク実行）、**Problems only**（実行が失敗した、またはあなたを待っている）、**Off**。 |
| **Draw attention when Coscribe needs you** | 返答が終わったときや Coscribe があなたを待っているときに、ウィンドウが前面になければタスクバーのボタンを点滅させます。 |
| **Keep computer awake while Coscribe works** | 返答中に PC がスリープしないようにし、長いタスクを最後まで進められるようにします。画面はオフになることがあり、ふたを閉じるとスリープします。**Keep awake on battery power** はバッテリー駆動時にも同じことを行います。 |
| **Proxy** | Coscribe がインターネットに接続する方法。**System**、**Manual**（アドレス、直接接続するホスト、ユーザー名とパスワード）、**No proxy**。 |

## Workspaces {#workspaces}

あなたの [ワークスペース](../workspaces/workspaces.md) の一覧です。**New** で追加し、各ワークスペースの **⋯** メニューで編集や削除を行います。**Allowed folders** は、ワークスペースのメインフォルダー以外のフォルダーとそれぞれのアクセス権をまとめた 1 つの一覧です。各ワークスペースは、そこから選んだフォルダーにだけアクセスできます。[許可済みフォルダー](../workspaces/workspaces.md#allowed-folders) を参照してください。

## Providers {#providers}

つないだモデルサービスと、それぞれで有効にしたモデル。[モデルプロバイダーを追加する](../get-started/providers.md) を参照してください。

## Capabilities {#capabilities}

| 設定 | 働き |
|---|---|
| **Create and edit files** | ワークスペースのフォルダー内で Coscribe がファイルを書いたり変更したりできるようにします。オフにすると、読むだけで、会話の中で答えます。 |
| **Artifacts** | 会話の横に開く Doc、デザイン、ダッシュボード。[Doc、デザイン、ダッシュボード](../office/artifacts.md) を参照してください。 |
| **Run scripts** | 組み込みツールでは大きすぎる作業のために、Coscribe が Python または Node.js のスクリプトを書き、あなたの承認後に実行します。範囲はワークスペースのフォルダーに限られます。[スクリプトと分離](../workspaces/workspaces.md#scripts-and-isolation) を参照してください。 |
| **Run commands** | git やインストーラーなど、スクリプトではできないことのための cmd や PowerShell のコマンドライン。1 つずつ承認します。**Command sandbox** と **Private folders** で、コマンドがアクセスできる範囲を設定します。 |
| **Chats can hand tasks to Code** | 会話からコーディングエージェントの Codex にコーディング作業を渡せるようにします。**Model for code** でそのモデルを選びます。**Change files without asking** をオンにすると、変更ごとに確認せずに編集します。 |
| **Python for scripts**、**Packages for scripts** | スクリプトを実行する Python と、スクリプトが使える追加の Python および Node.js ライブラリ。 |
| **LibreOffice**、**Codex** | オプションのダウンロード。ここでインストール、更新、削除します。LibreOffice はページのプレビューを作ります。 |

## Secrets {#secrets}

一度追加し、必要なワークスペースに渡すキーやトークンです。Coscribe がシークレットを Web リクエストで使えるのは、あなたが許可したホストに対してだけです。モデルがその値を見ることはありません。値はメッセージ、ツールの結果、ログから除かれます。シークレットはプレーンなファイルではなく、Windows の資格情報マネージャーに保存されます。

> [!IMPORTANT]
> これは、モデルが読む内容に値が入らないようにするものです。値を探しに行くプログラムへの防御ではありません。Coscribe があなたの PC で実行するものはすべてあなたとして実行され、キーチェーンを直接読むこともできます。

## Skills、Connectors、Design systems {#skills-connectors-design-systems}

[スキルとプラグイン](../customize/skills.md)、[コネクター](../customize/connectors.md)、[デザインシステム](../customize/design-systems.md) を参照してください。
