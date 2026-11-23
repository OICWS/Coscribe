# Discover: add a GitHub repository with a marketplace.json as a plugin source (shipped)

Why: step 4 of #1036 (decision 0058): a company's own repository and the open ones on GitHub
(Anthropic's, OpenAI's) install as they are.

## Shipped
- `tools/plugin_sources.py` (`PluginSources`): an address (`owner/repo`, a github.com URL,
  `/tree/<branch>`) is read through GitHub's API at its branch's current commit; the
  marketplace is `.claude-plugin/marketplace.json` (Claude) or `.agents/plugins/marketplace.json`
  (Codex). Plugins inside the repository are listed with their files and git blob hashes
  (Claude's relative path, `metadata.pluginRoot`, Codex's `{"source": "local"}`); an entry in
  another repository or package is counted. A plugin without a description in the marketplace
  (Codex's) is described from its manifest.
- Add downloads the whole plugin at the pinned commit into the skills folder, checks every file
  against its git blob hash and lands it whole or not at all; its skills show under "From your
  sources" in Your plugins.
- Routes: `GET/POST /api/skills/sources`, `DELETE /api/skills/sources/<owner>/<repo>`; a source's
  plugins join `GET /api/skills/plugins` with the id `gh:<owner>:<repo>:<name>` and use the same
  detail, file preview and add routes. The unused catalog-skill routes (`/api/skills/catalog`)
  are gone: Discover only offers plugins.
- Discover: Coscribe's catalog, then a section per source with "not reviewed by anyone" and
  Remove source, and an Add a source field.
- Tried on real repositories, read from local clones in the API's shape (this container's proxy
  refuses api.github.com): anthropics/knowledge-work-plugins lists 22 plugins (101 more live
  elsewhere), openai/plugins 46 (3 elsewhere). Through the app, Add on OpenAI's Canva downloaded
  its 13 files from raw.githubusercontent.com, checked them and listed its 8 skills.

## Not verified
- Adding a source through GitHub's real API (refused here); on Windows; GitHub's unauthenticated
  limit of 60 API requests an hour (a source costs two).

## Follow-ups
- Build Discover's own catalog from the curated repositories' marketplace.json and add its
  plugins whole; follow `github` and `git-subdir` entries. Steps 5 to 7 of #1036.
