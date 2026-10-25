//! coscribe's command sandbox: Codex's Windows sandbox (`codex-windows-sandbox`) without the rest
//! of Codex, so running a command in it doesn't need the Codex download (issue #607).
//!
//! `run` does what `codex sandbox --permission-profile` does on Windows, with the profile given
//! as a file instead of loaded from Codex's config; `setup` and `uninstall` do what
//! `codex sandbox setup --elevated --user` and `codex sandbox uninstall` do. Both of those need
//! an elevated process, which coscribe starts. The two helpers Codex's sandbox launches
//! (`codex-windows-sandbox-setup.exe`, `codex-command-runner.exe`) ship beside this one.

#[cfg(not(windows))]
fn main() {
    eprintln!("coscribe-sandbox runs only on Windows");
    std::process::exit(2);
}

#[cfg(windows)]
fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let code = match windows::run(args) {
        Ok(code) => code,
        Err(err) => {
            eprintln!("coscribe-sandbox: {err:#}");
            1
        }
    };
    std::process::exit(code);
}

#[cfg(windows)]
mod windows {
    use std::collections::HashMap;
    use std::path::PathBuf;

    use anyhow::Context;
    use anyhow::Result;
    use anyhow::anyhow;
    use anyhow::bail;
    use codex_protocol::config_types::WindowsSandboxLevel;
    use codex_protocol::models::PermissionProfile;
    use codex_protocol::permissions::FileSystemSandboxPolicy;
    use codex_protocol::permissions::NetworkSandboxPolicy;
    use codex_protocol::permissions::RawFileSystemSandboxPolicy;
    use codex_utils_absolute_path::AbsolutePathBuf;
    use codex_windows_sandbox::WindowsSandboxProvisioningSettings;
    use codex_windows_sandbox::WindowsSandboxProxySettingsMode;
    use codex_windows_sandbox::WindowsSandboxSessionRequest;

    const USAGE: &str = "usage:
  coscribe-sandbox run --codex-home DIR --level elevated|unelevated --cwd DIR --policy FILE --network on|off -- COMMAND...
  coscribe-sandbox setup --user NAME --codex-home DIR
  coscribe-sandbox uninstall";

    pub fn run(args: Vec<String>) -> Result<i32> {
        let Some((command, rest)) = args.split_first() else {
            bail!("{USAGE}");
        };
        match command.as_str() {
            "run" => run_command(rest),
            "setup" => {
                let options = Options::parse(rest)?;
                let codex_home = options.path("--codex-home")?;
                // Loopback stays closed to the offline identity, as Codex's own default.
                let settings = WindowsSandboxProvisioningSettings {
                    proxy_ports: Vec::new(),
                    allow_local_binding: false,
                };
                codex_windows_sandbox::run_elevated_provisioning_setup(
                    &codex_home,
                    options.value("--user")?,
                    settings,
                )?;
                println!("The sandbox is set up for {}.", options.value("--user")?);
                Ok(0)
            }
            "uninstall" => {
                codex_windows_sandbox::clean_up_legacy_windows_sandbox()?;
                Ok(0)
            }
            _ => bail!("{USAGE}"),
        }
    }

    fn run_command(args: &[String]) -> Result<i32> {
        let split = args
            .iter()
            .position(|arg| arg == "--")
            .ok_or_else(|| anyhow!("{USAGE}"))?;
        let options = Options::parse(&args[..split])?;
        let command = args[split + 1..].to_vec();
        if command.is_empty() {
            bail!("{USAGE}");
        }
        let level = match options.value("--level")? {
            "elevated" => WindowsSandboxLevel::Elevated,
            "unelevated" => WindowsSandboxLevel::RestrictedToken,
            other => bail!("unknown --level {other:?}"),
        };
        let network = match options.value("--network")? {
            "on" => NetworkSandboxPolicy::Enabled,
            "off" => NetworkSandboxPolicy::Restricted,
            other => bail!("unknown --network {other:?}"),
        };
        let policy_file = options.path("--policy")?;
        let raw: RawFileSystemSandboxPolicy = serde_json::from_slice(
            &std::fs::read(&policy_file)
                .with_context(|| format!("reading {}", policy_file.display()))?,
        )
        .context("reading the policy")?;
        let file_system = FileSystemSandboxPolicy::try_from(raw).map_err(|err| anyhow!(err))?;
        let profile = PermissionProfile::from_runtime_permissions(&file_system, network);
        let cwd = AbsolutePathBuf::from_absolute_path(options.path("--cwd")?)?;
        let codex_home = options.path("--codex-home")?;
        let env: HashMap<String, String> = std::env::vars().collect();

        let runtime = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()?;
        runtime.block_on(async move {
            // As `codex sandbox` does: the deny list is resolved against the command's folder,
            // and setup reconciles Codex's persistent deny entries against it.
            let workspace_roots = vec![cwd.clone()];
            let (mut runtime_fs, _) = profile.to_runtime_permissions();
            runtime_fs.remove_skip_missing_path_entries();
            let runtime_fs = runtime_fs.materialize_project_roots_with_workspace_roots(&workspace_roots);
            let deny_read = codex_windows_sandbox::resolve_windows_deny_read_paths(&runtime_fs, &cwd)
                .map_err(|err| anyhow!(err))?;
            let no_paths: &[AbsolutePathBuf] = &[];
            let spawned = codex_windows_sandbox::spawn_windows_sandbox_session_for_level(
                WindowsSandboxSessionRequest {
                    permission_profile: &profile,
                    workspace_roots: workspace_roots.as_slice(),
                    codex_home: codex_home.as_path(),
                    command,
                    cwd: cwd.as_path(),
                    env_map: env,
                    windows_sandbox_level: level,
                    proxy_settings_mode: WindowsSandboxProxySettingsMode::Preserve,
                    proxy_enforced: false,
                    network_proxy_restricting_sid: None,
                    timeout_ms: None,
                    read_roots_override: None,
                    read_roots_include_platform_defaults: false,
                    write_roots_override: None,
                    deny_read_paths_override: &deny_read,
                    deny_write_paths_override: no_paths,
                    tty: false,
                    stdin_open: true,
                },
            )
            .await?;
            Ok(codex_windows_sandbox::forward_sandbox_session_stdio(spawned).await)
        })
    }

    /// `--name value` pairs.
    struct Options(HashMap<String, String>);

    impl Options {
        fn parse(args: &[String]) -> Result<Self> {
            let mut values = HashMap::new();
            let mut rest = args.iter();
            while let Some(name) = rest.next() {
                if !name.starts_with("--") {
                    bail!("unexpected {name:?}\n{USAGE}");
                }
                let value = rest.next().ok_or_else(|| anyhow!("{name} needs a value"))?;
                values.insert(name.clone(), value.clone());
            }
            Ok(Self(values))
        }

        fn value(&self, name: &str) -> Result<&str> {
            self.0
                .get(name)
                .map(String::as_str)
                .ok_or_else(|| anyhow!("{name} is required\n{USAGE}"))
        }

        fn path(&self, name: &str) -> Result<PathBuf> {
            Ok(PathBuf::from(self.value(name)?))
        }
    }
}
