---
title: O que é o Coscribe
description: Um assistente de escritório que roda no seu PC e cria arquivos do Word, Excel e PowerPoint que você pode editar.
---

O Coscribe é um assistente de escritório com IA para Windows. Diga em uma frase o que você precisa, e ele lê suas planilhas e documentos e cria o arquivo pronto: um contrato com alterações controladas e comentários, uma apresentação de relatório com gráficos, uma pasta de trabalho do Excel conciliada.

Ele é de código aberto (licença MIT) e gratuito. Você paga apenas pelo serviço de modelos que escolher.

## O que ele pode fazer {#what-it-can-do}

- **Excel**: ler, limpar, resumir e conciliar dados; escrever fórmulas e gráficos.
- **Word**: redigir e revisar documentos, marcando as alterações com controle de alterações e comentários para que outras pessoas possam revisá-las.
- **PowerPoint**: transformar dados e materiais em uma apresentação, usando o modelo e as cores da sua empresa, se você os tiver.
- **PDF**: pesquisar, extrair e organizar conteúdo.
- **A web**: abrir sites em um navegador integrado, preencher formulários e salvar tabelas.
- **Fluxos de trabalho**: salvar o que uma conversa fez como passos fixos e executá-lo de novo com um clique ou em um horário programado.

## Como ele se diferencia de outras ferramentas de IA {#how-it-differs-from-other-ai-tools}

**Seus arquivos ficam no seu PC.** O Coscribe não tem serviço de nuvem próprio. Só o que o modelo precisa ler vai para o provedor de modelos que você escolheu; com um modelo rodando no seu próprio computador pelo Ollama, nada sai da máquina.

**Você escolhe o modelo.** Claude, GPT e Gemini são integrados. DeepSeek, Kimi, GLM, Qwen, Doubao e qualquer outro serviço com uma API compatível com a da OpenAI funcionam assim que você informar o endereço e a chave de API. Veja [Adicionar um provedor de modelos](providers.md).

**Ele pergunta antes de alterar algo.** Quatro modos de permissão vão de "pergunte antes de cada passo" a "deixe um modelo revisor aprovar o trabalho rotineiro por mim". Em todos os modos, ele só grava nas pastas que você permitiu. Veja [Sua primeira conversa](first-conversation.md#permission-modes).

**Ele entrega arquivos prontos, não rascunhos.** Depois de escrever um arquivo, o Coscribe o renderiza e olha o resultado para conferir o layout e o conteúdo, em vez de entregar um bloco de texto.

## Requisitos do sistema {#system-requirements}

- Windows 10 ou Windows 11.
- Uma chave de API de um serviço de modelos, ou o Ollama ou o LM Studio rodando no seu PC.

> [!NOTE]
> O Coscribe está disponível apenas para Windows. Ainda não há versão para Mac ou Linux.
