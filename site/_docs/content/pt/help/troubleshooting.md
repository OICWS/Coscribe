---
title: Solução de problemas
description: Verifique com /doctor o que o Coscribe precisa no seu PC, corrija problemas comuns e relate um problema.
---

## Executar uma verificação {#run-a-check}

Digite `/doctor` em qualquer conversa. O Coscribe verifica o que precisa neste computador e mostra um cartão com cada resultado, os problemas primeiro, e como corrigir cada um. Uma correção que é uma configuração leva à página dela.

| Verificação | O que examina |
|---|---|
| **Model** | Se o modelo padrão responde. Se não: verifique a chave, o endereço e o nome do modelo do provedor, ou a rede e o [proxy](../reference/settings.md#general). |
| **Python for scripts** | Se há um Python para scripts. Se não houver, baixe o do próprio Coscribe em **Settings** › **Capabilities**. |
| **Node.js for scripts** | Se `node` e `npm` estão instalados, para scripts em Node.js. Instale-os em [nodejs.org](https://nodejs.org) se precisar deles. |
| **Office conversion** | Se há Microsoft Office ou LibreOffice para gerar visualizações de páginas e converter documentos. Se não houver nenhum dos dois, instale o Office ou baixe o LibreOffice em **Settings** › **Capabilities**. |
| **Browser** | Se o Microsoft Edge ou o Google Chrome está instalado, para o painel do navegador e as imagens de páginas. |
| **Script isolation** | Se os scripts podem rodar no contêiner isolado. Até o autoteste passar, os scripts ficam desativados; execute-o de novo nas configurações do espaço de trabalho. |
| **Command sandbox** | Se os comandos rodam na sandbox. Se ela não estiver configurada, cada comando roda como você, depois que você o aprova. |

## Problemas comuns {#common-problems}

### Uma resposta falha ou nunca chega {#a-reply-fails-or-never-comes}

Execute `/doctor` e veja **Model**. Uma chave expirada, um nome de modelo errado ou uma rede que exige proxy são as causas habituais. Algumas redes corporativas bloqueiam serviços de IA; fale com sua equipe de TI ou configure o proxy em **Settings** › **General** › **Proxy**.

### O Coscribe não consegue abrir um arquivo ou uma pasta {#coscribe-cant-open-a-file-or-folder}

O Coscribe só trabalha no seu espaço de trabalho e nas pastas que você permitiu. Quando ele pedir outra pasta, permita-a ou adicione a pasta ao espaço de trabalho. Veja [Dar acesso a outra pasta](../use/approvals.md#give-access-to-another-folder).

Se você estiver editando o mesmo arquivo do Word, Excel ou PowerPoint, salve suas alterações antes de pedir. O Coscribe percebe quando um arquivo mudou desde a última leitura, lê de novo e faz a alteração na sua versão, mas só consegue ver o que você salvou.

### Os scripts não rodam {#scripts-dont-run}

Verifique se **Run scripts** está ativado em **Settings** › **Capabilities**, depois execute `/doctor` e veja **Python for scripts** e **Script isolation**.

### Um conector parou de funcionar {#a-connector-stops-working}

Abra-o em **Settings** › **Connectors**. Se ele disser que não está conectado, clique em **Retry**, ou em **Sign in** quando o login tiver expirado.

### Uma tarefa agendada não rodou {#a-scheduled-task-didnt-run}

As tarefas só rodam enquanto o Coscribe está rodando, na janela ou na bandeja do sistema. Verifique se **Keep running in the background** está ativado em **Settings** › **General** e se a tarefa não está pausada. Uma execução prevista enquanto o Coscribe estava fechado roda uma vez quando ele abre de novo. Veja [Tarefas agendadas](../workflows/scheduled-tasks.md).

## Relatar um problema {#report-a-problem}

Relate no [GitHub](https://github.com/OICWS/coscribe/issues/new). Diga o que você pediu, o que aconteceu em vez disso e o que o `/doctor` mostra.

Para mostrar como um turno deu errado sem compartilhar suas palavras, clique com o botão direito na conversa na barra lateral e escolha **Export a failed turn…**. O arquivo diz como o turno transcorreu: o modelo, suas chamadas de ferramentas e falhas, os tokens e o tempo, e o início de cada erro de ferramenta. Ele não contém nenhuma palavra da conversa, e nada é enviado: você salva o arquivo e decide quem o recebe.

O log do servidor fica em `%APPDATA%\Coscribe\logs\coscribe-server.log`.
