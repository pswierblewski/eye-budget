"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ReceiptText,
  BookMarked,
  FlaskConical,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/receipts", label: "Receipts", icon: ReceiptText },
  { href: "/ground-truth", label: "Ground Truth", icon: BookMarked },
  { href: "/evaluations", label: "Evaluations", icon: FlaskConical },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 w-56 flex flex-col border-r border-gray-200 bg-[#f6f9fc]">
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
      </nav>
    </aside>
  );
}
