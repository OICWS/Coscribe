---
title: スキルとプラグイン
description: 作業のやり方を一度 Coscribe に教え、他の人が作ったスキルを追加し、オンとオフを切り替えます。
---

スキルとは、1 種類の作業のための指示のまとまりです。たとえば、チームでの週報の書き方などです。作業がスキルの説明に合うと、Coscribe はそのスキルに従います。Coscribe にはいくつかの組み込みスキルがあり、自分のスキルを追加することもできます。

## スキルを使う {#use-a-skill}

何もする必要はありません。合うときは Coscribe がスキルを選びます。意図して使うには、メッセージ欄に <kbd>/</kbd> と入力して一覧から選ぶか、スラッシュの後にスキル名を入力し、続けて依頼を書きます。

## 作業をスキルとして保存する {#save-a-job-as-a-skill}

会話で作業を終えた後、そのやり方を残しておけます。

- `/create-skill` の後に名前を入力します。
- または、複数の手順からなる作業の後に Coscribe が **Save this job?** と提案したら、**Save as skill** を選びます。

**Settings** › **Skills** › **Add** › **Create with Coscribe** から始めることもできます。会話が開き、スキルの内容を説明できます。

## 他の人が作ったスキルを追加する {#add-skills-others-made}

**Settings** › **Skills** で:

- **Discover** には、[github.com/anthropics/skills](https://github.com/anthropics/skills) と [github.com/anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) のオープンソースのスキルが並びます。多くはプラグイン、つまりスキルのまとまりとして提供されます。開くと、含まれるスキル、使うコネクター、ライセンスを確認できます。**Add** でそのすべてのスキルをダウンロードします。
- **Add** › **Upload a skill** では、受け取ったスキルファイルを追加します。`SKILL.md`、または `.zip`、`.skill`、`.plugin` ファイルです。

> [!WARNING]
> スキルは Coscribe が従う指示です。信頼できる人のスキルだけを追加し、使う前に中身を読んでください。**Yours** で開くとファイルを確認できます。

## スキルのオンとオフ {#turn-skills-on-or-off}

**Yours** にはあなたのスキルが並びます。開くとファイルを読めます。スイッチを使うと、削除せずにオフにできます。スキルの横のメニューから削除できます。プラグインで追加したスキルを削除すると、そのプラグインのスキルがすべて削除されます。

## 1 つのフォルダー向けのスキル {#skills-for-one-folder}

フォルダーは `.coscribe/skills/` に独自のスキルを持てます。フォルダーの設定を受け入れると、そのフォルダーを使う会話でだけ適用されます。[フォルダー独自のメモとルール](../workspaces/folder-settings.md) を参照してください。

## スキルを手で書く {#write-a-skill-by-hand}

スキルは `SKILL.md` ファイルを含むフォルダーです。ファイルは `name` と `description` で始まり、その後に Markdown で指示を書きます。

```markdown
---
name: Weekly report
description: Write the weekly sales report from the order export. Use when asked for the weekly report.
---

1. Read the latest export in Reports/Exports.
2. ...
```

Coscribe がいつスキルを使うかは説明で決まります。スキルの用途と、いつ使うかを書いてください。これは Claude Code のスキルと同じ形式です。
