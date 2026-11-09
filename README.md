# Lendable Fee Calculator

A loan fee calculator with a Python backend (domain logic + HTTP API) and a React frontend.

## Fee calculation rules

- Fees are defined by a schedule of (loan amount -> fee) breakpoints, one per £1,000, separately for a 12-month and 24-month term.
- For a loan amount that falls between two breakpoints, the fee is **linearly interpolated** between the lower and upper breakpoint.
- The resulting fee is **rounded up** so that `fee + loan amount` is an exact multiple of £5.
- Loan amounts are supported from £1,000 to £20,000 (inclusive), with up to 2 decimal places.

## Project structure

```
backend/
  feecalculator/   # Domain logic: schedules, interpolation, rounding, calculator
  api/              # FastAPI application exposing the calculator over HTTP
  tests/            # pytest suite
frontend/
  src/              # React + TypeScript single-page app
```

## Backend

The domain logic lives in `backend/feecalculator` and is deliberately split into
small, independently replaceable pieces:

| Concern                                       | Abstraction             | Default implementation                                                         |
| --------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------ |
| Where the fee schedule data comes from        | `FeeScheduleRepository` | `JsonFileFeeScheduleRepository` (reads `feecalculator/data/fee_schedule.json`) |
| How a fee is interpolated between breakpoints | `InterpolationStrategy` | `LinearInterpolationStrategy`                                                  |
| How the final fee is rounded                  | `FeeRoundingStrategy`   | `RoundUpToNearestMultipleStrategy` (rounds up to the nearest £5)               |

This means, for example, that switching the fee schedule source to a database or a
remote REST API only requires a new `FeeScheduleRepository` implementation - the
calculator, API and tests are unaffected. Similarly, the interpolation or rounding
rules can be swapped by implementing the relevant strategy interface.

