import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import PatientListPage from './pages/PatientListPage';
import PatientDetailPage from './pages/PatientDetailPage';
import PrescriptionListPage from './pages/PrescriptionListPage';
import PrescriptionNewPage from './pages/PrescriptionNewPage';
import PrescriptionDetailPage from './pages/PrescriptionDetailPage';
import ReviewPage from './pages/ReviewPage';
import MedicinePage from './pages/MedicinePage';
import MedicineLocationsPage from './pages/MedicineLocationsPage';
import ScanPage from './pages/ScanPage';
import PlaceholderPage from './pages/PlaceholderPage';
import { useAuth } from './hooks/useAuth';

const isMobile = (): boolean => {
  if (typeof navigator === 'undefined') return false;
  const ua = navigator.userAgent || '';
  return /Android|iPhone|iPad|iPod|webOS/i.test(ua);
};

function MobileOnly({ children }: { children: React.ReactNode }) {
  if (!isMobile()) return <>{children}</>;
  const loc = useLocation();
  if (loc.pathname !== '/scan' && loc.pathname !== '/login') {
    return <Navigate to="/scan" replace />;
  }
  return <>{children}</>;
}

function PrivateRoute({ children, roles, noLayout }: { children: React.ReactNode; roles?: string[]; noLayout?: boolean }) {
  const { user, loading } = useAuth();

  // ── 第6层: 前端初始化截止日期检查 ──
  // 即使后端保护被绕过，前端自身也会拦截
  const d = new Date();
  if (d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate() > 20261231) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        height: '100vh', color: '#fff', fontFamily: 'sans-serif',
        background: 'linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%)',
      }}>
        <div style={{ fontSize: 64, marginBottom: 20 }}>⚠️</div>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 500 }}>系统已停止服务</h2>
      </div>
    );
  }

  if (loading) return <div className="loading">...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />;
  if (noLayout) return <MobileOnly>{children}</MobileOnly>;
  return (
    <MobileOnly>
      <AppLayout>{children}</AppLayout>
    </MobileOnly>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
      <Route path="/patients" element={<PrivateRoute><PatientListPage /></PrivateRoute>} />
      <Route path="/patients/:id" element={<PrivateRoute><PatientDetailPage /></PrivateRoute>} />
      <Route path="/prescriptions" element={<PrivateRoute><PrescriptionListPage /></PrivateRoute>} />
      <Route path="/prescriptions/new" element={<PrivateRoute roles={['doctor','admin']}><PrescriptionNewPage /></PrivateRoute>} />
      <Route path="/prescriptions/:id" element={<PrivateRoute><PrescriptionDetailPage /></PrivateRoute>} />
      <Route path="/review" element={<PrivateRoute roles={['pharmacist','admin']}><ReviewPage /></PrivateRoute>} />
      <Route path="/scan" element={<PrivateRoute noLayout><ScanPage /></PrivateRoute>} />
      <Route path="/medicines" element={<PrivateRoute><MedicinePage /></PrivateRoute>} />
      <Route path="/medicine-info" element={<PrivateRoute><MedicinePage /></PrivateRoute>} />
      <Route path="/medicine-locations" element={<PrivateRoute><MedicineLocationsPage /></PrivateRoute>} />
      <Route path="/dispense" element={<PrivateRoute><PlaceholderPage title="医嘱取药" icon="💉" /></PrivateRoute>} />
      <Route path="/medicine-settings" element={<PrivateRoute><PlaceholderPage title="药盒设置" icon="⚙️" /></PrivateRoute>} />
      <Route path="/reports" element={<PrivateRoute><PlaceholderPage title="报表生成" icon="📊" /></PrivateRoute>} />
      <Route path="/writeoff" element={<PrivateRoute><PlaceholderPage title="销账" icon="📒" /></PrivateRoute>} />
      <Route path="/operation-log" element={<PrivateRoute><PlaceholderPage title="操作记录" icon="📋" /></PrivateRoute>} />
      <Route path="/restock" element={<PrivateRoute><PlaceholderPage title="补药" icon="➕" /></PrivateRoute>} />
      <Route path="/inventory" element={<PrivateRoute><PlaceholderPage title="库存查询" icon="🔍" /></PrivateRoute>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
