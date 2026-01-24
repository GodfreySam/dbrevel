import { useEffect, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { ProjectDetail } from "../../types/api";
import { apiFetchJson } from "../../utils/api";
import DatabaseInput, { DatabaseConfig } from "../../components/DatabaseInput/DatabaseInput";
import "./ProjectForm.css";

interface EditProjectModalProps {
	isOpen: boolean;
	onClose: () => void;
	onSuccess: () => void;
	projectId: string;
}

export default function EditProjectModal({
	isOpen,
	onClose,
	onSuccess,
	projectId,
}: EditProjectModalProps) {
	const { token, logout } = useAuth();
	const [loading, setLoading] = useState(true);
	const [saving, setSaving] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const [formData, setFormData] = useState({
		name: "",
	});
	const [databases, setDatabases] = useState<DatabaseConfig[]>([]);
	const [existingDatabases, setExistingDatabases] = useState<{
		postgres_url?: string;
		mongodb_url?: string;
	}>({});

	// Reset state when modal closes
	useEffect(() => {
		if (!isOpen) {
			setFormData({ name: "" });
			setDatabases([]);
			setExistingDatabases({});
			setError(null);
			setLoading(true);
		}
	}, [isOpen]);

	useEffect(() => {
		const fetchProject = async () => {
			if (!projectId || !token || !isOpen) return;

			try {
				const project = await apiFetchJson<ProjectDetail>(
					`/projects/${projectId}`,
					{
						headers: {
							Authorization: `Bearer ${token}`,
						},
					},
					logout,
				);

				setFormData({
					name: project.name,
				});
				
				// Store existing databases for backward compatibility display
				setExistingDatabases({
					postgres_url: project.postgres_url,
					mongodb_url: project.mongodb_url,
				});
				
				// Initialize databases array from existing project data
				// Convert legacy format (postgres_url/mongodb_url) to new format
				const initialDatabases: DatabaseConfig[] = [];
				if (project.postgres_url && project.postgres_url !== "***" && project.postgres_url.trim()) {
					initialDatabases.push({
						id: `existing-postgres-${Date.now()}`,
						type: "postgres",
						connection_url: "", // Don't show masked URLs - user must enter new URL to update
					});
				}
				if (project.mongodb_url && project.mongodb_url !== "***" && project.mongodb_url.trim()) {
					initialDatabases.push({
						id: `existing-mongodb-${Date.now()}`,
						type: "mongodb",
						connection_url: "", // Don't show masked URLs - user must enter new URL to update
					});
				}
				setDatabases(initialDatabases);
			} catch (err) {
				setError(err instanceof Error ? err.message : "Failed to load project");
			} finally {
				setLoading(false);
			}
		};

		fetchProject();
	}, [projectId, token, logout, isOpen]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setSaving(true);

		try {
			const payload: any = { name: formData.name.trim() };

			// Find databases by type (regardless of whether URL is filled)
			const postgresDb = databases.find((db) => db.type === "postgres");
			const mongoDb = databases.find((db) => db.type === "mongodb");

			// Handle database updates:
			// - If database exists in array with URL → update it
			// - If database exists in array without URL → keep existing (don't include in payload)
			// - If database doesn't exist in array → clear it (set to empty string)
			
			if (postgresDb) {
				const pgUrl = postgresDb.connection_url.trim();
				if (pgUrl) {
					// User provided new URL - update it
					payload.postgres_url = pgUrl;
				}
				// If empty, don't include in payload - backend will keep existing
			} else {
				// No postgres in databases array - user removed it, clear it
				payload.postgres_url = "";
			}
			
			if (mongoDb) {
				const mongoUrl = mongoDb.connection_url.trim();
				if (mongoUrl) {
					// User provided new URL - update it
					payload.mongodb_url = mongoUrl;
				}
				// If empty, don't include in payload - backend will keep existing
			} else {
				// No mongodb in databases array - user removed it, clear it
				payload.mongodb_url = "";
			}

			// Also send databases array for future use
			if (databases.length > 0) {
				payload.databases = databases
					.filter((db) => db.connection_url.trim())
					.map((db) => ({
						type: db.type,
						connection_url: db.connection_url.trim(),
					}));
			}

			await apiFetchJson(
				`/projects/${projectId}`,
				{
					method: "PATCH",
					headers: {
						"Content-Type": "application/json",
						Authorization: `Bearer ${token}`,
					},
					body: JSON.stringify(payload),
				},
				logout,
			);
			onSuccess();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to update project");
		} finally {
			setSaving(false);
		}
	};

	if (!isOpen) return null;

	if (loading) {
		return (
			<div className="modal-overlay">
				<div className="modal-content">
					<div className="project-form-card">
						<div className="modal-header">
							<h2>Edit Project</h2>
							<button
								type="button"
								onClick={onClose}
								className="modal-close-btn"
								aria-label="Close"
							>
								×
							</button>
						</div>
						<div className="loading-message">Loading project details...</div>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="modal-overlay">
			<div className="modal-content">
				<div className="project-form-card">
					<div className="modal-header">
						<h2>Edit Project</h2>
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
							/>
						</div>

						<div className="form-group">
							<DatabaseInput
								databases={databases}
								onChange={setDatabases}
								existingDatabases={existingDatabases}
							/>
						</div>

						<div className="form-actions">
							<button type="submit" disabled={saving} className="submit-btn">
								{saving ? "Saving..." : "Save Changes"}
							</button>
						</div>
					</form>
				</div>
			</div>
		</div>
	);
}
