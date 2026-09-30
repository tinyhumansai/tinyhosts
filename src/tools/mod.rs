//! The `hosting_*` agent tools, as [`tinytools::Tool`]s over a [`Host`].
//!
//! Ten tools over one hosting account. They are thin on purpose: argument
//! parsing, one call into this crate, and a result described for a model.
//! Anything that looks like hosting logic belongs in the crate proper, where it
//! is provider-independent and tested against a mock of the provider's API.
//!
//! What a host supplies is the [`Host`] client (credentials are its business)
//! and the workspace directory `hosting_launch_site` deploys from. Whether to
//! register the tools at all, and the approval gate in front of the four that
//! change the world, stay with the host.
//!
//! `hosting_launch_site` uploads a directory to a third party and can spend
//! money on a database, and `hosting_rollback` repoints a live site's
//! production traffic; both route through the approval gate, as do
//! `hosting_set_env` and `hosting_add_domain`. The rest read.
//!
//! # Why there is a rollback but no separate "promote"
//!
//! [`Host::promote`] is both: a rollback *is* a promote of an older deployment,
//! and the crate models it once deliberately. The tool is named for the reason
//! an agent reaches for it. Without it an agent can deploy a broken site and
//! have no way back, which is the whole argument for the tool existing.

mod analytics;
mod deployments;
mod domains;
mod launch;
mod sites;

use serde_json::Value;

pub use analytics::AnalyticsTool;
pub use deployments::{
    DeploymentLogsTool, DeploymentStatusTool, ListDeploymentsTool, RollbackTool,
};
pub use domains::{AddDomainTool, DomainStatusTool};
pub use launch::LaunchSiteTool;
pub use sites::{ListSitesTool, SetEnvTool};

use std::path::{Path, PathBuf};
use std::sync::Arc;

use crate::Host;
use tinytools::Tool;

/// Every hosting tool, for one provider client and one workspace.
#[must_use]
pub fn hosting_tools(host: &Arc<dyn Host>, workspace_dir: &Path) -> Vec<Box<dyn Tool>> {
    vec![
        Box::new(LaunchSiteTool::new(
            Arc::clone(host),
            workspace_dir.to_path_buf(),
        )),
        Box::new(DeploymentStatusTool::new(Arc::clone(host))),
        Box::new(ListDeploymentsTool::new(Arc::clone(host))),
        Box::new(DeploymentLogsTool::new(Arc::clone(host))),
        Box::new(RollbackTool::new(Arc::clone(host))),
        Box::new(ListSitesTool::new(Arc::clone(host))),
        Box::new(SetEnvTool::new(Arc::clone(host))),
        Box::new(AddDomainTool::new(Arc::clone(host))),
        Box::new(DomainStatusTool::new(Arc::clone(host))),
        Box::new(AnalyticsTool::new(Arc::clone(host))),
    ]
}

/// Reads a required string argument.
fn required_str(args: &Value, key: &str) -> anyhow::Result<String> {
    args.get(key)
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(ToOwned::to_owned)
        .ok_or_else(|| anyhow::anyhow!("`{key}` is required"))
}

/// Renders one `env` object value. A number or a bool is still a variable, so
/// it is rendered rather than dropped. `null` and a container are refused: a
/// variable silently set to `"null"` is worse than a named error.
fn env_value(key: &str, value: &Value) -> anyhow::Result<String> {
    match value {
        Value::String(value) => Ok(value.clone()),
        Value::Number(_) | Value::Bool(_) => Ok(value.to_string()),
        _ => anyhow::bail!("`env.{key}` must be a string, number, or boolean"),
    }
}

/// Resolves `relative` against the workspace, refusing anything outside it.
///
/// An agent names the directory to deploy, and a deployment uploads every byte
/// under it to a third party. `../` and absolute paths are therefore refused
/// here rather than trusted to the model — this is the only place that decides
/// what may leave the machine.
///
/// # Errors
///
/// Returns an error when the path is absolute, escapes the workspace, or does
/// not name a directory.
pub fn resolve_in_workspace(workspace_dir: &Path, relative: &str) -> anyhow::Result<PathBuf> {
    let trimmed = relative.trim();
    let candidate = PathBuf::from(if trimmed.is_empty() { "." } else { trimmed });

    if candidate.is_absolute() {
        anyhow::bail!("path must be relative to the workspace, not absolute: {relative}");
    }

    let joined = workspace_dir.join(&candidate);
    let canonical = joined
        .canonicalize()
        .map_err(|error| anyhow::anyhow!("cannot read {}: {error}", joined.display()))?;
    let root = workspace_dir.canonicalize().map_err(|error| {
        anyhow::anyhow!(
            "cannot read the workspace {}: {error}",
            workspace_dir.display()
        )
    })?;

    if !canonical.starts_with(&root) {
        anyhow::bail!("path escapes the workspace: {relative}");
    }
    if !canonical.is_dir() {
        anyhow::bail!("not a directory: {relative}");
    }

    Ok(canonical)
}
