import "./ErrorBanner.css";

interface Props {
	message: string | null;
	onClose?: () => void;
}

export default function ErrorBanner({ message, onClose }: Props) {
	if (!message) return null;
	return (
		<div className="error-banner" role="alert">
			<div className="error-banner-message">{message}</div>
			{onClose && (
				<button
					className="error-banner-close"
					onClick={onClose}
					aria-label="Close"
				>
					×
				</button>
			)}
		</div>
	);
}
