import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import LeadsPage from "./pages/LeadsPage";
import AddLead from "./pages/AddLead";
import Reports from "./pages/Reports";
import ActivityLogs from "./pages/ActivityLogs";
import UserSettings from "./pages/UserSettings";
import UserManagement from "./pages/UserManagement";
import LeadDiscovery from "./pages/LeadDiscovery";
import MarkReferralPage from "./pages/MarkReferralPage";

export default function App() {
  const { user } = useAuth();
  if (!user) return <Login />;
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/lead-discovery" element={<LeadDiscovery />} />
        <Route path="/add-lead" element={<AddLead />} />
        <Route path="/view-leads" element={<LeadsPage title="Manage Leads" type="lead" />} />
        <Route path="/referrals" element={<LeadsPage title="Referrals" type="referral" />} />
        <Route path="/authorizations" element={<LeadsPage title="Authorizations" type="authorization" />} />
        <Route path="/mark-referral/:id" element={<MarkReferralPage />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/activity" element={<ActivityLogs />} />
        <Route path="/settings" element={<UserSettings />} />
        <Route path="/users" element={user.role === "admin" ? <UserManagement /> : <Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  );
}
