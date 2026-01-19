import "./ConfirmationModal.css";

interface ConfirmationModalProps {
	isOpen: boolean;
	title: string;
	message: string;
	confirmLabel?: string;
	cancelLabel?: string;
	confirmVariant?: "danger" | "primary";
	onConfirm: () => void;
	onCancel: () => void;
	loading?: boolean;
}

export default function ConfirmationModal({
	isOpen,
	title,
	message,
	confirmLabel = "Confirm",
	cancelLabel = "Cancel",
	confirmVariant = "primary",
	onConfirm,
	onCancel,
	loading = false,
}: ConfirmationModalProps) {
	if (!isOpen) return null;

	return (
		<div className="confirm-modal-overlay" onClick={onCancel}>
			<div
				className="confirm-modal-content"
				onClick={(e) => e.stopPropagation()}
			>
				<div className="confirm-modal-header">
					<h3>{title}</h3>
				</div>
				<div className="confirm-modal-body">
					<p>{message}</p>
				</div>
				<div className="confirm-modal-actions">
					<button
						type="button"
						className="confirm-cancel-btn"
						onClick={onCancel}
						disabled={loading}
					>
						{cancelLabel}
					</button>
					<button
						type="button"
						className={`confirm-action-btn ${confirmVariant}`}
						onClick={onConfirm}
						disabled={loading}
					>
						{loading ? "Processing..." : confirmLabel}
					</button>
				</div>
			</div>
		</div>
	);
}
