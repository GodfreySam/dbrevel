import { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { apiFetchJson } from "../../utils/api";
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
		postgres_url: "",
		mongodb_url: "",
	});

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setLoading(true);

		try {
			await apiFetchJson(
				"/projects",
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						Authorization: `Bearer ${token}`,
					},
					body: JSON.stringify({
						name: formData.name.trim(),
						postgres_url: formData.postgres_url.trim() || null,
						mongodb_url: formData.mongodb_url.trim() || null,
					}),
				},
				logout,
			);
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
					<h2>Create New Project</h2>

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
							<label htmlFor="postgres_url">
								PostgreSQL Connection URL (Optional)
							</label>
							<input
								type="text"
								id="postgres_url"
								value={formData.postgres_url}
								onChange={(e) =>
									setFormData({ ...formData, postgres_url: e.target.value })
								}
								placeholder="postgresql://user:password@host:5432/dbname"
							/>
							<span className="form-hint">
								Connection string for your PostgreSQL database.
							</span>
						</div>

						<div className="form-group">
							<label htmlFor="mongodb_url">
								MongoDB Connection URL (Optional)
							</label>
							<input
								type="text"
								id="mongodb_url"
								value={formData.mongodb_url}
								onChange={(e) =>
									setFormData({ ...formData, mongodb_url: e.target.value })
								}
								placeholder="mongodb+srv://user:password@host/dbname"
							/>
							<span className="form-hint">
								Connection string for your MongoDB database.
							</span>
						</div>

						<div className="form-actions">
							<button type="button" onClick={onClose} className="cancel-btn">
								Close
							</button>
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
