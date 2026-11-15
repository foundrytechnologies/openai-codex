use pretty_assertions::assert_eq;
use serde_json::json;
use tempfile::TempDir;

use super::TraceWriter;
use crate::payload::RawPayloadKind;
use crate::raw_event::RawTraceEventPayload;

fn size(path: &std::path::Path) -> anyhow::Result<u64> {
    let mut total = 0;
    for entry in std::fs::read_dir(path)? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            total += size(&entry.path())?;
        } else {
            total += entry.metadata()?.len();
        }
    }
    Ok(total)
}

#[test]
fn oversized_payload_stops_recording_without_writing_partial_file() -> anyhow::Result<()> {
    let temp = TempDir::new()?;
    let writer = TraceWriter::create_with_budget(
        temp.path(),
        "trace".into(),
        "rollout".into(),
        "root".into(),
        /*budget*/ 1024,
    )?;
    writer.write_json_payload(
        RawPayloadKind::ProtocolEvent,
        &json!({"data": "x".repeat(100_000)}),
    )?;
    assert_eq!(
        std::fs::read_to_string(temp.path().join("capture-limited"))?,
        "1"
    );
    let before = size(temp.path())?;
    assert!(before <= 1024);
    assert_eq!(std::fs::read_dir(temp.path().join("payloads"))?.count(), 0);
    writer.write_json_payload(RawPayloadKind::ProtocolEvent, &json!({"data": "again"}))?;
    writer.append(RawTraceEventPayload::RolloutStarted {
        trace_id: "trace".into(),
        root_thread_id: "root".into(),
    })?;
    assert_eq!(size(temp.path())?, before);
    Ok(())
}

#[test]
fn cumulative_events_and_payloads_share_the_budget() -> anyhow::Result<()> {
    let temp = TempDir::new()?;
    let writer = TraceWriter::create_with_budget(
        temp.path(),
        "trace".into(),
        "rollout".into(),
        "root".into(),
        /*budget*/ 1200,
    )?;
    writer.write_json_payload(
        RawPayloadKind::ProtocolEvent,
        &json!({"data": "x".repeat(200)}),
    )?;
    for _ in 0..20 {
        writer.append(RawTraceEventPayload::RolloutStarted {
            trace_id: "trace".into(),
            root_thread_id: "root".into(),
        })?;
    }
    assert_eq!(
        std::fs::read_to_string(temp.path().join("capture-limited"))?,
        "1"
    );
    let before = size(temp.path())?;
    assert!(before <= 1200);
    writer.append(RawTraceEventPayload::RolloutStarted {
        trace_id: "trace".into(),
        root_thread_id: "root".into(),
    })?;
    assert_eq!(size(temp.path())?, before);
    Ok(())
}
