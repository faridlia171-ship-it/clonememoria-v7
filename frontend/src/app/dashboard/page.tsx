'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { CloneCard } from '@/components/clone/CloneCard';
import { CloneForm } from '@/components/forms/CloneForm';
import { apiClient } from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { CloneWithStats, ToneConfig } from '@/types';
import { Plus, Loader2 } from 'lucide-react';

export default function DashboardPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();

  const [clones, setClones] = useState<CloneWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] =
