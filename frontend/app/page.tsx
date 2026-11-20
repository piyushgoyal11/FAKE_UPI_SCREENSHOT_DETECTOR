"use client";

import { useState, type ChangeEvent, type DragEvent } from "react";

type PaymentDetails = {
  app?: string | null;
  amount?: string | null;
  transaction_id?: string | null;
  status?: string | null;
  date?: string | null;
  time?: string | null;
  recipient_name?: string | null;
  upi_id?: string | null;
  utr?: string | null;
  debited_account?: string | null;
  ocr_text?: string[];
};

type ReferenceResult = {
  app: string;
  reference: string;
  status: string;
  difference_score?: number;
  edge_difference_percent?: number;
  message?: string;
};

type ReferenceComparison = {
  status?: string;
  message?: string;
  best_reference?: ReferenceResult | null;
  comparisons?: ReferenceResult[];
};

type AnalysisResult = {
  status?: string;
  verdict?: string;
  payment?: PaymentDetails | null;
  reference_comparison?: ReferenceComparison | null;
  reasons?: string[];
  warnings?: string[];
  analysis?: string;
  message?: string;
};

const MAX_FILE_SIZE = 5 * 1024 * 1024;

function formatFileSize(bytes: number) {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function humanize(value?: string | null) {
  if (!value) return "Not detected";
  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatAmount(value?: string | null) {
  if (!value) return "Not detected";
  const amount = Number(value.replace(/,/g, ""));
  if (!Number.isFinite(amount)) return value;
  return `₹${amount.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function UploadIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-7 w-7"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
    >
      <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 15v4a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path d="M12 3 19 6v5c0 4.5-2.9 8-7 10-4.1-2-7-5.5-7-10V6l7-3Z" strokeLinejoin="round" />
      <path d="m9 12 2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DetailCard({
  label,
  value,
  prominent = false,
}: {
  label: string;
  value?: string | null;
  prominent?: boolean;
}) {
  return (
    <div className="min-w-0 rounded-2xl border border-slate-200/80 bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </p>
      <p className={`mt-2 break-words font-semibold text-slate-900 ${prominent ? "text-xl" : "text-sm"}`}>
        {value || "Not detected"}
      </p>
    </div>
  );
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");

  function selectFile(selected: File | null) {
    if (!selected) return;

    if (!["image/png", "image/jpeg"].includes(selected.type)) {
      setError("Choose a PNG or JPEG image to continue.");
      return;
    }

    if (selected.size > MAX_FILE_SIZE) {
      setError("This image is larger than 5 MB. Choose a smaller file.");
      return;
    }

    setFile(selected);
    setResult(null);
    setError("");
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0] ?? null);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files[0] ?? null);
  }

  async function analyzeScreenshot() {
    if (!file) {
      setError("Choose a payment screenshot first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      if (!response.ok) {
        const details = await response.text();
        throw new Error(`Analysis failed (${response.status}): ${details}`);
      }

      const data: AnalysisResult = await response.json();
      setResult(data);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setError("The review took too long. Please try again.");
      } else {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to connect to the analysis service."
        );
      }
    } finally {
      clearTimeout(timeout);
      setLoading(false);
    }
  }

  const suspicious = result?.verdict?.toUpperCase() === "SUSPICIOUS";
  const payment = result?.payment;
  const referenceComparison = result?.reference_comparison;

  return (
    <main className="min-h-screen bg-[#f5f7fb] text-slate-900">
      <div className="mx-auto max-w-7xl px-5 pb-12 pt-5 sm:px-8">
        <nav className="flex items-center justify-between border-b border-slate-200/80 pb-5">
          <a href="#" className="flex items-center gap-3" aria-label="UPI Shield home">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-700 text-white shadow-sm shadow-emerald-900/20">
              <ShieldIcon />
            </span>
            <span className="text-base font-bold tracking-tight text-slate-900">
              UPI Shield
              <span className="ml-1.5 font-medium text-slate-500">AI</span>
            </span>
          </a>
          <span className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-white px-3 py-1.5 text-xs font-semibold text-emerald-800 sm:flex">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            Screenshot analysis
          </span>
        </nav>

        <header className="grid gap-8 py-10 sm:py-14 lg:grid-cols-[1fr_0.72fr] lg:items-end">
          <div className="max-w-3xl">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-800">
              A clearer look at payment screenshots
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-5xl">
              Review a payment screenshot with confidence.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
              Extract visible payment details and look for inconsistencies.
              Always confirm that money arrived in your account separately.
            </p>
          </div>

          <div className="rounded-2xl border border-emerald-100 bg-emerald-50/80 p-5 sm:p-6">
            <div className="flex gap-3">
              <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-emerald-800 shadow-sm">
                <ShieldIcon />
              </span>
              <div>
                <h2 className="font-semibold text-slate-900">Your screenshot, your review</h2>
                <p className="mt-1.5 text-sm leading-6 text-slate-600">
                  The analysis reads the image you submit. It cannot verify a
                  bank transfer or replace checking your account.
                </p>
              </div>
            </div>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_12px_40px_-24px_rgba(15,23,42,0.22)] sm:p-8">
            <div className="mb-6">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                Get started
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                Upload a payment screenshot
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                PNG or JPEG · Maximum file size 5 MB
              </p>
            </div>

            <label
              htmlFor="payment-screenshot"
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              className={`group flex min-h-52 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-5 py-8 text-center transition ${
                dragging
                  ? "border-emerald-600 bg-emerald-50"
                  : "border-slate-300 bg-slate-50/70 hover:border-emerald-500 hover:bg-emerald-50/60"
              }`}
            >
              <input
                id="payment-screenshot"
                type="file"
                accept="image/png,image/jpeg"
                onChange={handleFileChange}
                className="sr-only"
              />
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-emerald-800 shadow-sm ring-1 ring-slate-200 transition group-hover:-translate-y-0.5">
                <UploadIcon />
              </span>
              <span className="mt-4 font-semibold text-slate-900">
                Drop your screenshot here
              </span>
              <span className="mt-1 text-sm text-slate-500">
                or <span className="font-semibold text-emerald-800">browse files</span>
              </span>
            </label>

            {file && (
              <div className="mt-4 flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-xs font-bold text-slate-600">
                    IMG
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-900">{file.name}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{formatFileSize(file.size)}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setFile(null);
                    setResult(null);
                    setError("");
                  }}
                  className="rounded-lg px-2 py-1 text-sm font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
                >
                  Remove
                </button>
              </div>
            )}

            {error && (
              <p role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                {error}
              </p>
            )}

            <button
              type="button"
              onClick={analyzeScreenshot}
              disabled={!file || loading}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-800 px-5 py-3.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500 disabled:shadow-none"
            >
              {loading && (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
              )}
              {loading ? "Reviewing screenshot..." : "Review screenshot"}
            </button>

            {loading && (
              <p className="mt-3 text-center text-sm text-slate-500" role="status">
                This can take a little while. Please keep this page open.
              </p>
            )}
          </section>

          <aside className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-6">
            <h2 className="text-lg font-semibold tracking-tight text-slate-950">
              What we look at
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              A quick overview of what this experimental tool can review.
            </p>
            <ol className="mt-6 space-y-5">
              <li className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-sm font-bold text-emerald-800">1</span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Payment details</p>
                  <p className="mt-1 text-sm leading-5 text-slate-500">Visible amount, recipient, reference, and date.</p>
                </div>
              </li>
              <li className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-sm font-bold text-emerald-800">2</span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Image signals</p>
                  <p className="mt-1 text-sm leading-5 text-slate-500">Basic visual checks and experimental AI signals.</p>
                </div>
              </li>
              <li className="flex gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-sm font-bold text-emerald-800">3</span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Clear report</p>
                  <p className="mt-1 text-sm leading-5 text-slate-500">Findings and items that may need a closer look.</p>
                </div>
              </li>
            </ol>
            <div className="mt-6 border-t border-slate-100 pt-5 text-xs leading-5 text-slate-500">
              This tool does not contact banks or verify transactions.
            </div>
          </aside>
        </div>

        {result && (
          <section aria-live="polite" className="mt-8 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_12px_40px_-24px_rgba(15,23,42,0.22)]">
            <div className="flex flex-col gap-5 border-b border-slate-200 px-5 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-8">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Analysis report
                </p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                  Screenshot review complete
                </h2>
                <p className="mt-1 text-sm text-slate-600">
                  {result.message || "Review the extracted details below."}
                </p>
              </div>
              <span className={`inline-flex w-fit items-center gap-2 rounded-full px-3.5 py-2 text-sm font-semibold ${
                suspicious
                  ? "bg-amber-50 text-amber-800 ring-1 ring-amber-200"
                  : "bg-slate-100 text-slate-700 ring-1 ring-slate-200"
              }`}>
                <span className={`h-2 w-2 rounded-full ${suspicious ? "bg-amber-500" : "bg-slate-500"}`} />
                {suspicious ? "Needs a closer look" : "Not verified"}
              </span>
            </div>

            <div className="px-5 py-6 sm:px-8">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <DetailCard label="Payment app" value={payment?.app} />
                <DetailCard label="Amount" value={formatAmount(payment?.amount)} prominent />
                <DetailCard label="Payment status" value={humanize(payment?.status)} />
                <DetailCard label="Recipient" value={payment?.recipient_name} />
                <DetailCard label="UPI ID" value={payment?.upi_id} />
                <DetailCard label="Transaction ID" value={payment?.transaction_id} />
                <DetailCard label="UTR" value={payment?.utr} />
                <DetailCard label="Date and time" value={[payment?.date, payment?.time].filter(Boolean).join(" · ")} />
                <DetailCard label="Paid from" value={payment?.debited_account} />
              </div>

              {referenceComparison && (
                <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h3 className="font-semibold text-slate-900">
                        Reference screenshot comparison
                      </h3>
                      <p className="mt-1 text-sm leading-6 text-slate-600">
                        {referenceComparison.message || "Visual differences are listed below."}
                        {" "}A closest visual reference is not proof that a payment screenshot is genuine.
                      </p>
                    </div>
                    {referenceComparison.best_reference && (
                      <span className="w-fit rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                        Closest: {referenceComparison.best_reference.app}
                      </span>
                    )}
                  </div>
                  {Boolean(referenceComparison.comparisons?.length) && (
                    <div className="mt-4 overflow-x-auto">
                      <table className="w-full min-w-[560px] border-collapse text-left text-sm">
                        <thead>
                          <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                            <th className="py-2 pr-4 font-semibold">App</th>
                            <th className="py-2 pr-4 font-semibold">Reference</th>
                            <th className="py-2 pr-4 font-semibold">Visual difference</th>
                            <th className="py-2 font-semibold">Edge difference</th>
                          </tr>
                        </thead>
                        <tbody>
                          {referenceComparison.comparisons?.map((comparison, index) => (
                            <tr key={`${comparison.app}-${comparison.reference}-${index}`} className="border-b border-slate-200/70 last:border-0">
                              <td className="py-3 pr-4 font-medium text-slate-800">{comparison.app}</td>
                              <td className="py-3 pr-4 text-slate-600">{comparison.reference}</td>
                              <td className="py-3 pr-4 text-slate-600">{comparison.difference_score ?? comparison.message ?? "Unavailable"}</td>
                              <td className="py-3 text-slate-600">{comparison.edge_difference_percent !== undefined ? `${comparison.edge_difference_percent}%` : "Unavailable"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {((result.reasons?.length ?? 0) > 0 || (result.warnings?.length ?? 0) > 0) && (
                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  {Boolean(result.reasons?.length) && (
                    <div className="rounded-2xl border border-rose-200 bg-rose-50/70 p-5">
                      <h3 className="font-semibold text-rose-900">Items to review</h3>
                      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-rose-800">
                        {result.reasons?.map((reason, index) => <li key={`${reason}-${index}`}>{reason}</li>)}
                      </ul>
                    </div>
                  )}
                  {Boolean(result.warnings?.length) && (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-5">
                      <h3 className="font-semibold text-amber-900">Notes</h3>
                      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-amber-900">
                        {result.warnings?.map((warning, index) => <li key={`${warning}-${index}`}>{warning}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {Boolean(payment?.ocr_text?.length) && (
                <details className="mt-6 rounded-2xl border border-slate-200 bg-white">
                  <summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-slate-700">
                    View all text read from the screenshot ({payment?.ocr_text?.length} lines)
                  </summary>
                  <ol className="max-h-96 list-decimal space-y-1 overflow-auto border-t border-slate-200 px-10 py-4 text-sm leading-6 text-slate-700">
                    {payment?.ocr_text?.map((line, index) => (
                      <li key={`${index}-${line}`} className="break-words pl-1">{line}</li>
                    ))}
                  </ol>
                </details>
              )}

              {result.analysis && (
                <details className="mt-6 rounded-2xl border border-slate-200 bg-slate-50">
                  <summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-slate-700">
                    View technical analysis
                  </summary>
                  <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words border-t border-slate-200 px-5 py-4 font-mono text-xs leading-5 text-slate-600">
                    {result.analysis}
                  </pre>
                </details>
              )}
            </div>
            <div className="border-t border-slate-200 bg-slate-50 px-5 py-4 text-sm leading-6 text-slate-600 sm:px-8">
              A screenshot cannot confirm that funds were received. Verify the
              transaction in your bank or UPI app.
            </div>
          </section>
        )}

        <footer className="mt-10 border-t border-slate-200 pt-6 text-center text-xs leading-5 text-slate-500">
          UPI Shield AI is an experimental tool. Use your bank or UPI app as the source of truth.
        </footer>
      </div>
    </main>
  );
}
