---
title: 명령과 단축키
description: 메시지 상자에 입력할 수 있는 명령과 Coscribe의 키보드 단축키.
---

## 명령 {#commands}

메시지 상자에 <kbd>/</kbd>를 입력하면 명령 목록이 나타납니다. 계속 입력하면 목록이 좁혀지고, <kbd>Enter</kbd>를 누르면 강조된 명령을 실행합니다.

| 명령 | 하는 일 |
|---|---|
| `/compact` | 대화를 요약해 컨텍스트를 비웁니다. [모델, 추론 강도, 컨텍스트](../use/models.md#watch-the-context)를 참고하세요. |
| `/clear` | 대화를 보관하고 같은 워크스페이스에서 새 대화를 시작합니다. |
| `/fork [name]` | 대화를 새 대화로 복사해 엽니다. [대화 복사하기](../use/conversations.md#copy-a-conversation)를 참고하세요. |
| `/init` | 워크스페이스를 살펴보고 그 루트의 `OVERVIEW.md`를 쓰거나 새로 고칩니다. |
| `/create-skill <name>` | 대화를 재사용할 수 있는 스킬로 만듭니다. [스킬과 플러그인](../customize/skills.md)을 참고하세요. |
| `/doctor` | 이 컴퓨터에서 Coscribe에 필요한 것을 확인합니다. [문제 해결](../help/troubleshooting.md)을 참고하세요. |
| `/<skill>` | 그 스킬을 요청에 씁니다. 내 스킬은 각자의 이름으로 목록에 있습니다. |

몇몇 명령은 같은 일을 하는 버튼이 있어서 목록에 없지만, 입력하면 동작합니다.

| 명령 | 하는 일 |
|---|---|
| `/plan` | **Plan** 모드를 켭니다. 이미 켜져 있으면 **Manual**로 돌아갑니다. |
| `/accept-edits` | **Accept Edits** 모드를 켜거나 **Manual**로 돌아갑니다. |
| `/auto` | **Auto** 모드를 켜거나 **Manual**로 돌아갑니다. |
| `/stop` | 진행 중인 답변을 멈춥니다. |
| `/saveworkflow [name]` | 대화에서 워크플로 초안을 만듭니다. [워크플로](../workflows/workflows.md)를 참고하세요. |

## 키보드 단축키 {#keyboard-shortcuts}

텍스트 상자 밖 어디서든 <kbd>?</kbd>를 누르거나 오른쪽 위의 키보드 아이콘을 클릭하면 앱에서 단축키를 볼 수 있습니다.

### 어디서나 {#everywhere}

| 키 | 하는 일 |
|---|---|
| <kbd>?</kbd> | 단축키 목록을 표시합니다. |
| <kbd>Esc</kbd> | 대화 상자를 닫거나 메시지 편집을 취소합니다. |

### 메시지 상자에서 {#in-the-message-box}

| 키 | 하는 일 |
|---|---|
| <kbd>Enter</kbd> | 메시지를 보냅니다. |
| <kbd>Shift</kbd> + <kbd>Enter</kbd> 또는 <kbd>Ctrl</kbd> + <kbd>Enter</kbd> | 줄을 바꿉니다. |
| <kbd>/</kbd> | 명령 목록을 엽니다. |

### 모델 선택기에서 {#in-the-model-picker}

| 키 | 하는 일 |
|---|---|
| <kbd>1</kbd>~<kbd>9</kbd> | 그 번호의 모델로 바꿉니다. |

### 데스크톱 앱에서 {#in-the-desktop-app}

| 키 | 하는 일 |
|---|---|
| <kbd>Ctrl</kbd> + <kbd>N</kbd> | 새 대화. |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>O</kbd> | 워크스페이스를 고릅니다. |
| <kbd>Ctrl</kbd> + <kbd>,</kbd> | 설정을 엽니다. |
| <kbd>Ctrl</kbd> + <kbd>W</kbd> | 대화를 떠나 새 대화를 시작합니다. |
| <kbd>Ctrl</kbd> + <kbd>F</kbd> | 페이지에서 찾습니다. <kbd>F3</kbd>와 <kbd>Shift</kbd> + <kbd>F3</kbd>으로 다음 및 이전 결과로 이동합니다. |
| <kbd>Alt</kbd> + <kbd>←</kbd> / <kbd>Alt</kbd> + <kbd>→</kbd> | 이전 페이지로 돌아가거나 다시 앞으로 갑니다. |
| <kbd>Ctrl</kbd> + <kbd>/</kbd> | 단축키 목록을 표시합니다. |
