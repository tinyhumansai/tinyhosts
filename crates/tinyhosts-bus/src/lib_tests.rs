//! Contract wire compatibility without any hosting implementation dependency.
use super::*;

#[test]
fn requests_keep_provider_defaults_operation_tags_and_secret_redaction() {
    let request: rpc::Request = serde_json::from_value(serde_json::json!({
        "operation": "list_sites", "credentials": {"api_key": "private-key"}
    }))
    .unwrap();
    assert_eq!(request.provider, ProviderId::Vercel);
    assert!(matches!(
        request.operation,
        rpc::Operation::ListSites { limit: 20 }
    ));
    assert!(!format!("{request:?}").contains("private-key"));
}

#[test]
fn deployment_bytes_keep_the_existing_base64_wire_shape() {
    let operation: rpc::Operation = serde_json::from_value(serde_json::json!({
        "operation": "deploy", "request": { "site": "site", "bundle": [
            {"path": "index.html", "contents": "SGVsbG8="}
        ] }
    }))
    .unwrap();
    let value = serde_json::to_value(operation).unwrap();
    assert_eq!(value["request"]["bundle"][0]["contents"], "SGVsbG8=");
    assert_eq!(value["request"]["target"], "preview");
}

#[test]
fn tool_declarations_and_result_envelopes_keep_the_existing_wire() {
    let tools: Vec<ToolDeclaration> = serde_json::from_str(TOOL_DECLARATIONS_JSON).unwrap();
    assert_eq!(tools.len(), 10);
    assert_eq!(tools[0].name, "hosting_launch_site");
    assert_eq!(tools.iter().filter(|tool| tool.external_effect).count(), 4);
    let result: rpc::Outcome =
        serde_json::from_value(serde_json::json!({"result": "done"})).unwrap();
    assert_eq!(
        serde_json::to_value(result).unwrap(),
        serde_json::json!({"result": "done"})
    );
    assert_eq!(METHODS, ["Execute", "Providers"]);
    assert_eq!(CONTRACT_VERSION, env!("CARGO_PKG_VERSION"));
}

#[test]
fn authorized_preparation_is_additive_versioned_and_not_a_model_tool() {
    let op: rpc::Operation = serde_json::from_value(serde_json::json!({"operation":"prepare_bundle", "directory":{"workspace":"/approved", "path":"."}})).unwrap();
    let rpc::Operation::PrepareBundle { directory } = op else {
        panic!("wrong operation")
    };
    assert_eq!(directory.max_bytes, preparation::MAX_PREPARATION_BYTES);
    assert_eq!(directory.max_files, preparation::MAX_PREPARATION_FILES);
    assert!(is_compatible((1, 1)));
    assert!(is_compatible((1, 2)));
    assert!(!is_compatible((1, 0)));
    assert!(!is_compatible((2, 1)));
    assert_eq!(WIRE_CONTRACT_VERSION, (1, 1));
    assert!(!TOOL_DECLARATIONS_JSON.contains("prepare_bundle"));
    assert!(
        serde_json::from_value::<preparation::AuthorizedDirectory>(
            serde_json::json!({"workspace":"/approved", "path":".","extra":true})
        )
        .is_err()
    );
}
