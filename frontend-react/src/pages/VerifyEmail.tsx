import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import "./VerifyEmail.css";

export default function VerifyEmail() {
	const navigate = useNavigate();
	const [searchParams] = useSearchParams();
	const { verifyEmail, resendVerification } = useAuth();
	const [loading, setLoading] = useState(false);
	const [resending, setResending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [success, setSuccess] = useState<string | null>(null);
	const [email, setEmail] = useState<string>("");
	const [otp, setOtp] = useState<string>("");

	useEffect(() => {
		// Get email from URL params
		const emailParam = searchParams.get("email");
		if (emailParam) {
			setEmail(emailParam);
		}
	}, [searchParams]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setSuccess(null);

		if (!email.trim()) {
			setError("Email is required");
			return;
		}

		if (!otp.trim() || otp.length !== 6) {
			setError("Please enter a valid 6-digit verification code");
			return;
		}

		setLoading(true);
		try {
			await verifyEmail(email, otp);
			setSuccess("Email verified successfully! Redirecting to dashboard...");
			// Redirect to dashboard after a short delay
			setTimeout(() => {
				navigate("/dashboard");
			}, 1500);
		} catch (err) {
			setError(
				err instanceof Error
					? err.message
					: "Email verification failed. Please check your code and try again.",
			);
		} finally {
			setLoading(false);
		}
	};

	const handleResend = async () => {
		if (!email.trim()) {
			setError("Email is required");
			return;
		}

		setError(null);
		setResending(true);
		try {
			await resendVerification(email);
			setSuccess("Verification email sent! Please check your inbox.");
		} catch (err) {
			setError(
				err instanceof Error
					? err.message
					: "Failed to resend verification email. Please try again.",
			);
		} finally {
			setResending(false);
		}
	};

	const handleOtpChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		// Only allow digits and limit to 6 characters
		const value = e.target.value.replace(/\D/g, "").slice(0, 6);
		setOtp(value);
	};

	return (
		<div className="verify-email-page">
			<div className="verify-email-container">
				<div className="verify-email-header">
					<Link to="/">
						<img
							src="/assets/logo-horizontal.svg"
							alt="DBRevel - AI-Powered Database SDK"
							title="DBRevel Email Verification"
							className="verify-email-logo"
							width="160"
							height="48"
							loading="eager"
						/>
					</Link>
					<h1>Verify Your Email</h1>
					<p className="verify-email-subtitle">
						We've sent a 6-digit verification code to your email address. Please
						enter it below to verify your account.
					</p>
				</div>

				{success && <div className="success-message">{success}</div>}
				{error && <div className="error-message">{error}</div>}

				<form onSubmit={handleSubmit} className="verify-email-form">
					<div className="form-group">
						<label htmlFor="email">Email Address</label>
						<input
							type="email"
							id="email"
							required
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							placeholder="you@example.com"
							disabled={loading}
						/>
					</div>

					<div className="form-group">
						<label htmlFor="otp">Verification Code</label>
						<input
							type="text"
							id="otp"
							required
							value={otp}
							onChange={handleOtpChange}
							placeholder="000000"
							maxLength={6}
							pattern="[0-9]{6}"
							disabled={loading}
							className="otp-input"
						/>
						<small className="form-hint">
							Enter the 6-digit code sent to your email
						</small>
					</div>

					<button
						type="submit"
						disabled={loading || !otp || otp.length !== 6}
						className="submit-btn"
					>
						{loading ? "Verifying..." : "Verify Email"}
					</button>

					<div className="verify-email-actions">
						<button
							type="button"
							onClick={handleResend}
							disabled={resending || loading}
							className="resend-btn"
						>
							{resending
								? "Sending..."
								: "Didn't receive the code? Resend"}
						</button>
					</div>

					<div className="verify-email-links">
						<p>
							Already verified? <Link to="/login">Log in</Link>
						</p>
						<p>
							Need help?{" "}
							<a href="mailto:support@dbrevel.io" className="support-link">
								Contact Support
							</a>
						</p>
					</div>
				</form>
			</div>
		</div>
	);
}
