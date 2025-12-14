'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { useRouter } from 'next/navigation';

interface PlanDetails {
  name: string;
  price: number;
  messages_limit: number;
  clones_limit: number;
  documents_limit: number;
}

interface BillingPlan {
  current_plan: string;
  plan_details: PlanDetails;
  period_start: string | null;
  period_end: string | null;
  is_dummy_mode: boolean;
}

interface UsageStats {
  current_period: {
    clones: number;
    documents: number;
    messages: number;
  };
  today: {
    messages_count: number;
    tokens_used: number;
    tts_requests: number;
    avatar_requests: number;
  };
  timestamp: string;
}

export default function BillingPage() {
  const { user } = useAuth();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [plan, setPlan] = useState<BillingPlan | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [message, setMessage] =
    useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }
    void fetchBillingData();
  }, [user, router]);

  const fetchBillingData = async () => {
    setLoading(true);
    try {
      const [planData, usageData] = await Promise.all([
        apiClient.getBillingPlan(),
        apiClient.getBillingUsage(),
      ]);

      const typedPlan = planData as unknown as BillingPlan;
      const typedUsage = usageData as unknown as UsageStats;

      setPlan(typedPlan);
      setUsage(typedUsage);

      logger.info('Billing data fetched (frontend contract)', {
        plan: typedPlan.current_plan,
      });
    } catch (err) {
      logger.error('Failed to fetch billing data', { error: err });
      setMessage({
        type: 'error',
        text:
          err instanceof Error
            ? err.message
            : 'Unable to load billing information',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (targetPlan: string) => {
    setUpgrading(true);
    setMessage(null);
    try {
      const result = await apiClient.createCheckout(targetPlan);

      // Cas standard : redirection checkout
      if (result?.checkout_url) {
        window.location.href = result.checkout_url;
        return;
      }

      // Fallback (ne devrait pas arriver)
      setMessage({
        type: 'success',
        text: 'Upgrade initiated',
      });
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Upgrade failed',
      });
    } finally {
      setUpgrading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center">Loading billing information…</div>;
  }

  if (!plan || !usage) {
    return (
      <div className="p-8 text-center text-red-600">
        Failed to load billing data
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Billing & Usage</h1>

      {message && (
        <div
          className={`mb-4 ${
            message.type === 'error' ? 'text-red-600' : 'text-green-600'
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="bg-white shadow rounded p-6 mb-6">
        <h2 className="text-xl font-semibold mb-2">Current Plan</h2>
        <p className="text-lg">{plan.plan_details.name}</p>
        <p>${plan.plan_details.price}/month</p>

        {plan.current_plan === 'free' && (
          <button
            onClick={() => handleUpgrade('pro')}
            disabled={upgrading}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded"
          >
            {upgrading ? 'Processing…' : 'Upgrade to Pro'}
          </button>
        )}
      </div>

      <button
        onClick={() => router.push('/dashboard')}
        className="text-blue-600 underline"
      >
        ← Back to Dashboard
      </button>
    </div>
  );
}
