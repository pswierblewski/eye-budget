"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Input, Button, DateInput } from "@/components/ui";
import { createBudgetSimulation } from "@/lib/api";
import clsx from "clsx";

interface Props {
  onSuccess?: () => void;
}

export function SimulationForm({ onSuccess }: Props) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [expenseName, setExpenseName] = useState("");
  const [amount, setAmount] = useState("");
  const [expenseType, setExpenseType] = useState<"one_time" | "recurring">("one_time");
  const [startDate, setStartDate] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      createBudgetSimulation({
        name,
        expense_name: expenseName,
        expense_amount_pln: parseFloat(amount),
        expense_type: expenseType,
        expense_start_date: startDate,
      }),
    onSuccess: (data) => {
      onSuccess?.();
      router.push(`/budget/simulations/${data.simulation_id}`);
    },
  });

  const canSubmit =
    name.trim() !== "" &&
    expenseName.trim() !== "" &&
    !isNaN(parseFloat(amount)) &&
    parseFloat(amount) > 0 &&
    startDate !== "";

  return (
    <div className="space-y-4 p-1">
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Nazwa symulacji</label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="np. Zakup samochodu"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Nazwa wydatku</label>
        <Input
          value={expenseName}
          onChange={(e) => setExpenseName(e.target.value)}
          placeholder="np. Nowy samochód"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Kwota (PLN)</label>
        <Input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="20000"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-2">Typ wydatku</label>
        <div className="flex gap-2">
          {(["one_time", "recurring"] as const).map((type) => (
            <button
              key={type}
              onClick={() => setExpenseType(type)}
              className={clsx(
                "flex-1 py-2 px-3 rounded-md text-sm font-medium border transition-colors",
                expenseType === type
                  ? "border-[#635bff] bg-[#635bff]/10 text-[#635bff]"
                  : "border-gray-200 text-gray-600 hover:border-gray-300"
              )}
            >
              {type === "one_time" ? "Jednorazowy" : "Cykliczny"}
            </button>
          ))}
        </div>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Data rozpoczęcia</label>
        <DateInput value={startDate} onChange={setStartDate} />
      </div>
      {mutation.isError && (
        <p className="text-red-500 text-sm">Błąd: {(mutation.error as Error).message}</p>
      )}
      <Button
        onClick={() => mutation.mutate()}
        disabled={!canSubmit || mutation.isPending}
        className="w-full"
      >
        {mutation.isPending ? "Tworzę symulację…" : "Uruchom symulację"}
      </Button>
    </div>
  );
}
