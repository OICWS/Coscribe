---
title: フォルダー独自のメモとルール
description: フォルダーの中身、使うスキルとコネクター、確認なしで動いてよいことを、フォルダーから coscribe に伝えます。
---

フォルダーは、その中の `.coscribe` フォルダーに coscribe 向けの指示を置けます。あなたが受け入れれば、そのフォルダーを使う会話で coscribe が読みます。

## フォルダーに置けるもの {#what-a-folder-can-hold}

| ファイル | 役割 |
|---|---|
| `.coscribe/memory.md` | このフォルダーで会話を始めるたびに coscribe が読むメモ。フォルダーの用途、決まりごと、名前など。 |
| `.coscribe/skills/<name>/SKILL.md` | このフォルダーでだけ使う [スキル](../customize/skills.md)。 |
| `.coscribe/settings.json` | 権限ルール（`allow`、`ask`、`deny`）とスクリプト用の環境変数。 |
| `.coscribe/mcp.json` | このフォルダーで使う [コネクター](../customize/connectors.md)。 |

coscribe 自身が `memory.md`、`settings.json`、`mcp.json` を書くことはありません。編集するのはあなただけです。送った添付ファイルは `.coscribe/uploads/` に保存されます。

## フォルダーの設定を受け入れる {#accept-a-folders-settings}

フォルダーの設定は、そこに書き込める誰かが置いたものかもしれません。そのため、あなたが同意するまで coscribe は従いません。**Task details** パネルに **What Coscribe knows about this folder** が表示され、フォルダーが持ち込むスキル、コネクター、ルールが **Runs without asking**、**Always asks**、**Never runs** に分けて、スクリプト用の変数とともに並びます。**Use them** をクリックして受け入れます。

これらのファイルが coscribe の外で変更されると、もう一度確認します。

## 権限ルール {#permission-rules}

`.coscribe/settings.json` は Claude Code の設定ファイルと同じ形です。

```json
{
  "permissions": {
    "allow": ["write_file(reports/*)"],
    "ask": ["run_background_command"],
    "deny": ["delete_file"]
  },
  "env": {
    "REPORT_REGION": "East"
  }
}
```

ルールは、coscribe のツール名、`*` を使った名前のパターン、またはそれらに主な引数のパターンを括弧で付けたもの（`write_file(docs/*)` など）です。ルールが決めるのは、本来なら承認を待つ操作だけです。**deny** は **ask** に、**ask** は **allow** に優先します。

次の制限は常に有効です。

- コネクター経由でメッセージを送るなど、PC の外に出る操作をルールで許可することはできません。それらは引き続き確認されます。
- `*` 単体は何も許可しません。
- `ask` ルールは **Auto** モードでも確認します。

## スクリプト用の変数 {#variables-for-scripts}

`settings.json` の `env` の値は、そのフォルダーのスクリプトとコマンドに渡されます。`PATH`、プロキシ設定、`PYTHONPATH` など、どのプログラムが動くかや通信先を変える変数は、フォルダーからは設定できません。
