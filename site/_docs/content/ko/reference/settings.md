---
title: 설정
description: coscribe 설정의 모든 페이지와 각 설정이 하는 일.
---

오른쪽 위의 톱니바퀴로 설정을 엽니다. 데스크톱 앱에서는 <kbd>Ctrl</kbd> + <kbd>,</kbd>로도 열 수 있습니다. 위쪽의 검색 상자로 설정을 이름으로 찾을 수 있습니다.

## General {#general}

| 설정 | 하는 일 |
|---|---|
| **Theme** | 밝게, 어둡게, 또는 Windows와 같게. |
| **Interface font** | 메뉴, 패널, 대화의 글꼴. Figtree, 시스템 글꼴, OpenDyslexic 중에서 고릅니다. |
| **Motion** | **Reduced**로 하면 스트리밍 답변 등의 애니메이션을 줄입니다. |
| **Conversation view** | **Simple**은 각 답변을 그 뒤의 단계 없이 보여 주고, coscribe가 하는 일을 한 줄로 표시합니다. **Detailed**는 모든 단계를 보여 줍니다. |
| **What should Coscribe call you?** | 홈 화면 인사말에 쓰는 이름. |
| **Default model** | 새 대화가 시작할 때 쓰는 모델. 대화마다 자체 모델 선택기에서 바꿀 수 있습니다. |
| **Default mode** | 새 대화가 시작할 때의 [권한 모드](../get-started/first-conversation.md#permission-modes). |
| **Global instructions** | coscribe가 항상 알아야 할 것. [지침](../customize/instructions.md)을 참고하세요. |
| **Prompt suggestions** | 답변 뒤에 메시지 상자에 다음 메시지를 제안합니다. <kbd>Enter</kbd>로 보내고, <kbd>Tab</kbd>으로 상자에 넣어 편집합니다. 사용량이 조금 늘어납니다. |
| **Background agents** | 대화를 계속하는 동안 백그라운드에서 실행되는 도우미에게 coscribe가 작업을 넘길 수 있게 합니다. 사용량이 많이 들 수 있습니다. |
| **Archive inactive conversations** | 활동이 없는 대화를 7일, 30일, 90일 뒤에 보관하거나 보관하지 않습니다. 열려 있거나 작업이 진행 중인 대화는 보관하지 않습니다. |
| **Keep running in the background** | 창을 닫아도 coscribe가 알림 영역에 남아 예약 작업이 계속 실행됩니다. 끄면 창을 닫을 때 종료됩니다. |
| **Notifications** | **All**(모든 작업 실행), **Problems only**(실행이 실패했거나 사용자를 기다림), **Off**. |
| **Draw attention when Coscribe needs you** | 답변이 끝나거나 coscribe가 사용자를 기다릴 때, 창이 앞에 있지 않으면 작업 표시줄 버튼을 깜박입니다. |
| **Keep computer awake while Coscribe works** | 답변 중에 PC가 절전 모드로 들어가지 않게 해서 긴 작업을 끝낼 수 있게 합니다. 화면은 꺼질 수 있고, 덮개를 닫으면 절전 모드로 들어갑니다. **Keep awake on battery power**는 배터리 사용 중에도 같은 일을 합니다. |
| **Proxy** | coscribe가 인터넷에 연결하는 방법. **System**, **Manual**(주소, 직접 연결할 호스트, 사용자 이름과 비밀번호), **No proxy**. |

## Workspaces {#workspaces}

내 [워크스페이스](../workspaces/workspaces.md) 목록입니다. **New**로 추가하고, 각 워크스페이스의 **⋯** 메뉴에서 편집하거나 삭제합니다. **Allowed folders**는 워크스페이스 기본 폴더 밖의 폴더와 각각의 접근 수준을 담은 하나의 목록이며, 워크스페이스는 그중 고른 폴더에만 접근합니다. [허용된 폴더](../workspaces/workspaces.md#allowed-folders)를 참고하세요.

## Providers {#providers}

연결한 모델 서비스와 각 서비스에서 켠 모델. [모델 공급자 추가](../get-started/providers.md)를 참고하세요.

## Capabilities {#capabilities}

| 설정 | 하는 일 |
|---|---|
| **Create and edit files** | 워크스페이스 폴더에서 coscribe가 파일을 쓰고 바꿀 수 있게 합니다. 끄면 읽기만 하고 대화로 답합니다. |
| **Artifacts** | 대화 옆에 열리는 문서, 디자인, 대시보드. [문서, 디자인, 대시보드](../office/artifacts.md)를 참고하세요. |
| **Run scripts** | 기본 제공 도구로는 너무 큰 작업에 대해 coscribe가 Python 또는 Node.js 스크립트를 쓰고, 승인을 받은 뒤 워크스페이스 폴더 범위에서 실행합니다. [스크립트와 격리](../workspaces/workspaces.md#scripts-and-isolation)를 참고하세요. |
| **Run commands** | git이나 설치 프로그램처럼 스크립트로 할 수 없는 일을 위한 cmd 또는 PowerShell 명령줄. 하나하나 승인합니다. **Command sandbox**와 **Private folders**로 명령이 접근할 수 있는 범위를 정합니다. |
| **Chats can hand tasks to Code** | 대화가 코딩 에이전트인 Codex에 코딩 작업을 넘길 수 있게 합니다. **Model for code**로 모델을 고르고, **Change files without asking**을 켜면 변경마다 묻지 않고 편집합니다. |
| **Python for scripts**, **Packages for scripts** | 스크립트를 실행하는 Python과, 스크립트가 쓸 수 있는 추가 Python 및 Node.js 라이브러리. |
| **LibreOffice**, **Codex** | 선택 다운로드 항목으로, 여기서 설치, 업데이트, 제거합니다. LibreOffice는 페이지 미리 보기를 만듭니다. |

## Secrets {#secrets}

한 번 추가한 뒤 필요한 워크스페이스에 주는 키와 토큰입니다. coscribe는 사용자가 허용한 호스트로 보내는 웹 요청에서만 시크릿을 쓸 수 있고, 모델은 그 값을 절대 보지 못합니다. 값은 메시지, 도구 결과, 로그에서 빠집니다. 시크릿은 일반 파일이 아니라 Windows 자격 증명 관리자에 보관됩니다.

> [!IMPORTANT]
> 이것은 모델이 읽는 내용에 값이 들어가지 않게 할 뿐입니다. 값을 찾아 나서는 프로그램을 막아 주지는 않습니다. coscribe가 내 PC에서 실행하는 모든 것은 사용자 권한으로 실행되므로 자격 증명 저장소를 직접 읽을 수 있습니다.

## Skills, Connectors, Design systems {#skills-connectors-design-systems}

[스킬과 플러그인](../customize/skills.md), [커넥터](../customize/connectors.md), [디자인 시스템](../customize/design-systems.md)을 참고하세요.
