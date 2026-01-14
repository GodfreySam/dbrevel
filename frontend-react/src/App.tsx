import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AdminProtectedRoute from "./components/AdminProtectedRoute";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminDashboard from "./pages/AdminDashboard/AdminDashboard";
import AdminLogin from "./pages/AdminLogin";
import ApiDocs from "./pages/ApiDocs/ApiDocs";
import Dashboard from "./pages/Dashboard/Dashboard";
import ForgotPassword from "./pages/ForgotPassword/ForgotPassword";
import Home from "./pages/Home";
import Login from "./pages/Login/Login";
import ResetPassword from "./pages/ResetPassword/ResetPassword";
import Signup from "./pages/Signup/Signup";
import VerifyEmail from "./pages/VerifyEmail/VerifyEmail";

function App() {
	return (
		<BrowserRouter>
			<Routes>
				<Route path="/" element={<Home />} />
				<Route path="/docs" element={<ApiDocs />} />
				<Route path="/signup" element={<Signup />} />
				<Route path="/login" element={<Login />} />
				<Route path="/verify-email" element={<VerifyEmail />} />
				<Route path="/forgot-password" element={<ForgotPassword />} />
				<Route path="/reset-password" element={<ResetPassword />} />
				<Route
					path="/dashboard"
					element={
						<ProtectedRoute>
							<Dashboard />
						</ProtectedRoute>
					}
				/>
				{/* Admin routes */}
				<Route path="/admin/login" element={<AdminLogin />} />
				<Route
					path="/admin/*"
					element={
						<AdminProtectedRoute>
							<AdminDashboard />
						</AdminProtectedRoute>
					}
				/>
				<Route path="*" element={<Navigate to="/" replace />} />
			</Routes>
		</BrowserRouter>
	);
}

export default App;
