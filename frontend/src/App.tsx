import { Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import DashboardLayout from "./components/DashboardLayout";
import DocumentDetail from "./pages/DocumentDetail";
import EvalPage from "./pages/EvalPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<DashboardLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="documents/:id" element={<DocumentDetail />} />
              <Route path="documents/:id/eval" element={<EvalPage />} />
              {/* Unknown paths under the dashboard keep the app chrome. */}
              <Route path="*" element={<NotFound />} />
            </Route>
          </Route>
          {/* Everything else, signed in or not, rather than a blank page. */}
          <Route
            path="*"
            element={<NotFound to="/" linkLabel="Back to home" />}
          />
        </Routes>
      </AuthProvider>
    </QueryClientProvider>
  );
}
