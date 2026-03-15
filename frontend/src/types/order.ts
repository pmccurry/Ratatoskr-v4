export interface PaperOrder {
  id: string;
  signalId: string;
  riskDecisionId: string;
  strategyId: string;
  symbol: string;
  market: string;
  side: string;
  orderType: string;
  signalType: string;
  requestedQty: number;
  requestedPrice: number | null;
  filledQty: number;
  filledAvgPrice: number | null;
  status: string;
  rejectionReason: string | null;
  executionMode: string;
  brokerOrderId: string | null;
  brokerAccountId: string | null;
  contractMultiplier: number;
  submittedAt: string;
  filledAt: string | null;
  createdAt: string;
}

export interface PaperFill {
  id: string;
  orderId: string;
  strategyId: string;
  symbol: string;
  side: string;
  qty: number;
  referencePrice: number;
  price: number;
  grossValue: number;
  fee: number;
  slippageBps: number;
  slippageAmount: number;
  netValue: number;
  filledAt: string;
  createdAt: string;
}
