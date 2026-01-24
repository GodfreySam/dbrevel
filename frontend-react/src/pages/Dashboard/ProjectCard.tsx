import { useState } from "react";
import Spinner from "../../components/Spinner/Spinner";
import { useAuth } from "../../contexts/AuthContext";
import { ProjectDetail, ProjectSummary } from "../../types/api";
import { apiFetchJson } from "../../utils/api";
import DatabaseConnectionStatus from "./DatabaseConnectionStatus";

interface ProjectCardProps {
	project: ProjectSummary;
	detail?: ProjectDetail;
	apiKey?: string | null;
	isExpanded: boolean;
	onToggleExpand: () => void;
	onApiKeyUpdate: (projectId: string, newKey: string) => void;
	onEdit: (projectId: string) => void;
}

export default function ProjectCard({
	project,
	detail,
	apiKey,
	isExpanded,
	onToggleExpand,
	onApiKeyUpdate,
	onEdit,
}: ProjectCardProps) {
	const { token, logout } = useAuth();
	const [isApiKeyVisible, setIsApiKeyVisible] = useState(false);
	const [revealing, setRevealing] = useState(false);
	const [rotating, setRotating] = useState(false);

	const copyToClipboard = (text: string) => {
		navigator.clipboard.writeText(text);
	};

	const revealApiKey = async () => {
		if (revealing) return; // Prevent double-clicks
		
		setRevealing(true);
		try {
			const result = await apiFetchJson<{
				project_id: string;
				api_key: string;
			}>(
				`/projects/${project.id}/api-key`,
				{
					headers: { Authorization: `Bearer ${token}` },
				},
				logout,
			);
			onApiKeyUpdate(project.id, result.api_key);
		} catch (err) {
			const errorMsg = err instanceof Error ? err.message : "Failed to reveal API key";
			console.error("Failed to reveal API key:", err);
			alert(errorMsg);
		} finally {
			setRevealing(false);
		}
	};

	const rotateApiKey = async () => {
		if (rotating) return; // Prevent double-clicks
		
		if (
			!window.confirm(
				"Are you sure you want to rotate this API key? The old key will stop working immediately.",
			)
		) {
			return;
		}

		setRotating(true);
		try {
			const result = await apiFetchJson<{
				project_id: string;
				new_api_key: string;
				rotated_at: string;
			}>(
				`/projects/${project.id}/rotate-key`,
				{
					method: "POST",
					headers: { Authorization: `Bearer ${token}` },
				},
				logout,
			);
			onApiKeyUpdate(project.id, result.new_api_key);
		} catch (err) {
			const errorMsg = err instanceof Error ? err.message : "Failed to rotate API key";
			console.error("Failed to rotate API key:", err);
			alert(errorMsg);
		} finally {
			setRotating(false);
		}
	};

	return (
		<div className="project-card">
			<div
				className="project-header-clickable"
				onClick={onToggleExpand}
				style={{ cursor: "pointer" }}
			>
				<div>
					<h3 style={{ margin: "0 0 4px 0" }}>{project.name}</h3>
					<span className="project-id">{project.id}</span>
				</div>
				<span className="project-expand-icon">{isExpanded ? "▼" : "▶"}</span>
			</div>

			{isExpanded && !detail && (
				<div className="project-expanded-content">
					<Spinner />
				</div>
			)}
			{isExpanded && detail && (
				<div className="project-expanded-content">
					{/* API Key Section */}
					<div className="api-key-section">
						<label>API Key</label>
						<div className="api-key-display">
							<code>
								{apiKey ? (
									isApiKeyVisible ? (
										apiKey
									) : (
										"•".repeat(32) + (apiKey.slice(-8) || "")
									)
								) : (
									<span style={{ color: "#999", fontStyle: "italic" }}>
										API key not available. Reveal to see it.
									</span>
								)}
							</code>
							<div className="api-key-actions">
								{apiKey ? (
									<>
										<button
											onClick={() => setIsApiKeyVisible(!isApiKeyVisible)}
											className="icon-btn"
											title={isApiKeyVisible ? "Hide" : "Show"}
										>
											{isApiKeyVisible ? "Hide" : "Show"}
										</button>
										<button
											onClick={() => copyToClipboard(apiKey)}
											className="icon-btn"
											title="Copy"
										>
											Copy
										</button>
									</>
								) : (
									<button
										onClick={revealApiKey}
										disabled={revealing}
										className="icon-btn"
										title="Reveal API Key"
										style={{ fontSize: "12px", padding: "6px 12px" }}
									>
										{revealing ? "Loading..." : "Reveal"}
									</button>
								)}
								<button
									onClick={rotateApiKey}
									disabled={rotating}
									className="icon-btn"
									title="Rotate API Key"
									style={{
										fontSize: "12px",
										padding: "6px 12px",
										marginLeft: "8px",
									}}
								>
									{rotating ? "Rotating..." : "Rotate"}
								</button>
							</div>
						</div>
					</div>

					{/* Database Status */}
					<DatabaseConnectionStatus project={detail} />

					{/* Actions */}
					<div className="project-actions">
						<button
							onClick={() => onEdit(project.id)}
							className="action-btn secondary"
						>
							Edit Project
						</button>
					</div>
				</div>
			)}
		</div>
	);
}
