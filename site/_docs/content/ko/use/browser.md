---
title: 내장 브라우저
description: 지켜보고, 직접 넘겨받고, 사이트별로 제어할 수 있는 브라우저에서 Coscribe가 웹사이트를 쓰게 합니다.
---

데스크톱 앱에는 **Browser** 패널에 표시되는 자체 브라우저가 있습니다. Coscribe는 사용자가 보는 앞에서 이 브라우저를 씁니다. 페이지를 열고, 양식 전체를 채우고, 파일을 업로드·다운로드하고, 표를(여러 페이지에 걸쳐서도) CSV 파일로, 페이지를 PDF로 저장합니다. 로그인 상태는 세션 간에 유지되므로 사이트마다 한 번만 로그인하면 됩니다.

> [!NOTE]
> 브라우저는 데스크톱 앱의 일부입니다. Coscribe를 사용자 자신의 웹 브라우저에서 실행하면 Browser 패널이 없습니다.

## 사이트 허용하기 {#allow-a-site}

Coscribe가 어떤 사이트를 처음 쓰려고 하면 Browser 패널이 묻습니다.

- **Allow for this chat**: 이 대화에서 그 사이트를 쓰게 합니다.
- **Always allow**: 사이트를 워크스페이스에 추가해 그 뒤로는 묻지 않고 씁니다.
- **Don't allow**: 거부합니다.

워크스페이스마다 **Edit workspace › Sites**에 사이트별 수준을 보관합니다. **Use without asking**, **Ask each time**, **Not in the browser** 중 하나입니다. 가장 구체적인 항목이 우선하므로, `example.com`은 허용하면서 `admin.example.com`은 막아 둘 수 있습니다.

## 넘겨받기 {#take-over}

**Take over**를 클릭하면 직접 페이지를 쓸 수 있고, Coscribe는 기다립니다. **Allow AI**를 클릭하면 다시 넘겨줍니다.

사이트가 비밀번호, 일회용 코드, 캡차를 요구하면 Coscribe는 멈추고 사용자에게 처리해 달라고 요청합니다. 사용자가 주지 않은 비밀번호나 코드는 절대 입력하지 않습니다.

## 무언가 가리키기 {#point-at-something}

- **Select element**: 페이지의 한 부분을 클릭해 대화로 보냅니다.
- **Annotate**: 페이지 그림을 찍어 표시를 한 뒤 **Add to chat**으로 보냅니다.
