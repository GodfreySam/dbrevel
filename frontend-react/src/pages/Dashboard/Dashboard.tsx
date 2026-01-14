import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import "./Dashboard.css";

interface TenantInfo {
	id: string;
	name: string;
}

// ProjectListItem matches ProjectListResponse from backend (GET /projects)
interface ProjectListItem {
	id: string;
	name: string;
	is_active: boolean;
	created_at: string;
}

// ProjectDetail matches ProjectResponse from backend (GET /projects/{id} or POST /projects)
interface ProjectDetail {
	id: string;
	name: string;
	account_id: string;
	api_key: string; // May be "***" if masked
	postgres_url: string;
	mongodb_url: string;
	created_at: string;
	updated_at: string;
	is_active: boolean;
}

export default function Dashboard() {
	const { user, token, logout, refreshUser } = useAuth();
	const [tenantInfo, setTenantInfo] = useState<TenantInfo | null>(null);
	const [projects, setProjects] = useState<ProjectListItem[]>([]);
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

	// Visibility state for API keys
	const [visibleApiKeys, setVisibleApiKeys] = useState<Set<string>>(new Set());

	// Database connection test state
	const [testingConnection, setTestingConnection] = useState<Set<string>>(
		new Set(),
	);
	const [connectionResults, setConnectionResults] = useState<
		Map<string, { postgres?: string; mongodb?: string }>
	>(new Map());

	// Password change state
	const [showChangePassword, setShowChangePassword] = useState(false);
	const [passwordChangeData, setPasswordChangeData] = useState({
		currentPassword: "",
		newPassword: "",
	});
	const [showCurrentPassword, setShowCurrentPassword] = useState(false);
	const [showNewPassword, setShowNewPassword] = useState(false);
	const [passwordChangeLoading, setPasswordChangeLoading] = useState(false);
	const [passwordChangeError, setPasswordChangeError] = useState<string | null>(
		null,
	);
	const [passwordChangeSuccess, setPasswordChangeSuccess] = useState(false);

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
			const { apiFetchJson } = await import("../../utils/api");

			// Load projects (list endpoint doesn't include API keys)
			setLoadingProjects(true);
			const projectsData = await apiFetchJson<ProjectListItem[]>(
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

	// Load tenant info and projects on mount
	useEffect(() => {
		const loadTenantAndProjects = async () => {
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
				const { apiFetchJson } = await import("../../utils/api");

				// Load tenant info
				const tenantData = await apiFetchJson<TenantInfo>(
					"/tenants/me/info-jwt",
					{
						headers: {
							Authorization: `Bearer ${token}`,
						},
					},
					logout,
				);
				setTenantInfo(tenantData);

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
			loadTenantAndProjects();
		}
	}, [user?.id, token]); // Only depend on user.id and token, not the entire user object or logout

	const toggleApiKeyVisibility = (projectId: string) => {
		setVisibleApiKeys((prev) => {
			const newSet = new Set(prev);
			if (newSet.has(projectId)) {
				newSet.delete(projectId);
			} else {
				newSet.add(projectId);
			}
			return newSet;
		});
	};

	const copyToClipboard = (text: string) => {
		navigator.clipboard.writeText(text);
	};

	const toggleProjectExpanded = async (projectId: string) => {
		const newExpandedId = expandedProjectId === projectId ? null : projectId;
		setExpandedProjectId(newExpandedId);

		// If expanding and we don't have details yet, or details might be stale, fetch them
		if (newExpandedId) {
			try {
				const { apiFetchJson } = await import("../../utils/api");
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

	const testDatabaseConnections = async (projectId: string) => {
		// Ensure project details are loaded before testing
		let project = projectDetails.get(projectId);
		if (!project) {
			// Try to fetch project details if not in cache
			try {
				const { apiFetchJson } = await import("../../utils/api");
				project = await apiFetchJson<ProjectDetail>(
					`/projects/${projectId}`,
					{
						headers: {
							Authorization: `Bearer ${token}`,
						},
					},
					logout,
				);
				// Cache the project details
				setProjectDetails((prev) => {
					const newMap = new Map(prev);
					newMap.set(projectId, project!);
					return newMap;
				});
			} catch (err) {
				console.error(
					"Failed to fetch project details for connection test:",
					err,
				);
				setConnectionResults((prev) => {
					const newMap = new Map(prev);
					newMap.set(projectId, {
						postgres: "Error: Project details not available",
						mongodb: "Error: Project details not available",
					});
					return newMap;
				});
				return;
			}
		}

		setTestingConnection((prev) => new Set(prev).add(projectId));
		setConnectionResults((prev) => {
			const newMap = new Map(prev);
			newMap.delete(projectId);
			return newMap;
		});

		try {
			const { apiFetchJson } = await import("../../utils/api");
			const result = await apiFetchJson<{
				postgres?: {
					success: boolean;
					error?: string;
					schema_preview?: any;
				};
				mongodb?: {
					success: boolean;
					error?: string;
					schema_preview?: any;
				};
			}>(
				"/projects/test-connection",
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						Authorization: `Bearer ${token}`,
					},
					body: JSON.stringify({
						project_id: projectId,
					}),
				},
				logout,
			);

			// Format results for display
			const formattedResults: {
				postgres?: string;
				mongodb?: string;
			} = {};

			if (result.postgres) {
				if (result.postgres.success) {
					const preview = result.postgres.schema_preview;
					const tableCount = preview?.table_count || 0;
					const dbName = preview?.database_name || "database";
					formattedResults.postgres = `Success: Connected to ${dbName} (${tableCount} tables)`;
				} else {
					formattedResults.postgres = `Error: ${
						result.postgres.error || "Connection failed"
					}`;
				}
			}

			if (result.mongodb) {
				if (result.mongodb.success) {
					const preview = result.mongodb.schema_preview;
					const collCount = preview?.collection_count || 0;
					const dbName = preview?.database_name || "database";
					formattedResults.mongodb = `Success: Connected to ${dbName} (${collCount} collections)`;
				} else {
					formattedResults.mongodb = `Error: ${
						result.mongodb.error || "Connection failed"
					}`;
				}
			}

			setConnectionResults((prev) => {
				const newMap = new Map(prev);
				newMap.set(projectId, formattedResults);
				return newMap;
			});
		} catch (err) {
			const errorMessage =
				err instanceof Error ? err.message : "Connection test failed";
			setConnectionResults((prev) => {
				const newMap = new Map(prev);
				newMap.set(projectId, {
					postgres: `Error: ${errorMessage}`,
					mongodb: `Error: ${errorMessage}`,
				});
				return newMap;
			});
		} finally {
			setTestingConnection((prev) => {
				const newSet = new Set(prev);
				newSet.delete(projectId);
				return newSet;
			});
		}
	};

	const handleChangePassword = async (e: React.FormEvent) => {
		e.preventDefault();
		setPasswordChangeError(null);
		setPasswordChangeSuccess(false);

		if (passwordChangeData.newPassword.length < 8) {
			setPasswordChangeError("Password must be at least 8 characters");
			return;
		}

		setPasswordChangeLoading(true);
		try {
			const { apiFetchJson } = await import("../../utils/api");
			await apiFetchJson(
				"/auth/change-password",
				{
					method: "POST",
					headers: {
						"Content-Type": "application/json",
					},
					body: JSON.stringify({
						current_password: passwordChangeData.currentPassword,
						new_password: passwordChangeData.newPassword,
					}),
				},
				logout,
			);

			setPasswordChangeSuccess(true);
			setPasswordChangeData({
				currentPassword: "",
				newPassword: "",
			});

			await refreshUser();

			setTimeout(() => {
				setShowChangePassword(false);
				setPasswordChangeSuccess(false);
			}, 2000);
		} catch (err) {
			const errorMessage =
				err instanceof Error ? err.message : "Failed to change password";
			setPasswordChangeError(errorMessage);
		} finally {
			setPasswordChangeLoading(false);
		}
	};

	return (
		<div className="dashboard-container">
			<div className="dashboard-header">
				<div className="dashboard-title">
					<Link to="/">
						<img
							src="/assets/logo-horizontal.svg"
							alt="DbRevel"
							className="dashboard-logo"
						/>
					</Link>
					<div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
						<p style={{ margin: 0, fontSize: "16px", fontWeight: 500 }}>
							{user?.account_name || "Your Dashboard"}
						</p>
						<p
							style={{
								margin: 0,
								fontSize: "13px",
								color: "#666",
								fontWeight: 400,
							}}
						>
							Tenant ID: {tenantInfo?.id || "Loading..."}
						</p>
					</div>
				</div>
				<button onClick={logout} className="logout-btn">
					Logout
				</button>
			</div>

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
						<Link to="/projects/new" className="create-project-btn">
							+ New Project
						</Link>
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
								const isExpanded = expandedProjectId === project.id;
								const isApiKeyVisible = visibleApiKeys.has(project.id);
								const isTesting = testingConnection.has(project.id);
								const testResults = connectionResults.get(project.id);
								const projectDetail = projectDetails.get(project.id);

								// Get API key from stored keys or project detail
								const apiKey =
									projectApiKeys.get(project.id) ||
									(projectDetail && projectDetail.api_key !== "***"
										? projectDetail.api_key
										: null);

								return (
									<div key={project.id} className="project-card">
										<div
											className="project-header-clickable"
											onClick={() => toggleProjectExpanded(project.id)}
											style={{ cursor: "pointer" }}
										>
											<div>
												<h3 style={{ margin: "0 0 4px 0" }}>{project.name}</h3>
												<span className="project-id">{project.id}</span>
											</div>
											<span className="project-expand-icon">
												{isExpanded ? "▼" : "▶"}
											</span>
										</div>

										{isExpanded && (
											<div className="project-expanded-content">
												{/* API Key */}
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
																<span
																	style={{ color: "#999", fontStyle: "italic" }}
																>
																	API key not available. Create a new project or
																	rotate key to see it.
																</span>
															)}
														</code>
														<div className="api-key-actions">
															{apiKey ? (
																<>
																	<button
																		onClick={() =>
																			toggleApiKeyVisibility(project.id)
																		}
																		className="icon-btn"
																		title={isApiKeyVisible ? "Hide" : "Show"}
																	>
																		{isApiKeyVisible ? (
																			<svg
																				width="18"
																				height="18"
																				viewBox="0 0 24 24"
																				fill="none"
																				stroke="currentColor"
																				strokeWidth="2"
																				strokeLinecap="round"
																				strokeLinejoin="round"
																			>
																				<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
																				<line
																					x1="1"
																					y1="1"
																					x2="23"
																					y2="23"
																				></line>
																			</svg>
																		) : (
																			<svg
																				width="18"
																				height="18"
																				viewBox="0 0 24 24"
																				fill="none"
																				stroke="currentColor"
																				strokeWidth="2"
																				strokeLinecap="round"
																				strokeLinejoin="round"
																			>
																				<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
																				<circle cx="12" cy="12" r="3"></circle>
																			</svg>
																		)}
																	</button>
																	<button
																		onClick={() => copyToClipboard(apiKey)}
																		className="icon-btn"
																		title="Copy"
																	>
																		<svg
																			width="18"
																			height="18"
																			viewBox="0 0 24 24"
																			fill="none"
																			stroke="currentColor"
																			strokeWidth="2"
																			strokeLinecap="round"
																			strokeLinejoin="round"
																		>
																			<rect
																				x="9"
																				y="9"
																				width="13"
																				height="13"
																				rx="2"
																				ry="2"
																			></rect>
																			<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
																		</svg>
																	</button>
																</>
															) : (
																<button
																	onClick={async () => {
																		try {
																			const { apiFetchJson } = await import(
																				"../../utils/api"
																			);
																			const result = await apiFetchJson<{
																				project_id: string;
																				api_key: string;
																			}>(
																				`/projects/${project.id}/api-key`,
																				{
																					headers: {
																						Authorization: `Bearer ${token}`,
																					},
																				},
																				logout,
																			);
																			// Store the revealed API key using the handler
																			handleApiKeyUpdated(
																				project.id,
																				result.api_key,
																			);
																		} catch (err) {
																			console.error(
																				"Failed to reveal API key:",
																				err,
																			);
																		}
																	}}
																	className="icon-btn"
																	title="Reveal API Key"
																	style={{
																		fontSize: "12px",
																		padding: "6px 12px",
																	}}
																>
																	Reveal
																</button>
															)}
														</div>
													</div>
												</div>

												{/* Database Status */}
												<div className="database-status-section">
													<div
														style={{
															display: "flex",
															justifyContent: "space-between",
															alignItems: "center",
															marginBottom: "12px",
														}}
													>
														<label>Database Connections</label>
														<button
															onClick={() =>
																testDatabaseConnections(project.id)
															}
															className="test-connection-btn"
															disabled={
																isTesting ||
																!projectDetail ||
																((!projectDetail.postgres_url ||
																	projectDetail.postgres_url === "" ||
																	projectDetail.postgres_url.trim() === "" ||
																	projectDetail.postgres_url.startsWith(
																		"***",
																	)) &&
																	(!projectDetail.mongodb_url ||
																		projectDetail.mongodb_url === "" ||
																		projectDetail.mongodb_url.trim() === "" ||
																		projectDetail.mongodb_url.startsWith(
																			"***",
																		)))
															}
															title={
																!projectDetail ||
																((!projectDetail.postgres_url ||
																	projectDetail.postgres_url === "" ||
																	projectDetail.postgres_url.startsWith(
																		"***",
																	)) &&
																	(!projectDetail.mongodb_url ||
																		projectDetail.mongodb_url === "" ||
																		projectDetail.mongodb_url.startsWith(
																			"***",
																		)))
																	? "Add database URLs to the project to test connections"
																	: "Test database connections"
															}
														>
															{isTesting ? "Testing..." : "Test Connections"}
														</button>
													</div>

													{testResults && (
														<div className="connection-results">
															{testResults.postgres && (
																<div
																	className={`connection-result ${
																		testResults.postgres.includes("Success")
																			? "success"
																			: "error"
																	}`}
																>
																	<strong>PostgreSQL:</strong>{" "}
																	{testResults.postgres}
																</div>
															)}
															{testResults.mongodb && (
																<div
																	className={`connection-result ${
																		testResults.mongodb.includes("Success")
																			? "success"
																			: "error"
																	}`}
																>
																	<strong>MongoDB:</strong>{" "}
																	{testResults.mongodb}
																</div>
															)}
														</div>
													)}

													<div className="database-info">
														<div className="db-item">
															<span className="db-label">PostgreSQL</span>
															<span className="db-value">
																{projectDetail?.postgres_url &&
																projectDetail.postgres_url !== "***"
																	? "Configured"
																	: "Not configured"}
															</span>
														</div>
														<div className="db-item">
															<span className="db-label">MongoDB</span>
															<span className="db-value">
																{projectDetail?.mongodb_url &&
																projectDetail.mongodb_url !== "***"
																	? "Configured"
																	: "Not configured"}
															</span>
														</div>
													</div>
												</div>

												{/* Project Actions */}
												<div className="project-actions">
													<Link
														to={`/projects/${project.id}/edit`}
														className="action-btn secondary"
													>
														Edit Project
													</Link>
												</div>
											</div>
										)}
									</div>
								);
							})}
						</div>
					)}
				</section>

				{/* Account Information */}
				<section className="dashboard-section">
					<h2>Account Information</h2>
					<div className="info-card">
						<div className="info-row">
							<span className="info-label">Email</span>
							<span className="info-value">{user?.email}</span>
						</div>
						<div className="info-row">
							<span className="info-label">Email Verified</span>
							<span className="info-value">
								{user?.email_verified ? "✓ Yes" : "✗ No"}
							</span>
						</div>
						<div className="info-row">
							<span className="info-label">Organization</span>
							<span className="info-value">{user?.account_name}</span>
						</div>
						<div className="info-row">
							<span className="info-label">User ID</span>
							<span className="info-value">{user?.id}</span>
						</div>
					</div>

					{/* Password Change Section */}
					<div className="password-change-section">
						<button
							onClick={() => setShowChangePassword(!showChangePassword)}
							className="toggle-password-btn"
						>
							{showChangePassword
								? "Cancel Password Change"
								: "Change Password"}
						</button>

						{showChangePassword && (
							<form
								onSubmit={handleChangePassword}
								className="password-change-form"
							>
								{passwordChangeError && (
									<div className="error-message">{passwordChangeError}</div>
								)}
								{passwordChangeSuccess && (
									<div className="success-message">
										Password changed successfully!
									</div>
								)}
								<div className="form-group">
									<label htmlFor="currentPassword">Current Password</label>
									<div className="password-input-container">
										<input
											type={showCurrentPassword ? "text" : "password"}
											id="currentPassword"
											required
											value={passwordChangeData.currentPassword}
											onChange={(e) =>
												setPasswordChangeData({
													...passwordChangeData,
													currentPassword: e.target.value,
												})
											}
											placeholder="Enter current password"
											className="password-input"
										/>
										<button
											type="button"
											onClick={() =>
												setShowCurrentPassword(!showCurrentPassword)
											}
											className="password-toggle-btn"
											aria-label={
												showCurrentPassword ? "Hide password" : "Show password"
											}
										>
											{showCurrentPassword ? (
												<svg
													width="20"
													height="20"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													strokeWidth="2"
													strokeLinecap="round"
													strokeLinejoin="round"
												>
													<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
													<line x1="1" y1="1" x2="23" y2="23"></line>
												</svg>
											) : (
												<svg
													width="20"
													height="20"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													strokeWidth="2"
													strokeLinecap="round"
													strokeLinejoin="round"
												>
													<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
													<circle cx="12" cy="12" r="3"></circle>
												</svg>
											)}
										</button>
									</div>
								</div>
								<div className="form-group">
									<label htmlFor="newPassword">
										New Password (min 8 characters)
									</label>
									<div className="password-input-container">
										<input
											type={showNewPassword ? "text" : "password"}
											id="newPassword"
											required
											minLength={8}
											value={passwordChangeData.newPassword}
											onChange={(e) =>
												setPasswordChangeData({
													...passwordChangeData,
													newPassword: e.target.value,
												})
											}
											placeholder="At least 8 characters"
											className="password-input"
										/>
										<button
											type="button"
											onClick={() => setShowNewPassword(!showNewPassword)}
											className="password-toggle-btn"
											aria-label={
												showNewPassword ? "Hide password" : "Show password"
											}
										>
											{showNewPassword ? (
												<svg
													width="20"
													height="20"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													strokeWidth="2"
													strokeLinecap="round"
													strokeLinejoin="round"
												>
													<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
													<line x1="1" y1="1" x2="23" y2="23"></line>
												</svg>
											) : (
												<svg
													width="20"
													height="20"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													strokeWidth="2"
													strokeLinecap="round"
													strokeLinejoin="round"
												>
													<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
													<circle cx="12" cy="12" r="3"></circle>
												</svg>
											)}
										</button>
									</div>
								</div>
								<button
									type="submit"
									disabled={passwordChangeLoading}
									className="submit-password-btn"
								>
									{passwordChangeLoading ? "Changing..." : "Change Password"}
								</button>
							</form>
						)}
					</div>
				</section>

				{/* SDK Integration Guide */}
				<section className="dashboard-section">
					<h2>SDK Integration</h2>
					<div className="info-card">
						<p style={{ marginBottom: "16px" }}>
							Use your project's API key to integrate with the DbRevel SDK:
						</p>
						<pre className="code-snippet">
							{`import { DbRevelClient } from '@dbrevel/sdk';

const client = new DbRevelClient({
  apiKey: 'your_project_api_key_here'
});

// Query using natural language
const result = await client.query('Get all users from Lagos');`}
						</pre>
						<p style={{ marginTop: "16px", fontSize: "14px", color: "#666" }}>
							Learn more in our <Link to="/docs">documentation</Link>.
						</p>
					</div>
				</section>
			</div>
		</div>
	);
}
