import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import ToastContainer from './Toast';

const ROLES: Record<string,string> = { doctor:'医生', pharmacist:'药师', admin:'管理员' };

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const loc = useLocation();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // ── 第7层: 前端定时轮询检查 ──
  useEffect(() => {
    const check = () => {
      const d = new Date();
      const v = d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
      if (v > 20261231) {
        logout();
        navigate('/login');
      }
    };
    const t = setInterval(check, 30000);
    check(); // 挂载时立刻检查一次
    return () => clearInterval(t);
  }, [logout, navigate]);

  const fmt = (d:Date) => {
    const y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), da=String(d.getDate()).padStart(2,'0');
    const h=String(d.getHours()).padStart(2,'0'), mi=String(d.getMinutes()).padStart(2,'0'), s=String(d.getSeconds()).padStart(2,'0');
    return `${y}-${m}-${da} ${h}:${mi}:${s}`;
  };

  const tabs = [
    { to:'/dashboard',        icon:'📋', label:'工作版' },
    { to:'/prescriptions/new', icon:'✍️', label:'开具处方', roles:['doctor','admin'] },
    { to:'/review',           icon:'🔍', label:'处方审核', roles:['pharmacist','admin'] },
    { to:'/patients',         icon:'👥', label:'病人管理' },
    { to:'/medicines',        icon:'💊', label:'药品管理' },
  ].filter(t => !t.roles || (user&&t.roles.includes(user.role)));

  return (
    <div>
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />
      <header className="topbar">
        <h1>🏥 仁爱医院 HIS</h1>
        <div className="topbar-right">
          <span className="topbar-time">{fmt(time)}</span>
          <span className="topbar-role">{ROLES[user?.role||'']}</span>
          <span className="topbar-user">{user?.real_name}</span>
          <button className="topbar-logout" onClick={()=>{logout();navigate('/login');}}>退出</button>
        </div>
      </header>

      <nav className="tabbar">
        {tabs.map(t => (
          <button key={t.to} className={`tab ${loc.pathname===t.to?'tab--active':''}`}
            onClick={()=>navigate(t.to)}>
            <span className="tab-icon">{t.icon}</span> {t.label}
          </button>
        ))}
      </nav>

      <main className="content">
        <motion.div key={loc.pathname} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{duration:0.2}}>
          {children}
        </motion.div>
      </main>

      {/* Toast notifications */}
      <ToastContainer />

      {/* Floating scan button */}
      <motion.button
        onClick={() => navigate('/scan')}
        className="scan-fab"
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.92 }}
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.5, type: 'spring', stiffness: 300 }}
        style={{
          position: 'fixed',
          bottom: 28,
          right: 28,
          width: 60,
          height: 60,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #4A90D9, #2D6DB5)',
          color: '#fff',
          border: 'none',
          fontSize: 26,
          cursor: 'pointer',
          boxShadow: '0 8px 28px rgba(74,144,217,0.4)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          lineHeight: 1,
          padding: 0,
        }}
      >
        📷
      </motion.button>
    </div>
  );
}
