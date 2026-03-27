import { ReceiptText, Landmark, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type SourceType = "bank" | "cash" | "receipt";

export const SOURCE_CONFIG: Record<SourceType, { icon: LucideIcon; style: string; label: string }> = {
  bank:    { icon: Landmark,    style: "bg-blue-50 text-blue-700",   label: "Bank"     },
  cash:    { icon: Wallet,      style: "bg-green-50 text-green-700", label: "Gotówka"  },
  receipt: { icon: ReceiptText, style: "bg-purple-50 text-purple-700", label: "Paragon" },
};

export const SOURCE_FALLBACK = { style: "bg-gray-100 text-gray-500", label: "" };
