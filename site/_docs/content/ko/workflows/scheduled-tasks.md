---
title: 예약 작업
description: 아침 브리핑처럼 coscribe가 일정에 따라 작업하게 하고, 실행할 때마다 보고서를 읽습니다.
---

예약 작업은 coscribe가 사용자 없이 하는 일입니다. 정해진 시각에, 매시간, 또는 사용자가 시작할 때 실행됩니다. 실행마다 별도의 대화가 되며, 보고서로 끝납니다.

두 종류가 있습니다. **예약 작업**은 글로 쓴 지침을 따르므로 매번 모델이 각 단계를 정합니다. **워크플로**는 저장해 둔 고정 단계를 실행하며 실행 중에 확인합니다. [워크플로](workflows.md)를 참고하세요. 이 페이지는 둘의 공통점을 다룹니다.

## 작업 만들기 {#create-a-task}

탐색 메뉴에서 **Scheduled**를 열고 **New task**를 누릅니다.

- **Create with Coscribe**: 작업을 설명하거나 한 번 함께 해 보는 채팅을 시작합니다. 그러면 coscribe가 카드에 작업 초안을 만들고, **Review & save**를 누르면 저장하기 전에 무엇이든 고칠 수 있습니다.
- **Set up manually**: 이름, 지침, 일정을 직접 쓰는 양식을 엽니다.
- **Build a workflow**: 빈 워크플로를 시작합니다. [워크플로](workflows.md)를 참고하세요.

채팅에서 작업을 마친 뒤 coscribe가 **Save this job?** 카드를 보여 줄 수도 있습니다. **Save as workflow**는 다시 실행하거나 예약할 수 있는 고정 단계로 만들고, **Save as skill**은 다음을 위한 지침으로 보관합니다([스킬](../customize/skills.md) 참고).

## 실행 시점 정하기 {#choose-when-it-runs}

**Frequency**는 **Manual**(시작할 때만), **Hourly**, **Daily**, **Weekdays**, **Weekly**, **Monthly** 중에서 고릅니다. 매일, 평일, 매주 실행에는 시각을, 매주 실행에는 요일도 정합니다. 워크플로는 몇 분마다, 또는 어떤 일이 일어났을 때도 실행할 수 있습니다. [이벤트로 워크플로 시작하기](workflows.md#start-on-an-event)를 참고하세요.

작업에는 실행이 쓸 수 있는 폴더와 사이트를 정하는 **Workspace**([워크스페이스와 폴더](../workspaces/workspaces.md) 참고)와 **Model**도 있습니다. **Default model**은 설정에 지정한 모델을 씁니다.

## 사용자 없이 할 수 있는 일 정하기 {#choose-what-it-may-do-without-you}

실행을 지켜보는 사람이 없으므로, 작업은 자체 **Permissions**를 정합니다.

| 설정 | 동작 |
|---|---|
| **Ask before every action** | 승인이 필요한 작업 전에 실행을 멈추고 승인을 기다립니다. |
| **Automatically approve** | 파일은 스스로 만들고 편집하지만, 코드를 실행하거나 커넥터를 쓰기 전에는 멈춥니다. |
| **Never ask** | 코드 실행과 커넥터 사용을 포함해 승인을 위해 멈추지 않습니다. 차단 규칙은 계속 적용됩니다. |

**Most steps**는 그 단계 수에 이르면 실행을 끝내므로, 잘못된 실행이 오래 계속되지 않습니다.

> [!WARNING]
> **Never ask**에서는 실행이 묻지 않고 코드를 실행하고 커넥터를 쓸 수 있습니다. 지침을 신뢰하는 작업에만 쓰세요.

## 앱을 계속 실행하기 {#keep-the-app-running}

coscribe 창을 닫아도 알림 영역에서 계속 실행되므로 작업도 계속 실행됩니다. 종료하려면 알림 영역 아이콘에서 **Quit**을 고르세요. **Settings** › **General**에서 **Keep running in the background**를 끄면 창을 닫을 때 coscribe가 종료되고 작업도 함께 멈춥니다.

coscribe가 닫혀 있는 동안 예정된 실행이 있었다면, 다시 시작할 때 한 번 실행됩니다.

## 실행 확인하기 {#follow-the-runs}

작업 페이지에는 다음 실행 시각, 최근 실행과 그 상태가 표시됩니다. 상태는 **Running**, **Completed**, **Failed**, **Needs approval**, **Waiting**, **Stopped** 중 하나입니다. 실행을 열면 그 대화와 보고서를 볼 수 있습니다. 승인이 필요한 실행은 그곳에서 사용자를 기다립니다.

- **Run now**: 작업을 시험해 보도록 바로 실행합니다.
- 상태 옆의 스위치: 작업을 일시 중지하거나 다시 시작합니다.
- 연필 아이콘: 작업 이름이나 실행 시점을 바꿉니다.

**Settings** › **General**의 **Notifications**에서 실행이 끝날 때마다 알릴지, 실패했거나 사용자를 기다리는 실행처럼 문제가 있을 때만 알릴지 고릅니다. 알림을 클릭하면 그 실행이 열립니다.

## 실행 사이에 기억하기 {#remember-between-runs}

예약 작업 페이지에서 **Remember between runs**를 켜면, 각 실행이 진행 상황, 멈춘 곳, 바뀐 점을 다음 실행을 위한 메모로 남깁니다. 끄면 매번 메모 없이 시작합니다.
