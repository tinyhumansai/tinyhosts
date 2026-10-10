//! Minimal hosting vocabulary for hosts that execute through compiled TinyBus modules.
pub mod error;
pub mod inputs;
mod launch;
pub mod model;
pub mod rpc;
pub use error::{Error, Result};
pub use launch::Launch;
pub use model::*;
/// Well-known hosting interface and bus name.
pub const BUS_NAME: &str = "ai.tinyhumans.tinyhosts.Hosting";
/// Hosting object path.
pub const OBJECT_PATH: &str = "/ai/tinyhumans/tinyhosts/Hosting";
/// Member names in their existing order and arity.
pub const METHODS: [&str; 2] = ["Execute", "Providers"];
/// Contract package version, synchronized with the released module manifest.
pub const CONTRACT_VERSION: &str = env!("CARGO_PKG_VERSION");
/// Recorded agent tool declarations, including approval metadata.
pub const TOOL_DECLARATIONS_JSON: &str = include_str!("declarations.json");

/// Hosting provider identifiers, independent of provider connection behavior.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
#[non_exhaustive]
pub enum ProviderId {
    /// Vercel hosting.
    #[default]
    Vercel,
}

/// Agent-facing declaration, independent of the implementation Tool trait.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct ToolDeclaration {
    /// Stable tool name.
    pub name: String,
    /// Existing model-facing description.
    pub description: String,
    /// Existing JSON argument schema.
    pub parameters_schema: serde_json::Value,
    /// Whether OpenHuman must apply its external-effect approval policy.
    pub external_effect: bool,
}

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
