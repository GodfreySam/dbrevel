import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function Header() {
	const { isAuthenticated, logout } = useAuth();
	const location = useLocation();

	const [isDashboard, setIsDashboard] = useState<boolean>(false);

	const checkIfDashboard = useCallback(() => {
		const dashboardPaths = ["/dashboard"];
		const isDash = dashboardPaths.some((path) =>
			location.pathname.startsWith(path),
		);
		setIsDashboard(isDash);
	}, [location.pathname]);

	useEffect(() => {
		checkIfDashboard();
	}, [checkIfDashboard]);

	return (
		<header className="site-header">
			<div className="container">
				<div className="header-content">
					{isDashboard ? (
						<>
							<div className="dashboard-title">
								<Link to="/">
									<img
										src="/assets/logo-horizontal.svg"
										alt="DBRevel - AI-Powered Database SDK Logo"
										title="DBRevel - Convert natural language to database queries"
										className="site-logo"
										width="180"
										height="54"
										loading="eager"
									/>
								</Link>
							</div>
							<button onClick={logout} className="logout-btn">
								Logout
							</button>
						</>
					) : (
						<>
							<Link to="/">
								<img
									src="/assets/logo-horizontal.svg"
									alt="DBRevel - AI-Powered Database SDK Logo"
									title="DBRevel - Convert natural language to database queries"
									className="site-logo"
									width="180"
									height="54"
									loading="eager"
								/>
							</Link>
							<nav className="header-nav">
								<Link to="/docs" className="nav-link">
									Documentation
								</Link>
								{isAuthenticated ? (
									<>
										<Link to="/dashboard" className="nav-link">
											Dashboard
										</Link>
										<button
											onClick={logout}
											className="nav-link"
											style={{
												background: "none",
												border: "none",
												cursor: "pointer",
												fontSize: "inherit",
												fontFamily: "inherit",
												color: "inherit",
												padding: 0,
											}}
										>
											Logout
										</button>
									</>
								) : (
									<>
										<Link to="/signup" className="nav-link">
											Sign Up
										</Link>
										<Link to="/login" className="nav-link">
											Login
										</Link>
									</>
								)}
							</nav>
						</>
					)}
				</div>
			</div>
		</header>
	);
}