All fee arithmetic uses Python's `Decimal` type (never `float`) to avoid
binary floating-point rounding errors. Floats only appear at the HTTP boundary
(see [Known limitations](#known-limitations)).

#### Fee schedule data

`feecalculator/data/fee_schedule.json` maps each term (in months) to its
breakpoints, keyed by loan amount:

```json
{
  "12": { "1000": 50, "2000": 90, "...": "..." },
  "24": { "1000": 70, "2000": 100, "...": "..." }
}
```

The file is loaded and validated **once, at startup**. A missing or malformed
file raises `InvalidFeeScheduleError` and stops the process, rather than failing
customer requests. Each term must have at least two breakpoints, with finite
values, positive amounts, non-negative fees, and no duplicate amounts.

#### Domain exceptions

All exceptions derive from `FeeCalculatorError` (`feecalculator/exceptions.py`):

| Exception                     | Meaning                                                     | HTTP status |
| ----------------------------- | ----------------------------------------------------------- | ----------- |
| `InvalidLoanApplicationError` | Amount not a finite positive value with at most 2 dp, or term not a positive integer | 400         |
| `UnsupportedTermError`        | No schedule exists for the requested term                    | 400         |
| `AmountOutOfRangeError`       | Amount outside the schedule's min/max breakpoints            | 400         |
| `InvalidFeeScheduleError`     | Schedule data is broken (a server-side configuration error)  | 500         |

### Setup & running the API

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"     # or: pip install -r requirements-dev.txt
.\.venv\Scripts\python -m uvicorn api.main:app --reload --port 8000
```

`requirements.txt` holds runtime dependencies only. `requirements-dev.txt` adds
the test and lint tooling (pytest, httpx, ruff).

For production, install runtime dependencies only and run without `--reload`, e.g.
`uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4`. Each worker
loads its own copy of the fee schedule.

#### Configuration

| Environment variable | Default                                         | Purpose                                    |
| -------------------- | ----------------------------------------------- | ------------------------------------------ |
| `ALLOWED_ORIGINS`    | `http://localhost:5173,http://localhost:3000` | Comma-separated CORS allow-list (never `*`) |

CORS only allows `GET`/`POST` and the `Content-Type` header. Origins are read
once, when the app is created.

#### Endpoints

The API will be available at `http://localhost:8000` (interactive docs at `/docs`):

- `POST /api/fee` - body `{"amount": 2750, "term": 24}` -> `{"amount": 2750.0, "term": 24, "fee": 115.0, "total_repayable": 2865.0}`
  - `amount` may be a JSON number or a numeric string (e.g. `"2750.00"`).
  - `term` must be a JSON integer. `true`, `"12"` and `12.0` are rejected.
  - Unknown fields are rejected.
- `GET /api/health` - basic health check -> `{"status": "ok"}`

#### Error responses

| Status | When                                                                                                                                                   | Body                                                        |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| `422`  | Malformed request: invalid JSON, missing/unknown fields, non-numeric/NaN/Infinity/non-positive amount, more than 2 decimal places, non-integer or non-positive term | `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` |
| `400`  | Well-formed request the calculator can't serve: unsupported term, or amount outside £1,000-£20,000                                                      | `{"detail": "<reason>"}`                                    |
| `500`  | Internal error. Details are logged server-side, never returned                                                                                         | `{"detail": "Internal server error"}`                       |

Amounts with sub-pence precision are **rejected, never silently rounded**.
Validation errors never echo the submitted input back. This avoids reflecting
client data, and avoids crashing on values such as `NaN` that cannot be
JSON-encoded.

#### Using a custom calculator

`api.main.create_app(calculator=None)` builds the FastAPI app. Pass your own
`FeeCalculator` (e.g. backed by a different `FeeScheduleRepository`) to serve
it over HTTP, or to inject a fake in tests:

```python
from api.main import create_app
from feecalculator import FeeCalculator, InMemoryFeeScheduleRepository

app = create_app(FeeCalculator(InMemoryFeeScheduleRepository({...})))
```

`api.main:app` is the default instance, wired to the bundled JSON schedule.

### Running the tests

```powershell
cd backend
.\.venv\Scripts\python -m pytest -v
.\.venv\Scripts\python -m ruff check .
```

The suite covers:

- **Calculation:** every published breakpoint for both terms, interpolated
  values (including the worked example from the spec), decreasing fee segments,
  boundary amounts (£1,000 / £20,000), pence-level precision, and a
  property-style check that `fee + loan` is always a multiple of £5.
- **Input validation:** non-finite and sub-pence amounts, invalid terms,
  unsupported terms, and out-of-range amounts.
- **Schedule loading:** missing files, invalid JSON, wrong shapes, too few
  breakpoints, negative fees, and duplicate amounts.
- **HTTP layer:** status codes for every error class, malformed bodies,
  strict typing, unknown fields, that validation errors don't echo input, and
  that internal errors return a generic 500.

### Known limitations

- **JSON numbers are decoded as floats.** FastAPI parses the request body with
  the standard `json` module, so numeric amounts pass through `float` before
  validation. This is exact for every valid amount (at most 7 significant
  digits). But a literal with more than ~15 significant digits, such as
  `2750.0000000000001`, collapses to `2750` and is accepted. Send `amount` as a
  string if such input must be rejected.
- **Responses use JSON numbers.** `fee`, `amount` and `total_repayable` are
  serialised as floats. They are exact to the penny for this range, but clients
  should not do further arithmetic on them as floats.
- **Lenient numeric strings.** Pydantic accepts amounts such as `" 2750 "`,
  `"2_750"` and non-ASCII digits as valid numbers.
- **No rate limiting or request-size limits.** Apply these at the reverse
  proxy or API gateway.

## Frontend

A small React + TypeScript (Vite) app with a form for loan amount and term that
calls the API and displays the fee and total repayable amount.

```powershell
cd frontend
npm install --legacy-peer-deps
npm run dev
```

The frontend expects the API at `http://localhost:8000` by default; override
with a `VITE_API_BASE_URL` environment variable (see `.env.example`).
