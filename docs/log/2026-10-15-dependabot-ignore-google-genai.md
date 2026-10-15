# Dependabot leaves google-genai alone

`pyproject.toml` declares `google-genai<1.5.0` while every job installs 2.13.x by hand (aisuite's
`httpx<0.28` pin cannot resolve with it), so Dependabot's proposed ranges (#277, #288) never match
what runs, and #288 failed `test_gemini_sets_its_thinking_level_medium_included`. The pip
ecosystem now ignores `google-genai` until #299 settles whether aisuite goes.
