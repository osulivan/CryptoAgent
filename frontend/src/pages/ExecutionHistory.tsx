import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  ChevronRight,
  ChevronDown,
  Terminal,
  Bot,
  TrendingUp,
  AlertTriangle,
  Eye,
  FileText,
  X,
  Image,
  Trash2
} from 'lucide-react';
import { executionApi, taskApi } from '../api/client';
import type { Execution, Task } from '../types';

export default function ExecutionHistory() {
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);
  const [expandedIterations, setExpandedIterations] = useState<number[]>([]);
  const [showRulesModal, setShowRulesModal] = useState(false);
  const [showChartModal, setShowChartModal] = useState(false);
  const [chartUrl, setChartUrl] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ type: 'single' | 'all'; id?: string } | null>(null);
  const [showOnlyTrades, setShowOnlyTrades] = useState(false);

  // 获取API基础URL（用于图片等静态资源）
  const getApiBaseUrl = () => {
    return import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
  };

  // 删除执行记录
  const handleDelete = async () => {
    if (!deleteTarget) return;

    try {
      if (deleteTarget.type === 'single' && deleteTarget.id) {
        await executionApi.delete(deleteTarget.id);
        if (selectedExecution?.id === deleteTarget.id) {
          setSelectedExecution(null);
        }
      } else if (deleteTarget.type === 'all') {
        await executionApi.deleteAll();
        setSelectedExecution(null);
      }
      // 刷新列表
      window.location.reload();
    } catch (error) {
      console.error('删除失败:', error);
      alert('删除失败');
    }
    setShowDeleteConfirm(false);
    setDeleteTarget(null);
  };

  const filterToolResult = (result: any, toolName: string) => {
    if (!result) return result;
    const filtered = { ...result };
    if (toolName === 'get_market_data' && filtered.chart_url) {
      delete filtered.chart_url;
    }
    if (toolName === 'get_market_data' && filtered.chart_local_path) {
      delete filtered.chart_local_path;
    }
    return filtered;
  };

  const getChartLocalPath = (result: any, toolName: string): string | null => {
    if (!result || toolName !== 'get_market_data') return null;
    return result.chart_local_path || null;
  };

  // Fetch executions
  const { data: executions, isLoading } = useQuery({
    queryKey: ['executions'],
    queryFn: async () => {
      const response = await executionApi.getAll({ limit: 50 });
      return response.data as Execution[];
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Fetch tasks for names
  const { data: tasks } = useQuery({
    queryKey: ['tasks'],
    queryFn: async () => {
      const response = await taskApi.getAll();
      return response.data as Task[];
    },
  });

  const toggleIteration = (iteration: number) => {
    setExpandedIterations((prev) =>
      prev.includes(iteration) ? prev.filter((i) => i !== iteration) : [...prev, iteration]
    );
  };

  const getTaskName = (taskId: string) => {
    return tasks?.find((t) => t.id === taskId)?.name || taskId;
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running':
        return (
          <span className="badge badge-warning">
            <Loader2 size={12} className="spin" />
            执行中
          </span>
        );
      case 'completed':
        return (
          <span className="badge badge-success">
            <CheckCircle size={12} />
            已完成
          </span>
        );
      case 'failed':
        return (
          <span className="badge badge-danger">
            <XCircle size={12} />
            失败
          </span>
        );
      default:
        return <span className="badge badge-secondary">{status}</span>;
    }
  };

  const getDecisionBadge = (decision?: string) => {
    switch (decision) {
      case 'BUY':
      case 'OPEN':
        return (
          <span className="badge" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}>
            <TrendingUp size={12} />
            开仓
          </span>
        );
      case 'SELL':
      case 'CLOSE':
        return (
          <span className="badge" style={{ background: 'var(--danger-bg)', color: 'var(--danger)' }}>
            <TrendingUp size={12} style={{ transform: 'rotate(180deg)' }} />
            平仓
          </span>
        );
      case 'HOLD':
        return (
          <span className="badge badge-secondary">
            <Clock size={12} />
            观望
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1>执行历史</h1>
        <p>查看每次任务执行的详细信息和Agent决策过程</p>
      </div>

      {isLoading ? (
        <div className="loading">
          <div className="spinner"></div>
        </div>
      ) : executions?.length === 0 ? (
        <div className="card empty-state">
          <div className="empty-state-icon">
            <Terminal size={64} />
          </div>
          <p>暂无执行记录</p>
          <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
            运行任务后将在这里显示执行历史
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1.5rem' }}>
          {/* Execution List */}
          <div>
            <div className="card">
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                <h2 className="card-title">执行记录</h2>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  {/* 仅显示交易按钮 */}
                  <button
                    onClick={() => setShowOnlyTrades(!showOnlyTrades)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      padding: '0.375rem 0.75rem',
                      fontSize: '0.75rem',
                      background: showOnlyTrades ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                      color: showOnlyTrades ? 'white' : 'var(--text-secondary)',
                      border: 'none',
                      borderRadius: '0.25rem',
                      cursor: 'pointer',
                    }}
                  >
                    <TrendingUp size={14} />
                    {showOnlyTrades ? '显示全部' : '仅显示交易'}
                  </button>
                  {executions && executions.length > 0 && (
                    <button
                      onClick={() => {
                        setDeleteTarget({ type: 'all' });
                        setShowDeleteConfirm(true);
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        padding: '0.375rem 0.75rem',
                        fontSize: '0.75rem',
                        background: 'var(--danger)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.25rem',
                        cursor: 'pointer',
                      }}
                    >
                      <Trash2 size={14} />
                      全部删除
                    </button>
                  )}
                </div>
              </div>
              <div style={{ maxHeight: '600px', overflow: 'auto' }}>
                {executions
                  ?.filter((execution) => {
                    if (!showOnlyTrades) return true;
                    // 仅显示有交易的记录：决策为 OPEN 或 CLOSE
                    return execution.finalDecision?.decision === 'OPEN' || execution.finalDecision?.decision === 'CLOSE';
                  })
                  ?.map((execution) => (
                  <div
                    key={execution.id}
                    style={{
                      padding: '1rem',
                      borderBottom: '1px solid var(--border-color)',
                      cursor: 'pointer',
                      background: selectedExecution?.id === execution.id ? 'rgba(88, 166, 255, 0.15)' : 'transparent',
                      borderLeft: selectedExecution?.id === execution.id ? '3px solid var(--accent-primary)' : '3px solid transparent',
                    }}
                    onClick={() => setSelectedExecution(execution)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <span style={{ fontWeight: 500 }}>{getTaskName(execution.taskId)}</span>
                      {getStatusBadge(execution.status)}
                    </div>
                    <div
                      style={{
                        fontSize: '0.875rem',
                        color: 'var(--text-secondary)',
                        marginBottom: '0.5rem',
                      }}
                    >
                      {execution.symbol} · {execution.modelName || '-'} · {execution.accountName || '-'} · {new Date(execution.startTime).toLocaleString()}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        {getDecisionBadge(execution.finalDecision?.decision)}
                        {execution.finalDecision && (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            置信度: {(execution.finalDecision.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteTarget({ type: 'single', id: execution.id });
                          setShowDeleteConfirm(true);
                        }}
                        style={{
                          padding: '0.25rem',
                          background: 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          color: 'var(--text-secondary)',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                        title="删除"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Execution Detail */}
          <div>
            {selectedExecution ? (
              <div className="card">
                <div className="card-header">
                  <h2 className="card-title">执行详情</h2>
                </div>

                {/* Basic Info */}
                <div style={{ marginBottom: '1.5rem' }}>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(2, 1fr)',
                      gap: '1rem',
                      marginBottom: '1rem',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>任务</div>
                      <div>{getTaskName(selectedExecution.taskId)}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>交易账户</div>
                      <div>{selectedExecution.accountName || '-'}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>模型</div>
                      <div>{selectedExecution.modelName || '-'}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>交易对</div>
                      <div>{selectedExecution.symbol}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>开始时间</div>
                      <div>{new Date(selectedExecution.startTime).toLocaleString()}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>状态</div>
                      <div>{getStatusBadge(selectedExecution.status)}</div>
                    </div>
                  </div>
                  
                  {/* 总 Token 使用量 */}
                  {selectedExecution.totalTokens && (
                    <div
                      style={{
                        background: 'var(--bg-dark)',
                        padding: '0.75rem 1rem',
                        borderRadius: '0.5rem',
                        marginBottom: '1rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>总 Token 使用量</span>
                      <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.875rem' }}>
                        <span>输入: <strong>{selectedExecution.totalTokens.input}</strong></span>
                        <span>输出: <strong>{selectedExecution.totalTokens.output}</strong></span>
                        <span>总计: <strong>{selectedExecution.totalTokens.total}</strong></span>
                      </div>
                    </div>
                  )}

                  {selectedExecution.finalDecision && (
                    <div
                      style={{
                        background: 'var(--bg-dark)',
                        padding: '1rem',
                        borderRadius: '0.5rem',
                        marginBottom: '1rem',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: '0.5rem',
                        }}
                      >
                        <span style={{ fontWeight: 500 }}>最终决策</span>
                        {getDecisionBadge(selectedExecution.finalDecision.decision)}
                      </div>
                      <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                        {selectedExecution.finalDecision.reason}
                      </div>
                      <div style={{ fontSize: '0.75rem', marginTop: '0.5rem' }}>
                        置信度: {(selectedExecution.finalDecision.confidence * 100).toFixed(1)}% ·
                        已执行: {selectedExecution.finalDecision.actionTaken ? '是' : '否'}
                      </div>
                    </div>
                  )}

                  {selectedExecution.error && (
                    <div
                      style={{
                        background: 'var(--danger-bg)',
                        padding: '1rem',
                        borderRadius: '0.5rem',
                        color: 'var(--danger)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <AlertTriangle size={16} />
                        <span style={{ fontWeight: 500 }}>错误</span>
                      </div>
                      <div style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                        {selectedExecution.error}
                      </div>
                    </div>
                  )}
                </div>

                {/* Trading Rules Button */}
                {selectedExecution.tradingRules && (
                  <div style={{ marginBottom: '1rem' }}>
                    <button
                      onClick={() => setShowRulesModal(true)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.5rem 1rem',
                        background: 'var(--primary)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.375rem',
                        cursor: 'pointer',
                        fontSize: '0.875rem',
                      }}
                    >
                      <FileText size={16} />
                      查看交易规则
                    </button>
                  </div>
                )}

                {/* Iterations */}
                <div>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
                    执行迭代 ({selectedExecution.iterations.length})
                  </h3>
                  {selectedExecution.iterations.map((iteration, index) => (
                    <div
                      key={index}
                      style={{
                        border: '1px solid var(--border-color)',
                        borderRadius: '0.5rem',
                        marginBottom: '0.75rem',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        style={{
                          padding: '0.75rem 1rem',
                          background: 'var(--bg-dark)',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          cursor: 'pointer',
                        }}
                        onClick={() => toggleIteration(index)}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          {expandedIterations.includes(index) ? (
                            <ChevronDown size={16} />
                          ) : (
                            <ChevronRight size={16} />
                          )}
                          <span>迭代 {iteration.iteration}</span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            {selectedExecution.iterations.length > 0 && index === selectedExecution.iterations.length - 1 && iteration.toolCalls.length === 0 ? '(最终决策)' : `(${iteration.toolCalls.length} 个工具调用)`}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                          Tokens: {iteration.tokens.total}
                        </div>
                      </div>

                      {expandedIterations.includes(index) && (
                        <div style={{ padding: '1rem' }}>
                          {/* Final Decision - show for last iteration without tool calls */}
                          {selectedExecution.iterations.length > 0 && index === selectedExecution.iterations.length - 1 && iteration.toolCalls.length === 0 && selectedExecution.finalDecision && (
                            <div
                              style={{
                                marginBottom: '1rem',
                                padding: '0.75rem',
                                background: 'var(--bg-card)',
                                borderRadius: '0.375rem',
                                border: '1px solid var(--primary)',
                              }}
                            >
                              <div
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '0.5rem',
                                  marginBottom: '0.5rem',
                                  color: 'var(--primary)',
                                  fontWeight: 500,
                                }}
                              >
                                <TrendingUp size={14} />
                                <span>最终决策</span>
                              </div>
                              <pre
                                style={{
                                  fontSize: '0.75rem',
                                  background: 'var(--bg-card)',
                                  padding: '0.5rem',
                                  borderRadius: '0.25rem',
                                  overflow: 'auto',
                                  maxHeight: '200px',
                                  wordBreak: 'break-word',
                                  whiteSpace: 'pre-wrap',
                                }}
                              >
                                {JSON.stringify(selectedExecution.finalDecision, null, 2)}
                              </pre>
                            </div>
                          )}

                          {/* Tool Calls */}
                          {iteration.toolCalls.map((toolCall, toolIndex) => (
                            <div
                              key={toolIndex}
                              style={{
                                marginBottom: '0.75rem',
                                padding: '0.75rem',
                                background: 'var(--bg-dark)',
                                borderRadius: '0.375rem',
                              }}
                            >
                              <div
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '0.5rem',
                                  marginBottom: '0.5rem',
                                }}
                              >
                                <Bot size={14} />
                                <span style={{ fontWeight: 500 }}>{toolCall.tool}</span>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                  {new Date(toolCall.timestamp).toLocaleTimeString()}
                                </span>
                              </div>
                              <div style={{ fontSize: '0.875rem' }}>
                                <div style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                                  参数:
                                </div>
                                <pre
                                  style={{
                                    fontSize: '0.75rem',
                                    background: 'var(--bg-card)',
                                    padding: '0.5rem',
                                    borderRadius: '0.25rem',
                                    overflow: 'auto',
                                    maxHeight: '100px',
                                  }}
                                >
                                  {JSON.stringify(toolCall.params, null, 2)}
                                </pre>
                              </div>
                              {toolCall.result && (
                                <div style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                    <span style={{ color: 'var(--text-secondary)' }}>结果:</span>
                                    {getChartLocalPath(toolCall.result, toolCall.tool) && (
                                      <button
                                        onClick={() => {
                                          const path = getChartLocalPath(toolCall.result, toolCall.tool);
                                          if (path) {
                                            const filename = path.split('/').pop();
                                            const baseUrl = getApiBaseUrl().replace('/api', '');
                                            setChartUrl(`${baseUrl}/api/charts/${filename}`);
                                            setShowChartModal(true);
                                          }
                                        }}
                                        style={{
                                          display: 'flex',
                                          alignItems: 'center',
                                          gap: '0.25rem',
                                          padding: '0.25rem 0.5rem',
                                          fontSize: '0.75rem',
                                          background: 'var(--primary)',
                                          color: 'white',
                                          border: 'none',
                                          borderRadius: '0.25rem',
                                          cursor: 'pointer',
                                        }}
                                      >
                                        <Image size={12} />
                                        查看K线
                                      </button>
                                    )}
                                  </div>
                                  <pre
                                    style={{
                                      fontSize: '0.75rem',
                                      background: 'var(--bg-card)',
                                      padding: '0.5rem',
                                      borderRadius: '0.25rem',
                                      overflow: 'auto',
                                      maxHeight: '150px',
                                      wordBreak: 'break-word',
                                      whiteSpace: 'pre-wrap',
                                    }}
                                  >
                                    {JSON.stringify(filterToolResult(toolCall.result, toolCall.tool), null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="card empty-state">
                <div className="empty-state-icon">
                  <Eye size={64} />
                </div>
                <p>选择左侧记录查看详情</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Trading Rules Modal */}
      {showRulesModal && selectedExecution && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setShowRulesModal(false)}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              borderRadius: '0.5rem',
              padding: '1.5rem',
              maxWidth: '600px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto',
              margin: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1rem',
              }}
            >
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>交易规则</h2>
              <button
                onClick={() => setShowRulesModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--text-secondary)',
                }}
              >
                <X size={20} />
              </button>
            </div>
            <pre
              style={{
                background: 'var(--bg-dark)',
                padding: '1rem',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {selectedExecution.tradingRules}
            </pre>
          </div>
        </div>
      )}

      {showChartModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setShowChartModal(false)}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              borderRadius: '0.5rem',
              padding: '1rem',
              maxWidth: '90vw',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
              margin: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1rem',
              }}
            >
              <span style={{ fontWeight: 500 }}>K线图表</span>
              <button
                onClick={() => setShowChartModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--text-secondary)',
                }}
              >
                <X size={20} />
              </button>
            </div>
            <div style={{ overflow: 'auto', flex: 1 }}>
              <img
                src={chartUrl}
                alt="K线图表"
                style={{
                  maxWidth: '100%',
                  maxHeight: 'calc(90vh - 80px)',
                  height: 'auto',
                  borderRadius: '0.375rem',
                  display: 'block',
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => {
            setShowDeleteConfirm(false);
            setDeleteTarget(null);
          }}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              borderRadius: '0.5rem',
              padding: '1.5rem',
              maxWidth: '400px',
              width: '90%',
              margin: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.125rem' }}>
                <AlertTriangle size={20} style={{ color: 'var(--warning)', marginRight: '0.5rem', verticalAlign: 'middle' }} />
                确认删除
              </h3>
            </div>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              {deleteTarget?.type === 'all'
                ? '确定要删除所有执行记录吗？此操作不可恢复。'
                : '确定要删除这条执行记录吗？此操作不可恢复。'}
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeleteTarget(null);
                }}
                style={{
                  padding: '0.5rem 1rem',
                  background: 'var(--bg-dark)',
                  color: 'var(--text-primary)',
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                }}
              >
                取消
              </button>
              <button
                onClick={handleDelete}
                style={{
                  padding: '0.5rem 1rem',
                  background: 'var(--danger)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                }}
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
