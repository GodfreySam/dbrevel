import { useState } from "react";
import { config } from "../../config";
import "./ApiDocs.css";
import Header from "../../components/Header";

type ViewerType = "redoc" | "swagger";

export default function ApiDocs() {
	const [viewer, setViewer] = useState<ViewerType>("swagger");
	const [loading, setLoading] = useState(true);

	// Get the backend base URL
	const backendBaseUrl = config.baseUrl;
	const redocUrl = `${backendBaseUrl}/redoc`;
	const swaggerUrl = `${backendBaseUrl}/docs`;

	const handleViewerChange = (newViewer: ViewerType) => {
		setViewer(newViewer);
		setLoading(true);
	};

	const handleIframeLoad = () => {
		setLoading(false);
	};

	const handleIframeError = () => {
		setLoading(false);
	};

	return (
		<div className="app-wrapper">
			{/* Header with Logo */}
			<Header />

			{/* API Documentation Page */}
			<div className="api-docs-page">
				<div className="api-docs-header">
					<div className="container">
						<h1>API Documentation</h1>
						<p className="api-docs-subtitle">
							Explore the DbRevel API with interactive documentation. Switch
							between ReDoc and Swagger UI views.
						</p>

						{/* Developer & License Links */}
						<div className="docs-links">
							<a
								href="https://github.com/GodfreySam"
								target="_blank"
								rel="noopener noreferrer"
								className="docs-link"
							>
								<svg
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									strokeWidth="2"
									strokeLinecap="round"
									strokeLinejoin="round"
								>
									<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
									<path d="M9 18c-4.51 2-5-2-7-2" />
								</svg>
								Meet the Developer
							</a>
							<a
								href="https://opensource.org/licenses/MIT"
								target="_blank"
								rel="noopener noreferrer"
								className="docs-link"
							>
								<svg
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									strokeWidth="2"
									strokeLinecap="round"
									strokeLinejoin="round"
								>
									<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
								</svg>
								MIT License
							</a>
						</div>

						{/* Viewer Toggle */}
						<div className="viewer-toggle">
							<button
								type="button"
								className={`toggle-btn ${viewer === "swagger" ? "active" : ""}`}
								onClick={() => handleViewerChange("swagger")}
								aria-pressed={viewer === "swagger"}
							>
								<svg
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									strokeWidth="2"
									strokeLinecap="round"
									strokeLinejoin="round"
								>
									<rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
									<path d="M3 9h18M9 21V9" />
								</svg>
								Swagger UI
							</button>
							<button
								type="button"
								className={`toggle-btn ${viewer === "redoc" ? "active" : ""}`}
								onClick={() => handleViewerChange("redoc")}
								aria-pressed={viewer === "redoc"}
							>
								<svg
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									strokeWidth="2"
									strokeLinecap="round"
									strokeLinejoin="round"
								>
									<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
								</svg>
								ReDoc
							</button>
						</div>
					</div>
				</div>

				{/* Viewer Container */}
				<div className="viewer-container">
					{loading && (
						<div className="viewer-loading">
							<div className="loading-spinner"></div>
							<p>Loading documentation...</p>
						</div>
					)}

					{/* ReDoc Viewer */}
					{viewer === "redoc" && (
						<iframe
							src={redocUrl}
							title="ReDoc API Documentation"
							className="docs-iframe"
							onLoad={handleIframeLoad}
							onError={handleIframeError}
							style={{ display: loading ? "none" : "block" }}
						/>
					)}

					{/* Swagger UI Viewer */}
					{viewer === "swagger" && (
						<iframe
							src={swaggerUrl}
							title="Swagger UI API Documentation"
							className="docs-iframe"
							onLoad={handleIframeLoad}
							onError={handleIframeError}
							style={{ display: loading ? "none" : "block" }}
						/>
					)}
				</div>
			</div>
		</div>
	);
}
