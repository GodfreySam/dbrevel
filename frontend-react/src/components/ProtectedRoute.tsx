import { useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

interface ProtectedRouteProps {
	children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
	const { isAuthenticated, loading, refreshUser, token } = useAuth();
	const [validating, setValidating] = useState(true);
	const validatedTokenRef = useRef<string | null>(null);

	// Validate token on mount if user is authenticated (only once per token)
	useEffect(() => {
		// Skip if still loading
		if (loading) {
			return;
		}

		// If authenticated with token and this token hasn't been validated yet
		if (isAuthenticated && token && validatedTokenRef.current !== token) {
			validatedTokenRef.current = token;
			setValidating(true);
			refreshUser()
				.then(() => {
					setValidating(false);
				})
				.catch((error) => {
					console.error("Token validation failed in ProtectedRoute:", error);
					// Token is invalid, validation will clear it via logout callback
					setValidating(false);
				});
		} else if (!isAuthenticated || !token) {
			// Not authenticated, reset validation tracking
			validatedTokenRef.current = null;
			setValidating(false);
		} else if (validatedTokenRef.current === token) {
			// Already validated this token, just set validating to false
			setValidating(false);
		}
	}, [loading, isAuthenticated, token, refreshUser]);

	if (loading || validating) {
		return (
			<div
				style={{
					display: "flex",
					justifyContent: "center",
					alignItems: "center",
					minHeight: "100vh",
				}}
			>
				<div>Loading...</div>
			</div>
		);
	}

	if (!isAuthenticated) {
		return <Navigate to="/login" replace />;
	}

	return <>{children}</>;
}
