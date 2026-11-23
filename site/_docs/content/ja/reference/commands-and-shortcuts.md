---
title: コマンドとショートカット
description: メッセージ欄に入力できるコマンドと、coscribe のキーボードショートカット。
---

## コマンド {#commands}

メッセージ欄に <kbd>/</kbd> と入力するとコマンドの一覧が表示されます。続けて入力すると絞り込まれ、<kbd>Enter</kbd> で強調表示されたコマンドを実行します。

| コマンド | 働き |
|---|---|
| `/compact` | 会話を要約してコンテキストを空けます。[モデル、思考の深さ、コンテキスト](../use/models.md#watch-the-context) を参照してください。 |
| `/clear` | 会話をアーカイブし、同じワークスペースで新しい会話を始めます。 |
| `/fork [name]` | 会話を新しい会話にコピーして開きます。[会話をコピーする](../use/conversations.md#copy-a-conversation) を参照してください。 |
| `/init` | ワークスペースを調べ、そのルートの `OVERVIEW.md` を書くか更新します。 |
| `/create-skill <name>` | 会話を再利用できるスキルにします。[スキルとプラグイン](../customize/skills.md) を参照してください。 |
| `/doctor` | このコンピューターで coscribe に必要なものを確認します。[トラブルシューティング](../help/troubleshooting.md) を参照してください。 |
| `/<skill>` | そのスキルを依頼に使います。あなたのスキルはそれぞれの名前で一覧にあります。 |

いくつかのコマンドは、同じことをするボタンがあるため一覧にありませんが、入力すれば動きます。

| コマンド | 働き |
|---|---|
| `/plan` | **Plan** モードをオンにします。すでにオンなら **Manual** に戻します。 |
| `/accept-edits` | **Accept Edits** モードをオンにするか、**Manual** に戻します。 |
| `/auto` | **Auto** モードをオンにするか、**Manual** に戻します。 |
| `/stop` | 実行中の返答を止めます。 |
| `/saveworkflow [name]` | 会話からワークフローの下書きを作ります。[ワークフロー](../workflows/workflows.md) を参照してください。 |

## キーボードショートカット {#keyboard-shortcuts}

テキストボックスの外で <kbd>?</kbd> を押すか、右上のキーボードアイコンをクリックすると、アプリ内でショートカットを確認できます。

### どこでも {#everywhere}

| キー | 働き |
|---|---|
| <kbd>?</kbd> | ショートカットの一覧を表示します。 |
| <kbd>Esc</kbd> | ダイアログを閉じるか、メッセージの編集を取り消します。 |

### メッセージ欄で {#in-the-message-box}

| キー | 働き |
|---|---|
| <kbd>Enter</kbd> | メッセージを送信します。 |
| <kbd>Shift</kbd> + <kbd>Enter</kbd> または <kbd>Ctrl</kbd> + <kbd>Enter</kbd> | 改行します。 |
| <kbd>/</kbd> | コマンドの一覧を開きます。 |

### モデル選択で {#in-the-model-picker}

| キー | 働き |
|---|---|
| <kbd>1</kbd> ～ <kbd>9</kbd> | その番号のモデルに切り替えます。 |

### デスクトップアプリで {#in-the-desktop-app}

| キー | 働き |
|---|---|
| <kbd>Ctrl</kbd> + <kbd>N</kbd> | 新しい会話。 |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>O</kbd> | ワークスペースを選びます。 |
| <kbd>Ctrl</kbd> + <kbd>,</kbd> | 設定を開きます。 |
| <kbd>Ctrl</kbd> + <kbd>W</kbd> | 会話を離れ、新しい会話を始めます。 |
| <kbd>Ctrl</kbd> + <kbd>F</kbd> | ページ内を検索します。<kbd>F3</kbd> と <kbd>Shift</kbd> + <kbd>F3</kbd> で次と前の一致に移動します。 |
| <kbd>Alt</kbd> + <kbd>←</kbd> / <kbd>Alt</kbd> + <kbd>→</kbd> | 前のページに戻るか、もう一度進みます。 |
| <kbd>Ctrl</kbd> + <kbd>/</kbd> | ショートカットの一覧を表示します。 |
