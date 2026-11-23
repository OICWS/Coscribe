---
title: Aprovações e modos de permissão
description: Escolha quanto o Coscribe pode fazer sozinho e responda aos cartões que ele mostra quando precisa de você.
---

O Coscribe não faz nada fora do seu alcance sem a sua palavra. Com que frequência ele pergunta depende do modo de permissão da conversa; o que ele consegue alcançar depende do [espaço de trabalho](../workspaces/workspaces.md).

## Os quatro modos {#the-four-modes}

Escolha um modo com o botão de modo abaixo da caixa de mensagem. O padrão para novas conversas é definido em **Settings › General › Default mode**.

| Modo | O que faz |
|---|---|
| **Manual** | Pergunta antes de cada alteração, script ou ação externa. |
| **Accept Edits** | Edita arquivos nas suas pastas sem perguntar; ainda pergunta antes de executar código ou ações externas. |
| **Plan** | Pesquisa e escreve um plano para você aprovar antes de qualquer alteração. Veja [Planos e listas de tarefas](plans.md). |
| **Auto** | Um modelo revisor aprova ações rotineiras e bloqueia as arriscadas, em vez de perguntar a você. |

Se você trocar de modo enquanto uma resposta está em andamento, o novo modo vale quando a resposta terminar.

## Aprovar uma ação {#approve-an-action}

Quando o Coscribe precisa da sua aprovação, um cartão na conversa nomeia a ação, como "Run a command", e mostra o que ela fará: o arquivo que vai gravar, o script ou o comando. Leia-o e escolha:

- **Approve** deixa esta ação seguir.
- **Allow for this task** (mostrado para os comandos e alterações do módulo de código) deixa o mesmo tipo de ação seguir pelo resto da tarefa sem perguntar de novo.
- **Deny** recusa. Para dizer por quê, digite o motivo na caixa de mensagem; o Coscribe o lê e se ajusta.

Se o cartão saiu da tela, um aviso acima da caixa de mensagem diz que algo está esperando; **Show** leva você de volta a ele.

> [!IMPORTANT]
> O cartão de um script diz como ele será executado. Normalmente, um script roda isolado: só pode usar as pastas da conversa, não pode excluir nem renomear arquivos nelas e só acessa a internet quando a configuração **Sites** do espaço de trabalho é **Any site**. Um selo **Not isolated** significa que o script rodará sem esse isolamento e pode acessar qualquer arquivo que você acessa; passe o mouse sobre o selo para ver por quê e leia o script antes de aprovar.

## Dar acesso a outra pasta {#give-access-to-another-folder}

Quando o Coscribe precisa de uma pasta fora do espaço de trabalho e das pastas que você permitiu, ele pergunta em um cartão. Escolha o acesso (**Read only**, **Read and write** ou **Read, write and delete**) e depois:

- **Allow** adiciona a pasta às suas pastas permitidas de vez.
- **Only this chat** permite apenas nesta conversa.
- **Save in my workspace instead** (quando ele queria gravar) mantém o arquivo no espaço de trabalho.
- **Don't allow** recusa.

O Coscribe nunca oferece uma unidade inteira nem sua pasta pessoal.

## Instalar um pacote para um script {#install-a-package-for-a-script}

Um script pode precisar de uma biblioteca Python ou Node.js que o Coscribe ainda não tem. O cartão **Install a Python package** (ou Node.js) a nomeia e diz por quê. **Install** a instala no ambiente próprio do Coscribe, que o resto do seu computador não usa; **Not now** recusa nesta conversa. Se a instalação falhar, **Details** mostra a saída do instalador.

## Responder a uma pergunta {#answer-a-question}

Às vezes o Coscribe pede que você escolha, por exemplo, entre dois layouts. Escolha uma opção no cartão ou digite sua própria resposta na caixa de mensagem.
