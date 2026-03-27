import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Plus, 
  Edit2, 
  Trash2, 
  CheckCircle, 
  XCircle, 
  TestTube,
  Star,
  Loader2,
  Settings
} from 'lucide-react';
import { modelApi } from '../api/client';
import type { Model, ModelTestResult, LLMProvider } from '../types';
import Modal from '../components/Modal';

// 按实际调用方式分类的提供商选项
const PROVIDER_OPTIONS: { value: LLMProvider; label: string; description: string }[] = [
  {
    value: 'openai-compatible',
    label: 'OpenAI 兼容 API',
    description: '支持 OpenAI、火山引擎、DeepSeek、通义千问、智谱GLM 等'
  },
  { value: 'azure', label: 'Azure OpenAI', description: '微软 Azure OpenAI 服务' },
  { value: 'anthropic', label: 'Anthropic Claude', description: 'Claude 系列模型' },
  { value: 'google', label: 'Google Gemini', description: 'Google Gemini 系列模型' },
];

export default function ModelSettings() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<Model | null>(null);
  const [testResult, setTestResult] = useState<ModelTestResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    provider: 'openai-compatible' as LLMProvider,
    baseUrl: '',
    apiKey: '',
  });

  // Fetch models
  const { data: models, isLoading } = useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const response = await modelApi.getAll();
      return response.data as Model[];
    },
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: modelApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
      closeModal();
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => modelApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
      closeModal();
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: modelApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
    },
  });

  // Set default mutation
  const setDefaultMutation = useMutation({
    mutationFn: (id: string) => modelApi.update(id, { isDefault: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
    },
  });

  const openModal = (model?: Model) => {
    if (model) {
      setEditingModel(model);
      setFormData({
        name: model.name,
        provider: model.provider || 'openai-compatible',
        baseUrl: model.baseUrl,
        apiKey: model.apiKey,
      });
    } else {
      setEditingModel(null);
      setFormData({ name: '', provider: 'openai-compatible', baseUrl: '', apiKey: '' });
    }
    setTestResult(null);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingModel(null);
    setFormData({ name: '', provider: 'openai-compatible', baseUrl: '', apiKey: '' });
    setTestResult(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingModel) {
      updateMutation.mutate({ id: editingModel.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleTest = async () => {
    if (!formData.name || !formData.baseUrl || !formData.apiKey) {
      setTestResult({
        success: false,
        message: '请填写模型名称、Base URL和API Key',
      });
      return;
    }

    setIsTesting(true);
    setTestResult(null);

    try {
      const response = await modelApi.test({
        name: formData.name,
        provider: formData.provider,
        baseUrl: formData.baseUrl,
        apiKey: formData.apiKey,
      });
      setTestResult(response.data as ModelTestResult);
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
    if (confirm('确定要删除这个模型吗？')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>模型设置</h1>
        <p>管理您的AI模型配置，支持添加多个模型并测试连通性</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <div className="stat-label">模型总数</div>
          <div className="stat-value">{models?.length || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">默认模型</div>
          <div className="stat-value">
            {models?.find(m => m.isDefault)?.name || '-'}
          </div>
        </div>
      </div>

      {/* Add Button */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">模型列表</h2>
          <button className="btn btn-primary" onClick={() => openModal()}>
            <Plus size={18} />
            添加模型
          </button>
        </div>

        {/* Models Table */}
        {isLoading ? (
          <div className="loading">
            <div className="spinner"></div>
          </div>
        ) : models?.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <Settings size={64} />
            </div>
            <p>暂无模型配置</p>
            <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
              点击上方按钮添加您的第一个模型
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>模型名称</th>
                  <th>Base URL</th>
                  <th>默认</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {models?.map((model) => (
                  <tr key={model.id}>
                    <td>{model.name}</td>
                    <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {model.baseUrl}
                    </td>
                    <td>
                      {model.isDefault ? (
                        <span className="badge badge-success">
                          <Star size={12} />
                          默认
                        </span>
                      ) : (
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => setDefaultMutation.mutate(model.id)}
                        >
                          设为默认
                        </button>
                      )}
                    </td>
                    <td>{new Date(model.createdAt).toLocaleDateString()}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => openModal(model)}
                        >
                          <Edit2 size={14} />
                        </button>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDelete(model.id)}
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
            {editingModel ? '编辑模型' : '添加模型'}
          </h3>
          <button className="modal-close" onClick={closeModal}>
            <XCircle size={24} />
          </button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label className="form-label">提供商</label>
              <select
                className="form-input"
                value={formData.provider}
                onChange={(e) => setFormData({ ...formData, provider: e.target.value as LLMProvider })}
                required
              >
                {PROVIDER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <small style={{ color: 'var(--text-secondary)', marginTop: '0.25rem', display: 'block' }}>
                {PROVIDER_OPTIONS.find(opt => opt.value === formData.provider)?.description}
              </small>
            </div>

            <div className="form-group">
              <label className="form-label">模型名称</label>
              <input
                type="text"
                className="form-input"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="例如：gpt-4o 或 endpoint-xxx"
                required
              />
              <small style={{ color: 'var(--text-secondary)', marginTop: '0.25rem', display: 'block' }}>
                OpenAI格式填写模型名(gpt-4o)，火山引擎填写Endpoint ID
              </small>
            </div>

            <div className="form-group">
              <label className="form-label">Base URL</label>
              <input
                type="url"
                className="form-input"
                value={formData.baseUrl}
                onChange={(e) => setFormData({ ...formData, baseUrl: e.target.value })}
                placeholder="https://api.openai.com/v1"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">API Key</label>
              <input
                type="password"
                className="form-input"
                value={formData.apiKey}
                onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                placeholder="your-api-key"
                required
              />
            </div>

            {/* Test Connection */}
            <div className="form-group">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleTest}
                disabled={isTesting || !formData.baseUrl || !formData.apiKey}
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

            {/* Test Result */}
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
                <div>
                  <div>{testResult.message}</div>
                  {testResult.latency && (
                    <div style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                      延迟: {testResult.latency}ms
                    </div>
                  )}
                </div>
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
