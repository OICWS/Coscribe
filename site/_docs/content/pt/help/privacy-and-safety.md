---
title: Privacidade e segurança
description: O que sai do seu computador quando você usa o Coscribe, onde seus dados ficam e o que mantém as ações dele sob controle.
---

O Coscribe roda no seu PC. Ele não tem conta nem servidor próprio e não envia nada sobre você ou sobre o seu uso para quem o desenvolve.

## O que sai do seu computador {#what-leaves-your-computer}

| Vai para | O quê | Quando |
|---|---|---|
| O provedor de modelos que você escolheu | Suas mensagens, as partes dos arquivos que o Coscribe lê para responder e os resultados das ferramentas dele | A cada resposta. Um [modelo no seu PC](../get-started/providers.md#run-a-model-on-your-pc) mantém também isso no seu computador. |
| Mecanismos de busca | As palavras pesquisadas | Quando o Coscribe pesquisa na web. Ele usa mecanismos gratuitos, como o DuckDuckGo, sem chave. |
| Sites | Requisições comuns de páginas | Quando o Coscribe abre uma página que você pediu ou de que uma tarefa precisa. Veja [O navegador integrado](../use/browser.md). |
| Serviços que você conectou | O que a ferramenta de um conector envia | Quando o Coscribe usa aquele [conector](../customize/connectors.md). |

Os próprios termos do provedor decidem o que ele guarda e por quanto tempo. Leia-os antes de enviar documentos de trabalho.

## Onde seus dados ficam {#where-your-data-is-kept}

Todo o resto fica no seu PC:

- Seus arquivos ficam onde estão; o Coscribe trabalha neles no próprio lugar.
- Conversas, tarefas agendadas, habilidades e configurações ficam em `%APPDATA%\Coscribe`.
- Chaves de API e [segredos](../reference/settings.md#secrets) ficam no Gerenciador de Credenciais do Windows, nunca em um arquivo de texto simples.
- Um registro de como cada turno transcorreu (o modelo, as chamadas de ferramentas, os erros, os tokens e o tempo, sem as palavras da conversa) fica no seu PC para solução de problemas. Nada o envia para fora.

## O que mantém as ações sob controle {#what-keeps-actions-in-check}

- **Pastas**: o Coscribe só grava no seu espaço de trabalho e nas outras pastas que você permitiu. Veja [Espaços de trabalho e pastas](../workspaces/workspaces.md).
- **Aprovações**: ações que alteram algo esperam por você, conforme o [modo de permissão](../use/approvals.md). Um arquivo que o Coscribe exclui com suas próprias ferramentas de arquivo vai para a Lixeira.
- **Scripts** rodam em um contêiner isolado quando o Windows permite, restritos às pastas do espaço de trabalho; quando o isolamento não pode ser configurado, os scripts ficam desativados, a menos que você escolha outra coisa. Veja [Scripts e isolamento](../workspaces/workspaces.md#scripts-and-isolation).
- **Sites**: o que o Coscribe pode abrir no navegador segue a configuração de sites do espaço de trabalho. Veja [Permitir um site](../use/browser.md#allow-a-site).

> [!IMPORTANT]
> As aprovações são uma verificação feita por você, não uma sandbox. Um script ou comando que você aprova pode fazer o que sua conta do Windows pode fazer, a menos que o isolamento o contenha. Leia o que diz o cartão de aprovação antes de clicar em **Allow**.

## Pontos de atenção {#things-to-watch-for}

- Textos da web, de um e-mail ou de um documento podem conter instruções destinadas a uma IA. O Coscribe trata o que lê como material, não como ordens suas, mas nenhum modelo é perfeito: tenha cuidado com **Never ask** e **Auto** quando uma tarefa lê coisas que outras pessoas escreveram.
- Adicione habilidades, plugins e conectores apenas de pessoas em quem você confia.
