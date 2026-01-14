import { useEffect, useState } from "react";
import "./Toast.css";

interface ToastProps {
	message: string;
	type?: "success" | "error" | "info";
	duration?: number;
	onClose: () => void;
}

export default function Toast({
	message,
	type = "success",
	duration = 3000,
	onClose,
}: ToastProps) {
	const [isVisible, setIsVisible] = useState(true);

	useEffect(() => {
		const timer = setTimeout(() => {
			setIsVisible(false);
			setTimeout(onClose, 300); // Wait for fade out animation
		}, duration);

		return () => clearTimeout(timer);
	}, [duration, onClose]);

	return (
		<div className={`toast toast-${type} ${isVisible ? "toast-visible" : "toast-hidden"}`}>
			<div className="toast-content">
				<span className="toast-icon">
					{type === "success" && "✓"}
					{type === "error" && "✗"}
					{type === "info" && "ℹ"}
				</span>
				<span className="toast-message">{message}</span>
			</div>
		</div>
	);
}
