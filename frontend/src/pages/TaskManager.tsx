import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Edit2,
  Trash2,
  Play,
  Square,
  RotateCw,
  Clock,
  X,
  Loader2,
  Bot,
  XCircle
} from 'lucide-react';
import { taskApi, exchangeApi, modelApi, accountApi } from '../api/client';
import type { Task, Model, Account, TradingPair, IntervalType } from '../types';
import Modal from '../components/Modal';

const INTERVAL_OPTIONS: { value: IntervalType; label: string; description: string }[] = [
  { value: '5m', label: '5分钟', description: '每5分钟执行一次 (0, 5, 10...分)' },
  { value: '15m', label: '15分钟', description: '每15分钟执行一次 (0, 15, 30, 45分)' },
  { value: '1h', label: '1小时', description: '每小时执行一次 (整点)' },
  { value: '4h', label: '4小时', description: '每4小时执行一次 (0, 4, 8, 12, 16, 20点)' },
  { value: 'daily', label: '每天', description: '每天指定时间执行' },
];

const TRADING_RULES_PLACEHOLDER = `一个完整的交易策略应具备以下几个基本元素：

1、开仓条件：如满足什么周期的指标条件或K线形态开仓

2、平仓条件：如盈利或亏损多少平仓，到达什么指标条件或技术形态平仓

3、交易数量：如10%仓位或0.75（币数量）等

4、约束条件：如已有相同方向持仓时，不再开仓`;

