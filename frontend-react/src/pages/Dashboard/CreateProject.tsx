import { useEffect, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { apiFetchJson } from "../../utils/api";
import DatabaseInput, { DatabaseConfig } from "../../components/DatabaseInput/DatabaseInput";
import "./ProjectForm.css";

interface CreateProjectModalProps {
	isOpen: boolean;
	onClose: () => void;
	onSuccess: () => void;
}

export default function CreateProjectModal({
	isOpen,
	onClose,
	onSuccess,
}: CreateProjectModalProps) {
	const { token, logout } = useAuth();
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const [formData, setFormData] = useState({
		name: "",
	});
	const [databases, setDatabases] = useState<DatabaseConfig[]>([]);

	// Reset form when modal closes
	useEffect(() => {
		if (!isOpen) {
			setFormData({
				name: "",
			});
			setDatabases([]);
			setError(null);
		}
	}, [isOpen]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setLoading(true);

		try {
			// Convert databases array to backward-compatible format
			// For now, we'll send both formats for compatibility
			const payload: any = {
				name: formData.name.trim(),
			};

			// Extract postgres and mongodb URLs for backward compatibility
			const postgresDb = databases.find((db) => db.type === "postgres" && db.connection_url.trim());
			const mongoDb = databases.find((db) => db.type === "mongodb" && db.connection_url.trim());

			if (postgresDb) {
				payload.postgres_url = postgresDb.connection_url.trim();
			}
			if (mongoDb) {
				payload.mongodb_url = mongoDb.connection_url.trim();
			}

			// Also send databases array for future use (backend can ignore if not supported yet)
			if (databases.length > 0) {
				payload.databases = databases
					.filter((db) => db.connection_url.trim())
					.map((db) => ({
						type: db.type,
						connection_url: db.connection_url.trim(),
					}));
			}

			const response = await apiFetchJson<{
				id: string;
				name: string;
				api_key: string;
				postgres_url: string;
				mongodb_url: string;
				created_at: string;
				updated_at: string;
				is_active: boolean;
			}>(
				"/projects",
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						Authorization: `Bearer ${token}`,
					},
					body: JSON.stringify(payload),
				},
				logout,
			);
			
			// Store the API key immediately (only time it's returned in plain text)
			if (response.api_key) {
				const storedKeys = localStorage.getItem("project_api_keys");
				let keysMap = new Map<string, string>();
				if (storedKeys) {
					try {
						keysMap = new Map(JSON.parse(storedKeys));
					} catch (e) {
						console.warn("Failed to parse stored API keys:", e);
					}
				}
				keysMap.set(response.id, response.api_key);
				localStorage.setItem(
					"project_api_keys",
					JSON.stringify(Array.from(keysMap.entries())),
				);
			}
			
			onSuccess();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to create project");
		} finally {
			setLoading(false);
		}
	};

	if (!isOpen) return null;

	return (
		<div className="modal-overlay">
			<div className="modal-content">
				<div className="project-form-card">
					<div className="modal-header">
						<h2>Create New Project</h2>
						<button
							type="button"
							onClick={onClose}
							className="modal-close-btn"
							aria-label="Close"
						>
							×
						</button>
					</div>

					{error && <div className="error-message">{error}</div>}

					<form onSubmit={handleSubmit}>
						<div className="form-group">
							<label htmlFor="name">Project Name *</label>
							<input
								type="text"
								id="name"
								required
								value={formData.name}
								onChange={(e) =>
									setFormData({ ...formData, name: e.target.value })
								}
								placeholder="e.g. Production, Staging, Mobile App"
							/>
						</div>

						<div className="form-group">
							<DatabaseInput
								databases={databases}
								onChange={setDatabases}
							/>
						</div>

						<div className="form-actions">
							<button type="submit" disabled={loading} className="submit-btn">
								{loading ? "Creating..." : "Create Project"}
							</button>
						</div>
					</form>
				</div>
			</div>
		</div>
	);
}
