import { useEffect, useState } from "react";
import { config } from "../../config";
import { parseApiError } from "../../utils/handleApiError";
import ErrorBanner from "../ErrorBanner/ErrorBanner";
import "./ProjectModal.css";

interface Project {
	id: string;
	name: string;
	api_key: string;
	api_key_masked: string;
	postgres_url: string;
	mongodb_url: string;
	created_at: string;
	updated_at: string;
	is_active: boolean;
}

interface ProjectModalProps {
	isOpen: boolean;
	onClose: () => void;
	onSuccess: (createdProject?: any) => void;
	project?: Project | null;
	token: string;
	logout: () => void;
}

export default function ProjectModal({
	isOpen,
	onClose,
	onSuccess,
	project,
	token,
	logout,
}: ProjectModalProps) {
	const [name, setName] = useState("");
	const [postgresUrl, setPostgresUrl] = useState("");
	const [mongodbUrl, setMongodbUrl] = useState("");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [testingConnection, setTestingConnection] = useState(false);
	const [connectionResults, setConnectionResults] = useState<{
		postgres?: { success: boolean; error?: string };
		mongodb?: { success: boolean; error?: string };
	}>({});

	const isEditMode = !!project;

	useEffect(() => {
		if (project) {
			setName(project.name);
			// Don't populate URLs in edit mode since they're encrypted
			setPostgresUrl("");
			setMongodbUrl("");
		} else {
			setName("");
			setPostgresUrl("");
			setMongodbUrl("");
		}
		setError(null);
		setConnectionResults({});
	}, [project, isOpen]);

	const handleTestConnection = async () => {
		if (!postgresUrl && !mongodbUrl) {
			setError("Please provide at least one database URL");
			return;
		}

		setTestingConnection(true);
		setError(null);
		setConnectionResults({});

		try {
			const response = await fetch(
				`${config.apiUrl}/projects/test-connection`,
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						Authorization: `Bearer ${token}`,
					},
					body: JSON.stringify({
						postgres_url: postgresUrl || null,
						mongodb_url: mongodbUrl || null,
					}),
				},
			);

			if (!response.ok) {
				if (response.status === 401) {
					logout();
					return;
				}
				const msg = await parseApiError(response);
				throw new Error(msg || "Connection test failed");
			}

			const data = await response.json();
			setConnectionResults(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Connection test failed");
		} finally {
			setTestingConnection(false);
		}
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setLoading(true);

		try {
			const url = isEditMode
				? `${config.apiUrl}/projects/${project.id}`
				: `${config.apiUrl}/projects`;

			const method = isEditMode ? "PATCH" : "POST";

			const body: any = { name };

			// Only include URLs if they're provided (not empty)
			if (postgresUrl) body.postgres_url = postgresUrl;
			if (mongodbUrl) body.mongodb_url = mongodbUrl;

			const response = await fetch(url, {
				method,
				headers: {
					"Content-Type": "application/json",
					Authorization: `Bearer ${token}`,
				},
				body: JSON.stringify(body),
			});

			if (!response.ok) {
				if (response.status === 401) {
					logout();
					return;
				}
				const msg = await parseApiError(response);
				throw new Error(
					msg || `Failed to ${isEditMode ? "update" : "create"} project`,
				);
			}

			const data = await response.json();

			// If creating a new project, capture and store the API key
			if (!isEditMode && data.api_key) {
				// Store API key in localStorage
				const storedKeys = localStorage.getItem("project_api_keys");
				let keysMap = new Map<string, string>();
				if (storedKeys) {
					try {
						keysMap = new Map(JSON.parse(storedKeys));
					} catch (e) {
						console.warn("Failed to parse stored API keys:", e);
					}
				}
				keysMap.set(data.id, data.api_key);
				localStorage.setItem(
					"project_api_keys",
					JSON.stringify(Array.from(keysMap.entries())),
				);
			} else if (isEditMode) {
				// If updating, invalidate the API key cache since we don't get it back on update
				// The user will need to reveal it again if they want to see it
				const storedKeys = localStorage.getItem("project_api_keys");
				if (storedKeys) {
					try {
						// Validate stored keys JSON without creating an unused Map
						JSON.parse(storedKeys);
						// Note: we intentionally do not remove or mutate the cached keys here
					} catch (e) {
						console.warn("Failed to parse stored API keys:", e);
					}
				}
			}

			// Pass the created/updated project data to onSuccess callback
			onSuccess(data);
			onClose();
		} catch (err) {
			setError(
				err instanceof Error
					? err.message
					: `Failed to ${isEditMode ? "update" : "create"} project`,
			);
		} finally {
			setLoading(false);
		}
	};

	if (!isOpen) return null;

	return (
		<div className="modal-overlay" onClick={onClose}>
			<div className="modal-content" onClick={(e) => e.stopPropagation()}>
				<div className="modal-header">
					<h2>{isEditMode ? "Edit Project" : "Create New Project"}</h2>
					<button className="modal-close-btn" onClick={onClose}>
						×
					</button>
				</div>

				<form onSubmit={handleSubmit} className="project-form">
					{error && (
						<ErrorBanner message={error} onClose={() => setError(null)} />
					)}

					<div className="form-group">
						<label htmlFor="projectName">
							Project Name <span className="required">*</span>
						</label>
						<input
							type="text"
							id="projectName"
							value={name}
							onChange={(e) => setName(e.target.value)}
							placeholder="e.g., Production, Staging, Development"
							required
							autoFocus
						/>
						<p className="field-hint">
							Give your project a descriptive name to identify it easily
						</p>
					</div>

					<div className="form-group">
						<label htmlFor="postgresUrl">PostgreSQL Connection URL</label>
						<input
							type="text"
							id="postgresUrl"
							value={postgresUrl}
							onChange={(e) => setPostgresUrl(e.target.value)}
							placeholder="postgresql://user:password@host:5432/database"
						/>
						{isEditMode && !postgresUrl && (
							<p className="field-hint">
								Leave empty to keep existing connection (encrypted)
							</p>
						)}
					</div>

					<div className="form-group">
						<label htmlFor="mongodbUrl">MongoDB Connection URL</label>
						<input
							type="text"
							id="mongodbUrl"
							value={mongodbUrl}
							onChange={(e) => setMongodbUrl(e.target.value)}
							placeholder="mongodb://host:27017/database"
						/>
						{isEditMode && !mongodbUrl && (
							<p className="field-hint">
								Leave empty to keep existing connection (encrypted)
							</p>
						)}
					</div>

					{(postgresUrl || mongodbUrl) && (
						<div className="connection-test-section">
							<button
								type="button"
								onClick={handleTestConnection}
								disabled={testingConnection}
								className="test-connection-btn"
							>
								{testingConnection ? "Testing..." : "Test Connection"}
							</button>

							{(connectionResults.postgres || connectionResults.mongodb) && (
								<div className="connection-results">
									{connectionResults.postgres && (
										<div
											className={`result-item ${
												connectionResults.postgres.success ? "success" : "error"
											}`}
										>
											<strong>PostgreSQL:</strong>{" "}
											{connectionResults.postgres.success
												? "✓ Connected"
												: `✗ ${connectionResults.postgres.error}`}
										</div>
									)}
									{connectionResults.mongodb && (
										<div
											className={`result-item ${
												connectionResults.mongodb.success ? "success" : "error"
											}`}
										>
											<strong>MongoDB:</strong>{" "}
											{connectionResults.mongodb.success
												? "✓ Connected"
												: `✗ ${connectionResults.mongodb.error}`}
										</div>
									)}
								</div>
							)}
						</div>
					)}

					<div className="security-note">
						🔒 <strong>Security:</strong> All connection strings are encrypted
						at rest and only decrypted when establishing database connections.
					</div>

					<div className="modal-actions">
						<button type="button" onClick={onClose} className="cancel-btn">
							Cancel
						</button>
						<button
							type="submit"
							disabled={loading || !name.trim()}
							className="submit-btn"
						>
							{loading
								? isEditMode
									? "Updating..."
									: "Creating..."
								: isEditMode
								? "Update Project"
								: "Create Project"}
						</button>
					</div>
				</form>
			</div>
		</div>
	);
}
