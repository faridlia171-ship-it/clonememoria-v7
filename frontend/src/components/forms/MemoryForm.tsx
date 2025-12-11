'use client';

import { useState } from 'react';

interface MemoryFormProps {
  onSubmit: (data: { title?: string; content: string }) => Promise<void>;
  onCancel: () => void;
}

export function MemoryForm({ onSubmit, onCancel }: MemoryFormProps) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await onSubmit({
        title: title.trim() || undefined,
        content,
      });
      setTitle('');
      setContent('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="title" className="label">
          Title (Optional)
        </label>
        <input
          id="title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="input-field"
          placeholder="A brief title for this memory..."
          maxLength={200}
        />
      </div>

      <div>
        <label htmlFor="content" className="label">
          Memory Content
        </label>
        <textarea
          id="content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          required
          className="input-field min-h-[200px] resize-y"
          placeholder="Write about a moment, a conversation, a habit, anything that captures who they are..."
        />
        <p className="mt-1 text-xs text-gray-500">
          Be specific and detailed. These memories help the AI understand and
          emulate the person.
        </p>
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
          {loading ? 'Saving...' : 'Add Memory'}
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
