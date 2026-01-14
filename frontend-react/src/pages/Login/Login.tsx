import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./Login.css";
import { useAuth } from "../../contexts/AuthContext";

export default function Login() {
	const navigate = useNavigate();
	const { login } = useAuth();
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [showPassword, setShowPassword] = useState(false);

	const [formData, setFormData] = useState({
		email: "",
		password: "",
	});

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setLoading(true);

		try {
			await login(formData.email, formData.password);
			navigate("/dashboard");
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : "Login failed";
			// Check if error is due to unverified email
			if (errorMessage === "EMAIL_NOT_VERIFIED") {
				setError(
					"Email not verified. Please check your email and verify your account before logging in.",
				);
			} else {
				setError(errorMessage);
			}
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className="login-page">
			<div className="login-container">
				<div className="login-header">
					<Link to="/">
						<img
							src="/assets/logo-horizontal.svg"
							alt="DBRevel - AI-Powered Database SDK"
							title="DBRevel Password Reset"
							className="forgot-password-logo"
							width="140"
							height="42"
							loading="eager"
						/>
					</Link>
					<h1>Welcome Back</h1>
					<p>Sign in to your DBRevel account</p>
				</div>

				<form onSubmit={handleSubmit} className="login-form">
					{error && <div className="error-message">{error}</div>}

					<div className="form-group">
						<label htmlFor="email">Email Address</label>
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
						<label htmlFor="password">Password</label>
						<div className="password-input-container">
							<input
								type={showPassword ? "text" : "password"}
								id="password"
								required
								value={formData.password}
								onChange={(e) =>
									setFormData({ ...formData, password: e.target.value })
								}
								placeholder="Enter your password"
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

					<button type="submit" disabled={loading} className="submit-btn">
						{loading ? "Signing in..." : "Sign In"}
					</button>

					<div className="login-links">
						<p className="signup-link">
							Don't have an account? <Link to="/signup">Sign up</Link>
						</p>
						{error?.includes("verified") && (
							<p className="verify-email-link">
								<Link
									to={`/verify-email?email=${encodeURIComponent(
										formData.email,
									)}`}
								>
									Verify your email
								</Link>
							</p>
						)}
						<p className="forgot-password-link">
							<Link to="/forgot-password">Forgot your password?</Link>
						</p>
					</div>
				</form>
			</div>
		</div>
	);
}
