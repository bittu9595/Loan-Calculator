"""Entry point for the fee calculator HTTP API."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from feecalculator import FeeCalculator, LoanApplication, create_default_calculator
from feecalculator.exceptions import AmountOutOfRangeError, InvalidLoanApplicationError, UnsupportedTermError

from .config import get_allowed_origins
from .schemas import FeeRequest, FeeResponse

logger = logging.getLogger(__name__)

# Domain errors caused by the client's input. Anything else raised by the
# calculator (e.g. a broken fee schedule) is our fault and must surface as a 500.
_CLIENT_ERRORS = (InvalidLoanApplicationError, UnsupportedTermError, AmountOutOfRangeError)


def get_calculator(request: Request) -> FeeCalculator:
    return request.app.state.calculator


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Return only location/message/type: the default handler echoes the raw
    # input back, which reflects client data and crashes on values such as NaN
    # that cannot be JSON-encoded.
    errors = [{"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]} for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Never leak internal exception details/stack traces to clients.
    logger.exception("Unhandled error processing %s %s", request.method, request.url.path)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})


def create_app(calculator: FeeCalculator | None = None) -> FastAPI:
    app = FastAPI(title="Lendable Fee Calculator API", version="1.0.0")

    # Built eagerly so a missing or malformed fee schedule stops the process at
    # startup instead of failing on the first customer request.
    app.state.calculator = calculator or create_default_calculator()

    # Origins are restricted via ALLOWED_ORIGINS (see api/config.py) rather than
    # "*" - a wildcard CORS policy is an OWASP security misconfiguration.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/fee", response_model=FeeResponse)
    def calculate_fee(
        payload: FeeRequest,
        calculator: Annotated[FeeCalculator, Depends(get_calculator)],
    ) -> FeeResponse:
        try:
            application = LoanApplication(term=payload.term, amount=payload.amount)
            fee = calculator.calculate(application)
        except _CLIENT_ERRORS as exc:
            logger.info("Rejected fee request (amount=%s, term=%s): %s", payload.amount, payload.term, exc)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        return FeeResponse(
            amount=float(application.amount),
            term=application.term,
            fee=float(fee),
            total_repayable=float(application.amount + fee),
        )

    return app


app = create_app()
