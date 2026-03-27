import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  Settings,
  Bot,
  History,
  TrendingUp,
  Menu,
  X,
  Wallet
} from 'lucide-react';
import { useState } from 'react';
import ModelSettings from './pages/ModelSettings';
import AccountSettings from './pages/AccountSettings';
import TaskManager from './pages/TaskManager';
import ExecutionHistory from './pages/ExecutionHistory';
import Dashboard from './pages/Dashboard';
import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="app">
          {/* Sidebar */}
          <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
            <div className="sidebar-header">
              <div className="logo">
                <TrendingUp className="logo-icon" />
                <span className="logo-text">CryptoAgent</span>
              </div>
              <button 
                className="toggle-btn"
                onClick={() => setSidebarOpen(!sidebarOpen)}
              >
                {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
              </button>
            </div>
            
            <nav className="sidebar-nav">
              <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
                <TrendingUp size={20} />
                <span>概览</span>
              </NavLink>
              <NavLink to="/models" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                <Settings size={20} />
                <span>模型设置</span>
              </NavLink>
              <NavLink to="/accounts" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                <Wallet size={20} />
                <span>交易账户</span>
              </NavLink>
              <NavLink to="/tasks" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                <Bot size={20} />
                <span>交易任务</span>
              </NavLink>
              <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                <History size={20} />
                <span>执行历史</span>
              </NavLink>
            </nav>
          </aside>

          {/* Main Content */}
          <main className={`main-content ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/models" element={<ModelSettings />} />
              <Route path="/accounts" element={<AccountSettings />} />
              <Route path="/tasks" element={<TaskManager />} />
              <Route path="/history" element={<ExecutionHistory />} />
            </Routes>
          </main>
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
