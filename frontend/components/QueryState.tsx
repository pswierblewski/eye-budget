"use client";

import type { ReactNode } from "react";
import type { UseMutationResult, UseQueryResult } from "@tanstack/react-query";
import { clsx } from "clsx";
import { Button } from "@/components/ui/Button";
import { formatQueryError } from "@/lib/query-error";

export type QueryStateVariant = "panel" | "inline";

type ErrorCalloutProps = {
  title: string;
  message: string;
  onRetry?: () => void;
  variant: QueryStateVariant;
  className?: string;
};

export function QueryErrorCallout({
  title,
  message,
  onRetry,
  variant,
  className,
}: ErrorCalloutProps) {
  const isPanel = variant === "panel";
  return (
    <div
      className={clsx(
        isPanel
          ? "rounded-lg border border-red-200 bg-red-50/90 p-4 text-sm text-red-900"
          : "text-xs text-red-800",
        className
      )}
      role="alert"
    >
      <p className={clsx(isPanel && "font-medium")}>{title}</p>
      <p
        className={clsx(
          "mt-1 break-words",
          isPanel ? "text-red-800/95" : "text-red-700"
        )}
      >
        {message}
      </p>
      {onRetry && (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className={clsx("mt-3", !isPanel && "mt-2")}
          onClick={onRetry}
        >
          Spróbuj ponownie
        </Button>
      )}
    </div>
  );
}

/**
 * Obsługa stanu useQuery: błąd (priorytet), pierwsze ładowanie, brak danych przy `enabled: false`, sukces.
 * Przy `placeholderData` — jeśli refetch zakończy się błędem, wyświetlany jest komunikat błędu.
 */
export function QueryState<TData>({
  query,
  children,
  loadingFallback,
  idleFallback = null,
  errorVariant = "panel",
  errorTitle = "Nie udało się pobrać danych.",
  className,
}: {
  query: UseQueryResult<TData, Error>;
  children: (data: TData) => ReactNode;
  loadingFallback?: ReactNode;
  idleFallback?: ReactNode;
  errorVariant?: QueryStateVariant;
  errorTitle?: string;
  className?: string;
}) {
  if (query.isError) {
    return (
      <QueryErrorCallout
        variant={errorVariant}
        title={errorTitle}
        message={formatQueryError(query.error)}
        onRetry={() => void query.refetch()}
        className={className}
      />
    );
  }
  if (query.data === undefined && query.isFetching) {
    return (
      <>
        {loadingFallback ?? (
          <div className="text-sm text-gray-400">Ładowanie…</div>
        )}
      </>
    );
  }
  if (query.data === undefined) {
    return <>{idleFallback}</>;
  }
  return <>{children(query.data)}</>;
}

/** Tylko komunikat błędu (np. nad listą w panelu); bez sukcesu / ładowania. */
export function QueryErrorNotice({
  query,
  errorTitle = "Nie udało się pobrać danych.",
  className,
}: {
  query: UseQueryResult<unknown, Error>;
  errorTitle?: string;
  className?: string;
}) {
  if (!query.isError) return null;
  return (
    <QueryErrorCallout
      variant="inline"
      title={errorTitle}
      message={formatQueryError(query.error)}
      onRetry={() => void query.refetch()}
      className={className}
    />
  );
}

type MutationPick = Pick<
  UseMutationResult<unknown, Error, unknown>,
  "isError" | "error" | "reset"
>;

export function MutationErrorNotice({
  mutation,
  title = "Operacja nie powiodła się.",
  className,
}: {
  mutation: MutationPick;
  title?: string;
  className?: string;
}) {
  if (!mutation.isError || !mutation.error) return null;
  return (
    <div
      role="alert"
      className={clsx(
        "rounded-md border border-red-200 bg-red-50/90 p-3 text-xs text-red-900",
        className
      )}
    >
      <p className="font-medium">{title}</p>
      <p className="mt-1 break-words text-red-800">
        {formatQueryError(mutation.error)}
      </p>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="mt-2 text-gray-600"
        onClick={() => mutation.reset()}
      >
        Ukryj komunikat
      </Button>
    </div>
  );
}
