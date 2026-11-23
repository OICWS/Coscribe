---
title: 技能和插件
description: 把一种做事的方法教给 coscribe 一次，添加别人做好的技能，并随时打开或关闭。
---

技能是针对某一类工作的一套说明，比如你们团队写周报的方法。工作和某个技能的描述对得上时，coscribe 就会照着做。coscribe 自带一些技能，你也可以添加自己的。

## 使用技能 {#use-a-skill}

不用做任何事：合适的时候 coscribe 会自己选用技能。想指定使用某个技能，就在输入框里输入 <kbd>/</kbd> 从列表里选，或者在斜杠后输入它的名字，再接上你的请求。

## 把一项工作存成技能 {#save-a-job-as-a-skill}

在对话里做完一项工作后，可以把做法保存下来：

- 输入 `/create-skill`，后面跟一个名字。
- 或者在完成一项多步骤的工作后，coscribe 提示 **Save this job?** 时选 **Save as skill**。

也可以从 **Settings** › **Skills** › **Add** › **Create with Coscribe** 开始，它会开一个对话让你描述这个技能。

## 添加别人做好的技能 {#add-skills-others-made}

在 **Settings** › **Skills** 里：

- **Discover** 列出来自 [github.com/anthropics/skills](https://github.com/anthropics/skills) 和 [github.com/anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) 的开源技能。大多数以插件的形式提供，也就是一组技能。打开一个可以看到它的技能、用到的连接器和许可证；**Add** 会下载它的全部技能。
- **Add** › **Upload a skill** 用来添加别人给你的技能文件：`SKILL.md`，或者 `.zip`、`.skill`、`.plugin` 文件。

> [!WARNING]
> 技能是 coscribe 会照着执行的说明。只添加你信任的人做的技能，使用前读一遍：在 **Yours** 里打开它就能看到它的文件。

## 打开或关闭技能 {#turn-skills-on-or-off}

**Yours** 列出你的技能。打开一个可以阅读它的文件，用它的开关可以关掉它而不删除。技能旁边的菜单可以删除它。删除来自插件的技能，会删除这个插件的全部技能。

## 只在一个文件夹里用的技能 {#skills-for-one-folder}

文件夹可以在 `.coscribe/skills/` 里带上自己的技能。你接受这个文件夹的设置后，它们只在使用这个文件夹的对话里生效。见[文件夹自己的说明和规则](../workspaces/folder-settings.md)。

## 手写一个技能 {#write-a-skill-by-hand}

技能是一个包含 `SKILL.md` 文件的文件夹。文件开头是 `name` 和 `description`，后面是 Markdown 写的说明：

```markdown
---
name: Weekly report
description: Write the weekly sales report from the order export. Use when asked for the weekly report.
---

1. Read the latest export in Reports/Exports.
2. ...
```

描述决定 coscribe 什么时候用这个技能，所以要写清楚它是做什么的、什么时候用。格式和 Claude Code 的技能相同。
