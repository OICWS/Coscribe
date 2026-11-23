---
title: 다운로드와 첫 실행
description: 포터블 버전을 다운로드해 압축을 풀고, 실행한 뒤 작업할 폴더를 고릅니다.
---

Coscribe는 설치가 필요 없습니다. zip 파일 하나를 다운로드해 아무 곳에나 압축을 풀고 실행하면 됩니다. 시스템 설정은 전혀 바꾸지 않습니다.

## 다운로드 {#download}

1. GitHub의 [Coscribe 릴리스 페이지](https://github.com/OICWS/coscribe/releases/tag/beta)를 엽니다.
2. **Assets**에서 `.zip` 파일을 다운로드합니다.
3. `D:\coscribe`처럼 찾기 쉬운 곳에 압축을 풉니다.

> [!NOTE]
> 현재 릴리스는 베타 버전입니다.

## 첫 실행 {#first-start}

압축을 푼 폴더에서 `Coscribe.exe`를 두 번 클릭합니다.

앱에 아직 코드 서명이 없어서, 처음 열 때 Windows가 "Windows의 PC 보호"라는 파란 창을 표시할 수 있습니다. **추가 정보**를 클릭한 다음 **실행**을 클릭하세요. 다시는 묻지 않습니다.

## 워크스페이스 선택 {#choose-a-workspace}

처음 실행하면 Coscribe가 **워크스페이스**(workspace)를 고르라고 합니다. 업무 파일을 보관하는 폴더입니다. 기본으로 `Documents\Coscribe`를 제안하며, **Browse…** 버튼을 클릭해 다른 폴더를 고른 뒤 **Use this folder**를 클릭합니다.

워크스페이스는 두 가지 역할을 합니다.

- Coscribe가 만든 파일은 기본적으로 이곳에 저장됩니다.
- 대화에 첨부한 파일은 이곳의 `.coscribe` 폴더로 복사됩니다.

Coscribe는 워크스페이스 안의 모든 파일을 읽고 바꿀 수 있습니다. 다른 워크스페이스로 바꾸거나 다른 폴더에도 접근하게 하려면 메시지 상자 아래의 선택기를 쓰거나 **Settings › Workspaces**로 가세요.

## 다음 단계 {#next-step}

이제 [모델 공급자를 추가](providers.md)하면 Coscribe가 일할 준비가 됩니다.
