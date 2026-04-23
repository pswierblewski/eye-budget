"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getVersionInfo } from "@/lib/api";
import { QueryState } from "@/components/QueryState";
import {
  ReceiptText,
  BookMarked,
  FlaskConical,
  Landmark,
  Wallet,
  ArrowLeftRight,
  ChartBar,
  PiggyBank,
  Target,
  Sliders,
  Sparkles,
  Link2,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Transakcje", icon: ArrowLeftRight },
  { href: "/receipts", label: "Paragony", icon: ReceiptText },
  { href: "/bank-transactions", label: "Transakcje bankowe", icon: Landmark },
  { href: "/cash-transactions", label: "Transakcje gotówkowe", icon: Wallet },
  { href: "/settlement-groups", label: "Powiązane operacje", icon: Link2 },
  { href: "/budget", label: "Budżet", icon: PiggyBank },
];

const budgetSubItems = [
  { href: "/budget/goals", label: "Cele finansowe", icon: Target },
  { href: "/budget/simulations", label: "Symulacje", icon: Sliders },
  { href: "/budget/ai-insights", label: "Rekomendacje AI", icon: Sparkles },
];

const adminItems = [
  { href: "/ground-truth", label: "Dane wzorcowe", icon: BookMarked },
  { href: "/evaluations", label: "Ewaluacje", icon: FlaskConical },
  { href: "/analytics", label: "Analityka promptów", icon: ChartBar },
];

export function Sidebar() {
  const pathname = usePathname();
  const versionQuery = useQuery({
    queryKey: ["version"],
    queryFn: getVersionInfo,
    staleTime: Infinity,
    gcTime: Infinity,
    retry: 1,
  });

  return (
    <aside className="fixed inset-y-0 left-0 w-64 flex flex-col border-r border-gray-200 bg-[#f6f9fc]">
      <div className="flex items-center gap-2 px-6 h-16 border-b border-gray-200">
        <span className="text-[#635bff] font-bold text-lg tracking-tight">
          eye-budget
        </span>
      </div>
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-3">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            const isBudget = href === "/budget";
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    active
                      ? "bg-[#635bff] text-white"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {label}
                </Link>
                {isBudget && active && (
                  <ul className="mt-1 ml-4 space-y-1">
                    {budgetSubItems.map(({ href: subHref, label: subLabel, icon: SubIcon }) => {
                      const subActive = pathname.startsWith(subHref);
                      return (
                        <li key={subHref}>
                          <Link
                            href={subHref}
                            className={`flex items-center gap-3 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                              subActive
                                ? "bg-[#635bff]/20 text-[#635bff]"
                                : "text-gray-500 hover:bg-gray-100"
                            }`}
                          >
                            <SubIcon className="h-3.5 w-3.5 shrink-0" />
                            {subLabel}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
        <div className="mx-3 my-3 border-t border-gray-200" />
        <p className="px-6 mb-1 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
          Narzędzia
        </p>
        <ul className="space-y-1 px-3">
          {adminItems.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    active
                      ? "bg-[#635bff] text-white"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <footer className="px-6 py-3 border-t border-gray-200 space-y-2">
        <p className="text-[10px] text-gray-400">
          Frontend: v{process.env.NEXT_PUBLIC_FRONTEND_VERSION ?? "?"}
        </p>
        <div className="text-[10px] text-gray-400">
          Backend:{" "}
          <QueryState
            query={versionQuery}
            errorVariant="inline"
            errorTitle="Nie udało się pobrać wersji backendu."
            loadingFallback={<span>ładowanie…</span>}
          >
            {(v) => <span>v{v.version}</span>}
          </QueryState>
        </div>
      </footer>
    </aside>
  );
}
