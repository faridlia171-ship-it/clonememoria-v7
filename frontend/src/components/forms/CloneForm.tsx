'use client';

import { useState } from 'react';
import { ToneConfig } from '@/types';

interface CloneFormProps {
  initialData?: {
    name: string;
    description: string;
    tone_config: ToneConfig;
  };
  onSubmit: (data: {
    name: string;
    description: string;
    tone_config: ToneConfig;
  }) => Promise<void>;
  onCancel: () => void;
  submitLabel?: string;
}

export function CloneForm({
  initialData,
  onSubmit,
  onCancel,
  submitLabel = 'Create Clone',
}: CloneFormProps) {
  const [name, setName] = useState(initialData?.name || '');
  const [description, setDescription] = useState(
    initialData?.description || ''
  );
  const [warmth, setWarmth] = useState(
    initialData?.tone_config.warmth || 0.7
  );
  const [humor, setHumor] = useState(initialData?.tone_config.humor || 0.5);
  const [formality, setFormality] = useState(
    initialData?.tone_config.formality || 0.3
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await onSubmit({
        name,
        description,
        tone_config: { warmth, humor, formality },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="name" className="label">
          Name
        </label>
        <input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="input-field"
          placeholder="e.g., Papa, Maman, Best Friend..."
          maxLength={100}
        />
        <p className="mt-1 text-xs text-gray-500">
          What do you call this person?
        </p>
      </div>

      <div>
        <label htmlFor="description" className="label">
          Description
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="input-field min-h-[120px] resize-y"
          placeholder="Describe this person's personality, quirks, way of speaking..."
          maxLength={2000}
        />
        <p className="mt-1 text-xs text-gray-500">
          Help the AI understand their unique personality
        </p>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-medium text-gray-700">
          Personality Traits
        </h3>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label htmlFor="warmth" className="text-sm text-gray-600">
              Warmth & Affection
            </label>
            <span className="text-sm font-medium text-rose-500">
              {Math.round(warmth * 100)}%
            </span>
          </div>
          <input
            id="warmth"
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={warmth}
            onChange={(e) => setWarmth(parseFloat(e.target.value))}
            className="w-full accent-rose-400"
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label htmlFor="humor" className="text-sm text-gray-600">
              Humor & Playfulness
            </label>
            <span className="text-sm font-medium text-sage-500">
              {Math.round(humor * 100)}%
            </span>
          </div>
          <input
            id="humor"
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={humor}
            onChange={(e) => setHumor(parseFloat(e.target.value))}
            className="w-full accent-sage-400"
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label htmlFor="formality" className="text-sm text-gray-600">
              Formality
            </label>
            <span className="text-sm font-medium text-gray-500">
              {Math.round(formality * 100)}%
            </span>
          </div>
          <input
            id="formality"
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={formality}
            onChange={(e) => setFormality(parseFloat(e.target.value))}
            className="w-full accent-gray-400"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl">
          <p className="text-rose-700 text-sm">{error}</p>
        </div>
      )}

      <div className="flex space-x-4">
        <button
          type="submit"
          disabled={loading}
          className="flex-1 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Saving...' : submitLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={loading}
          className="flex-1 btn-secondary disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
