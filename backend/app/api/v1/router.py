from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    cadences,
    customers,
    dashboard,
    integrations,
    invoices,
    payments,
)

api_v1_router = APIRouter()
api_v1_router.include_router(auth.router)
api_v1_router.include_router(customers.router)
api_v1_router.include_router(invoices.router)
api_v1_router.include_router(payments.router)
api_v1_router.include_router(dashboard.router)
api_v1_router.include_router(cadences.router)
api_v1_router.include_router(cadences.activities_router)
api_v1_router.include_router(integrations.router)
