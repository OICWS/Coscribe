"""The providers the app knows about: the built-in ones and the OpenAI-compatible
ones offered as a convenience, with the .env variables each uses."""

from __future__ import annotations

# Well-known OpenAI-compatible services, offered so nobody types a base_url;
# any other endpoint is added by hand. No entry guesses a default model: a
# vendor's lineup turns over on its own schedule, and a stale name pre-filled
# into the form looks authoritative and fails as "model not found" (DeepSeek's
# once did). An API host rarely changes; each base_url answered a request at
# /chat/completions on 2026-11-17.
PROVIDER_CATALOG = [
    {
        "name": "deepseek",
        "title": "DeepSeek",
        "description": "DeepSeek's models through their OpenAI-compatible API.",
        "base_url": "https://api.deepseek.com/v1",
        "key_url": "https://platform.deepseek.com/api_keys",
    },
    {
        "name": "kimi",
        "title": "Kimi",
        "description": "Moonshot AI's Kimi models.",
        "base_url": "https://api.moonshot.ai/v1",
        "key_url": "https://platform.kimi.ai/console/api-keys",
    },
    {
        "name": "glm",
        "title": "GLM",
        "description": "Zhipu AI's GLM models.",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "key_url": "https://open.bigmodel.cn/usercenter/proj-mgmt/apikeys",
    },
    {
        "name": "qwen",
        "title": "Qwen",
        "description": "Alibaba Cloud Model Studio (Bailian): Qwen and other models.",
        "about": (
            "The address is the mainland China region. Outside it, use "
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1 and a key from that region."
        ),
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "key_url": "https://bailian.console.aliyun.com/",
    },
    {
        "name": "doubao",
        "title": "Doubao",
        "description": "ByteDance's Doubao models on Volcano Engine Ark.",
        "about": (
            "Ark names a model by its model ID or by an endpoint ID (ep-...) "
            "you created in the console."
        ),
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "key_url": "https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey",
    },
    {
        "name": "minimax",
        "title": "MiniMax",
        "description": "MiniMax's models.",
        "about": (
            "The address is the mainland China platform. Outside it, use "
            "https://api.minimax.io/v1 and a key from platform.minimax.io."
        ),
        "base_url": "https://api.minimaxi.com/v1",
        "key_url": "https://platform.minimaxi.com/user-center/basic-information/interface-key",
    },
    {
        "name": "siliconflow",
        "title": "SiliconFlow",
        "description": "Many open models (DeepSeek, Qwen, GLM and more) behind one key.",
        "base_url": "https://api.siliconflow.cn/v1",
        "key_url": "https://cloud.siliconflow.cn/account/ak",
    },
    {
        "name": "openrouter",
        "title": "OpenRouter",
        "description": "Hundreds of models from many labs behind one key.",
        "about": (
            "Name a model the way OpenRouter lists it, with its lab in front, "
            "such as openai/... or anthropic/...."
        ),
        "base_url": "https://openrouter.ai/api/v1",
        "key_url": "https://openrouter.ai/settings/keys",
    },
    {
        "name": "mistral",
        "title": "Mistral AI",
        "description": "Mistral's models.",
        "base_url": "https://api.mistral.ai/v1",
        "key_url": "https://console.mistral.ai/api-keys",
    },
    {
        "name": "xai",
        "title": "xAI",
        "description": "xAI's Grok models.",
        "base_url": "https://api.x.ai/v1",
        "key_url": "https://console.x.ai",
    },
    {
        "name": "groq",
        "title": "Groq",
        "description": "Open models on Groq's fast inference hardware.",
        "base_url": "https://api.groq.com/openai/v1",
        "key_url": "https://console.groq.com/keys",
    },
    {
        "name": "together",
        "title": "Together AI",
        "description": "Open models hosted by Together AI.",
        "base_url": "https://api.together.xyz/v1",
        "key_url": "https://api.together.ai/settings/api-keys",
    },
    {
        "name": "fireworks",
        "title": "Fireworks AI",
        "description": "Open models hosted by Fireworks AI.",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "key_url": "https://app.fireworks.ai/settings/users/api-keys",
    },
    {
        "name": "cerebras",
        "title": "Cerebras",
        "description": "Open models on Cerebras' fast inference hardware.",
        "base_url": "https://api.cerebras.ai/v1",
        "key_url": "https://cloud.cerebras.ai",
    },
    {
        "name": "ollama",
        "title": "Ollama",
        "description": "Models running on this computer, offline, with no account.",
        # add_provider requires a non-blank API key for every custom provider,
        # and Ollama's server never reads the Authorization header.
        "about": (
            'The API key can be any text (e.g. "ollama"): it isn\'t checked. For the default '
            "model, name one you already pulled with `ollama pull <model>`; Coscribe can't see "
            "what is installed."
        ),
        "base_url": "http://localhost:11434/v1",
        "key_url": "https://ollama.com/download",
    },
    {
        "name": "lmstudio",
        "title": "LM Studio",
        "description": "Models running on this computer through LM Studio's local server.",
        "about": (
            'Start the server in LM Studio first. The API key can be any text (e.g. "lmstudio"): '
            "it isn't checked. For the default model, name one you loaded in LM Studio."
        ),
        "base_url": "http://localhost:1234/v1",
        "key_url": "https://lmstudio.ai/download",
    },
]

