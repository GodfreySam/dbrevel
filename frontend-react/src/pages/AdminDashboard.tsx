import { useEffect, useState } from "react";
import { Link, Route, Routes, useNavigate } from "react-router-dom";
import { config } from "../config";
import { useAuth } from "../contexts/AuthContext";
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
			const response = await fetch(`${config.apiUrl}/admin/analytics/stats`, {
				headers: {
					Authorization: `Bearer ${token}`,
				},
			});

			if (!response.ok) {
				if (response.status === 401 || response.status === 403) {
					logout();
					return;
				}
				throw new Error("Failed to load stats");
			}

			const data = await response.json();
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
				<div className="error-message">{error}</div>
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

interface Tenant {
	id: string;
	name: string;
	api_key: string;
	postgres_url: string;
	mongodb_url: string;
	gemini_mode: string;
}

function AdminTenants() {
	const { token, logout } = useAuth();
	const [tenants, setTenants] = useState<Tenant[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [search, setSearch] = useState("");
	const [page, setPage] = useState(1);

	useEffect(() => {
		loadTenants();
	}, [page, search]);

	const loadTenants = async () => {
		if (!token) return;

		try {
			const params = new URLSearchParams({
				page: page.toString(),
				limit: "20",
			});
			if (search) params.append("search", search);

			const response = await fetch(`${config.apiUrl}/admin/tenants?${params}`, {
				headers: {
					Authorization: `Bearer ${token}`,
				},
			});

			if (!response.ok) {
				if (response.status === 401 || response.status === 403) {
					logout();
					return;
				}
				throw new Error("Failed to load tenants");
			}

			const data = await response.json();
			setTenants(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load tenants");
		} finally {
			setLoading(false);
		}
	};

	if (loading) {
		return (
			<div>
				<h2>Tenant Management</h2>
				<p>Loading tenants...</p>
			</div>
		);
	}

	if (error) {
		return (
			<div>
				<h2>Tenant Management</h2>
				<div className="error-message">{error}</div>
			</div>
		);
	}

	return (
		<div>
			<h2>Tenant Management</h2>
			<div className="admin-search-bar">
				<input
					type="text"
					placeholder="Search tenants by name..."
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
							<th>ID</th>
							<th>Name</th>
							<th>API Key</th>
							<th>PostgreSQL</th>
							<th>MongoDB</th>
							<th>Gemini Mode</th>
						</tr>
					</thead>
					<tbody>
						{tenants.length === 0 ? (
							<tr>
								<td colSpan={6} style={{ textAlign: "center" }}>
									No tenants found
								</td>
							</tr>
						) : (
							tenants.map((tenant) => (
								<tr key={tenant.id}>
									<td>
										<code>{tenant.id}</code>
									</td>
									<td>{tenant.name}</td>
									<td>
										<code style={{ fontSize: "11px" }}>
											{tenant.api_key.substring(0, 20)}...
										</code>
									</td>
									<td>
										<span
											className={
												tenant.postgres_url
													? "status-active"
													: "status-inactive"
											}
										>
											{tenant.postgres_url ? "Configured" : "Not set"}
										</span>
									</td>
									<td>
										<span
											className={
												tenant.mongodb_url ? "status-active" : "status-inactive"
											}
										>
											{tenant.mongodb_url ? "Configured" : "Not set"}
										</span>
									</td>
									<td>
										<span className="badge">{tenant.gemini_mode}</span>
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
					disabled={tenants.length < 20}
					className="pagination-btn"
				>
					Next
				</button>
			</div>
		</div>
	);
}

interface AdminUser {
	id: string;
	email: string;
	account_id: string;
	account_name: string;
	email_verified: boolean;
	role: string;
	created_at: string;
}

function AdminUsers() {
	const { token, logout } = useAuth();
	const [users, setUsers] = useState<AdminUser[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [search, setSearch] = useState("");
	const [page, setPage] = useState(1);

	useEffect(() => {
		loadUsers();
	}, [page, search]);

	const loadUsers = async () => {
		if (!token) return;

		try {
			const params = new URLSearchParams({
				page: page.toString(),
				limit: "20",
			});
			if (search) params.append("search", search);

			const response = await fetch(`${config.apiUrl}/admin/users?${params}`, {
				headers: {
					Authorization: `Bearer ${token}`,
				},
			});

			if (!response.ok) {
				if (response.status === 401 || response.status === 403) {
					logout();
					return;
				}
				throw new Error("Failed to load users");
			}

			const data = await response.json();
			setUsers(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load users");
		} finally {
			setLoading(false);
		}
	};

	if (loading) {
		return (
			<div>
				<h2>User Management</h2>
				<p>Loading users...</p>
			</div>
		);
	}

	if (error) {
		return (
			<div>
				<h2>User Management</h2>
				<div className="error-message">{error}</div>
			</div>
		);
	}

	return (
		<div>
			<h2>User Management</h2>
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
							<th>Tenant</th>
							<th>Role</th>
							<th>Verified</th>
							<th>Created</th>
						</tr>
					</thead>
					<tbody>
						{users.length === 0 ? (
							<tr>
								<td colSpan={5} style={{ textAlign: "center" }}>
									No users found
								</td>
							</tr>
						) : (
							users.map((user) => (
								<tr key={user.id}>
									<td>{user.email}</td>
									<td>{user.account_name}</td>
									<td>
										<span className={`badge badge-${user.role}`}>
											{user.role}
										</span>
									</td>
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
	const [page] = useState(1);

	useEffect(() => {
		loadProjects();
	}, [page]);

	const loadProjects = async () => {
		if (!token) return;

		try {
			const response = await fetch(`${config.apiUrl}/admin/projects`, {
				headers: {
					Authorization: `Bearer ${token}`,
				},
			});

			if (!response.ok) {
				if (response.status === 401 || response.status === 403) {
					logout();
					return;
				}
				throw new Error("Failed to load projects");
			}

			const data = await response.json();
			setProjects(data);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load projects");
		} finally {
			setLoading(false);
		}
	};

	if (loading) {
		return (
			<div>
				<h2>Project Management</h2>
				<p>Loading projects...</p>
			</div>
		);
	}

	if (error) {
		return (
			<div>
				<h2>Project Management</h2>
				<div className="error-message">{error}</div>
			</div>
		);
	}

	return (
		<div>
			<h2>Project Management</h2>

			<div className="admin-table-container">
				<table className="admin-table">
					<thead>
						<tr>
							<th>Name</th>
							<th>Tenant ID</th>
							<th>PostgreSQL</th>
							<th>MongoDB</th>
							<th>Status</th>
							<th>Created</th>
						</tr>
					</thead>
					<tbody>
						{projects.length === 0 ? (
							<tr>
								<td colSpan={6} style={{ textAlign: "center" }}>
									No projects found
								</td>
							</tr>
						) : (
							projects.map((project) => (
								<tr key={project.id}>
									<td>{project.name}</td>
									<td>
										<code>{project.account_id}</code>
									</td>
									<td>
										<span
											className={
												project.postgres_url
													? "status-active"
													: "status-inactive"
											}
										>
											{project.postgres_url ? "Configured" : "Not set"}
										</span>
									</td>
									<td>
										<span
											className={
												project.mongodb_url
													? "status-active"
													: "status-inactive"
											}
										>
											{project.mongodb_url ? "Configured" : "Not set"}
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
								</tr>
							))
						)}
					</tbody>
				</table>
			</div>
		</div>
	);
}

function AdminAnalytics() {
	return (
		<div>
			<h2>Usage Analytics</h2>
			<p className="placeholder-message">Charts and analytics coming soon.</p>
		</div>
	);
}

function AdminHealth() {
	return (
		<div>
			<h2>Database Health</h2>
			<p className="placeholder-message">
				Connection health monitoring coming soon.
			</p>
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
					<Link to="/admin/tenants" className="admin-nav-item">
						Tenants
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
					<Route path="/tenants" element={<AdminTenants />} />
					<Route path="/users" element={<AdminUsers />} />
					<Route path="/projects" element={<AdminProjects />} />
					<Route path="/analytics" element={<AdminAnalytics />} />
					<Route path="/health" element={<AdminHealth />} />
				</Routes>
			</main>
		</div>
	);
}
