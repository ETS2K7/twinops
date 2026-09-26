import time
from typing import Optional
from pydantic import BaseModel, Field


class IncidentRecord(BaseModel):
    incident_id: str
    timestamp: float = Field(default_factory=time.time)
    service: str = "checkout-api"
    severity: str = "P1-CRITICAL"
    status: str = "OPEN"
    failing_endpoint: str = "POST /api/checkout"
    error_type: str = "ConnectionPoolExhaustedError"
    error_message: str
    stack_trace: str
    culprit_commit: str = "a4b9c1e: feat(checkout): validate inventory locks before order settlement"
    error_rate_percent: float
    pool_metrics: dict


class TelemetryTracker:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.recent_latencies_ms: list[float] = []
        self.active_incident: Optional[IncidentRecord] = None
        self._incident_counter = 892

    def record_request(
        self,
        status_code: int,
        duration_ms: float,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        pool_metrics: Optional[dict] = None
    ) -> None:
        self.total_requests += 1
        self.recent_latencies_ms.append(duration_ms)
        if len(self.recent_latencies_ms) > 100:
            self.recent_latencies_ms.pop(0)

        if 200 <= status_code < 400:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        error_rate = self.current_error_rate()

        if status_code >= 500 and error_message and not self.active_incident:
            self._incident_counter += 1
            self.active_incident = IncidentRecord(
                incident_id=f"INC-{self._incident_counter}",
                error_message=error_message,
                stack_trace=stack_trace or "",
                error_rate_percent=error_rate,
                pool_metrics=pool_metrics or {},
            )
        elif self.active_incident and error_rate > 10.0:
            self.active_incident.error_rate_percent = error_rate
            if pool_metrics:
                self.active_incident.pool_metrics = pool_metrics

    def current_error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round((self.failed_requests / self.total_requests) * 100, 1)

    def p99_latency(self) -> float:
        if not self.recent_latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.recent_latencies_ms)
        index = int(len(sorted_latencies) * 0.99)
        return round(sorted_latencies[min(index, len(sorted_latencies) - 1)], 1)

    def metrics_summary(self) -> dict:
        return {
            "service": "checkout-api",
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "error_rate_percent": self.current_error_rate(),
            "p99_latency_ms": self.p99_latency(),
            "active_incident_id": self.active_incident.incident_id if self.active_incident else None,
            "health": "CRITICAL" if self.current_error_rate() > 30.0 else "HEALTHY"
        }

    def resolve_incident(self) -> Optional[IncidentRecord]:
        if self.active_incident:
            self.active_incident.status = "RESOLVED"
            resolved = self.active_incident
            self.active_incident = None
            return resolved
        return None

    def reset(self) -> None:
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.recent_latencies_ms.clear()
        self.active_incident = None
