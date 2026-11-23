---
title: O navegador integrado
description: Deixe o Coscribe usar sites em um navegador que você pode acompanhar, assumir e controlar site por site.
---

O app para desktop tem seu próprio navegador, mostrado no painel **Browser**. O Coscribe o usa na sua frente: abre páginas, preenche formulários inteiros, envia e baixa arquivos, salva tabelas (em várias páginas) como arquivos CSV e páginas como PDF. Os logins são mantidos entre sessões, então você entra em um site uma única vez.

> [!NOTE]
> O navegador faz parte do app para desktop. Se você usar o Coscribe no seu próprio navegador da web, não há painel Browser.

## Permitir um site {#allow-a-site}

Na primeira vez que o Coscribe quer usar um site, o painel Browser pergunta a você:

- **Allow for this chat** permite usar o site nesta conversa.
- **Always allow** adiciona o site ao espaço de trabalho, para que ele seja usado sem perguntar daí em diante.
- **Don't allow** recusa.

Cada espaço de trabalho guarda um nível por site em **Edit workspace › Sites**: **Use without asking**, **Ask each time** ou **Not in the browser**. A entrada mais específica prevalece, então `admin.example.com` pode ficar de fora enquanto `example.com` é permitido.

## Assumir o controle {#take-over}

Clique em **Take over** para usar a página você mesmo; o Coscribe espera. Clique em **Allow AI** para devolvê-la.

Quando um site pede uma senha, um código de uso único ou um captcha, o Coscribe para e pede que você resolva. Ele nunca digita uma senha ou um código que você não lhe deu.

## Apontar para algo {#point-at-something}

- **Select element** permite clicar em uma parte da página para enviá-la à conversa.
- **Annotate** tira uma imagem da página que você pode marcar e enviar com **Add to chat**.
