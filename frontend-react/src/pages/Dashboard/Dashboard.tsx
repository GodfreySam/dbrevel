import { useEffect, useRef, useState } from "react";
import Header from "../../components/Header";
import { useAuth } from "../../contexts/AuthContext";
import { AccountDetail, ProjectDetail, ProjectSummary } from "../../types/api";
import { apiFetchJson } from "../../utils/api";
import AccountInfo from "./AccountInfo";
import CreateProjectModal from "./CreateProject";
import "./Dashboard.css";
import EditProjectModal from "./EditProject";
import ProjectCard from "./ProjectCard";
import SdkIntegrationGuide from "./SdkIntegrationGuide";

export default function Dashboard() {
	const { user, token, logout, refreshUser } = useAuth();
	const [accountInfo, setAccountInfo] = useState<AccountDetail | null>(null);
	const [projects, setProjects] = useState<ProjectSummary[]>([]);

	// Store API keys separately (keyed by project ID)
	const [projectApiKeys, setProjectApiKeys] = useState<Map<string, string>>(
		new Map(),
	);

	// Store full project details when expanded
	const [projectDetails, setProjectDetails] = useState<
		Map<string, ProjectDetail>
	>(new Map());

	const [loadingProjects, setLoadingProjects] = useState(true);
	const [projectsError, setProjectsError] = useState<string | null>(null);
	const [expandedProjectId, setExpandedProjectId] = useState<string | null>(
		null,
	);

	const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
	const [editingProjectId, setEditingProjectId] = useState<string | null>(null);

	// Ref to track if we're currently loading to prevent duplicate calls
	const isLoadingRef = useRef(false);
	// Ref to track the last loaded user/token combination
	const hasLoadedRef = useRef<string | null>(null);

	// Function to load projects (can be called from multiple places)
	const loadProjects = async () => {
		if (!token || !user) {
			return;
		}

		try {
			// Load projects (list endpoint doesn't include API keys)
			setLoadingProjects(true);
			const projectsData = await apiFetchJson<ProjectSummary[]>(
				"/projects",
				{
					headers: {
						Authorization: `Bearer ${token}`,
					},
				},
				logout,
			);
			setProjects(projectsData);

			// Clean up API keys for projects that no longer exist
			const existingProjectIds = new Set(projectsData.map((p) => p.id));
			setProjectApiKeys((prev) => {
				const newMap = new Map(prev);
				let hasChanges = false;
				for (const [projectId] of newMap) {
					if (!existingProjectIds.has(projectId)) {
						newMap.delete(projectId);
						hasChanges = true;
					}
				}
				if (hasChanges) {
					// Update localStorage
					const storedKeys = localStorage.getItem("project_api_keys");
					if (storedKeys) {
						try {
							const keysMap = new Map<string, string>(JSON.parse(storedKeys));
							for (const [projectId] of keysMap) {
								if (!existingProjectIds.has(projectId)) {
									keysMap.delete(projectId);
								}
							}
							localStorage.setItem(
								"project_api_keys",
								JSON.stringify(Array.from(keysMap.entries())),
							);
						} catch (e) {
							console.warn("Failed to update stored API keys:", e);
						}
					}
				}
				return newMap;
			});

			// Clean up project details cache for projects that no longer exist
			setProjectDetails((prev) => {
				const newMap = new Map(prev);
				for (const [projectId] of newMap) {
					if (!existingProjectIds.has(projectId)) {
						newMap.delete(projectId);
					}
				}
				return newMap;
			});
		} catch (err) {
			const errorMessage =
				err instanceof Error ? err.message : "Failed to load projects";
			setProjectsError(errorMessage);
		} finally {
			setLoadingProjects(false);
		}
	};

	// Load account info and projects on mount
	useEffect(() => {
		const loadAccountAndProjects = async () => {
			// Wait for token to be available before making requests
			if (!token || !user) {
				return;
			}

			// Prevent duplicate concurrent calls
			if (isLoadingRef.current) {
				return;
			}

			// Track the current user/token combination we're loading for
			const currentUserToken = `${user.id}-${token.slice(0, 20)}`;
			const lastLoadedKey = hasLoadedRef.current;

			// If we've already loaded for this exact user/token, skip
			if (lastLoadedKey === currentUserToken) {
				return;
			}

			isLoadingRef.current = true;

			try {
				// Load account info
				const accountData = await apiFetchJson<AccountDetail>(
					"/accounts/me/info-jwt",
					{
						headers: {
							Authorization: `Bearer ${token}`,
						},
					},
					logout,
				);
				setAccountInfo(accountData);

				// Load projects
				await loadProjects();

				// Load stored API keys from localStorage
				const storedKeys = localStorage.getItem("project_api_keys");
				if (storedKeys) {
					try {
						const keysMap = new Map<string, string>(JSON.parse(storedKeys));
						setProjectApiKeys(keysMap);
					} catch (e) {
						console.warn("Failed to load stored API keys:", e);
					}
				}

				// Mark as loaded for this user/token combination
				hasLoadedRef.current = currentUserToken;
			} catch (err) {
				const errorMessage =
					err instanceof Error ? err.message : "Failed to load data";
				setProjectsError(errorMessage);
			} finally {
				isLoadingRef.current = false;
			}
		};

		if (user && token) {
			loadAccountAndProjects();
		}
	}, [user?.id, token]); // Only depend on user.id and token, not the entire user object or logout

	const toggleProjectExpanded = async (projectId: string) => {
		const newExpandedId = expandedProjectId === projectId ? null : projectId;
		setExpandedProjectId(newExpandedId);

		// If expanding and we don't have details yet, or details might be stale, fetch them
		if (newExpandedId) {
			try {
				const detail = await apiFetchJson<ProjectDetail>(
					`/projects/${newExpandedId}`,
					{
						headers: {
							Authorization: `Bearer ${token}`,
						},
					},
					logout,
				);
				setProjectDetails((prev) => {
					const newMap = new Map(prev);
					newMap.set(newExpandedId, detail);
					return newMap;
				});
			} catch (err) {
				console.error("Failed to fetch project details:", err);
				// Remove from cache if fetch failed (project might be deleted)
				setProjectDetails((prev) => {
					const newMap = new Map(prev);
					newMap.delete(newExpandedId);
					return newMap;
				});
			}
		}
	};

	// Function to invalidate project cache (call after updates/deletions)
	const invalidateProjectCache = (projectId: string) => {
		setProjectDetails((prev) => {
			const newMap = new Map(prev);
			newMap.delete(projectId);
			return newMap;
		});
		// Also remove API key if project is deleted
		setProjectApiKeys((prev) => {
			const newMap = new Map(prev);
			if (newMap.has(projectId)) {
				newMap.delete(projectId);
				// Update localStorage
				const storedKeys = localStorage.getItem("project_api_keys");
				if (storedKeys) {
					try {
						const keysMap = new Map<string, string>(JSON.parse(storedKeys));
						keysMap.delete(projectId);
						localStorage.setItem(
							"project_api_keys",
							JSON.stringify(Array.from(keysMap.entries())),
						);
					} catch (e) {
						console.warn("Failed to update stored API keys:", e);
					}
				}
			}
			return newMap;
		});
	};

	// Function to handle API key updates (used for reveal and rotation)
	const handleApiKeyUpdated = (projectId: string, newApiKey: string) => {
		// Update API key in state
		setProjectApiKeys((prev) => {
			const newMap = new Map(prev);
			newMap.set(projectId, newApiKey);
			return newMap;
		});
		// Update localStorage
		const storedKeys = localStorage.getItem("project_api_keys");
		let keysMap = new Map<string, string>();
		if (storedKeys) {
			try {
				keysMap = new Map(JSON.parse(storedKeys));
			} catch (e) {
				console.warn("Failed to parse stored API keys:", e);
			}
		}
		keysMap.set(projectId, newApiKey);
		localStorage.setItem(
			"project_api_keys",
			JSON.stringify(Array.from(keysMap.entries())),
		);
		// Invalidate project details cache to force refresh
		invalidateProjectCache(projectId);
	};

	return (
		<div className="dashboard-container">
			<Header />

			<div className="dashboard-content">
				{/* Projects Section - Primary Focus */}
				<section className="dashboard-section">
					<div
						style={{
							display: "flex",
							justifyContent: "space-between",
							alignItems: "center",
							marginBottom: "20px",
						}}
					>
						<h2>Projects</h2>
						<button
							onClick={() => setIsCreateModalOpen(true)}
							className="create-project-btn"
						>
							+ New Project
						</button>
					</div>

					{loadingProjects ? (
						<div className="loading-message">Loading projects...</div>
					) : projectsError ? (
						<div className="error-message">{projectsError}</div>
					) : projects.length === 0 ? (
						<div className="info-card">
							<p>You haven't created any projects yet.</p>
							<p style={{ marginTop: "12px" }}>
								Projects let you organize your databases and API keys
								separately.
							</p>
						</div>
					) : (
						<div className="projects-grid">
							{projects.map((project) => {
								const projectDetail = projectDetails.get(project.id);
								const apiKey =
									projectApiKeys.get(project.id) ||
									(projectDetail && projectDetail.api_key !== "***"
										? projectDetail.api_key
										: null);

								return (
									<ProjectCard
										key={project.id}
										project={project}
										detail={projectDetail}
										apiKey={apiKey}
										isExpanded={expandedProjectId === project.id}
										onToggleExpand={() => toggleProjectExpanded(project.id)}
										onApiKeyUpdate={handleApiKeyUpdated}
										onEdit={(id) => setEditingProjectId(id)}
									/>
								);
							})}
						</div>
					)}
				</section>

				{/* Account Information */}
				{user && (
					<AccountInfo
						user={user}
						accountInfo={accountInfo}
						onUserRefresh={refreshUser}
					/>
				)}

				{/* SDK Integration Guide */}
				<SdkIntegrationGuide />
			</div>

			{/* Modals */}
			{isCreateModalOpen && (
				<CreateProjectModal
					isOpen={isCreateModalOpen}
					onClose={() => setIsCreateModalOpen(false)}
					onSuccess={() => {
						setIsCreateModalOpen(false);
						loadProjects();
					}}
				/>
			)}
			{editingProjectId && (
				<EditProjectModal
					isOpen={!!editingProjectId}
					projectId={editingProjectId}
					onClose={() => setEditingProjectId(null)}
					onSuccess={() => {
						setEditingProjectId(null);
						loadProjects();
					}}
				/>
			)}
		</div>
	);
}
