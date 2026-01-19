import { useEffect, useState } from "react";
import { Link, Route, Routes, useNavigate } from "react-router-dom";
import {
	LineChart,
	Line,
	XAxis,
	YAxis,
	CartesianGrid,
	Tooltip,
	ResponsiveContainer,
	BarChart,
	Bar,
	Cell,
} from "recharts";
import ConfirmationModal from "../../components/ConfirmationModal/ConfirmationModal";
import ErrorBanner from "../../components/ErrorBanner/ErrorBanner";
import { useAuth } from "../../contexts/AuthContext";
import { apiFetchJson } from "../../utils/api";
import "./AdminDashboard.css";

interface PlatformStats {
	total_tenants: number;
	total_users: number;
	total_projects: number;
	verified_users: number;
	active_tenants_last_7_days: number;
	total_queries_today: number;
}

// Admin Overview Component
function AdminOverview() {
	const { token, logout } = useAuth();
	const [stats, setStats] = useState<PlatformStats | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		loadStats();
	}, []);

	const loadStats = async () => {
		if (!token) return;

		try {
			const data = await apiFetchJson<PlatformStats>(
				"/admin/analytics/stats",
				{ headers: { Authorization: `Bearer ${token}` } },
				() => logout(),
			);
			setStats(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load stats");
		} finally {
			setLoading(false);
		}
	};

	if (loading) {
		return (
			<div>
				<h2>Platform Overview</h2>
				<p>Loading statistics...</p>
			</div>
		);
	}

	if (error) {
		return (
			<div>
				<h2>Platform Overview</h2>
				<ErrorBanner message={error} onClose={() => setError(null)} />
			</div>
		);
	}

	return (
		<div>
			<h2>Platform Overview</h2>
			<div className="stats-grid">
				<div className="stat-card">
					<h3>Total Tenants</h3>
					<p className="stat-value">{stats?.total_tenants || 0}</p>
				</div>
				<div className="stat-card">
					<h3>Total Users</h3>
					<p className="stat-value">{stats?.total_users || 0}</p>
					<p className="stat-subtitle">{stats?.verified_users || 0} verified</p>
				</div>
				<div className="stat-card">
					<h3>Total Projects</h3>
					<p className="stat-value">{stats?.total_projects || 0}</p>
				</div>
				<div className="stat-card">
					<h3>Queries Today</h3>
					<p className="stat-value">{stats?.total_queries_today || 0}</p>
				</div>
				<div className="stat-card">
					<h3>Active Tenants (7 days)</h3>
					<p className="stat-value">{stats?.active_tenants_last_7_days || 0}</p>
				</div>
			</div>
		</div>
	);
}

interface AdminUser {
	id: string;
	email: string;
	account_id: string;
	account_name: string;
	projects_count?: number;
	email_verified: boolean;
	role: string;
	created_at: string;
	last_login?: string;
}