# The built-in providers as the Providers page offers them. Anthropic's entry
# pins a real model ID because Anthropic publishes no rolling "-latest" alias
# (Gemini's "gemini-flash-latest" is one); bump it with coscribe's own
# supported-model docs, it has gone stale before.
BUILTIN_CATALOG = [
    {
        "name": "anthropic",
        "title": "Anthropic",
        "description": "Anthropic's Claude models.",
        "default_model": "claude-opus-5",
        "key_url": "https://platform.claude.com/settings/keys",
    },
    {
        "name": "openai",
        "title": "OpenAI",
        "description": "OpenAI's GPT models.",
        "default_model": "",
        "key_url": "https://platform.openai.com/api-keys",
    },
    {
        "name": "gemini",
        "title": "Google Gemini",
        "description": "Google's Gemini models.",
        "default_model": "gemini-flash-latest",
        "key_url": "https://aistudio.google.com/apikey",
    },
]

# Built-in providers: each has a raw (unprefixed) API-key env var -- read
# directly by each provider SDK, not modeled on Settings (see config.py's
# Settings docstring); values are never sent to the browser in full, only
# masked -- and an *optional*, COSCRIBE_-prefixed "default model"
# companion. The companion is deliberately COSCRIBE_-prefixed, unlike
# the key itself: no provider SDK reads
# "COSCRIBE_ANTHROPIC_DEFAULT_MODEL" -- it's pure coscribe
# bookkeeping (which model to offer as this provider's quick-pick in the
# model-picker / Providers tab), exactly what that prefix is used for
# everywhere else. Deliberately NOT added to COSCRIBE_ENV_VARS/Settings:
# get_config/get_providers below read it fresh from dotenv_values(".env")
# on every request, so (unlike every COSCRIBE_ENV_VARS entry) it never
# needs a restart to take effect -- see update_config's restart_required
# computation.
BUILTIN_PROVIDERS: list[dict[str, str]] = [
    {
        "key": "anthropic",
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model_env": "COSCRIBE_ANTHROPIC_DEFAULT_MODEL",
    },
    {
        "key": "openai",
        "api_key_env": "OPENAI_API_KEY",
        "default_model_env": "COSCRIBE_OPENAI_DEFAULT_MODEL",
    },
    {
        "key": "gemini",
        "api_key_env": "GEMINI_API_KEY",
        "default_model_env": "COSCRIBE_GEMINI_DEFAULT_MODEL",
    },
]

PROVIDER_KEY_ENV_VARS = [p["api_key_env"] for p in BUILTIN_PROVIDERS]
PROVIDER_DEFAULT_MODEL_ENV_VARS = [p["default_model_env"] for p in BUILTIN_PROVIDERS]
