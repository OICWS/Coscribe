---
title: 지침
description: coscribe가 항상 알아야 할 것을 모든 대화 또는 한 폴더에 대해 한 번만 알려 줍니다.
---

지침은 coscribe가 요청을 시작하기 전에 읽는 상시 메모입니다. 같은 말을 되풀이하지 않아도 됩니다.

## 모든 대화에 {#for-every-conversation}

**Settings** › **General**을 열고 **Global instructions**에 coscribe가 항상 알아야 할 선호, 규칙, 배경을 씁니다. 예를 들어 회사 이름, 쓰는 날짜 형식, 보고서는 영어로 쓴다는 점 같은 것입니다. 모든 새 대화에 적용되며, 사용자만 바꿀 수 있습니다. coscribe는 이를 직접 편집할 수 없습니다.

## 한 폴더에 {#for-one-folder}

한 폴더에 대한 메모는 그 안의 `.coscribe/memory.md`에 씁니다. 폴더의 용도, 규칙, 거기서 쓰는 이름 등입니다. 폴더 설정을 받아들이면, coscribe는 그 폴더에서 대화를 시작할 때마다 이를 읽습니다. [폴더 자체의 메모와 규칙](../workspaces/folder-settings.md)을 참고하세요.

## coscribe가 폴더를 설명하게 하기 {#have-coscribe-describe-a-folder}

대화에서 `/init`을 입력하면 coscribe가 워크스페이스를 살펴보고 그 루트에 `OVERVIEW.md`를 씁니다. 폴더에 무엇이 있고 어떻게 구성되어 있는지 정리한 파일입니다. 나중에 다시 실행하면 파일을 새로 고칩니다.

## 내 이름 {#your-name}

**Settings** › **General**의 **What should Coscribe call you?** 항목은 홈 화면 인사말에 쓰일 이름을 정합니다.
