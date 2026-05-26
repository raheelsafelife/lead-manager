import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { isAdminRole } from "./utils/roles";
import Login from "./pages/Login";
import Layout from "./components/Layout";
import { AppRouteSkeleton } from "./components/Skeleton";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const LeadsPage = lazy(() => import("./pages/LeadsPage"));
const AddLead = lazy(() => import("./pages/AddLead"));
const Reports = lazy(() => import("./pages/Reports"));
const ActivityLogs = lazy(() => import("./pages/ActivityLogs"));
const UserSettings = lazy(() => import("./pages/UserSettings"));
const UserManagement = lazy(() => import("./pages/UserManagement"));
const LeadDiscovery = lazy(() => import("./pages/LeadDiscovery"));
const MarkReferralPage = lazy(() => import("./pages/MarkReferralPage"));

export default function App() {
  const { user } = useAuth();
  if (!user) return <Login />;
  return (
    <Layout>
      <Suspense fallback={<AppRouteSkeleton />}>
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
          <Route path="/users" element={isAdminRole(user.role) ? <UserManagement /> : <Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
