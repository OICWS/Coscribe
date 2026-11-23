---
title: 문제 해결
description: /doctor로 PC에 coscribe가 필요로 하는 것을 확인하고, 흔한 문제를 해결하고, 문제를 보고합니다.
---

## 점검 실행하기 {#run-a-check}

아무 대화에서나 `/doctor`를 입력합니다. coscribe가 이 컴퓨터에서 필요한 것을 점검하고, 결과마다 카드에 표시합니다. 문제가 먼저 나오고, 각각을 고치는 방법도 함께 나옵니다. 설정으로 고칠 수 있으면 그 설정 페이지로 연결됩니다.

| 점검 | 확인하는 것 |
|---|---|
| **Model** | 기본 모델이 응답하는지. 응답하지 않으면 공급자의 키, 주소, 모델 이름이나 네트워크와 [프록시](../reference/settings.md#general)를 확인하세요. |
| **Python for scripts** | 스크립트용 Python이 있는지. 없으면 **Settings** › **Capabilities**에서 coscribe 자체 Python을 다운로드합니다. |
| **Node.js for scripts** | Node.js 스크립트용 `node`와 `npm`이 설치되어 있는지. 필요하면 [nodejs.org](https://nodejs.org)에서 설치하세요. |
| **Office conversion** | 페이지 미리 보기와 문서 변환을 위한 Microsoft Office나 LibreOffice가 있는지. 둘 다 없으면 Office를 설치하거나 **Settings** › **Capabilities**에서 LibreOffice를 다운로드합니다. |
| **Browser** | 브라우저 패널과 페이지 그림을 위한 Microsoft Edge나 Google Chrome이 설치되어 있는지. |
| **Script isolation** | 스크립트가 격리된 컨테이너에서 실행될 수 있는지. 자체 테스트를 통과할 때까지 스크립트는 꺼져 있으며, 워크스페이스 설정에서 다시 실행할 수 있습니다. |
| **Command sandbox** | 명령이 샌드박스에서 실행되는지. 설정되어 있지 않으면 각 명령은 승인 후 사용자 권한으로 실행됩니다. |

## 흔한 문제 {#common-problems}

### 답변이 실패하거나 오지 않음 {#a-reply-fails-or-never-comes}

`/doctor`를 실행하고 **Model**을 확인합니다. 만료된 키, 잘못된 모델 이름, 프록시가 필요한 네트워크가 흔한 원인입니다. 일부 회사 네트워크는 AI 서비스를 차단합니다. IT 팀에 문의하거나 **Settings** › **General** › **Proxy**에서 프록시를 설정하세요.

### coscribe가 파일이나 폴더를 열지 못함 {#coscribe-cant-open-a-file-or-folder}

coscribe는 워크스페이스와 사용자가 허용한 폴더에서만 작업합니다. 다른 폴더를 요청하면 허용하거나, 그 폴더를 워크스페이스에 추가하세요. [다른 폴더에 접근 허용하기](../use/approvals.md#give-access-to-another-folder)를 참고하세요.

같은 Word, Excel, PowerPoint 파일을 직접 편집하고 있다면 요청하기 전에 저장하세요. coscribe는 마지막으로 읽은 뒤 파일이 바뀐 것을 알아채고 다시 읽어 사용자의 버전에 변경을 적용하지만, 저장된 내용만 볼 수 있습니다.

### 스크립트가 실행되지 않음 {#scripts-dont-run}

**Settings** › **Capabilities**에서 **Run scripts**가 켜져 있는지 확인한 다음, `/doctor`를 실행해 **Python for scripts**와 **Script isolation**을 확인합니다.

### 커넥터가 동작하지 않음 {#a-connector-stops-working}

**Settings** › **Connectors**에서 커넥터를 엽니다. 연결되어 있지 않다고 나오면 **Retry**를 클릭하고, 로그인이 만료되었다면 **Sign in**을 클릭합니다.

### 예약 작업이 실행되지 않음 {#a-scheduled-task-didnt-run}

작업은 coscribe가 창이나 알림 영역에서 실행 중일 때만 실행됩니다. **Settings** › **General**에서 **Keep running in the background**가 켜져 있는지, 작업이 일시 중지되지 않았는지 확인하세요. coscribe가 닫혀 있는 동안 예정되었던 실행은 다시 시작할 때 한 번 실행됩니다. [예약 작업](../workflows/scheduled-tasks.md)을 참고하세요.

## 문제 보고하기 {#report-a-problem}

[GitHub](https://github.com/OICWS/coscribe/issues/new)에 보고해 주세요. 무엇을 요청했는지, 대신 무엇이 일어났는지, `/doctor`에 무엇이 표시되는지 적어 주세요.

내 말을 공유하지 않고 턴이 어떻게 잘못되었는지 보여 주려면, 사이드바에서 대화를 마우스 오른쪽 단추로 클릭하고 **Export a failed turn…** 항목을 고르세요. 파일에는 턴의 진행 과정이 담깁니다. 모델, 도구 호출과 실패, 토큰과 시간, 각 도구 오류의 앞부분입니다. 대화 내용은 전혀 들어 있지 않고, 아무것도 전송되지 않습니다. 파일을 저장한 뒤 누구에게 줄지는 사용자가 정합니다.

서버 로그는 `%APPDATA%\Coscribe\logs\coscribe-server.log`입니다.
