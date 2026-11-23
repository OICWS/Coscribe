---
title: トラブルシューティング
description: /doctor で PC に必要なものを確認し、よくある問題を解決し、問題を報告します。
---

## 確認を実行する {#run-a-check}

どの会話でも `/doctor` と入力します。Coscribe がこのコンピューターで必要なものを確認し、各結果をカードに表示します。問題が先に並び、それぞれの直し方も示されます。設定で直せるものは、その設定ページにリンクします。

| 確認 | 調べる内容 |
|---|---|
| **Model** | 既定のモデルが応答するか。応答しない場合は、プロバイダーのキー、アドレス、モデル名、またはネットワークと [プロキシ](../reference/settings.md#general) を確認してください。 |
| **Python for scripts** | スクリプト用の Python があるか。ない場合は、**Settings** › **Capabilities** で Coscribe 独自の Python をダウンロードします。 |
| **Node.js for scripts** | Node.js のスクリプト用に `node` と `npm` がインストールされているか。必要なら [nodejs.org](https://nodejs.org) からインストールしてください。 |
| **Office conversion** | ページのプレビュー作成や文書の変換のために、Microsoft Office または LibreOffice があるか。どちらもない場合は、Office をインストールするか、**Settings** › **Capabilities** で LibreOffice をダウンロードします。 |
| **Browser** | ブラウザーパネルとページの画像のために、Microsoft Edge または Google Chrome がインストールされているか。 |
| **Script isolation** | スクリプトを分離されたコンテナーで実行できるか。自己テストに合格するまでスクリプトはオフです。ワークスペースの設定でもう一度実行してください。 |
| **Command sandbox** | コマンドがサンドボックスで実行されるか。設定されていない場合、各コマンドはあなたの承認後、あなたとして実行されます。 |

## よくある問題 {#common-problems}

### 返答が失敗する、または返ってこない {#a-reply-fails-or-never-comes}

`/doctor` を実行し、**Model** を確認します。よくある原因は、期限切れのキー、誤ったモデル名、プロキシが必要なネットワークです。会社のネットワークが AI サービスをブロックしていることもあります。IT 部門に問い合わせるか、**Settings** › **General** › **Proxy** でプロキシを設定してください。

### Coscribe がファイルやフォルダーを開けない {#coscribe-cant-open-a-file-or-folder}

Coscribe が作業できるのは、ワークスペースと、あなたが許可したフォルダーだけです。別のフォルダーへのアクセスを求められたら許可するか、そのフォルダーをワークスペースに追加してください。[ほかのフォルダーへのアクセスを許可する](../use/approvals.md#give-access-to-another-folder) を参照してください。

同じ Word、Excel、PowerPoint ファイルを自分でも編集している場合は、依頼する前に変更を保存してください。Coscribe は、前回読んだ後にファイルが変わったことに気づくと、もう一度読み込んであなたの版に変更を加えますが、見えるのは保存された内容だけです。

### スクリプトが実行されない {#scripts-dont-run}

**Settings** › **Capabilities** で **Run scripts** がオンになっていることを確認してから、`/doctor` を実行して **Python for scripts** と **Script isolation** を確認します。

### コネクターが動かなくなった {#a-connector-stops-working}

**Settings** › **Connectors** で開きます。つながっていないと表示されたら **Retry** をクリックし、サインインの期限が切れている場合は **Sign in** をクリックします。

### スケジュールタスクが実行されなかった {#a-scheduled-task-didnt-run}

タスクは、Coscribe がウィンドウまたはトレイで動いている間だけ実行されます。**Settings** › **General** で **Keep running in the background** がオンになっていること、タスクが一時停止されていないことを確認してください。Coscribe が閉じている間に予定されていた実行は、次の起動時に 1 回実行されます。[スケジュールタスク](../workflows/scheduled-tasks.md) を参照してください。

## 問題を報告する {#report-a-problem}

[GitHub](https://github.com/OICWS/coscribe/issues/new) で報告してください。何を依頼したか、代わりに何が起きたか、`/doctor` に何が表示されたかを書いてください。

あなたの言葉を共有せずにターンがどう失敗したかを伝えるには、サイドバーで会話を右クリックし、**Export a failed turn…** を選びます。ファイルにはターンの経過が記録されます。モデル、ツール呼び出しとその失敗、トークン数と時間、各ツールエラーの冒頭です。会話の言葉は一切含まれず、何も送信されません。ファイルを保存し、誰に渡すかはあなたが決めます。

サーバーのログは `%APPDATA%\Coscribe\logs\coscribe-server.log` です。
