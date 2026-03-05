import React from "react";
import { Modal } from "./Modal";
import { Button } from "./Button";

interface ConfirmDeleteModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description?: string;
  loading?: boolean;
}

export function ConfirmDeleteModal({
  open,
  onClose,
  onConfirm,
  title,
  description,
  loading = false,
}: ConfirmDeleteModalProps) {
  return (
    <Modal open={open} onClose={onClose} maxWidth="sm">
      <div className="p-5 space-y-3">
        <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
        {description && (
          <p className="text-xs text-gray-600">{description}</p>
        )}
        <p className="text-xs text-gray-500">
          Tej operacji nie można cofnąć.
        </p>
        <div className="flex gap-2 justify-end pt-1">
          <Button variant="secondary" size="sm" onClick={onClose} disabled={loading}>
            Anuluj
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? "Usuwanie…" : "Usuń"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
