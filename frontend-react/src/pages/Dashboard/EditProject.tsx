import { useEffect, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { ProjectDetail } from "../../types/api";
import { apiFetchJson } from "../../utils/api";
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
		postgres_url: "",
		mongodb_url: "",
	});

	const [hasExistingPostgres, setHasExistingPostgres] = useState(false);
	const [hasExistingMongo, setHasExistingMongo] = useState(false);
	const [removePostgres, setRemovePostgres] = useState(false);
	const [removeMongo, setRemoveMongo] = useState(false);

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
					// Don't pre-fill masked URLs to avoid accidentally saving "***"
					// Users should only type here if they want to UPDATE the URL
					postgres_url: "",
					mongodb_url: "",
				});
				setHasExistingPostgres(!!project.postgres_url);
				setHasExistingMongo(!!project.mongodb_url);
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
			// Only include fields that have values
			const payload: any = { name: formData.name };

			if (removePostgres) {
				payload.postgres_url = "";
			} else if (formData.postgres_url) {
				payload.postgres_url = formData.postgres_url;
			}

			if (removeMongo) {
				payload.mongodb_url = "";
			} else if (formData.mongodb_url) {
				payload.mongodb_url = formData.mongodb_url;
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
					<div className="loading-message">Loading project details...</div>
				</div>
			</div>
		);
	}

	return (
		<div className="modal-overlay">
			<div className="modal-content">
				<div className="project-form-card">
					<h2>Edit Project</h2>

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
							<div className="input-header">
								<label htmlFor="postgres_url" style={{ marginBottom: 0 }}>
									PostgreSQL Connection URL
								</label>
								{hasExistingPostgres && (
									<button
										type="button"
										onClick={() => setRemovePostgres(!removePostgres)}
										className={removePostgres ? "undo-btn" : "disconnect-btn"}
									>
										{removePostgres ? "Undo Remove" : "Disconnect Database"}
									</button>
								)}
							</div>
							<input
								type="text"
								id="postgres_url"
								value={formData.postgres_url}
								disabled={removePostgres}
								onChange={(e) =>
									setFormData({ ...formData, postgres_url: e.target.value })
								}
								placeholder={
									removePostgres
										? "Database will be disconnected"
										: "Leave blank to keep current configuration"
								}
							/>
						</div>

						<div className="form-group">
							<div className="input-header">
								<label htmlFor="mongodb_url" style={{ marginBottom: 0 }}>
									MongoDB Connection URL
								</label>
								{hasExistingMongo && (
									<button
										type="button"
										onClick={() => setRemoveMongo(!removeMongo)}
										className={removeMongo ? "undo-btn" : "disconnect-btn"}
									>
										{removeMongo ? "Undo Remove" : "Disconnect Database"}
									</button>
								)}
							</div>
							<input
								type="text"
								id="mongodb_url"
								value={formData.mongodb_url}
								disabled={removeMongo}
								onChange={(e) =>
									setFormData({ ...formData, mongodb_url: e.target.value })
								}
								placeholder={
									removeMongo
										? "Database will be disconnected"
										: "Leave blank to keep current configuration"
								}
							/>
						</div>

						<div className="form-actions">
							<button type="button" onClick={onClose} className="cancel-btn">
								Close
							</button>
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
