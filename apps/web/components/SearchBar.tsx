"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { StockSummary } from "@/lib/types";

export default function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSummary[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const timeout = setTimeout(() => {
      api
        .listStocks(query)
        .then(setResults)
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(timeout);
  }, [query]);

  function goToSymbol(symbol: string) {
    setOpen(false);
    setQuery("");
    router.push(`/stock/${symbol.toUpperCase()}`);
  }

  return (
    <div className="relative w-full max-w-sm">
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && query.trim()) goToSymbol(query.trim());
        }}
        placeholder="Tìm mã cổ phiếu (VD: FPT)"
        className="w-full rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:border-emerald-500 focus:outline-none"
      />
      {open && results.length > 0 && (
        <ul className="absolute z-10 mt-1 w-full rounded-md border border-neutral-700 bg-neutral-900 shadow-lg">
          {results.map((s) => (
            <li key={s.symbol}>
              <button
                onClick={() => goToSymbol(s.symbol)}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-neutral-800"
              >
                <span className="font-mono font-semibold text-neutral-100">{s.symbol}</span>
                <span className="truncate text-neutral-400">{s.company_name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
