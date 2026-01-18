'use client';

import React, { useEffect, useState } from 'react';

interface UpdateStatusProps {
  lastUpdatedAt?: number;
  refreshIntervalMs?: number;
  isFetching?: boolean;
  className?: string;
}

const ONE_MINUTE_MS = 60 * 1000;

const formatDuration = (ms: number) => {
  if (ms <= 0) return 'soon';
  const totalMinutes = Math.round(ms / ONE_MINUTE_MS);
  if (totalMinutes < 1) return '1m';
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours > 0) {
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  }
  return `${totalMinutes}m`;
};

const formatRelative = (ms: number) => {
  if (ms < ONE_MINUTE_MS) return 'just now';
  const totalMinutes = Math.round(ms / ONE_MINUTE_MS);
  if (totalMinutes < 60) return `${totalMinutes}m ago`;
  const hours = Math.floor(totalMinutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

const UpdateStatus: React.FC<UpdateStatusProps> = ({
  lastUpdatedAt,
  refreshIntervalMs,
  isFetching,
  className = ''
}) => {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), ONE_MINUTE_MS);
    return () => clearInterval(id);
  }, []);

  if (!lastUpdatedAt) return null;

  const lastUpdatedLabel = formatRelative(now - lastUpdatedAt);
  let nextUpdateLabel: string | null = null;

  if (refreshIntervalMs) {
    const nextDelta = lastUpdatedAt + refreshIntervalMs - now;
    nextUpdateLabel = nextDelta <= 0
      ? 'next update soon'
      : `next update in ${formatDuration(nextDelta)}`;
  }

  return (
    <div className={`text-xs ${className} flex flex-wrap items-center gap-2`}>
      <span>Last updated {lastUpdatedLabel}</span>
      {nextUpdateLabel && <span>| {nextUpdateLabel}</span>}
      {isFetching && <span className="text-blue-400">Refreshing...</span>}
    </div>
  );
};

export default UpdateStatus;
