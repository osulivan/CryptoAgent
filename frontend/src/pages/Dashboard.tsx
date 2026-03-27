import { useQuery } from '@tanstack/react-query';
import {
  Bot,
  Clock,
  CheckCircle,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Coins,
} from 'lucide-react';
import { taskApi, executionApi, modelApi } from '../api/client';
import type { Task, Execution, Model } from '../types';

export default function Dashboard() {
  // Fetch data
  const { data: tasks } = useQuery({
    queryKey: ['tasks'],
    queryFn: async () => {
      const response = await taskApi.getAll();
      return response.data as Task[];
    },
  });

  const { data: executions } = useQuery({
    queryKey: ['executions'],
    queryFn: async () => {
      const response = await executionApi.getAll({ limit: 10 });
      return response.data as Execution[];
    },
    refetchInterval: 5000,
  });

  const { data: models } = useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const response = await modelApi.getAll();
      return response.data as Model[];
    },
  });

  const { data: stats } = useQuery({
    queryKey: ['executionStats'],
    queryFn: async () => {
      const response = await executionApi.getStats();
      return response.data as {
        totalExecutions: number;
        completedExecutions: number;
        failedExecutions: number;
        buyDecisions: number;
        sellDecisions: number;
        holdDecisions: number;
        totalTokens: {
          input: number;
          output: number;
          total: number;
        };
      };
    },
  });

  const activeTasks = tasks?.filter((t) => t.isActive) || [];
  const recentExecutions = executions?.slice(0, 5) || [];

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>概览</h1>
        <p>CryptoAgent AI交易系统总览</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <div className="stat-label">
            <Bot size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
            运行中任务
          </div>
          <div className="stat-value">{activeTasks.length}</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            共 {tasks?.length || 0} 个任务
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">
            <Activity size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
            今日执行
          </div>
          <div className="stat-value">{stats?.totalExecutions || 0}</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            成功 {stats?.completedExecutions || 0} · 失败 {stats?.failedExecutions || 0}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">
            <Clock size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
            已配置模型
          </div>
          <div className="stat-value">{models?.length || 0}</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            默认: {models?.find((m) => m.isDefault)?.name || '无'}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">
            <Coins size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
            累计 Token 使用
          </div>
          <div className="stat-value">{(stats?.totalTokens?.total || 0).toLocaleString()}</div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            输入: {(stats?.totalTokens?.input || 0).toLocaleString()} · 输出: {(stats?.totalTokens?.output || 0).toLocaleString()}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2">
        {/* Active Tasks */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Bot size={20} style={{ display: 'inline', marginRight: '0.5rem' }} />
              运行中的任务
            </h2>
          </div>
          {activeTasks.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>暂无运行中的任务</p>
              <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                前往"交易任务"页面启动任务
              </p>
            </div>
          ) : (
            <div>
              {activeTasks.map((task) => (
                <div
                  key={task.id}
                  style={{
                    padding: '1rem',
                    borderBottom: '1px solid var(--border-color)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 500 }}>{task.name}</div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                      {task.symbol} · {task.interval}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span className="badge badge-success">
                      <span
                        style={{
                          width: '6px',
                          height: '6px',
                          borderRadius: '50%',
                          background: 'currentColor',
                          display: 'inline-block',
                          marginRight: '4px',
                        }}
                      />
                      运行中
                    </span>
                    {task.nextRunAt && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                        下次: {new Date(task.nextRunAt).toLocaleTimeString()}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Executions */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Clock size={20} style={{ display: 'inline', marginRight: '0.5rem' }} />
              最近执行
            </h2>
          </div>
          {recentExecutions.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <p>暂无执行记录</p>
              <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                运行任务后将显示执行历史
              </p>
            </div>
          ) : (
            <div>
              {recentExecutions.map((execution) => (
                <div
                  key={execution.id}
                  style={{
                    padding: '1rem',
                    borderBottom: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: 500 }}>
                      {tasks?.find((t) => t.id === execution.taskId)?.name || execution.taskId}
                    </span>
                    {execution.status === 'completed' ? (
                      <CheckCircle size={16} style={{ color: 'var(--success)' }} />
                    ) : execution.status === 'failed' ? (
                      <span style={{ color: 'var(--danger)' }}>失败</span>
                    ) : (
                      <span style={{ color: 'var(--warning)' }}>执行中</span>
                    )}
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '0.875rem',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    <span>{execution.symbol}</span>
                    <span>{new Date(execution.startTime).toLocaleString()}</span>
                  </div>
                  {execution.finalDecision && (
                    <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem' }}>
                      {execution.finalDecision.decision === 'BUY' && (
                        <span
                          className="badge"
                          style={{
                            background: 'rgba(16, 185, 129, 0.2)',
                            color: '#10b981',
                          }}
                        >
                          <ArrowUpRight size={12} />
                          买入
                        </span>
                      )}
                      {execution.finalDecision.decision === 'SELL' && (
                        <span
                          className="badge"
                          style={{
                            background: 'rgba(239, 68, 68, 0.2)',
                            color: '#ef4444',
                          }}
                        >
                          <ArrowDownRight size={12} />
                          卖出
                        </span>
                      )}
                      {execution.finalDecision.decision === 'HOLD' && (
                        <span className="badge badge-secondary">持有</span>
                      )}
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        {(execution.finalDecision.confidence * 100).toFixed(0)}% 置信度
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
