import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus,
  Edit2,
  Trash2,
  CheckCircle,
  XCircle,
  TestTube,
  Loader2,
  Wallet
} from 'lucide-react';
import { accountApi } from '../api/client';
import type { Account } from '../types';
import Modal from '../components/Modal';

export default function AccountSettings() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    exchange: 'okx',
    apiKey: '',
    apiSecret: '',
    passphrase: '',
    isSimulated: true,
  });

  const { data: accountsData, isLoading, error: accountsError } = useQuery({
    queryKey: ['accounts'],
    queryFn: async () => {
      console.log('[AccountSettings] Fetching accounts...');
      const response = await accountApi.getAll();
      console.log('[AccountSettings] Accounts response:', response);
      console.log('[AccountSettings] Accounts data:', response.data);
      return response.data as Account[];
    },
    initialData: [],
  });

  // 确保 accounts 是数组
  const accounts = Array.isArray(accountsData) ? accountsData : [];

  // 直接使用硬编码的交易所列表，绕过React Query问题
  const exchanges = [
    { id: 'okx', name: 'OKX', description: 'OKX交易所' },
    { id: 'binance', name: 'Binance', description: '币安交易所' },
  ];

  const createMutation = useMutation({
    mutationFn: accountApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      closeModal();
    },
    onError: (error: any) => {
      setApiError(error.response?.data?.detail || '创建账户失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => accountApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      closeModal();
    },
    onError: (error: any) => {
      setApiError(error.response?.data?.detail || '更新账户失败');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: accountApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
    },
  });

  const openModal = (account?: Account) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        name: account.name,
        exchange: account.exchange || 'okx',
        apiKey: account.apiKey,
        apiSecret: '', // 编辑时清空，需要用户重新输入
        passphrase: '', // 编辑时清空，需要用户重新输入
        isSimulated: account.isSimulated,
      });
    } else {
      setEditingAccount(null);
      setFormData({ name: '', exchange: 'okx', apiKey: '', apiSecret: '', passphrase: '', isSimulated: true });
    }
    setTestResult(null);
    setApiError(null);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingAccount(null);
    setFormData({ name: '', exchange: 'okx', apiKey: '', apiSecret: '', passphrase: '', isSimulated: true });
    setTestResult(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingAccount) {
      updateMutation.mutate({ id: editingAccount.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleTest = async () => {
    if (!formData.apiKey || !formData.apiSecret) {
      setTestResult({
        success: false,
        message: '请填写 API Key 和 API Secret',
      });
      return;
    }
    // Passphrase 仅 OKX 需要
    if (formData.exchange === 'okx' && !formData.passphrase) {
      setTestResult({
        success: false,
        message: '请填写 Passphrase',
      });
      return;
    }

    setIsTesting(true);
    setTestResult(null);

    try {
      // 无论是新增还是编辑，都使用表单中的数据测试
      const response = await accountApi.testConfig(formData);
      setTestResult({
        success: response.data?.success ?? false,
        message: response.data?.message || '测试完成',
      });
    } catch (error: any) {
      setTestResult({
        success: false,
        message: error.response?.data?.message || '测试失败',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleDelete = (id: string) => {
    if (confirm('确定要删除这个交易账户吗？')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>交易账户</h1>
        <p>管理您的OKX交易账户配置，支持添加多个账户并测试连通性</p>
      </div>

      <div className="grid grid-cols-3" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <div className="stat-label">账户总数</div>
          <div className="stat-value">{accounts?.length || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">实盘账户</div>
          <div className="stat-value">
            {accounts?.filter(a => !a.isSimulated).length || 0}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">模拟账户</div>
          <div className="stat-value">
            {accounts?.filter(a => a.isSimulated).length || 0}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">账户列表</h2>
          <button className="btn btn-primary" onClick={() => openModal()}>
            <Plus size={18} />
            添加账户
          </button>
        </div>

        {accountsError ? (
          <div className="empty-state">
            <div className="empty-state-icon" style={{ color: '#ef4444' }}>
              <XCircle size={64} />
            </div>
            <p>加载账户失败</p>
            <p style={{ fontSize: '0.875rem', marginTop: '0.5rem', color: '#ef4444' }}>
              {(accountsError as Error).message}
            </p>
          </div>
        ) : isLoading ? (
          <div className="loading">
            <div className="spinner"></div>
          </div>
        ) : accounts?.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <Wallet size={64} />
            </div>
            <p>暂无交易账户</p>
            <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
              点击上方按钮添加您的第一个交易账户
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>账户名称</th>
                  <th>API Key</th>
                  <th>类型</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {accounts?.map((account) => (
                  <tr key={account.id}>
                    <td>{account.name}</td>
                    <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {account.apiKey.substring(0, 8)}***
                    </td>
                    <td>
                      {account.isSimulated ? (
                        <span className="badge badge-warning">模拟</span>
                      ) : (
                        <span className="badge badge-success">实盘</span>
                      )}
                    </td>
                    <td>{new Date(account.createdAt).toLocaleDateString()}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => openModal(account)}
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDelete(account.id)}
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
          <h3 className="modal-title">
            {editingAccount ? '编辑账户' : '添加账户'}
          </h3>
          <button className="modal-close" onClick={closeModal}>
            <XCircle size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label className="form-label">账户名称</label>
              <input
                type="text"
                className="form-input"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="例如：我的OKX账户"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">交易所</label>
              <select
                className="form-select"
                value={formData.exchange}
                onChange={(e) => setFormData({ ...formData, exchange: e.target.value })}
              >
                {exchanges?.map((exchange) => (
                  <option key={exchange.id} value={exchange.id}>
                    {exchange.name} - {exchange.description}
                  </option>
                ))}
              </select>
              {exchanges?.length === 0 && (
                <div style={{ color: 'red', fontSize: '12px' }}>
                  交易所列表为空 - 请检查网络请求
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">API Key</label>
              <input
                type="text"
                className="form-input"
                value={formData.apiKey}
                onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                placeholder="your-api-key"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">API Secret</label>
              <input
                type="password"
                className="form-input"
                value={formData.apiSecret}
                onChange={(e) => setFormData({ ...formData, apiSecret: e.target.value })}
                placeholder={editingAccount ? '请重新输入API Secret' : 'your-api-secret'}
                required
              />
              {editingAccount && (
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  编辑账户时需要重新输入API Secret
                </p>
              )}
            </div>

            <div className="form-group" style={{ display: formData.exchange === 'okx' ? 'block' : 'none' }}>
              <label className="form-label">Passphrase {formData.exchange !== 'okx' && '(仅OKX需要)'}</label>
              <input
                type="password"
                className="form-input"
                value={formData.passphrase}
                onChange={(e) => setFormData({ ...formData, passphrase: e.target.value })}
                placeholder={editingAccount ? '请重新输入Passphrase' : 'your-passphrase'}
              />
              {editingAccount && formData.exchange === 'okx' && (
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                  编辑账户时需要重新输入Passphrase
                </p>
              )}
            </div>

            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={formData.isSimulated}
                  onChange={(e) => setFormData({ ...formData, isSimulated: e.target.checked })}
                />
                模拟交易模式
              </label>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                勾选后使用模拟盘进行交易，不会使用真实资金
              </p>
            </div>

            <div className="form-group">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleTest}
                disabled={isTesting || !formData.apiKey || !formData.apiSecret || (formData.exchange === 'okx' && !formData.passphrase)}
              >
                {isTesting ? (
                  <>
                    <Loader2 size={18} className="spin" />
                    测试中...
                  </>
                ) : (
                  <>
                    <TestTube size={18} />
                    测试连通性
                  </>
                )}
              </button>
            </div>

            {testResult && (
              <div
                className={`badge ${testResult.success ? 'badge-success' : 'badge-danger'}`}
                style={{ width: '100%', padding: '1rem', justifyContent: 'flex-start' }}
              >
                {testResult.success ? (
                  <CheckCircle size={18} />
                ) : (
                  <XCircle size={18} />
                )}
                <div>{testResult.message}</div>
              </div>
            )}

            {apiError && (
              <div
                className="badge badge-danger"
                style={{ width: '100%', padding: '1rem', justifyContent: 'flex-start' }}
              >
                <XCircle size={18} />
                <div>{apiError}</div>
              </div>
            )}
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
