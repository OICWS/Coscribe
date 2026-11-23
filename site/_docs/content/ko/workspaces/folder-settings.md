---
title: 폴더 자체의 메모와 규칙
description: 폴더가 직접 coscribe에 무엇이 들어 있는지, 어떤 스킬과 커넥터를 쓸지, 무엇을 묻지 않고 실행해도 되는지 알려 주게 합니다.
---

폴더는 안에 있는 `.coscribe` 폴더에 coscribe를 위한 지침을 담을 수 있습니다. 사용자가 받아들이면, coscribe는 그 폴더를 쓰는 모든 대화에서 이를 읽습니다.

## 폴더에 담을 수 있는 것 {#what-a-folder-can-hold}

| 파일 | 역할 |
|---|---|
| `.coscribe/memory.md` | 이 폴더에서 대화를 시작할 때마다 coscribe가 읽는 메모. 폴더의 용도, 규칙, 이름 등. |
| `.coscribe/skills/<name>/SKILL.md` | 이 폴더에서만 적용되는 [스킬](../customize/skills.md). |
| `.coscribe/settings.json` | 권한 규칙(`allow`, `ask`, `deny`)과 스크립트용 환경 변수. |
| `.coscribe/mcp.json` | 이 폴더가 쓰는 [커넥터](../customize/connectors.md). |

coscribe는 `memory.md`, `settings.json`, `mcp.json`을 직접 쓰지 않습니다. 편집은 사용자만 합니다. 보낸 첨부 파일은 `.coscribe/uploads/`에 보관됩니다.

## 폴더 설정 받아들이기 {#accept-a-folders-settings}

폴더의 설정은 그 폴더에 쓸 수 있는 누구에게서나 올 수 있으므로, coscribe는 사용자가 동의하기 전에는 따르지 않습니다. **Task details** 패널의 **What Coscribe knows about this folder**에는 폴더가 가져오는 스킬, 커넥터, 규칙이 **Runs without asking**, **Always asks**, **Never runs**로 묶여 표시되고, 스크립트용 변수도 함께 표시됩니다. **Use them**을 클릭하면 받아들입니다.

이 파일 중 하나라도 coscribe 밖에서 바뀌면 다시 묻습니다.

## 권한 규칙 {#permission-rules}

`.coscribe/settings.json`은 Claude Code 설정 파일과 같은 형식입니다.

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

규칙은 coscribe 도구 이름, 이름에 대한 `*` 패턴, 또는 둘 중 하나에 주 인수의 패턴을 괄호로 붙인 것입니다. 예: `write_file(docs/*)`. 규칙은 원래 사용자의 승인을 기다릴 작업만 결정합니다. **deny**가 **ask**보다, **ask**가 **allow**보다 우선합니다.

항상 적용되는 제한이 있습니다.

- 커넥터로 메시지를 보내는 것처럼 컴퓨터 밖으로 나가는 작업은 규칙으로 허용되지 않으며, 여전히 묻습니다.
- `*` 하나만 있는 규칙은 아무것도 허용하지 않습니다.
- `ask` 규칙은 **Auto** 모드에서도 묻습니다.

## 스크립트용 변수 {#variables-for-scripts}

`settings.json`의 `env` 값은 폴더 안의 스크립트와 명령에 전달됩니다. `PATH`, 프록시 설정, `PYTHONPATH`처럼 어떤 프로그램이 실행되는지나 트래픽이 어디로 가는지를 바꾸는 변수는 폴더에서 설정할 수 없습니다.
