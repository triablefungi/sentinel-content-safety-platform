from fastapi import APIRouter, HTTPException, Request, status

from sentinel.review.auth import ReviewAuthorizer
from sentinel.review.errors import (
    ReviewAuthorizationError,
    ReviewConflictError,
    ReviewNotFoundError,
)
from sentinel.review.models import (
    FeedbackExport,
    ReviewAppealRequest,
    ReviewAuditEvent,
    ReviewCase,
    ReviewDecisionRequest,
    ReviewPrincipal,
    ReviewState,
)
from sentinel.review.service import ReviewService

review_router = APIRouter(prefix="/v1", tags=["human review"])


def _components(request: Request) -> tuple[ReviewService, ReviewAuthorizer]:
    service: ReviewService | None = request.app.state.review_service
    authorizer: ReviewAuthorizer | None = request.app.state.review_authorizer
    if service is None or authorizer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="human review is not enabled",
        )
    return service, authorizer


def _principal(request: Request, authorizer: ReviewAuthorizer) -> ReviewPrincipal:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="reviewer bearer token is required",
        )
    try:
        return authorizer.authenticate(token)
    except ReviewAuthorizationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error


def _translate(error: Exception) -> HTTPException:
    if isinstance(error, ReviewNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, ReviewConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, ReviewAuthorizationError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    raise error


def _refresh_backlog(request: Request, service: ReviewService, principal: ReviewPrincipal) -> None:
    service.list_cases(principal)
    for state, count in service.backlog().items():
        request.app.state.metrics.review_backlog.labels(state.value).set(count)


@review_router.get("/review-feedback/export", response_model=FeedbackExport)
async def export_review_feedback(request: Request) -> FeedbackExport:
    service, authorizer = _components(request)
    principal = _principal(request, authorizer)
    try:
        export = service.export_feedback(principal)
    except (ReviewAuthorizationError, ReviewConflictError, ReviewNotFoundError) as error:
        raise _translate(error) from error
    request.app.state.metrics.record_review_event("feedback_exported", "success")
    return export


@review_router.get("/reviews", response_model=list[ReviewCase])
async def list_review_cases(
    request: Request,
    state: ReviewState | None = None,
) -> list[ReviewCase]:
    service, authorizer = _components(request)
    principal = _principal(request, authorizer)
    try:
        cases = service.list_cases(principal, state)
        _refresh_backlog(request, service, principal)
        return cases
    except ReviewAuthorizationError as error:
        raise _translate(error) from error


@review_router.get("/reviews/{case_id}", response_model=ReviewCase)
async def get_review_case(case_id: str, request: Request) -> ReviewCase:
    service, authorizer = _components(request)
    principal = _principal(request, authorizer)
    try:
        return service.get(case_id, principal)
    except (ReviewAuthorizationError, ReviewNotFoundError) as error:
        raise _translate(error) from error


@review_router.post("/reviews/{case_id}/claim", response_model=ReviewCase)
async def claim_review_case(case_id: str, request: Request) -> ReviewCase:
    service, authorizer = _components(request)
    principal = _principal(request, authorizer)
    try:
        case = service.claim(case_id, principal)
        _refresh_backlog(request, service, principal)
    except (ReviewAuthorizationError, ReviewConflictError, ReviewNotFoundError) as error:
        request.app.state.metrics.record_review_event("claimed", "failed")
        raise _translate(error) from error
    request.app.state.metrics.record_review_event("claimed", "success")
    return case


@review_router.post("/reviews/{case_id}/decisions", response_model=ReviewCase)
async def decide_review_case(
    case_id: str,
    payload: ReviewDecisionRequest,
    request: Request,
) -> ReviewCase:
    service, authorizer = _components(request)
    principal = _principal(request, authorizer)
    try:
        case = service.decide(case_id, principal, payload.decision, payload.reason_code)
        _refresh_backlog(request, service, principal)
    except (ReviewAuthorizationError, ReviewConflictError, ReviewNotFoundError) as error:
        request.app.state.metrics.record_review_event("decided", "failed")
        raise _translate(error) from error
    request.app.state.metrics.record_review_event("decided", "success")
    if case.resolved_at is not None:
        duration = (case.resolved_at - case.created_at).total_seconds()
        request.app.state.metrics.review_resolution_duration.observe(duration)
    return case


@review_router.post("/reviews/{case_id}/appeals", response_model=ReviewCase)
async def appeal_review_case(
    case_id: str,
    payload: ReviewAppealRequest,
    request: Request,
) -> ReviewCase:
    service, authorizer = _components(request)
    principal = _principal(request, authorizer)
    try:
        case = service.appeal(case_id, principal, payload.reason_code)
        _refresh_backlog(request, service, principal)
    except (ReviewAuthorizationError, ReviewConflictError, ReviewNotFoundError) as error:
        request.app.state.metrics.record_review_event("appealed", "failed")
        raise _translate(error) from error
    request.app.state.metrics.record_review_event("appealed", "success")
    return case


@review_router.get("/reviews/{case_id}/audit", response_model=list[ReviewAuditEvent])
async def get_review_audit(case_id: str, request: Request) -> list[ReviewAuditEvent]:
    service, authorizer = _components(request)
    principal = _principal(request, authorizer)
    try:
        return service.audit(case_id, principal)
    except (ReviewAuthorizationError, ReviewNotFoundError) as error:
        raise _translate(error) from error
