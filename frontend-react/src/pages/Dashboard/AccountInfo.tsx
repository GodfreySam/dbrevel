import { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { AccountDetail, User } from "../../types/api";
import { apiFetchJson } from "../../utils/api";

interface AccountInfoProps {
	user: User;
	accountInfo: AccountDetail | null;
	onUserRefresh: () => Promise<void>;
}

export default function AccountInfo({
	user,
	accountInfo,
	onUserRefresh,
}: AccountInfoProps) {
	const { logout } = useAuth();
	const [showChangePassword, setShowChangePassword] = useState(false);
	const [passwordData, setPasswordData] = useState({
		current: "",
		new: "",
	});
	const [loading, setLoading] = useState(false);
	const [message, setMessage] = useState<{
		type: "error" | "success";
		text: string;
	} | null>(null);

	const handleChangePassword = async (e: React.FormEvent) => {
		e.preventDefault();
		setMessage(null);

		if (passwordData.new.length < 8) {
			setMessage({
				type: "error",
				text: "Password must be at least 8 characters",
			});
			return;
		}

		setLoading(true);
		try {
			await apiFetchJson(
				"/auth/change-password",
				{
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						current_password: passwordData.current,
						new_password: passwordData.new,
					}),
				},
				logout,
			);

			setMessage({ type: "success", text: "Password changed successfully!" });
			setPasswordData({ current: "", new: "" });
			await onUserRefresh();
			setTimeout(() => {
				setShowChangePassword(false);
				setMessage(null);
			}, 2000);
		} catch (err) {
			setMessage({
				type: "error",
				text: err instanceof Error ? err.message : "Failed to change password",
			});
		} finally {
			setLoading(false);
		}
	};

	return (
		<section className="dashboard-section">
			<h2>Account Information</h2>
			<div className="info-card">
				<div className="info-row">
					<span className="info-label">Email</span>
					<span className="info-value">{user.email}</span>
				</div>
				<div className="info-row">
					<span className="info-label">Email Verified</span>
					<span className="info-value">
						{user.email_verified ? "✓ Yes" : "✗ No"}
					</span>
				</div>
				<div className="info-row">
					<span className="info-label">Organization</span>
					<span className="info-value">{user.account_name}</span>
				</div>
				<div className="info-row">
					<span className="info-label">Account ID</span>
					<span className="info-value">
						{accountInfo?.id || user.account_id}
					</span>
				</div>
			</div>

			<div className="password-change-section">
				<button
					onClick={() => setShowChangePassword(!showChangePassword)}
					className="toggle-password-btn"
				>
					{showChangePassword ? "Cancel Password Change" : "Change Password"}
				</button>

				{showChangePassword && (
					<form
						onSubmit={handleChangePassword}
						className="password-change-form"
					>
						{message && (
							<div
								className={
									message.type === "error" ? "error-message" : "success-message"
								}
							>
								{message.text}
							</div>
						)}
						<div className="form-group">
							<label>Current Password</label>
							<input
								type="password"
								required
								value={passwordData.current}
								onChange={(e) =>
									setPasswordData({ ...passwordData, current: e.target.value })
								}
								className="password-input"
							/>
						</div>
						<div className="form-group">
							<label>New Password (min 8 chars)</label>
							<input
								type="password"
								required
								minLength={8}
								value={passwordData.new}
								onChange={(e) =>
									setPasswordData({ ...passwordData, new: e.target.value })
								}
								className="password-input"
							/>
						</div>
						<button
							type="submit"
							disabled={loading}
							className="submit-password-btn"
						>
							{loading ? "Changing..." : "Change Password"}
						</button>
					</form>
				)}
			</div>
		</section>
	);
}
