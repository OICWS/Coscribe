---
title: 워크스페이스와 폴더
description: 각 대화가 접근할 수 있는 폴더, 사이트, 시크릿, 스크립트를 정합니다.
---

**워크스페이스**(workspace)는 대화가 작업하는 폴더와, 그 밖에서 접근할 수 있는 다른 폴더, 웹사이트, 시크릿, 스크립트를 함께 묶은 것입니다. 대화마다 워크스페이스 하나를 씁니다. 워크스페이스를 고르지 않은 대화는 **Default** 워크스페이스를 씁니다.

## 대화의 워크스페이스 고르기 {#pick-a-workspace-for-a-conversation}

메시지 상자 아래의 워크스페이스 선택기를 씁니다. 워크스페이스 목록과 **New workspace**가 있습니다. 다른 워크스페이스를 고르지 않은 대화는 모두 **Default** 워크스페이스를 씁니다.

## 워크스페이스 편집하기 {#edit-a-workspace}

**Settings › Workspaces**를 열고 워크스페이스의 **⋯** 메뉴에서 **Edit**를 고르거나, **New**로 새로 만듭니다. 대화 상자에는 이름, 기본 **Folder**(새 파일, 스크린샷, 아티팩트가 저장되는 곳), 그리고 접근 종류별로 한 줄씩이 있습니다. 각 줄은 현재 설정을 보여 주고 자체 페이지를 엽니다.

| 페이지 | 설정하는 내용 |
|---|---|
| **Allowed folders** | 이 워크스페이스가 쓸 수 있는 다른 폴더와 각각의 접근 수준. 다른 워크스페이스는 접근하지 못합니다. |
| **Sites** | 쓸 수 있는 웹사이트(**None**, **Listed sites**, **Any site**)와, [내장 브라우저](../use/browser.md#allow-a-site)가 목록의 각 사이트를 다루는 방식. |
| **Secrets** | 저장된 시크릿 중 웹 요청에 보낼 수 있는 것. 모델은 시크릿 값을 절대 보지 못합니다. |
| **Scripts and commands** | Python과 Node.js **Scripts**, 그리고 **Commands**를 실행할 수 있는지 여부. |
| **Environment variables** | 스크립트와 명령에 전달되는 값. |

**Sites** 선택의 의미는 다음과 같습니다.

- **None**: 웹 검색, 웹 페이지, 다운로드, 브라우저 단계가 모두 없고, 스크립트는 오프라인으로 실행됩니다.
- **Listed sites**: 목록의 사이트와 그 하위 도메인만 열고, 다운로드하고, 브라우저에서 씁니다. 검색은 계속 되고, 스크립트는 오프라인으로 실행됩니다.
- **Any site**: 모든 사이트. 사이트를 목록에 추가하면 브라우저가 그 사이트를 쓰는 방식을 고를 수 있습니다.

## 허용된 폴더 {#allowed-folders}

Coscribe가 워크스페이스의 기본 폴더 밖에서 쓸 수 있는 모든 폴더는 **Settings › Workspaces › Manage**의 **Allowed folders**라는 하나의 목록에 있습니다. 목록의 폴더마다 접근 수준(**Read only**, **Read and write**, **Read, write and delete**)이 있습니다. 워크스페이스는 자신의 **Allowed folders** 페이지에서 고른 허용 폴더에만 접근합니다. **Use an allowed folder**는 목록에서 하나를 고르고, **Add new folder…** 항목은 새 폴더를 추가하며 이 폴더는 읽기·쓰기 권한으로 목록에 들어갑니다.

**Allowed folders**에서 폴더를 빼면 모든 워크스페이스에서 빠집니다. 분리된 드라이브처럼 지금 찾을 수 없는 폴더는 표시만 되어 있다가 다시 나타나면 다시 쓰입니다.

대화에 접근할 수 없는 폴더가 필요하면 카드로 묻습니다. [다른 폴더에 접근 허용하기](../use/approvals.md#give-access-to-another-folder)를 참고하세요.

## 스크립트와 격리 {#scripts-and-isolation}

Windows에서 스크립트는 격리된 상태로 실행됩니다. 대화의 폴더만 쓸 수 있고, 그 안의 파일을 삭제하거나 이름을 바꿀 수 없으며, 워크스페이스의 **Sites** 설정이 **Any site**일 때만 인터넷에 접속합니다. Coscribe는 내 컴퓨터에서 격리가 작동하는지 한 번 확인합니다. 확인에 실패하면 스크립트가 꺼지며, **Scripts and commands** 페이지의 **Run scripts without isolation**으로 그 워크스페이스에서 다시 켤 수 있습니다. 그에 따르는 위험은 감수해야 합니다.
