// Model Types
// 按实际调用方式分类：openai-compatible 使用 ChatOpenAI，其他使用特定客户端
export type LLMProvider = 'openai-compatible' | 'azure' | 'anthropic' | 'google';

export interface Model {
  id: string;
  name: string;
  provider: LLMProvider;
  baseUrl: string;
  apiKey: string;
  isDefault: boolean;
  createdAt: string;
}

export interface ModelTestResult {
  success: boolean;
  message: string;
  latency?: number;
}

// Account Types
export interface Account {
  id: string;
  name: string;
  exchange: string;
  apiKey: string;
  apiSecret: string;
  passphrase: string;
  isSimulated: boolean;
  createdAt: string;
}

// Task Types
export type IntervalType = '1m' | '5m' | '15m' | '1h' | '4h' | 'daily';

export interface Task {
  id: string;
  name: string;
  symbol: string;
  tradingRules: string;
  interval: IntervalType;
  dailyTime?: string; // For daily interval, e.g., "09:00"
  modelId: string;
  accountId: string;
  isActive: boolean;
  lastRunAt?: string;
  nextRunAt?: string;
  createdAt: string;
  totalTokens?: {
    input: number;
    output: number;
    total: number;
  };
}

// Execution Types
export interface ToolCall {
  tool: string;
  params: Record<string, any>;
  result: any;
  timestamp: string;
}

export interface Iteration {
  iteration: number;
  maxIterations: number;
  messages: any[];
  toolCalls: ToolCall[];
  tokens: {
    input: number;
    output: number;
    total: number;
  };
}

export interface ExecutionDecision {
  decision: 'BUY' | 'SELL' | 'HOLD' | string;
  reason: string;
  confidence: number;
  actionTaken: boolean;
}

export interface Execution {
  id: string;
  taskId: string;
  taskName: string;
  symbol: string;
  tradingRules?: string;
  accountId?: string;
  accountName?: string;
  modelId?: string;
  modelName?: string;
  modelProvider?: string;
  status: 'running' | 'completed' | 'failed';
  startTime: string;
  endTime?: string;
  iterations: Iteration[];
  finalDecision?: ExecutionDecision;
  error?: string;
  totalTokens?: {
    input: number;
    output: number;
    total: number;
  };
}

// OKX Types
export interface TradingPair {
  instId: string;
  instType: string;
  baseCcy: string;
  quoteCcy: string;
  state: string;
}
