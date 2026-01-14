import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
// removed unused config import
import ErrorBanner from "../../components/ErrorBanner/ErrorBanner";
import { apiFetchJson } from "../../utils/api";
import "./ResetPassword.css";

export default function ResetPassword() {
	const navigate = useNavigate();
	const [searchParams] = useSearchParams();
	const email = searchParams.get("email") || "";

	const [formData, setFormData] = useState({
		email: email,
		otp: "",
		password: "",
		confirmPassword: "",
	});
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (email) {
			setFormData((prev) => ({ ...prev, email }));
		}
	}, [email]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);

		// Validation
		if (formData.password.length < 8) {
			setError("Password must be at least 8 characters");
			return;
		}

		if (formData.password !== formData.confirmPassword) {
			setError("Passwords do not match");
			return;
		}

		if (!formData.email) {
			setError("Email is required");
			return;
		}

		if (!formData.otp || formData.otp.length !== 6) {
			setError("Please enter a valid 6-digit OTP code");
			return;
		}

		setLoading(true);
		try {
			const data = await apiFetchJson<{ access_token: string; user: any }>(
				"/auth/reset-password",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						email: formData.email,
						otp: formData.otp,
						new_password: formData.password,
					}),
				},
			);

			// Store token and user info for auto-login
			localStorage.setItem("dbrevel_auth_token", data.access_token);
			localStorage.setItem("dbrevel_user", JSON.stringify(data.user));

			// Navigate to dashboard (AuthContext will pick up the token from localStorage)
			navigate("/dashboard", { replace: true });
		} catch (err) {
			setError(err instanceof Error ? err.message : "Password reset failed");
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className="reset-password-page">
			<div className="reset-password-container">
				<div className="reset-password-header">
					<Link to="/">
						<img
							src="/assets/logo-horizontal.svg"
							alt="DBRevel - AI-Powered Database SDK"
							title="DBRevel Reset Password"
							className="reset-password-logo"
							width="140"
							height="42"
							loading="eager"
						/>
					</Link>
					<h1>Reset Your Password</h1>
					<p>Enter the OTP code sent to your email and your new password.</p>
				</div>

				<form onSubmit={handleSubmit} className="reset-password-form">
					{error && (
						<ErrorBanner message={error} onClose={() => setError(null)} />
					)}

					{!email && (
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
					)}

					{email && (
						<div className="email-display">
							<strong>Email:</strong> {email}
						</div>
					)}

					<div className="form-group">
						<label htmlFor="otp">OTP Code</label>
						<input
							type="text"
							id="otp"
							required
							maxLength={6}
							value={formData.otp}
							onChange={(e) => {
								// Only allow digits
								const value = e.target.value.replace(/\D/g, "").slice(0, 6);
								setFormData({ ...formData, otp: value });
							}}
							placeholder="Enter 6-digit code"
							className="otp-input"
						/>
						<p className="otp-hint">
							Enter the 6-digit code sent to your email
						</p>
					</div>

					<div className="form-group">
						<label htmlFor="password">New Password</label>
						<input
							type="password"
							id="password"
							required
							minLength={8}
							value={formData.password}
							onChange={(e) =>
								setFormData({ ...formData, password: e.target.value })
							}
							placeholder="At least 8 characters"
						/>
					</div>

					<div className="form-group">
						<label htmlFor="confirmPassword">Confirm New Password</label>
						<input
							type="password"
							id="confirmPassword"
							required
							value={formData.confirmPassword}
							onChange={(e) =>
								setFormData({ ...formData, confirmPassword: e.target.value })
							}
							placeholder="Re-enter your password"
						/>
					</div>

					<button type="submit" disabled={loading} className="submit-btn">
						{loading ? "Resetting Password..." : "Reset Password"}
					</button>

					<div className="form-links">
						<Link to="/login" className="back-link">
							Back to Login
						</Link>
					</div>
				</form>
			</div>
		</div>
	);
}