export default function TaskManager() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [showSymbolDropdown, setShowSymbolDropdown] = useState(false);
  const [symbolSearch, setSymbolSearch] = useState('');
  
  // 用于强制重新渲染以更新倒计时
  const [, setTick] = useState(0);
  
  useEffect(() => {
    const interval = setInterval(() => {
      setTick(t => t + 1);
    }, 60000); // 每分钟更新一次
    return () => clearInterval(interval);
  }, []);

  const [formData, setFormData] = useState({
    name: '',
    symbol: '',
    tradingRules: '',
    interval: '15m' as IntervalType,
    dailyTime: '09:00',
    modelId: '',
    accountId: '',
  });

  // 定时获取任务数据（用于更新下次执行时间）
  const { data: latestTasksData } = useQuery({
    queryKey: ['tasks-latest'],
    queryFn: async () => {
      const response = await taskApi.getAll();
      return response.data as Task[];
    },
    enabled: true,
    refetchInterval: 30000,
  });
  
  // 主数据
  const { data: tasksData, isLoading: tasksLoading, error: tasksError } = useQuery({
    queryKey: ['tasks'],
    queryFn: async () => {
      const response = await taskApi.getAll();
      return response.data as Task[];
    },
    initialData: [],
  });
  
  // 使用最新数据（如果有）
  const tasks = Array.isArray(latestTasksData) ? latestTasksData : (Array.isArray(tasksData) ? tasksData : []);

  // Fetch accounts
  const { data: accountsData } = useQuery({
    queryKey: ['accounts'],
    queryFn: async () => {
      const response = await accountApi.getAll();
      return response.data as Account[];
    },
    initialData: [],
  });

  // 确保 accounts 是数组
  const accounts = Array.isArray(accountsData) ? accountsData : [];

  // Fetch models
  const { data: modelsData } = useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const response = await modelApi.getAll();
      return response.data as Model[];
    },
    initialData: [],
  });

  // 确保 models 是数组
  const models = Array.isArray(modelsData) ? modelsData : [];

  // 获取当前账户的交易所和模拟状态
  const currentAccount = accounts?.find(a => a.id === formData.accountId);
  const currentExchange = currentAccount?.exchange || 'okx';
  const currentIsSimulated = currentAccount?.isSimulated ?? true;

  // 根据账户交易所和模拟状态获取交易对（只有选择了账户后才查询）
  const { data: tradingPairsData } = useQuery({
    queryKey: ['tradingPairs', currentExchange, currentIsSimulated],
    queryFn: async () => {
      console.log('[TaskManager] Fetching trading pairs for:', currentExchange, 'simulated:', currentIsSimulated);
      const response = await exchangeApi.getTradingPairs(currentExchange, currentIsSimulated);
      console.log('[TaskManager] Trading pairs response:', response);
      return response.data as TradingPair[];
    },
    enabled: !!formData.accountId && !!currentExchange,
    initialData: [],
    staleTime: 0,
    gcTime: 0,
  });

  // 确保 tradingPairs 是数组
  const tradingPairs = Array.isArray(tradingPairsData) ? tradingPairsData : [];

  // Create mutation
  const createMutation = useMutation({
    mutationFn: taskApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['tasks-latest'] });
      closeModal();
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => taskApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['tasks-latest'] });
      closeModal();
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: taskApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['tasks-latest'] });
    },
  });

  // Toggle mutation - 为每个任务维护loading状态
  const [togglingTasks, setTogglingTasks] = useState<Record<string, boolean>>({});

  const toggleMutation = useMutation({
    mutationFn: taskApi.toggle,
    onMutate: (taskId) => {
      setTogglingTasks(prev => ({ ...prev, [taskId]: true }));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['tasks-latest'] });
    },
    onSettled: (_, __, taskId) => {
      setTogglingTasks(prev => ({ ...prev, [taskId]: false }));
    },
  });

  // Run once mutation
  const runOnceMutation = useMutation({
    mutationFn: taskApi.runOnce,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['executions'] });
    },
  });

  const openModal = (task?: Task) => {
    if (task) {
      setEditingTask(task);
      setFormData({
        name: task.name,
        symbol: task.symbol,
        tradingRules: task.tradingRules,
        interval: task.interval,
        dailyTime: task.dailyTime || '09:00',
        modelId: task.modelId,
        accountId: task.accountId,
      });
    } else {
      setEditingTask(null);
      setFormData({
        name: '',
        symbol: '',
        tradingRules: '',
        interval: '15m',
        dailyTime: '09:00',
        modelId: models?.find(m => m.isDefault)?.id || '',
        accountId: '',
      });
    }
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingTask(null);
    setShowSymbolDropdown(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingTask) {
      updateMutation.mutate({ id: editingTask.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleDelete = (id: string) => {
    if (confirm('确定要删除这个任务吗？')) {
      deleteMutation.mutate(id);
    }
  };

  // 过滤并排序交易对
  const filteredSymbols = tradingPairs
    ?.filter(
      (pair) =>
        pair.instId.toLowerCase().includes(symbolSearch.toLowerCase()) ||
        pair.baseCcy.toLowerCase().includes(symbolSearch.toLowerCase())
    )
    .sort((a, b) => a.instId.localeCompare(b.instId));

  const getIntervalLabel = (interval: string) => {
    return INTERVAL_OPTIONS.find((opt) => opt.value === interval)?.label || interval;
  };

  const getNextRunText = (task: Task) => {
    if (!task.isActive) return '已停止';
    if (!task.nextRunAt) return '等待调度';
    const nextRun = new Date(task.nextRunAt);
    const now = new Date();
    const diff = nextRun.getTime() - now.getTime();
    if (diff < 0) return '即将执行';
    if (diff < 60000) return '1分钟内';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟后`;
    return nextRun.toLocaleString();
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>交易任务管理</h1>
        <p>创建和管理您的自动化交易任务，支持多种时间间隔</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <div className="stat-label">任务总数</div>
          <div className="stat-value">{tasks?.length || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">运行中</div>
          <div className="stat-value" style={{ color: 'var(--success)' }}>
            {tasks?.filter((t) => t.isActive).length || 0}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">已停止</div>
          <div className="stat-value" style={{ color: 'var(--danger)' }}>
            {tasks?.filter((t) => !t.isActive).length || 0}
          </div>
        </div>
      </div>

      {/* Add Button */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">任务列表</h2>
          <button className="btn btn-primary" onClick={() => openModal()}>
            <Plus size={18} />
            添加任务
          </button>
        </div>

        {/* Tasks Table */}
        {tasksError ? (
          <div className="empty-state">
            <div className="empty-state-icon" style={{ color: '#ef4444' }}>
              <XCircle size={64} />
            </div>
            <p>加载任务失败</p>
            <p style={{ fontSize: '0.875rem', marginTop: '0.5rem', color: '#ef4444' }}>
              {(tasksError as Error).message}
            </p>
          </div>
        ) : tasksLoading ? (
          <div className="loading">
            <div className="spinner"></div>
          </div>
        ) : tasks?.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <Bot size={64} />
            </div>
            <p>暂无交易任务</p>
            <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
              点击上方按钮创建您的第一个交易任务
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>任务名称</th>
                  <th>交易对</th>
                  <th>执行间隔</th>
                  <th>模型</th>
                  <th>账户</th>
                  <th>状态</th>
                  <th>Token使用量</th>
                  <th>下次执行</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {tasks?.map((task) => (
                  <tr key={task.id}>
                    <td>{task.name}</td>
                    <td>
                      <span className="badge badge-secondary">{task.symbol}</span>
                    </td>
                    <td>
                      <span className="badge badge-secondary">
                        <Clock size={12} />
                        {getIntervalLabel(task.interval)}
                      </span>
                    </td>
                    <td>
                      {models?.find((m) => m.id === task.modelId)?.name || task.modelId}
                    </td>
                    <td>
                      {accounts?.find((a) => a.id === task.accountId)?.name || '-'}
                    </td>
                    <td>
                      {task.isActive ? (
                        <span className="badge badge-success">
                          <span
                            style={{
                              width: '8px',
                              height: '8px',
                              borderRadius: '50%',
                              background: 'currentColor',
                              display: 'inline-block',
                              marginRight: '4px',
                            }}
                          />
                          运行中
                        </span>
                      ) : (
                        <span className="badge badge-secondary">已停止</span>
                      )}
                    </td>
                    <td>
                      {task.totalTokens ? (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          {task.totalTokens.total.toLocaleString()}
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>-</span>
                      )}
                    </td>
                    <td>{getNextRunText(task)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className={togglingTasks[task.id] ? "btn btn-sm btn-secondary" : (task.isActive ? "btn btn-sm btn-danger" : "btn btn-sm btn-success")}
                          onClick={() => toggleMutation.mutate(task.id)}
                          disabled={togglingTasks[task.id]}
                        >
                          {togglingTasks[task.id] ? (
                            <Loader2 size={14} className="spin" />
                          ) : (
                            task.isActive ? <Square size={14} /> : <Play size={14} />
                          )}
                        </button>
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => {
                            if (confirm(`确定要立即执行任务"${task.name}"吗？`)) {
                              runOnceMutation.mutate(task.id);
                            }
                          }}
                          disabled={runOnceMutation.isPending}
                          title="立即执行一次"
                        >
                          <RotateCw size={14} />
                        </button>
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => openModal(task)}
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDelete(task.id)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal isOpen={isModalOpen} onClose={closeModal}>
        <div className="modal-header">
          <h3 className="modal-title">{editingTask ? '编辑任务' : '添加任务'}</h3>
          <button className="modal-close" onClick={closeModal}>
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="grid grid-cols-2">
              <div className="form-group">
                <label className="form-label">任务名称</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="例如：BTC趋势跟踪策略"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">AI模型</label>
                <select
                  className="form-select"
                  value={formData.modelId}
                  onChange={(e) => setFormData({ ...formData, modelId: e.target.value })}
                  required
                >
                  <option value="">选择模型</option>
                  {models?.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} {model.isDefault ? '(默认)' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">交易账户</label>
                <select
                  className="form-select"
                  value={formData.accountId}
                  onChange={(e) => setFormData({ ...formData, accountId: e.target.value })}
                  required
                >
                  <option value="">选择交易账户</option>
                  {accounts?.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name} {account.isSimulated ? '(模拟)' : '(实盘)'}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">交易对</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.symbol}
                    onChange={(e) => {
                      setFormData({ ...formData, symbol: e.target.value });
                      setSymbolSearch(e.target.value);
                      setShowSymbolDropdown(true);
                    }}
                    onFocus={() => setShowSymbolDropdown(true)}
                    placeholder="搜索或选择交易对"
                    required
                  />
                  {showSymbolDropdown && filteredSymbols && filteredSymbols.length > 0 && (
                    <div
                      style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        background: 'var(--bg-card)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '0.5rem',
                        maxHeight: '300px',
                        overflow: 'auto',
                        zIndex: 10,
                        marginTop: '4px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                      }}
                    >
                      <div style={{ padding: '0.5rem 0' }}>
                        {symbolSearch && (
                          <div style={{ padding: '0.5rem 1rem', fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                            搜索结果 ({filteredSymbols.length})
                          </div>
                        )}
                        {filteredSymbols.slice(0, 50).map((pair) => (
                            <div key={pair.instId}>
                              <div
                                style={{
                                  padding: '0.625rem 1rem',
                                  cursor: 'pointer',
                                  borderBottom: '1px solid var(--border-color)',
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  background: formData.symbol === pair.instId ? 'var(--bg-hover)' : 'transparent',
                                }}
                                onClick={() => {
                                  setFormData({ ...formData, symbol: pair.instId });
                                  setShowSymbolDropdown(false);
                                }}
                                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-hover)'; }}
                                onMouseLeave={(e) => { if (formData.symbol !== pair.instId) e.currentTarget.style.background = 'transparent'; }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                  <span style={{ fontWeight: 500 }}>{pair.baseCcy}</span>
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>/</span>
                                  <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{pair.quoteCcy}</span>
                                </div>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{pair.instId}</span>
                              </div>
                            </div>
                          ))}
                        {filteredSymbols.length > 50 && (
                          <div style={{ padding: '0.5rem 1rem', fontSize: '0.75rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
                            还有 {filteredSymbols.length - 50} 个结果
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2">
              <div className="form-group">
                <label className="form-label">执行间隔</label>
                <select
                  className="form-select"
                  value={formData.interval}
                  onChange={(e) => setFormData({ ...formData, interval: e.target.value as IntervalType })}
                >
                  {INTERVAL_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label} - {opt.description}
                    </option>
                  ))}
                </select>
              </div>

              {formData.interval === 'daily' && (
                <div className="form-group">
                  <label className="form-label">执行时间</label>
                  <input
                    type="time"
                    className="form-input"
                    value={formData.dailyTime}
                    onChange={(e) => setFormData({ ...formData, dailyTime: e.target.value })}
                    required
                  />
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">交易规则</label>
              <textarea
                className="form-textarea"
                value={formData.tradingRules}
                onChange={(e) => setFormData({ ...formData, tradingRules: e.target.value })}
                placeholder={TRADING_RULES_PLACEHOLDER}
                rows={14}
                required
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={closeModal}>
              取消
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending ? (
                <>
                  <Loader2 size={18} className="spin" />
                  保存中...
                </>
              ) : (
                '保存'
              )}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