function AdminUsers() {
	const { token, logout } = useAuth();
	const [users, setUsers] = useState<AdminUser[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [search, setSearch] = useState("");
	const [page, setPage] = useState(1);

	// Modal states
	const [deleteModalOpen, setDeleteModalOpen] = useState(false);
	const [promoteModalOpen, setPromoteModalOpen] = useState(false);
	const [verifyModalOpen, setVerifyModalOpen] = useState(false);
	const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
	const [actionLoading, setActionLoading] = useState(false);

	useEffect(() => {
		loadUsers();
	}, [page, search]);

	const loadUsers = async () => {
		if (!token) return;

		try {
			setLoading(true);
			const params = new URLSearchParams({
				page: page.toString(),
				limit: "20",
			});
			if (search) params.append("search", search);

			const data = await apiFetchJson<AdminUser[]>(
				`/admin/users?${params}`,
				{ headers: { Authorization: `Bearer ${token}` } },
				() => logout(),
			);

			// Filter out admin users from the general users list
			setUsers(data.filter((u) => u.role !== "admin"));
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load users");
		} finally {
			setLoading(false);
		}
	};

	const handleDeleteUser = async () => {
		if (!selectedUser || !token) return;

		setActionLoading(true);
		try {
			await apiFetchJson(
				`/admin/users/${selectedUser.id}`,
				{
					method: "DELETE",
					headers: { Authorization: `Bearer ${token}` },
				},
				() => logout(),
			);
			setDeleteModalOpen(false);
			setSelectedUser(null);
			loadUsers();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to delete user");
		} finally {
			setActionLoading(false);
		}
	};

	const handlePromoteUser = async () => {
		if (!selectedUser || !token) return;

		setActionLoading(true);
		try {
			await apiFetchJson(
				`/admin/users/${selectedUser.id}`,
				{
					method: "PATCH",
					headers: {
						Authorization: `Bearer ${token}`,
						"Content-Type": "application/json",
					},
					body: JSON.stringify({ role: "admin" }),
				},
				() => logout(),
			);
			setPromoteModalOpen(false);
			setSelectedUser(null);
			loadUsers();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to promote user");
		} finally {
			setActionLoading(false);
		}
	};

	const handleVerifyUser = async () => {
		if (!selectedUser || !token) return;

		setActionLoading(true);
		try {
			await apiFetchJson(
				`/admin/users/${selectedUser.id}`,
				{
					method: "PATCH",
					headers: {
						Authorization: `Bearer ${token}`,
						"Content-Type": "application/json",
					},
					body: JSON.stringify({ email_verified: true }),
				},
				() => logout(),
			);
			setVerifyModalOpen(false);
			setSelectedUser(null);
			loadUsers();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to verify user");
		} finally {
			setActionLoading(false);
		}
	};

	if (loading && users.length === 0) {
		return (
			<div>
				<h2>User Management</h2>
				<p>Loading users...</p>
			</div>
		);
	}

	return (
		<div>
			<h2>User Management</h2>

			{error && <ErrorBanner message={error} onClose={() => setError(null)} />}

			<div className="admin-search-bar">
				<input
					type="text"
					placeholder="Search users by email..."
					value={search}
					onChange={(e) => {
						setSearch(e.target.value);
						setPage(1);
					}}
					className="search-input"
				/>
			</div>

			<div className="admin-table-container">
				<table className="admin-table">
					<thead>
						<tr>
							<th>Email</th>
							<th>Account</th>
							<th>Projects</th>
							<th>Verified</th>
							<th>Created</th>
							<th>Actions</th>
						</tr>
					</thead>
					<tbody>
						{users.length === 0 ? (
							<tr>
								<td colSpan={6} style={{ textAlign: "center" }}>
									No users found
								</td>
							</tr>
						) : (
							users.map((user) => (
								<tr key={user.id}>
									<td>{user.email}</td>
									<td>{user.account_name}</td>
									<td>{user.projects_count ?? "-"}</td>
									<td>
										<span
											className={
												user.email_verified
													? "status-active"
													: "status-inactive"
											}
										>
											{user.email_verified ? "Yes" : "No"}
										</span>
									</td>
									<td>{new Date(user.created_at).toLocaleDateString()}</td>
									<td>
										<div className="action-buttons">
											{!user.email_verified && (
												<button
													className="action-btn action-btn-verify"
													onClick={() => {
														setSelectedUser(user);
														setVerifyModalOpen(true);
													}}
													title="Verify email"
												>
													Verify
												</button>
											)}
											<button
												className="action-btn action-btn-promote"
												onClick={() => {
													setSelectedUser(user);
													setPromoteModalOpen(true);
												}}
												title="Promote to admin"
											>
												Promote
											</button>
											<button
												className="action-btn action-btn-delete"
												onClick={() => {
													setSelectedUser(user);
													setDeleteModalOpen(true);
												}}
												title="Delete user"
											>
												Delete
											</button>
										</div>
									</td>
								</tr>
							))
						)}
					</tbody>
				</table>
			</div>

			<div className="pagination">
				<button
					onClick={() => setPage(Math.max(1, page - 1))}
					disabled={page === 1}
					className="pagination-btn"
				>
					Previous
				</button>
				<span className="pagination-info">Page {page}</span>
				<button
					onClick={() => setPage(page + 1)}
					disabled={users.length < 20}
					className="pagination-btn"
				>
					Next
				</button>
			</div>

			{/* Delete Confirmation Modal */}
			<ConfirmationModal
				isOpen={deleteModalOpen}
				title="Delete User"
				message={`Are you sure you want to delete ${selectedUser?.email}? This action cannot be undone.`}
				confirmLabel="Delete"
				confirmVariant="danger"
				onConfirm={handleDeleteUser}
				onCancel={() => {
					setDeleteModalOpen(false);
					setSelectedUser(null);
				}}
				loading={actionLoading}
			/>

			{/* Promote Confirmation Modal */}
			<ConfirmationModal
				isOpen={promoteModalOpen}
				title="Promote to Admin"
				message={`Are you sure you want to promote ${selectedUser?.email} to admin? They will have full administrative access.`}
				confirmLabel="Promote"
				confirmVariant="primary"
				onConfirm={handlePromoteUser}
				onCancel={() => {
					setPromoteModalOpen(false);
					setSelectedUser(null);
				}}
				loading={actionLoading}
			/>

			{/* Verify Email Confirmation Modal */}
			<ConfirmationModal
				isOpen={verifyModalOpen}
				title="Verify Email"
				message={`Are you sure you want to manually verify the email for ${selectedUser?.email}?`}
				confirmLabel="Verify"
				confirmVariant="primary"
				onConfirm={handleVerifyUser}
				onCancel={() => {
					setVerifyModalOpen(false);
					setSelectedUser(null);
				}}
				loading={actionLoading}
			/>
		</div>
	);
}

interface AdminProject {
	id: string;
	name: string;
	account_id: string;
	api_key: string;
	postgres_url: string;
	mongodb_url: string;
	created_at: string;
	is_active: boolean;
}

function AdminProjects() {
	const { token, logout } = useAuth();
	const [projects, setProjects] = useState<AdminProject[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [search, setSearch] = useState("");

	// Modal states
	const [deleteModalOpen, setDeleteModalOpen] = useState(false);
	const [toggleStatusModalOpen, setToggleStatusModalOpen] = useState(false);
	const [selectedProject, setSelectedProject] = useState<AdminProject | null>(null);
	const [actionLoading, setActionLoading] = useState(false);

	useEffect(() => {
		loadProjects();
	}, []);

	const loadProjects = async () => {
		if (!token) return;

		try {
			setLoading(true);
			const data = await apiFetchJson<AdminProject[]>(
				"/admin/projects",
				{ headers: { Authorization: `Bearer ${token}` } },
				() => logout(),
			);

			setProjects(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load projects");
		} finally {
			setLoading(false);
		}
	};

	const handleDeleteProject = async () => {
		if (!selectedProject || !token) return;

		setActionLoading(true);
		try {
			await apiFetchJson(
				`/admin/projects/${selectedProject.id}`,
				{
					method: "DELETE",
					headers: { Authorization: `Bearer ${token}` },
				},
				() => logout(),
			);
			setDeleteModalOpen(false);
			setSelectedProject(null);
			loadProjects();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to delete project");
		} finally {
			setActionLoading(false);
		}
	};

	const handleToggleStatus = async () => {
		if (!selectedProject || !token) return;

		const action = selectedProject.is_active ? "deactivate" : "activate";

		setActionLoading(true);
		try {
			await apiFetchJson(
				`/admin/projects/${selectedProject.id}/${action}`,
				{
					method: "PATCH",
					headers: { Authorization: `Bearer ${token}` },
				},
				() => logout(),
			);
			setToggleStatusModalOpen(false);
			setSelectedProject(null);
			loadProjects();
		} catch (err) {
			setError(err instanceof Error ? err.message : `Failed to ${action} project`);
		} finally {
			setActionLoading(false);
		}
	};

	// Filter projects by search term
	const filteredProjects = projects.filter(
		(p) =>
			p.name.toLowerCase().includes(search.toLowerCase()) ||
			p.account_id.toLowerCase().includes(search.toLowerCase()),
	);

	if (loading && projects.length === 0) {
		return (
			<div>
				<h2>Project Management</h2>
				<p>Loading projects...</p>
			</div>
		);
	}

	return (
		<div>
			<h2>Project Management</h2>

			{error && <ErrorBanner message={error} onClose={() => setError(null)} />}

			<div className="admin-search-bar">
				<input
					type="text"
					placeholder="Search by name or account ID..."
					value={search}
					onChange={(e) => setSearch(e.target.value)}
					className="search-input"
				/>
			</div>

			<div className="admin-table-container">
				<table className="admin-table">
					<thead>
						<tr>
							<th>Name</th>
							<th>Account ID</th>
							<th>PostgreSQL</th>
							<th>MongoDB</th>
							<th>Status</th>
							<th>Created</th>
							<th>Actions</th>
						</tr>
					</thead>
					<tbody>
						{filteredProjects.length === 0 ? (
							<tr>
								<td colSpan={7} style={{ textAlign: "center" }}>
									No projects found
								</td>
							</tr>
						) : (
							filteredProjects.map((project) => (
								<tr key={project.id}>
									<td>{project.name}</td>
									<td>
										<code>{project.account_id}</code>
									</td>
									<td>
										<span
											className={
												project.postgres_url && project.postgres_url !== "***"
													? "status-active"
													: "status-inactive"
											}
										>
											{project.postgres_url && project.postgres_url !== "***"
												? "Configured"
												: "Not set"}
										</span>
									</td>
									<td>
										<span
											className={
												project.mongodb_url && project.mongodb_url !== "***"
													? "status-active"
													: "status-inactive"
											}
										>
											{project.mongodb_url && project.mongodb_url !== "***"
												? "Configured"
												: "Not set"}
										</span>
									</td>
									<td>
										<span
											className={
												project.is_active ? "status-active" : "status-inactive"
											}
										>
											{project.is_active ? "Active" : "Inactive"}
										</span>
									</td>
									<td>{new Date(project.created_at).toLocaleDateString()}</td>
									<td>
										<div className="action-buttons">
											<button
												className={`action-btn ${project.is_active ? "action-btn-demote" : "action-btn-verify"}`}
												onClick={() => {
													setSelectedProject(project);
													setToggleStatusModalOpen(true);
												}}
												title={project.is_active ? "Deactivate" : "Activate"}
											>
												{project.is_active ? "Deactivate" : "Activate"}
											</button>
											<button
												className="action-btn action-btn-delete"
												onClick={() => {
													setSelectedProject(project);
													setDeleteModalOpen(true);
												}}
												title="Delete project"
											>
												Delete
											</button>
										</div>
									</td>
								</tr>
							))
						)}
					</tbody>
				</table>
			</div>

			{/* Delete Confirmation Modal */}
			<ConfirmationModal
				isOpen={deleteModalOpen}
				title="Delete Project"
				message={`Are you sure you want to delete "${selectedProject?.name}"? This action cannot be undone and will remove all associated data.`}
				confirmLabel="Delete"
				confirmVariant="danger"
				onConfirm={handleDeleteProject}
				onCancel={() => {
					setDeleteModalOpen(false);
					setSelectedProject(null);
				}}
				loading={actionLoading}
			/>

			{/* Toggle Status Confirmation Modal */}
			<ConfirmationModal
				isOpen={toggleStatusModalOpen}
				title={selectedProject?.is_active ? "Deactivate Project" : "Activate Project"}
				message={
					selectedProject?.is_active
						? `Are you sure you want to deactivate "${selectedProject?.name}"? Users will not be able to use this project until it's reactivated.`
						: `Are you sure you want to activate "${selectedProject?.name}"?`
				}
				confirmLabel={selectedProject?.is_active ? "Deactivate" : "Activate"}
				confirmVariant={selectedProject?.is_active ? "danger" : "primary"}
				onConfirm={handleToggleStatus}
				onCancel={() => {
					setToggleStatusModalOpen(false);
					setSelectedProject(null);
				}}
				loading={actionLoading}
			/>
		</div>
	);
}

function AdminAdmins() {
	const { token, logout, user: currentUser } = useAuth();
	const [admins, setAdmins] = useState<AdminUser[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	// Modal states
	const [demoteModalOpen, setDemoteModalOpen] = useState(false);
	const [selectedAdmin, setSelectedAdmin] = useState<AdminUser | null>(null);
	const [actionLoading, setActionLoading] = useState(false);

	useEffect(() => {
		loadAdmins();
	}, []);

	const loadAdmins = async () => {
		if (!token) return;

		try {
			setLoading(true);
			const params = new URLSearchParams({ page: "1", limit: "100" });
			const data = await apiFetchJson<AdminUser[]>(
				`/admin/users?${params}`,
				{ headers: { Authorization: `Bearer ${token}` } },
				() => logout(),
			);

			setAdmins(data.filter((u) => u.role === "admin"));
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load admins");
		} finally {
			setLoading(false);
		}
	};

	const handleDemoteAdmin = async () => {
		if (!selectedAdmin || !token) return;

		setActionLoading(true);
		try {
			await apiFetchJson(
				`/admin/users/${selectedAdmin.id}`,
				{
					method: "PATCH",
					headers: {
						Authorization: `Bearer ${token}`,
						"Content-Type": "application/json",
					},
					body: JSON.stringify({ role: "user" }),
				},
				() => logout(),
			);
			setDemoteModalOpen(false);
			setSelectedAdmin(null);
			loadAdmins();
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to demote admin");
		} finally {
			setActionLoading(false);
		}
	};

	if (loading && admins.length === 0) {
		return (
			<div>
				<h2>Admin Accounts</h2>
				<p>Loading admins...</p>
			</div>
		);
	}

	return (
		<div>
			<h2>Admin Accounts</h2>

			{error && <ErrorBanner message={error} onClose={() => setError(null)} />}

			<div className="admin-table-container">
				<table className="admin-table">
					<thead>
						<tr>
							<th>Email</th>
							<th>Account</th>
							<th>Role</th>
							<th>Verified</th>
							<th>Created</th>
							<th>Actions</th>
						</tr>
					</thead>
					<tbody>
						{admins.length === 0 ? (
							<tr>
								<td colSpan={6} style={{ textAlign: "center" }}>
									No admins found
								</td>
							</tr>
						) : (
							admins.map((admin) => (
								<tr key={admin.id}>
									<td>
										{admin.email}
										{currentUser?.email === admin.email && (
											<span className="current-user-badge"> (You)</span>
										)}
									</td>
									<td>{admin.account_name}</td>
									<td>
										<span className={`badge badge-${admin.role}`}>
											{admin.role}
										</span>
									</td>
									<td>
										<span
											className={
												admin.email_verified
													? "status-active"
													: "status-inactive"
											}
										>
											{admin.email_verified ? "Yes" : "No"}
										</span>
									</td>
									<td>{new Date(admin.created_at).toLocaleDateString()}</td>
									<td>
										<div className="action-buttons">
											{currentUser?.email !== admin.email && (
												<button
													className="action-btn action-btn-demote"
													onClick={() => {
														setSelectedAdmin(admin);
														setDemoteModalOpen(true);
													}}
													title="Demote to regular user"
												>
													Demote
												</button>
											)}
											{currentUser?.email === admin.email && (
												<span className="no-actions">-</span>
											)}
										</div>
									</td>
								</tr>
							))
						)}
					</tbody>
				</table>
			</div>

			{/* Demote Confirmation Modal */}
			<ConfirmationModal
				isOpen={demoteModalOpen}
				title="Demote Admin"
				message={`Are you sure you want to demote ${selectedAdmin?.email} to a regular user? They will lose all administrative access.`}
				confirmLabel="Demote"
				confirmVariant="danger"
				onConfirm={handleDemoteAdmin}
				onCancel={() => {
					setDemoteModalOpen(false);
					setSelectedAdmin(null);
				}}
				loading={actionLoading}
			/>
		</div>
	);
}

interface UsageDataPoint {
	date: string;
	queries: number;
	execution_time_ms: number;
}

interface UsageAnalytics {
	total_queries: number;
	total_execution_time_ms: number;
	total_tokens: number;
	daily_usage: UsageDataPoint[];
	queries_by_type: { postgres: number; mongodb: number };
}

function AdminAnalytics() {
	const { token, logout } = useAuth();
	const [analytics, setAnalytics] = useState<UsageAnalytics | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		loadAnalytics();
	}, []);

	const loadAnalytics = async () => {
		if (!token) return;

		try {
			setLoading(true);
			const data = await apiFetchJson<UsageAnalytics>(
				"/admin/analytics/usage",
				{ headers: { Authorization: `Bearer ${token}` } },
				() => logout(),
			);
			setAnalytics(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load analytics");
		} finally {
			setLoading(false);
		}
	};

	if (loading) {
		return (
			<div>
				<h2>Usage Analytics</h2>
				<p>Loading analytics...</p>
			</div>
		);
	}

	if (error) {
		return (
			<div>
				<h2>Usage Analytics</h2>
				<ErrorBanner message={error} onClose={() => setError(null)} />
			</div>
		);
	}

	const avgExecutionTime =
		analytics && analytics.total_queries > 0
			? (analytics.total_execution_time_ms / analytics.total_queries).toFixed(2)
			: "0";

	// Prepare data for query type bar chart
	const queryTypeData = analytics
		? [
				{ name: "PostgreSQL", value: analytics.queries_by_type.postgres },
				{ name: "MongoDB", value: analytics.queries_by_type.mongodb },
			]
		: [];

	const COLORS = ["#6a9d3a", "#3a6a9d"];

	// Format date for chart display (show only day/month)
	const formatDate = (dateStr: string) => {
		const date = new Date(dateStr);
		return `${date.getMonth() + 1}/${date.getDate()}`;
	};

	return (
		<div>
			<h2>Usage Analytics</h2>

			{/* Summary Cards */}
			<div className="stats-grid">
				<div className="stat-card">
					<h3>Total Queries</h3>
					<p className="stat-value">{analytics?.total_queries || 0}</p>
					<p className="stat-subtitle">Last 30 days</p>
				</div>
				<div className="stat-card">
					<h3>Avg Execution Time</h3>
					<p className="stat-value">{avgExecutionTime} ms</p>
					<p className="stat-subtitle">Per query</p>
				</div>
				<div className="stat-card">
					<h3>Total Tokens</h3>
					<p className="stat-value">{analytics?.total_tokens || 0}</p>
					<p className="stat-subtitle">AI tokens used</p>
				</div>
			</div>

			{/* Queries Over Time Chart */}
			<div className="chart-container">
				<h3>Queries Over Time</h3>
				{analytics && analytics.daily_usage.length > 0 ? (
					<ResponsiveContainer width="100%" height={300}>
						<LineChart data={analytics.daily_usage}>
							<CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
							<XAxis
								dataKey="date"
								tickFormatter={formatDate}
								stroke="#666"
								fontSize={12}
							/>
							<YAxis stroke="#666" fontSize={12} />
							<Tooltip
								labelFormatter={(label) => `Date: ${label}`}
								formatter={(value) => [value, "Queries"]}
								contentStyle={{
									backgroundColor: "#fff",
									border: "1px solid #ddd",
									borderRadius: "4px",
								}}
							/>
							<Line
								type="monotone"
								dataKey="queries"
								stroke="#6a9d3a"
								strokeWidth={2}
								dot={{ fill: "#6a9d3a", strokeWidth: 2, r: 3 }}
								activeDot={{ r: 5 }}
							/>
						</LineChart>
					</ResponsiveContainer>
				) : (
					<p className="no-data-message">No query data available</p>
				)}
			</div>

			{/* Query Distribution by Type */}
			<div className="chart-container">
				<h3>Query Distribution by Database Type</h3>
				{queryTypeData.some((d) => d.value > 0) ? (
					<ResponsiveContainer width="100%" height={200}>
						<BarChart data={queryTypeData} layout="vertical">
							<CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
							<XAxis type="number" stroke="#666" fontSize={12} />
							<YAxis
								dataKey="name"
								type="category"
								stroke="#666"
								fontSize={12}
								width={80}
							/>
							<Tooltip
								formatter={(value) => [value, "Queries"]}
								contentStyle={{
									backgroundColor: "#fff",
									border: "1px solid #ddd",
									borderRadius: "4px",
								}}
							/>
							<Bar dataKey="value" radius={[0, 4, 4, 0]}>
								{queryTypeData.map((_, index) => (
									<Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
								))}
							</Bar>
						</BarChart>
					</ResponsiveContainer>
				) : (
					<p className="no-data-message">No query data available</p>
				)}
			</div>
		</div>
	);
}

interface HealthStatus {
	account_id: string;
	account_name: string;
	postgres_status: string;
	mongodb_status: string;
	last_checked: string;
}

function AdminHealth() {
	const { token, logout } = useAuth();
	const [healthData, setHealthData] = useState<HealthStatus[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [refreshing, setRefreshing] = useState(false);

	useEffect(() => {
		loadHealth();
	}, []);

	const loadHealth = async (isRefresh = false) => {
		if (!token) return;

		try {
			if (isRefresh) {
				setRefreshing(true);
			} else {
				setLoading(true);
			}

			const data = await apiFetchJson<HealthStatus[]>(
				"/admin/analytics/health",
				{ headers: { Authorization: `Bearer ${token}` } },
				() => logout(),
			);
			setHealthData(data);
			setError(null);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load health data");
		} finally {
			setLoading(false);
			setRefreshing(false);
		}
	};

	const getStatusBadge = (status: string) => {
		const statusClasses: Record<string, string> = {
			healthy: "status-healthy",
			unhealthy: "status-unhealthy",
			not_configured: "status-not-configured",
			no_projects: "status-not-configured",
			unknown: "status-unknown",
		};

		const statusLabels: Record<string, string> = {
			healthy: "Healthy",
			unhealthy: "Unhealthy",
			not_configured: "Not Configured",
			no_projects: "No Projects",
			unknown: "Unknown",
		};

		return (
			<span className={`health-badge ${statusClasses[status] || "status-unknown"}`}>
				{statusLabels[status] || status}
			</span>
		);
	};

	if (loading) {
		return (
			<div>
				<h2>Database Health</h2>
				<p>Checking database connections...</p>
			</div>
		);
	}

	if (error) {
		return (
			<div>
				<h2>Database Health</h2>
				<ErrorBanner message={error} onClose={() => setError(null)} />
			</div>
		);
	}

	return (
		<div>
			<div className="health-header">
				<h2>Database Health</h2>
				<button
					onClick={() => loadHealth(true)}
					disabled={refreshing}
					className="refresh-btn"
				>
					{refreshing ? "Checking..." : "Refresh"}
				</button>
			</div>

			<div className="admin-table-container">
				<table className="admin-table">
					<thead>
						<tr>
							<th>Account</th>
							<th>PostgreSQL</th>
							<th>MongoDB</th>
							<th>Last Checked</th>
						</tr>
					</thead>
					<tbody>
						{healthData.length === 0 ? (
							<tr>
								<td colSpan={4} style={{ textAlign: "center" }}>
									No accounts found
								</td>
							</tr>
						) : (
							healthData.map((health) => (
								<tr key={health.account_id}>
									<td>
										<strong>{health.account_name}</strong>
										<br />
										<code className="account-id">{health.account_id}</code>
									</td>
									<td>{getStatusBadge(health.postgres_status)}</td>
									<td>{getStatusBadge(health.mongodb_status)}</td>
									<td>
										{new Date(health.last_checked).toLocaleString()}
									</td>
								</tr>
							))
						)}
					</tbody>
				</table>
			</div>

			<div className="health-legend">
				<h4>Status Legend</h4>
				<div className="legend-items">
					<span className="health-badge status-healthy">Healthy</span>
					<span>Connection successful</span>
					<span className="health-badge status-unhealthy">Unhealthy</span>
					<span>Connection failed</span>
					<span className="health-badge status-not-configured">Not Configured</span>
					<span>Database URL not set</span>
				</div>
			</div>
		</div>
	);
}

export default function AdminDashboard() {
	const { user, logout } = useAuth();
	const navigate = useNavigate();

	const handleLogout = () => {
		logout();
		navigate("/admin/login");
	};

	return (
		<div className="admin-dashboard">
			<aside className="admin-sidebar">
				<div className="admin-sidebar-header">
					<Link to="/">
						<img
							src="/assets/logo-horizontal.svg"
							alt="DBRevel Admin"
							className="admin-logo"
							width="120"
						/>
					</Link>
					<h3>Admin Panel</h3>
					<p className="admin-user">{user?.email}</p>
				</div>

				<nav className="admin-nav">
					<Link to="/admin" className="admin-nav-item">
						Dashboard
					</Link>
					<Link to="/admin/admins" className="admin-nav-item">
						Admins
					</Link>
					<Link to="/admin/users" className="admin-nav-item">
						Users
					</Link>
					<Link to="/admin/projects" className="admin-nav-item">
						Projects
					</Link>
					<Link to="/admin/analytics" className="admin-nav-item">
						Analytics
					</Link>
					<Link to="/admin/health" className="admin-nav-item">
						Health
					</Link>
				</nav>

				<div className="admin-sidebar-footer">
					<button onClick={handleLogout} className="admin-logout-btn">
						Logout
					</button>
				</div>
			</aside>

			<main className="admin-content">
				<Routes>
					<Route path="/" element={<AdminOverview />} />
					<Route path="/users" element={<AdminUsers />} />
					<Route path="/admins" element={<AdminAdmins />} />
					<Route path="/projects" element={<AdminProjects />} />
					<Route path="/analytics" element={<AdminAnalytics />} />
					<Route path="/health" element={<AdminHealth />} />
				</Routes>
			</main>
		</div>
	);
}
