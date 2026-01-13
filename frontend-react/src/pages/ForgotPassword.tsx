import { useState } from "react";
import { Link } from "react-router-dom";
import { config } from "../config";
import "./ForgotPassword.css";

export default function ForgotPassword() {
	const [email, setEmail] = useState("");
	const [loading, setLoading] = useState(false);
	const [success, setSuccess] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setLoading(true);

		try {
			const response = await fetch(`${config.apiUrl}/auth/forgot-password`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({ email }),
			});

			if (!response.ok) {
				const errorData = await response
					.json()
					.catch(() => ({ detail: response.statusText }));
				throw new Error(errorData.detail || "Request failed");
			}

			setSuccess(true);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Request failed");
		} finally {
			setLoading(false);
		}
	};

	if (success) {
		return (
			<div className="forgot-password-page">
				<div className="forgot-password-container">
					<div className="success-message">
						<h2>Check Your Email</h2>
						<p>
							If an account with <strong>{email}</strong> exists, we've sent you
							a 6-digit OTP code.
						</p>
						<p className="note">
							Please check your email and enter the code on the next page. The
							code will expire in 10 minutes.
						</p>
						<div className="actions">
							<Link
								to={`/reset-password?email=${encodeURIComponent(email)}`}
								className="action-btn"
							>
								Enter OTP Code
							</Link>
							<Link to="/login" className="back-link">
								Back to Login
							</Link>
						</div>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="forgot-password-page">
			<div className="forgot-password-container">
				<div className="forgot-password-header">
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
					<h1>Forgot Password</h1>
					<p>
						Enter your email address and we'll send you a 6-digit OTP code to
						reset your password.
					</p>
				</div>

				<form onSubmit={handleSubmit} className="forgot-password-form">
					{error && <div className="error-message">{error}</div>}

					<div className="form-group">
						<label htmlFor="email">Email Address</label>
						<input
							type="email"
							id="email"
							required
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							placeholder="you@example.com"
						/>
					</div>

					<button type="submit" disabled={loading} className="submit-btn">
						{loading ? "Sending..." : "Send OTP Code"}
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
