---
title: Models, effort and context
description: Pick the model for a conversation, set how hard it thinks, and see how full its context is.
---

## Pick a model

Click the model name below the message box to switch models. The switch applies from the next message, and the conversation keeps everything said so far. While the picker is open, the keys <kbd>1</kbd> to <kbd>9</kbd> pick the model with that number.

The picker lists the models you switched on for each provider in **Settings** › **Providers**; see [Connect a model](../get-started/providers.md). A new conversation starts with the **Default model** from **Settings** › **General**.

## Set the effort

Next to the model is the effort control, a scale from **Faster** to **Smarter**. More effort lets the model reason longer: better on hard tasks, slower, and it costs more. **Medium** is a good start.

When coscribe knows the model's own levels, the scale shows those, such as **Low**, **Medium**, **High**, **Extra high** and **Max**. Otherwise it shows the whole scale and the model runs the nearest level it supports. A model without an effort setting shows the control greyed out.

Your choice is kept when you switch models: the new model runs the nearest level it has.

## Watch the context

Every model can read only so much at once: its context window. Once a conversation has started, a ring beside the message box shows how much of it is used. Click the ring to see what takes the room: the messages, the system prompt, tools and skills, and the free space left.

When the window is about four-fifths full, coscribe summarizes the earlier part of the conversation on its own so it can go on. You can also type `/compact` to do it now. See [Keep a long conversation going](conversations.md#keep-a-long-conversation-going).

## Keep costs down

You pay the provider for what the model reads and writes. A few habits help:

- Use a lower effort for routine work.
- Start a new conversation for a new job, rather than going on in a long one.
- Turn off **Prompt suggestions** and **Background agents** in **Settings** › **General** if you don't use them; both add model calls.
- For work that must not leave your PC, or that you do often, a [model on your PC](../get-started/providers.md#run-a-model-on-your-pc) costs nothing per use.
