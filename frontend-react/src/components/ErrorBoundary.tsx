import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
	children: ReactNode;
	fallback?: ReactNode;
}

interface State {
	hasError: boolean;
	error: Error | null;
	errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary component to catch and display React component errors
 * Prevents the entire app from crashing when a component throws an error
 */
export class ErrorBoundary extends Component<Props, State> {
	constructor(props: Props) {
		super(props);
		this.state = {
			hasError: false,
			error: null,
			errorInfo: null,
		};
	}

	static getDerivedStateFromError(error: Error): State {
		// Update state so the next render will show the fallback UI
		return {
			hasError: true,
			error,
			errorInfo: null,
		};
	}

	componentDidCatch(error: Error, errorInfo: ErrorInfo) {
		// Log error to console for debugging
		console.error("ErrorBoundary caught an error:", error, errorInfo);
		this.setState({
			error,
			errorInfo,
		});

		// You can also log the error to an error reporting service here
		// Example: logErrorToService(error, errorInfo);
	}

	handleReset = () => {
		this.setState({
			hasError: false,
			error: null,
			errorInfo: null,
		});
	};

	render() {
		if (this.state.hasError) {
			// Custom fallback UI
			if (this.props.fallback) {
				return this.props.fallback;
			}

			// Default error UI
			return (
				<div
					style={{
						display: "flex",
						flexDirection: "column",
						justifyContent: "center",
						alignItems: "center",
						minHeight: "100vh",
						padding: "20px",
						textAlign: "center",
						background: "#f4f7f1",
					}}
				>
					<div
						style={{
							background: "white",
							padding: "40px",
							borderRadius: "16px",
							boxShadow: "0 4px 20px rgba(0, 0, 0, 0.08)",
							maxWidth: "600px",
							width: "100%",
						}}
					>
						<h1 style={{ color: "#3a4f2a", marginBottom: "20px" }}>
							Something went wrong
						</h1>
						<p style={{ color: "#666", marginBottom: "30px" }}>
							We're sorry, but something unexpected happened. Please try
							refreshing the page or contact support if the problem persists.
						</p>

						{import.meta.env.DEV && this.state.error && (
							<details
								style={{
									background: "#f9f9f9",
									padding: "20px",
									borderRadius: "8px",
									marginBottom: "20px",
									textAlign: "left",
									fontSize: "12px",
									fontFamily: "monospace",
									overflow: "auto",
									maxHeight: "300px",
								}}
							>
								<summary style={{ cursor: "pointer", marginBottom: "10px" }}>
									Error Details (Development Only)
								</summary>
								<div style={{ color: "#c33" }}>
									<strong>Error:</strong> {this.state.error.toString()}
								</div>
								{this.state.errorInfo && (
									<div style={{ marginTop: "10px", color: "#666" }}>
										<strong>Component Stack:</strong>
										<pre style={{ whiteSpace: "pre-wrap", marginTop: "5px" }}>
											{this.state.errorInfo.componentStack}
										</pre>
									</div>
								)}
							</details>
						)}

						<div
							style={{ display: "flex", gap: "15px", justifyContent: "center" }}
						>
							<button
								onClick={this.handleReset}
								style={{
									background: "#6a9d3a",
									color: "white",
									border: "none",
									padding: "12px 24px",
									borderRadius: "8px",
									fontSize: "16px",
									fontWeight: "600",
									cursor: "pointer",
									transition: "background 0.2s",
								}}
								onMouseOver={(e) => {
									e.currentTarget.style.background = "#5a8a2f";
								}}
								onMouseOut={(e) => {
									e.currentTarget.style.background = "#6a9d3a";
								}}
							>
								Try Again
							</button>
							<button
								onClick={() => window.location.reload()}
								style={{
									background: "transparent",
									color: "#6a9d3a",
									border: "2px solid #6a9d3a",
									padding: "12px 24px",
									borderRadius: "8px",
									fontSize: "16px",
									fontWeight: "600",
									cursor: "pointer",
									transition: "all 0.2s",
								}}
								onMouseOver={(e) => {
									e.currentTarget.style.background = "#f0f5eb";
								}}
								onMouseOut={(e) => {
									e.currentTarget.style.background = "transparent";
								}}
							>
								Reload Page
							</button>
						</div>
					</div>
				</div>
			);
		}

		return this.props.children;
	}
}
