import { useState, type FormEvent } from "react";
import { ApiError, calculateFee, type FeeResponse } from "../api/feeClient";

const TERMS = [12, 24] as const;
const MIN_AMOUNT = 1000;
const MAX_AMOUNT = 20000;

const currency = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "GBP",
});

export function FeeCalculatorForm() {
  const [amount, setAmount] = useState("2750");
  const [term, setTerm] = useState<number>(24);
  const [result, setResult] = useState<FeeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setResult(null);

    const parsedAmount = Number(amount);
    if (Number.isNaN(parsedAmount)) {
      setError("Please enter a valid loan amount.");
      return;
    }
    if (parsedAmount < MIN_AMOUNT || parsedAmount > MAX_AMOUNT) {
      setError(
        `Loan amount must be between ${currency.format(MIN_AMOUNT)} and ${currency.format(MAX_AMOUNT)}.`,
      );
      return;
    }

    setIsLoading(true);
    try {
      const response = await calculateFee({ amount: parsedAmount, term });
      setResult(response);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fee-calculator">
      <h1>Loan Fee Calculator</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="amount">
          Loan amount (£{MIN_AMOUNT} - £{MAX_AMOUNT})
        </label>
        <input
          id="amount"
          name="amount"
          type="number"
          min={MIN_AMOUNT}
          max={MAX_AMOUNT}
          step="0.01"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          required
        />

        <label htmlFor="term">Term (months)</label>
        <select
          id="term"
          name="term"
          value={term}
          onChange={(event) => setTerm(Number(event.target.value))}
        >
          {TERMS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        <button type="submit" disabled={isLoading}>
          {isLoading ? "Calculating..." : "Calculate fee"}
        </button>
      </form>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {result && (
        <dl className="result">
          <div>
            <dt>Fee</dt>
            <dd>{currency.format(result.fee)}</dd>
          </div>
          <div>
            <dt>Total repayable</dt>
            <dd>{currency.format(result.total_repayable)}</dd>
          </div>
        </dl>
      )}
    </div>
  );
}
