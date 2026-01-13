import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import "./Signup.css";

export default function Signup() {
	const navigate = useNavigate();
	const { register } = useAuth();
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const [formData, setFormData] = useState({
		email: "",
		password: "",
		name: "",
	});
	const [showPassword, setShowPassword] = useState(false);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);

		// Validation
		if (formData.password.length < 8) {
			setError("Password must be at least 8 characters");
			return;
		}

		if (!formData.name.trim()) {
			setError("Tenant name is required");
			return;
		}

		setLoading(true);
		try {
			const registeredEmail = await register(
				formData.email,
				formData.password,
				formData.name,
			);
			// Navigate to verify email page after successful registration
			navigate(`/verify-email?email=${encodeURIComponent(registeredEmail)}`);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Registration failed");
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className="signup-page">
			<div className="signup-container">
				<div className="signup-header">
					<Link to="/">
						<img
							src="/assets/logo-horizontal.svg"
							alt="DBRevel - AI-Powered Database SDK"
							title="DBRevel Sign Up"
							className="signup-logo"
							width="160"
							height="48"
							loading="eager"
						/>
					</Link>
					<h1>Create Your DBRevel Account</h1>
					<p className="signup-subtitle">
						Start querying your databases with natural language
					</p>
				</div>

				<div className="signup-info">
					<h3>What is DbRevel?</h3>
					<p>
						DbRevel converts natural language into secure, optimized database
						queries. No SQL knowledge needed—just describe what you want in
						plain English.
					</p>
					<ul>
						<li>Connect your PostgreSQL and/or MongoDB databases</li>
						<li>
							Query using natural language (e.g., "Get all users from Lagos")
						</li>
						<li>Get secure, optimized queries automatically</li>
						<li>
							Integrate the SDK or API directly into your codebase for seamless
							database queries
						</li>
					</ul>
					<p className="info-note">
						<strong>Note:</strong> After creating your account and verifying
						your email, you can add database connections in your dashboard.
						We'll generate a secure API key for you upon registration.
					</p>
				</div>

				<form onSubmit={handleSubmit} className="signup-form">
					{error && <div className="error-message">{error}</div>}

					<div className="form-group">
						<label htmlFor="email">Email Address *</label>
						<input
							type="email"
							id="email"
							required
							value={formData.email}
							onChange={(e) =>
								setFormData({ ...formData, email: e.target.value })
							}
							placeholder="you@example.com"
						/>
					</div>

					<div className="form-group">
						<label htmlFor="password">Password *</label>
						<div className="password-input-container">
							<input
								type={showPassword ? "text" : "password"}
								id="password"
								required
								minLength={8}
								value={formData.password}
								onChange={(e) =>
									setFormData({ ...formData, password: e.target.value })
								}
								placeholder="At least 8 characters"
								className="password-input"
							/>
							<button
								type="button"
								onClick={() => setShowPassword(!showPassword)}
								className="password-toggle-btn"
								aria-label={showPassword ? "Hide password" : "Show password"}
							>
								{showPassword ? (
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
						<label htmlFor="name">Organization/Tenant Name *</label>
						<input
							type="text"
							id="name"
							required
							value={formData.name}
							onChange={(e) =>
								setFormData({ ...formData, name: e.target.value })
							}
							placeholder="Acme Corp"
						/>
					</div>

					<button type="submit" disabled={loading} className="submit-btn">
						{loading ? "Creating Account..." : "Create Account"}
					</button>

					<p className="login-link">
						Already have an account? <Link to="/login">Log in</Link>
					</p>
				</form>
			</div>
		</div>
	);
}
