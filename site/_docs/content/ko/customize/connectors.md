---
title: 커넥터
description: 메일, 캘린더, 프로젝트 관리 도구처럼 쓰는 서비스에 Coscribe를 연결하고, 거기서 할 수 있는 일을 정합니다.
---

커넥터를 쓰면 Coscribe가 다른 서비스를 이용할 수 있습니다. 메일 읽기, 캘린더에 일정 추가, 티켓 조회 같은 일입니다. 커넥터는 Model Context Protocol(MCP)을 쓰므로, Coscribe 목록에 있는 것뿐 아니라 어떤 MCP 서버든 쓸 수 있습니다.

## 커넥터 추가하기 {#add-a-connector}

**Settings** › **Connectors** › **Discover**를 열고 서비스를 고른 뒤 **Connect**를 클릭합니다.

- 대부분의 호스팅 서비스는 로그인을 요청합니다. 로그인은 브라우저에서 서비스 자체 페이지로 열리며, 한 번만 하면 됩니다. Coscribe는 비밀번호를 절대 보지 않습니다.
- **Needs setup** 표시가 있는 서비스는 먼저 앱을 등록해야 합니다. Coscribe가 한 번만 안내합니다. 팀의 누군가가 이미 설정했다면 **Copy a message for your admin**으로 그 사람에게 설정 파일을 요청할 수 있습니다.

연결하지 않은 서비스가 요청에 필요하면 Coscribe가 대화 중에 커넥터를 제안할 수도 있습니다. 카드의 **Connect**를 클릭하면 연결된 뒤 Coscribe가 이어서 작업합니다. **Not now**를 누르면 그대로 두며, 언제든 **Settings** › **Connectors**에서 연결할 수 있습니다.

## 사용자 지정 커넥터 추가하기 {#add-a-custom-connector}

목록에 없는 MCP 서버는 **Add** › **Add custom connector**를 고르고 이름을 붙인 뒤, 다음 중 하나를 합니다.

- 호스팅 서버의 **MCP server URL**과 필요한 헤더를 입력합니다. 키를 직접 쓰지 않고 헤더에 넣으려면 **Insert a secret**을 쓰세요. 헤더가 `{{secret:NAME}}`이 되고 값은 [Secrets](../reference/settings.md#secrets)에서 가져옵니다.
- 또는 **Run a local command instead**를 고르고 `npx` 같은 명령과 인수, 필요한 환경 변수를 입력합니다. 이 컴퓨터에서 사용자 권한으로 실행되는 프로그램입니다.

> [!WARNING]
> 로컬 명령은 내 Windows 계정이 할 수 있는 모든 일을 할 수 있습니다. 신뢰하는 서버만 추가하세요.

## 할 수 있는 일 정하기 {#choose-what-it-may-do}

**Yours**에서 커넥터를 열면 도구가 **Read-only tools**와 **Write/delete tools**로 나뉘어 표시됩니다. 도구마다 고릅니다.

| 선택 | 동작 |
|---|---|
| **Always allow** | Coscribe가 묻지 않고 씁니다. |
| **Needs approval** | Coscribe가 매번 묻습니다. [승인과 권한 모드](../use/approvals.md)를 참고하세요. |
| **Blocked** | Coscribe가 쓸 수 없습니다. |

커넥터 페이지에는 연결 여부도 표시됩니다. 연결되어 있지 않으면 **Retry**로 다시 연결하고, **Sign in**으로 서비스 로그인 페이지를 엽니다.

## 한 폴더용 커넥터 {#connectors-for-one-folder}

폴더는 `.coscribe/mcp.json`에 자체 커넥터를 담을 수 있습니다. 폴더 설정을 받아들이면, 그 폴더를 쓰는 대화에서만 적용됩니다. [폴더 자체의 메모와 규칙](../workspaces/folder-settings.md)을 참고하세요.

## 워크플로에서 커넥터 쓰기 {#use-a-connector-in-a-workflow}

커넥터의 도구는 [워크플로](../workflows/workflows.md)의 단계가 될 수 있고, 커넥터에 새 항목이 나타나면 워크플로를 시작할 수도 있습니다. [이벤트로 워크플로 시작하기](../workflows/workflows.md#start-on-an-event)를 참고하세요.
