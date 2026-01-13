import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { config } from "../config";
import { useAuth } from "../contexts/AuthContext";
import "./Login.css"; // Reuse existing login styles

export default function AdminLogin() {
	const navigate = useNavigate();
	const { adminRequestOTP, adminVerifyOTP } = useAuth();
	const [step, setStep] = useState<"email" | "otp">("email");
	const [email, setEmail] = useState("");
	const [otp, setOtp] = useState("");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [message, setMessage] = useState<string | null>(null);

	const handleRequestOTP = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setMessage(null);
		setLoading(true);

		try {
			await adminRequestOTP(email);
			setMessage("OTP sent to your email. Please check your inbox.");
			setStep("otp");
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Failed to send OTP. Please try again.",
			);
		} finally {
			setLoading(false);
		}
	};

	const handleVerifyOTP = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setMessage(null);
		setLoading(true);

		try {
			await adminVerifyOTP(email, otp);
			navigate("/admin");
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Invalid OTP. Please try again.",
			);
		} finally {
			setLoading(false);
		}
	};

	const handleResendOTP = async () => {
		setError(null);
		setMessage(null);
		setLoading(true);

		try {
			await adminRequestOTP(email);
			setMessage("OTP resent to your email.");
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Failed to resend OTP.",
			);
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
							className="login-logo"
						/>
					</Link>
					<h1>Admin Login</h1>
					<p style={{ color: "#666", fontSize: "15px", marginTop: "8px" }}>
						{step === "email"
							? "Secure OTP-based authentication for platform administrators"
							: "Enter the 6-digit code sent to your email"}
					</p>
				</div>

				{step === "email" ? (
					<form onSubmit={handleRequestOTP} className="login-form">
						{error && <div className="error-message">{error}</div>}
						{message && <div className="success-message">{message}</div>}

						<div className="form-group">
							<label htmlFor="email">Admin Email</label>
							<input
								type="email"
								id="email"
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								placeholder="admin@example.com"
								required
								disabled={loading}
								autoFocus
							/>
						</div>

						<button type="submit" className="submit-btn" disabled={loading}>
							{loading ? "Sending OTP..." : "Request OTP"}
						</button>

						<div className="login-footer">
							<p>
								Not an admin? <Link to="/login">User Login</Link>
							</p>
						</div>
					</form>
				) : (
					<form onSubmit={handleVerifyOTP} className="login-form">
						{error && <div className="error-message">{error}</div>}
						{message && <div className="success-message">{message}</div>}

						<div className="form-group">
							<label htmlFor="otp">6-Digit OTP</label>
							<input
								type="text"
								id="otp"
								value={otp}
								onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
								placeholder="123456"
								required
								disabled={loading}
								autoFocus
								maxLength={6}
								pattern="\d{6}"
								style={{
									fontSize: "24px",
									letterSpacing: "8px",
									textAlign: "center",
									fontFamily: "monospace",
								}}
							/>
							<p style={{
								fontSize: "13px",
								color: "#666",
								marginTop: "8px",
								textAlign: "center"
							}}>
								OTP sent to <strong>{email}</strong>
							</p>
						</div>

						<button type="submit" className="submit-btn" disabled={loading}>
							{loading ? "Verifying..." : "Verify & Login"}
						</button>

						<div className="login-footer" style={{
							display: "flex",
							justifyContent: "center",
							gap: "20px",
							marginTop: "16px"
						}}>
							<button
								type="button"
								onClick={handleResendOTP}
								className="link-button"
								disabled={loading}
							>
								Resend OTP
							</button>
							<span style={{ color: "#ddd" }}>|</span>
							<button
								type="button"
								onClick={() => {
									setStep("email");
									setOtp("");
									setError(null);
									setMessage(null);
								}}
								className="link-button"
								disabled={loading}
							>
								Change Email
							</button>
						</div>
					</form>
				)}
			</div>
		</div>
	);
}
