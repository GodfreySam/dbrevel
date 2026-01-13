import { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

interface AdminProtectedRouteProps {
	children: ReactNode;
}

export default function AdminProtectedRoute({ children }: AdminProtectedRouteProps) {
	const { isAdmin, loading } = useAuth();

	if (loading) {
		return (
			<div style={{
				display: "flex",
				justifyContent: "center",
				alignItems: "center",
				minHeight: "100vh"
			}}>
				<div>Loading...</div>
			</div>
		);
	}

	if (!isAdmin) {
		return <Navigate to="/admin/login" replace />;
	}

	return <>{children}</>;
}
