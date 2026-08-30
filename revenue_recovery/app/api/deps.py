import os
from fastapi import Request
from app.db.container import PersistenceContainer
from app.adapters.razorpay import RazorpayWebhookService

def get_container(request: Request) -> PersistenceContainer:
    if hasattr(request.app, "state") and hasattr(request.app.state, "container"):
        return request.app.state.container
    from app.main import _container
    return _container

def get_webhook_service(request: Request) -> RazorpayWebhookService:
    if hasattr(request.app, "state") and hasattr(request.app.state, "webhook_service"):
        return request.app.state.webhook_service
    from app.main import _default_webhook_service
    return _default_webhook_service

def get_webhook_secret(request: Request) -> str:
    if hasattr(request.app, "state") and hasattr(request.app.state, "webhook_secret"):
        return request.app.state.webhook_secret
    return os.environ.get("RAZORPAY_WEBHOOK_SECRET", "") or "unconfigured-placeholder-secret"
