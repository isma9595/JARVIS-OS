"""Pure policy boundary for durable user-memory decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any
import unicodedata


BOUNDED_CANDIDATE_TTL_SECONDS = 86_400
_MAX_OPAQUE_RECORD_ID_LENGTH = 128


def _contains_mutable_container(value: Any) -> bool:
    if isinstance(value, (list, dict, set, bytearray)):
        return True
    if isinstance(value, (tuple, frozenset)):
        return any(_contains_mutable_container(item) for item in value)
    return False


def _reject_mutable_container(value: Any, *, field_name: str) -> None:
    if _contains_mutable_container(value):
        raise TypeError(f"{field_name} must not contain mutable containers")


class MemoryPolicyDecisionType(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    REJECT = "reject"


class MemoryPolicyOperation(str, Enum):
    UPSERT = "upsert"
    DELETE_EXACT = "delete_exact"
    DELETE_ALL = "delete_all"


class MemoryOrigin(str, Enum):
    EXPLICIT_USER_COMMAND = "explicit_user_command"
    INFERRED_CONVERSATION = "inferred_conversation"
    SYSTEM_DERIVED = "system_derived"
    PROVIDER_DERIVED = "provider_derived"


class MemorySubjectKind(str, Enum):
    USER_FACT = "user_fact"
    PROFILE_PREFERENCE = "profile_preference"
    CONVERSATION_SESSION = "conversation_session"
    WORKFLOW_STATE = "workflow_state"
    EXECUTION_OPERATION = "execution_operation"
    DESKTOP_DIAGNOSTIC = "desktop_diagnostic"
    PROVIDER_CONTEXT = "provider_context"


class MemorySensitivity(str, Enum):
    GENERAL_PERSONAL = "general_personal"
    SENSITIVE_PERSONAL = "sensitive_personal"
    SECRET_LIKE = "secret_like"
    UNKNOWN = "unknown"


class MemoryRetentionClass(str, Enum):
    UNTIL_USER_FORGETS = "until_user_forgets"
    BOUNDED_CANDIDATE = "bounded_candidate"
    DO_NOT_STORE = "do_not_store"


class MemoryMutationInstruction(str, Enum):
    CREATE = "create"
    NOOP_DUPLICATE = "noop_duplicate"
    SUPERSEDE_EXISTING = "supersede_existing"
    DELETE_EXACT = "delete_exact"
    DELETE_ALL = "delete_all"


class MemoryPolicyReasonCode(str, Enum):
    ALLOWED_EXPLICIT_USER_FACT = "allowed_explicit_user_fact"
    APPROVAL_REQUIRED_FOR_INFERRED_FACT = "approval_required_for_inferred_fact"
    APPROVED_INFERRED_FACT = "approved_inferred_fact"
    DERIVED_WRITE_REJECTED = "derived_write_rejected"
    APPROVED_DERIVED_FACT = "approved_derived_fact"
    SECRET_LIKE_CONTENT = "secret_like_content"
    WRONG_AUTHORITY = "wrong_authority"
    PROFILE_SUBSYSTEM_AUTHORITY = "profile_subsystem_authority"
    MALFORMED_REQUEST = "malformed_request"
    MISSING_REQUIRED_KEY = "missing_required_key"
    MISSING_REQUIRED_VALUE = "missing_required_value"
    EXACT_DUPLICATE = "exact_duplicate"
    SUPERSEDES_EXISTING = "supersedes_existing"
    AMBIGUOUS_EXISTING_RECORD = "ambiguous_existing_record"
    EXACT_DELETE_ALLOWED = "exact_delete_allowed"
    MISSING_EXACT_TARGET = "missing_exact_target"
    AMBIGUOUS_EXACT_TARGET = "ambiguous_exact_target"
    FORGET_ALL_REQUIRES_APPROVAL = "forget_all_requires_approval"
    FORGET_ALL_APPROVED = "forget_all_approved"
    UNKNOWN_SENSITIVITY = "unknown_sensitivity"


@dataclass(frozen=True)
class ExistingMemoryRecordSummary:
    """Detached minimum record view needed for deterministic comparisons."""

    record_id: Any
    key: Any
    value: Any

    def __post_init__(self) -> None:
        _reject_mutable_container(self.record_id, field_name="record_id")
        _reject_mutable_container(self.key, field_name="key")
        _reject_mutable_container(self.value, field_name="value")


@dataclass(frozen=True)
class MemoryPolicyRequest:
    """Fully formed request evaluated without loading any external state."""

    operation: Any
    origin: Any
    subject_kind: Any
    key: Any = None
    value: Any = None
    target_record_id: Any = None
    existing_records: tuple[ExistingMemoryRecordSummary, ...] = ()
    approval_verified: Any = False

    def __post_init__(self) -> None:
        _reject_mutable_container(self.operation, field_name="operation")
        _reject_mutable_container(self.origin, field_name="origin")
        _reject_mutable_container(
            self.subject_kind,
            field_name="subject_kind",
        )
        _reject_mutable_container(self.key, field_name="key")
        _reject_mutable_container(self.value, field_name="value")
        _reject_mutable_container(
            self.target_record_id,
            field_name="target_record_id",
        )
        _reject_mutable_container(
            self.approval_verified,
            field_name="approval_verified",
        )
        records = self.existing_records
        if not isinstance(records, tuple):
            if isinstance(records, (str, bytes)) or records is None:
                records = (records,)
            else:
                try:
                    records = tuple(records)
                except TypeError:
                    records = (records,)
            object.__setattr__(self, "existing_records", records)
        _reject_mutable_container(records, field_name="existing_records items")


@dataclass(frozen=True)
class MemoryPolicyDecision:
    """Safe policy result; its projection intentionally excludes memory content."""

    decision_type: MemoryPolicyDecisionType
    reason_codes: tuple[MemoryPolicyReasonCode, ...]
    approval_required: bool
    sensitivity: MemorySensitivity
    retention_class: MemoryRetentionClass
    retention_duration_seconds: int | None
    mutation_instruction: MemoryMutationInstruction | None
    existing_record_id: str | None = None

    def __post_init__(self) -> None:
        reasons = self.reason_codes
        if not isinstance(reasons, tuple):
            reasons = tuple(reasons)
            object.__setattr__(self, "reason_codes", reasons)
        _reject_mutable_container(reasons, field_name="reason_codes items")
        for field_name in (
            "decision_type",
            "approval_required",
            "sensitivity",
            "retention_class",
            "retention_duration_seconds",
            "mutation_instruction",
            "existing_record_id",
        ):
            _reject_mutable_container(
                getattr(self, field_name),
                field_name=field_name,
            )
        if (
            self.existing_record_id is not None
            and not _is_safe_opaque_record_id(self.existing_record_id)
        ):
            raise TypeError("existing_record_id must be a safe opaque identifier")

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_type": self.decision_type.value,
            "reason_codes": [reason.value for reason in self.reason_codes],
            "approval_required": self.approval_required,
            "sensitivity": self.sensitivity.value,
            "retention_class": self.retention_class.value,
            "retention_duration_seconds": self.retention_duration_seconds,
            "mutation_instruction": (
                self.mutation_instruction.value
                if self.mutation_instruction is not None
                else None
            ),
            "existing_record_id": self.existing_record_id,
        }


_CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SECRET_MATERIAL = r"[A-Za-z0-9_./+=-]{8,}"
_SECRET_KEY_LABEL_PATTERN = re.compile(
    r"(?:password|passwd|pwd|пароль|credentials?|"
    r"api[_ -]?key|access[_ -]?token|auth[_ -]?token|"
    r"authorization|bearer|secret|private[_ -]?key)",
    re.IGNORECASE,
)
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(
        rf"\b(?:password|passwd|pwd|пароль|credentials?)"
        r"\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\bauthorization\s*:\s*bearer\s+{_SECRET_MATERIAL}",
        re.IGNORECASE,
    ),
    re.compile(rf"\bbearer\s+{_SECRET_MATERIAL}", re.IGNORECASE),
    re.compile(
        r"\b(?:api[_ -]?key|access[_ -]?token|auth[_ -]?token|secret|token)"
        rf"(?:\s*[:=]\s*|\s+){_SECRET_MATERIAL}",
        re.IGNORECASE,
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}", re.IGNORECASE),
)
_SENSITIVE_PERSONAL_PATTERNS = (
    re.compile(
        r"\b(?:passport|social security|ssn|medical|diagnosis|health|"
        r"bank account|credit card|religion|sexual orientation)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:паспорт\w*|снилс|инн|диагноз\w*|здоровь\w*)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:медицинск\w*\s+диагноз\w*|"
        r"кредитн\w*\s+карт\w*|банковск\w*\s+карт\w*)\b",
        re.IGNORECASE,
    ),
)
_OPAQUE_RECORD_ID_PATTERN = re.compile(
    rf"[A-Za-z0-9][A-Za-z0-9._:-]{{0,{_MAX_OPAQUE_RECORD_ID_LENGTH - 1}}}\Z"
)
_RECORD_ID_CREDENTIAL_PATTERN = re.compile(
    r"\A(?:"
    r"sk|token|bearer|credentials?|password|passwd|pwd|secret|authorization|"
    r"api[-_.:]?key|private[-_.:]?key|"
    r"access[-_.:]?token|auth[-_.:]?token"
    r")[-_.:]",
    re.IGNORECASE,
)


def _normalize_text(value: Any, *, fold_case: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFKC", value)
    normalized = " ".join(normalized.strip().split())
    return normalized.casefold() if fold_case else normalized


def _has_control_characters(value: str) -> bool:
    return _CONTROL_CHARACTER_PATTERN.search(value) is not None


def _is_secret_like_text(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)


def _is_safe_opaque_record_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not value or len(value) > _MAX_OPAQUE_RECORD_ID_LENGTH:
        return False
    if _has_control_characters(value) or any(character.isspace() for character in value):
        return False
    if unicodedata.normalize("NFKC", value) != value:
        return False
    if _OPAQUE_RECORD_ID_PATTERN.fullmatch(value) is None:
        return False
    if _RECORD_ID_CREDENTIAL_PATTERN.search(value) is not None:
        return False
    return not _is_secret_like_text(value)


class MemoryPolicy:
    """Stateless evaluator for memory eligibility and mutation intent."""

    def classify(self, key: Any, value: Any) -> MemorySensitivity:
        normalized_key = _normalize_text(key, fold_case=True)
        normalized_value = _normalize_text(value)
        if (
            normalized_key is None
            or normalized_value is None
            or not normalized_key
            or not normalized_value
            or _has_control_characters(key)
            or _has_control_characters(value)
        ):
            return MemorySensitivity.UNKNOWN

        combined = f"{normalized_key}\n{normalized_value}"
        if (
            _SECRET_KEY_LABEL_PATTERN.fullmatch(normalized_key) is not None
            or _is_secret_like_text(normalized_value)
            or _is_secret_like_text(combined)
        ):
            return MemorySensitivity.SECRET_LIKE
        if any(
            pattern.search(combined)
            for pattern in _SENSITIVE_PERSONAL_PATTERNS
        ):
            return MemorySensitivity.SENSITIVE_PERSONAL
        return MemorySensitivity.GENERAL_PERSONAL

    def evaluate(self, request: Any) -> MemoryPolicyDecision:
        if not self._is_structurally_valid(request):
            return self._reject(MemoryPolicyReasonCode.MALFORMED_REQUEST)

        if request.subject_kind is MemorySubjectKind.PROFILE_PREFERENCE:
            return self._reject(
                MemoryPolicyReasonCode.PROFILE_SUBSYSTEM_AUTHORITY
            )
        if request.subject_kind is not MemorySubjectKind.USER_FACT:
            return self._reject(MemoryPolicyReasonCode.WRONG_AUTHORITY)

        if request.operation is MemoryPolicyOperation.UPSERT:
            return self._evaluate_upsert(request)
        if request.operation is MemoryPolicyOperation.DELETE_EXACT:
            return self._evaluate_delete_exact(request)
        return self._evaluate_delete_all(request)

    @staticmethod
    def _is_structurally_valid(request: Any) -> bool:
        if not isinstance(request, MemoryPolicyRequest):
            return False
        if not isinstance(request.operation, MemoryPolicyOperation):
            return False
        if not isinstance(request.origin, MemoryOrigin):
            return False
        if not isinstance(request.subject_kind, MemorySubjectKind):
            return False
        if not isinstance(request.approval_verified, bool):
            return False
        if not isinstance(request.existing_records, tuple):
            return False
        for record in request.existing_records:
            if not isinstance(record, ExistingMemoryRecordSummary):
                return False
            record_id = record.record_id
            key = _normalize_text(record.key, fold_case=True)
            value = _normalize_text(record.value)
            if (
                not _is_safe_opaque_record_id(record_id)
                or not key
                or value is None
            ):
                return False
        return True

    def _evaluate_upsert(
        self,
        request: MemoryPolicyRequest,
    ) -> MemoryPolicyDecision:
        normalized_key = _normalize_text(request.key, fold_case=True)
        if not normalized_key:
            return self._reject(MemoryPolicyReasonCode.MISSING_REQUIRED_KEY)
        normalized_value = _normalize_text(request.value)
        if not normalized_value:
            return self._reject(MemoryPolicyReasonCode.MISSING_REQUIRED_VALUE)

        sensitivity = self.classify(request.key, request.value)
        if sensitivity is MemorySensitivity.SECRET_LIKE:
            return self._reject(
                MemoryPolicyReasonCode.SECRET_LIKE_CONTENT,
                sensitivity=sensitivity,
            )
        if sensitivity is MemorySensitivity.UNKNOWN:
            return self._reject(
                MemoryPolicyReasonCode.UNKNOWN_SENSITIVITY,
                sensitivity=sensitivity,
            )

        same_key = tuple(
            record
            for record in request.existing_records
            if _normalize_text(record.key, fold_case=True) == normalized_key
        )
        if len(same_key) > 1:
            return self._reject(
                MemoryPolicyReasonCode.AMBIGUOUS_EXISTING_RECORD,
                sensitivity=sensitivity,
            )

        mutation = MemoryMutationInstruction.CREATE
        existing_record_id = None
        mutation_reason = None
        if same_key:
            record = same_key[0]
            existing_record_id = record.record_id
            if _normalize_text(record.value) == normalized_value:
                mutation = MemoryMutationInstruction.NOOP_DUPLICATE
                mutation_reason = MemoryPolicyReasonCode.EXACT_DUPLICATE
            else:
                mutation = MemoryMutationInstruction.SUPERSEDE_EXISTING
                mutation_reason = MemoryPolicyReasonCode.SUPERSEDES_EXISTING

        origin_decision = self._origin_decision(
            request,
            sensitivity=sensitivity,
            mutation=mutation,
            existing_record_id=existing_record_id,
        )
        if (
            mutation_reason is None
            or origin_decision.decision_type is MemoryPolicyDecisionType.REJECT
        ):
            return origin_decision
        return MemoryPolicyDecision(
            decision_type=origin_decision.decision_type,
            reason_codes=origin_decision.reason_codes + (mutation_reason,),
            approval_required=origin_decision.approval_required,
            sensitivity=origin_decision.sensitivity,
            retention_class=origin_decision.retention_class,
            retention_duration_seconds=(
                origin_decision.retention_duration_seconds
            ),
            mutation_instruction=origin_decision.mutation_instruction,
            existing_record_id=origin_decision.existing_record_id,
        )

    @staticmethod
    def _origin_decision(
        request: MemoryPolicyRequest,
        *,
        sensitivity: MemorySensitivity,
        mutation: MemoryMutationInstruction,
        existing_record_id: str | None,
    ) -> MemoryPolicyDecision:
        if request.origin is MemoryOrigin.EXPLICIT_USER_COMMAND:
            decision_type = MemoryPolicyDecisionType.ALLOW
            reason = MemoryPolicyReasonCode.ALLOWED_EXPLICIT_USER_FACT
            approval_required = False
            retention = MemoryRetentionClass.UNTIL_USER_FORGETS
            duration = None
        elif request.origin is MemoryOrigin.INFERRED_CONVERSATION:
            if request.approval_verified:
                decision_type = MemoryPolicyDecisionType.ALLOW
                reason = MemoryPolicyReasonCode.APPROVED_INFERRED_FACT
                approval_required = False
                retention = MemoryRetentionClass.UNTIL_USER_FORGETS
                duration = None
            else:
                decision_type = MemoryPolicyDecisionType.REQUIRE_APPROVAL
                reason = (
                    MemoryPolicyReasonCode.APPROVAL_REQUIRED_FOR_INFERRED_FACT
                )
                approval_required = True
                retention = MemoryRetentionClass.BOUNDED_CANDIDATE
                duration = BOUNDED_CANDIDATE_TTL_SECONDS
        elif request.approval_verified:
            decision_type = MemoryPolicyDecisionType.ALLOW
            reason = MemoryPolicyReasonCode.APPROVED_DERIVED_FACT
            approval_required = False
            retention = MemoryRetentionClass.UNTIL_USER_FORGETS
            duration = None
        else:
            return MemoryPolicy._reject(
                MemoryPolicyReasonCode.DERIVED_WRITE_REJECTED,
                sensitivity=sensitivity,
            )

        return MemoryPolicyDecision(
            decision_type=decision_type,
            reason_codes=(reason,),
            approval_required=approval_required,
            sensitivity=sensitivity,
            retention_class=retention,
            retention_duration_seconds=duration,
            mutation_instruction=mutation,
            existing_record_id=existing_record_id,
        )

    @staticmethod
    def _evaluate_delete_exact(
        request: MemoryPolicyRequest,
    ) -> MemoryPolicyDecision:
        normalized_target = _normalize_text(request.target_record_id)
        if not normalized_target:
            return MemoryPolicy._reject(
                MemoryPolicyReasonCode.MISSING_EXACT_TARGET
            )
        if not _is_safe_opaque_record_id(request.target_record_id):
            return MemoryPolicy._reject(
                MemoryPolicyReasonCode.MALFORMED_REQUEST
            )
        target = request.target_record_id

        matches = tuple(
            record
            for record in request.existing_records
            if record.record_id == target
        )
        if not matches:
            return MemoryPolicy._reject(
                MemoryPolicyReasonCode.MISSING_EXACT_TARGET
            )
        if len(matches) > 1:
            return MemoryPolicy._reject(
                MemoryPolicyReasonCode.AMBIGUOUS_EXACT_TARGET
            )
        return MemoryPolicyDecision(
            decision_type=MemoryPolicyDecisionType.ALLOW,
            reason_codes=(MemoryPolicyReasonCode.EXACT_DELETE_ALLOWED,),
            approval_required=False,
            sensitivity=MemorySensitivity.UNKNOWN,
            retention_class=MemoryRetentionClass.DO_NOT_STORE,
            retention_duration_seconds=None,
            mutation_instruction=MemoryMutationInstruction.DELETE_EXACT,
            existing_record_id=target,
        )

    @staticmethod
    def _evaluate_delete_all(
        request: MemoryPolicyRequest,
    ) -> MemoryPolicyDecision:
        approved = request.approval_verified
        return MemoryPolicyDecision(
            decision_type=(
                MemoryPolicyDecisionType.ALLOW
                if approved
                else MemoryPolicyDecisionType.REQUIRE_APPROVAL
            ),
            reason_codes=(
                MemoryPolicyReasonCode.FORGET_ALL_APPROVED
                if approved
                else MemoryPolicyReasonCode.FORGET_ALL_REQUIRES_APPROVAL,
            ),
            approval_required=not approved,
            sensitivity=MemorySensitivity.UNKNOWN,
            retention_class=MemoryRetentionClass.DO_NOT_STORE,
            retention_duration_seconds=None,
            mutation_instruction=MemoryMutationInstruction.DELETE_ALL,
            existing_record_id=None,
        )

    @staticmethod
    def _reject(
        reason: MemoryPolicyReasonCode,
        *,
        sensitivity: MemorySensitivity = MemorySensitivity.UNKNOWN,
    ) -> MemoryPolicyDecision:
        return MemoryPolicyDecision(
            decision_type=MemoryPolicyDecisionType.REJECT,
            reason_codes=(reason,),
            approval_required=False,
            sensitivity=sensitivity,
            retention_class=MemoryRetentionClass.DO_NOT_STORE,
            retention_duration_seconds=None,
            mutation_instruction=None,
            existing_record_id=None,
        )
