# TASK-081 - Unified Policy Decision Boundary

## Summary

TASK-081 adds a typed, immutable, serializable policy decision boundary before
side-effect-capable requests. The boundary is metadata-only and deterministic.
It does not execute actions, call `ActionRouter`, call providers, read
credentials, touch audio, or depend on GUI objects.

Russian remains the default user-facing language.

## Contracts

`core.policy_boundary.PolicyRequest` contains only safe metadata:

- `source`
- `command_id`
- `action_id`
- `intent_kind`
- `risk`
- `required_capabilities`
- `requires_network`
- `confirmation_present`
- `clarification_resolved`
- `metadata`

`core.policy_boundary.PolicyDecision` contains:

- `decision`
- `reason_codes`
- `required_capabilities`
- `requires_confirmation`
- `user_message`
- `safe_to_execute`

Both contracts are frozen dataclasses and expose `to_dict()` for safe
serialization. The serializer redacts obvious API key and token shapes.

## Decisions

- `ALLOW`: the request may continue through the existing execution path.
- `REQUIRE_CONFIRMATION`: execution must stop before `ActionRouter`, providers,
  or other side-effecting handlers. Existing confirmation flows may re-submit
  the same pending action with `confirmation_present=True`.
- `DENY`: execution must stop. Forbidden commands preserve the existing
  forbidden result shape for compatibility.

## Capabilities

The current capability taxonomy is intentionally small and behavior-driven:

- `read_system_state`
- `microphone_capture`
- `network_provider_request`
- `credential_use`
- `file_read`
- `file_write`
- `file_delete`
- `email_send`
- `process_launch`
- `system_control`

No persistent user permission profiles or permissions GUI were added. Those are
deferred to a future task.

## Enforcement Location

The common app/UI boundary is `JarvisAppService._execute_resolved_command()`.
It evaluates policy after TASK-080 intent resolution and clarification, but
before delegating to `CommandProcessor`.

Direct execution paths are also gated inside `CommandProcessor`:

- final action fallback before `SafeActionRouter.route()`;
- explicit provider one-shot, consensus, fallback execution, continuation, and
  local Ollama provider paths before provider request gates.

Desktop Shell continues to call `JarvisAppService`; no policy logic was added
to the GUI. Voice AppService execution uses the same `execute_contract()` path.
The older `VoiceInputManager` confirmation path remains separate and
single-use.

## Clarification Versus Confirmation

TASK-080 clarification happens before policy. A clarification answer such as
`системы` can select the system-status option, but it is not treated as
dangerous-action confirmation.

Confirmation is represented only by `confirmation_present=True` for the same
pending action being re-submitted by an existing confirmation flow. The marker
is cleared immediately after the recursive processing call.

## Provider And Network Handling

Provider requests still require explicit provider-request syntax. The policy
boundary adds `network_provider_request` and `credential_use` capability
metadata for provider commands before request gates can run.

Provider outputs are returned as text only. They are never re-submitted to
`CommandProcessor` or `ActionRouter`.

## Known Limitations

- Policy does not persist user permissions.
- Policy does not perform deep natural-language planning.
- Policy does not execute confirmations itself.
- Existing non-policy safety layers remain authoritative for their own domains.

## Manual Smoke Steps

```powershell
python -m pytest tests/unit/test_policy_decision_boundary.py
python -m pytest tests/integration/test_task_081_unified_policy_boundary.py
python -m pytest tests/integration/test_task_080_hybrid_intent_resolver.py
```

Manual command checks:

- `статус системы` -> allowed system status.
- `покажи статус` -> clarification, no execution.
- `системы` after clarification -> system status, not confirmation.
- `удали файл test.txt` -> confirmation required, no execution.
- `удали System32` -> denied, no `ActionRouter`.
- `можно ли удалить файл` -> conversation, no pending confirmation.

## Separation From Future Permissions

This task creates a decision boundary only. User profiles, persistent permission
settings, policy editing UI, and role-based permission management are outside
TASK-081.
