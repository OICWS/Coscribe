---
title: 스킬과 플러그인
description: 일하는 방식을 coscribe에 한 번 가르치고, 다른 사람이 만든 스킬을 추가하고, 켜거나 끕니다.
---

스킬(skill)은 팀이 주간 보고서를 쓰는 방식처럼 한 가지 작업을 위한 지침 모음입니다. 작업이 스킬의 설명과 맞으면 coscribe는 그 스킬을 따릅니다. coscribe에는 기본 제공 스킬이 몇 가지 있고, 직접 추가할 수도 있습니다.

## 스킬 쓰기 {#use-a-skill}

따로 할 일은 없습니다. 맞는 스킬이 있으면 coscribe가 고릅니다. 일부러 쓰려면 메시지 상자에 <kbd>/</kbd>를 입력해 목록에서 고르거나, 슬래시 뒤에 스킬 이름과 요청을 이어서 입력합니다.

## 작업을 스킬로 저장하기 {#save-a-job-as-a-skill}

대화에서 작업을 마친 뒤 그 방식을 보관할 수 있습니다.

- `/create-skill` 뒤에 이름을 입력합니다.
- 또는 여러 단계로 된 작업 뒤에 coscribe가 **Save this job?** 카드를 보여 주면 **Save as skill**을 고릅니다.

**Settings** › **Skills** › **Add** › **Create with Coscribe**에서 시작할 수도 있습니다. 스킬을 설명할 대화가 열립니다.

## 다른 사람이 만든 스킬 추가하기 {#add-skills-others-made}

**Settings** › **Skills**에서:

- **Discover**는 [github.com/anthropics/skills](https://github.com/anthropics/skills)와 [github.com/anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)의 오픈 소스 스킬을 보여 줍니다. 대부분은 스킬 묶음인 플러그인으로 제공됩니다. 열면 포함된 스킬, 쓰는 커넥터, 라이선스를 볼 수 있고, **Add**를 누르면 모든 스킬을 다운로드합니다.
- **Add** › **Upload a skill**은 받은 스킬 파일을 추가합니다. `SKILL.md`, 또는 `.zip`, `.skill`, `.plugin` 파일입니다.

> [!WARNING]
> 스킬은 coscribe가 따르는 지침입니다. 신뢰하는 사람의 스킬만 추가하고, 쓰기 전에 읽어 보세요. **Yours**에서 열면 파일을 볼 수 있습니다.

## 스킬 켜고 끄기 {#turn-skills-on-or-off}

**Yours**에는 내 스킬이 나열됩니다. 열면 파일을 읽을 수 있고, 스위치로 삭제하지 않고 끌 수 있습니다. 스킬 옆의 메뉴로 삭제합니다. 플러그인으로 들어온 스킬을 삭제하면 그 플러그인의 모든 스킬이 삭제됩니다.

## 한 폴더용 스킬 {#skills-for-one-folder}

폴더는 `.coscribe/skills/`에 자체 스킬을 담을 수 있습니다. 폴더 설정을 받아들이면, 그 폴더를 쓰는 대화에서만 적용됩니다. [폴더 자체의 메모와 규칙](../workspaces/folder-settings.md)을 참고하세요.

## 스킬 직접 쓰기 {#write-a-skill-by-hand}

스킬은 `SKILL.md` 파일이 들어 있는 폴더입니다. 파일은 `name`과 `description`으로 시작하고, 그 뒤에 Markdown으로 지침을 씁니다.

```markdown
---
name: Weekly report
description: Write the weekly sales report from the order export. Use when asked for the weekly report.
---

1. Read the latest export in Reports/Exports.
2. ...
```

coscribe가 언제 스킬을 쓸지는 설명으로 정해지므로, 스킬의 용도와 언제 쓰는지를 적으세요. Claude Code의 스킬과 같은 형식입니다.
