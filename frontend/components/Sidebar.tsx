"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ReceiptText,
  BookMarked,
  FlaskConical,
  Landmark,
  Wallet,
  ArrowLeftRight,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Transakcje", icon: ArrowLeftRight },
  { href: "/receipts", label: "Paragony", icon: ReceiptText },
  { href: "/bank-transactions", label: "Transakcje bankowe", icon: Landmark },
  { href: "/cash-transactions", label: "Transakcje gotówkowe", icon: Wallet },
];

const adminItems = [
  { href: "/ground-truth", label: "Dane wzorcowe", icon: BookMarked },
  { href: "/evaluations", label: "Ewaluacje", icon: FlaskConical },
];

export function Sidebar() {
  const pathname = usePathname();

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
    </aside>
  );
}
