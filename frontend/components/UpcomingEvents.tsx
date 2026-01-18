"use client";

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Calendar, TrendingUp, AlertTriangle, DollarSign, Building2, Rocket, Loader2, AlertCircle } from 'lucide-react';
import { getUpcomingEvents, type CalendarEvent } from '@/lib/api';

interface UpcomingEventsProps {
  daysAhead?: number;
  maxItems?: number;
}

const UpcomingEvents: React.FC<UpcomingEventsProps> = ({
  daysAhead = 30,
  maxItems
}) => {
  const [selectedType, setSelectedType] = useState<string>('ALL');

  // Fetch upcoming events from API
  const { data, isLoading, error } = useQuery({
    queryKey: ['upcoming-events', daysAhead],
    queryFn: () => getUpcomingEvents(daysAhead),
    staleTime: 1000 * 60 * 60, // 1 hour
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Calendar className="w-7 h-7 text-purple-500" />
            Upcoming Events
          </h2>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-28 bg-slate-800/50 rounded-lg animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-6 h-6 text-red-400" />
          <div>
            <h3 className="font-semibold text-red-300">Error loading events</h3>
            <p className="text-sm text-red-400">
              {error instanceof Error ? error.message : 'Failed to fetch calendar events'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const events = data?.data || [];

  const eventTypes = [
    { value: 'ALL', label: 'All Events', icon: Calendar, color: 'blue' },
    { value: 'EARNINGS', label: 'Earnings', icon: DollarSign, color: 'green' },
    { value: 'FDA', label: 'FDA Decisions', icon: AlertTriangle, color: 'red' },
    { value: 'FED', label: 'Fed Events', icon: Building2, color: 'purple' },
    { value: 'IPO', label: 'IPOs', icon: Rocket, color: 'orange' },
  ];

  const getEventIcon = (type: string) => {
    const iconMap: Record<string, any> = {
      EARNINGS: DollarSign,
      FDA: AlertTriangle,
      FED: Building2,
      IPO: Rocket,
      CONFERENCE: TrendingUp,
      DIVIDEND: DollarSign,
    };
    const Icon = iconMap[type] || Calendar;
    return <Icon className="w-5 h-5" />;
  };

  const getEventColor = (type: string) => {
    const colorMap: Record<string, string> = {
      EARNINGS: 'bg-green-500/20 text-green-300 border-green-500/30',
      FDA: 'bg-red-500/20 text-red-300 border-red-500/30',
      FED: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      IPO: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
      CONFERENCE: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
      DIVIDEND: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    };
    return colorMap[type] || 'bg-slate-500/20 text-slate-300 border-slate-500/30';
  };

  const getImpactColor = (impact: string) => {
    const colorMap: Record<string, string> = {
      HIGH: 'bg-red-500/30 text-red-300',
      MEDIUM: 'bg-yellow-500/30 text-yellow-300',
      LOW: 'bg-green-500/30 text-green-300',
    };
    return colorMap[impact] || 'bg-slate-500/30 text-slate-300';
  };

  const formatDate = (dateStr: string): string => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const eventDate = new Date(dateStr);
    eventDate.setHours(0, 0, 0, 0);

    const diffTime = eventDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays < 7) return `In ${diffDays} days`;

    return eventDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const filteredEvents = selectedType === 'ALL'
    ? events
    : events.filter((event: CalendarEvent) => event.eventType === selectedType);

  // Limit number of events if maxItems is specified
  const limitedEvents = maxItems ? filteredEvents.slice(0, maxItems) : filteredEvents;

  // Group events by date
  const groupedEvents = limitedEvents.reduce((acc, event) => {
    const dateKey = new Date(event.date).toDateString();
    if (!acc[dateKey]) {
      acc[dateKey] = [];
    }
    acc[dateKey].push(event);
    return acc;
  }, {} as Record<string, CalendarEvent[]>);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Calendar className="w-7 h-7 text-purple-500" />
          Upcoming Events
        </h2>
        <div className="text-sm text-slate-400">
          Next {daysAhead} days
        </div>
      </div>

      {/* Filter Buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        {eventTypes.map((type) => {
          const Icon = type.icon;
          return (
            <button
              key={type.value}
              onClick={() => setSelectedType(type.value)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                selectedType === type.value
                  ? `bg-${type.color}-500 text-white shadow-lg`
                  : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700/50'
              }`}
            >
              <Icon className="w-4 h-4" />
              {type.label}
            </button>
          );
        })}
      </div>

      {/* Events Calendar */}
      <div className="space-y-6 max-h-[800px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-slate-900">
        {Object.entries(groupedEvents)
          .sort(([dateA], [dateB]) => new Date(dateA).getTime() - new Date(dateB).getTime())
          .map(([dateKey, dayEvents]) => (
            <div key={dateKey}>
              {/* Date Header */}
              <div className="flex items-center gap-3 mb-3">
                <div className="h-px flex-1 bg-gradient-to-r from-transparent via-slate-700 to-transparent"></div>
                <div className="px-4 py-2 bg-slate-800/80 rounded-lg border border-slate-700/50">
                  <div className="text-sm font-semibold text-slate-300">
                    {formatDate(dayEvents[0].date)}
                  </div>
                  <div className="text-xs text-slate-500">
                    {new Date(dayEvents[0].date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
                  </div>
                </div>
                <div className="h-px flex-1 bg-gradient-to-r from-slate-700 via-transparent to-transparent"></div>
              </div>

              {/* Events for this date */}
              <div className="space-y-3">
                {dayEvents.map((event, idx) => (
                  <div
                    key={`${event.date}-${event.ticker}-${idx}`}
                    className="bg-slate-800/50 backdrop-blur-sm rounded-lg border border-slate-700/50 hover:border-slate-600 transition-all hover:shadow-lg hover:shadow-slate-900/50 p-4 cursor-pointer group"
                  >
                    <div className="flex items-start gap-4">
                      {/* Event Icon */}
                      <div className={`flex-shrink-0 w-12 h-12 rounded-lg border flex items-center justify-center ${getEventColor(event.eventType)}`}>
                        {getEventIcon(event.eventType)}
                      </div>

                      {/* Event Details */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              {event.ticker && (
                                <span className="font-bold text-white px-3 py-1 bg-slate-700/50 rounded-md">
                                  {event.ticker}
                                </span>
                              )}
                              <span className={`text-xs px-2 py-1 rounded-md border ${getEventColor(event.eventType)}`}>
                                {event.eventType}
                              </span>
                            </div>
                            <h3 className="text-white font-semibold text-lg mb-1 group-hover:text-blue-400 transition-colors">
                              {event.company || event.ticker || event.eventType}
                            </h3>
                            <p className="text-slate-400 text-sm">
                              {event.description}
                            </p>
                          </div>

                          <div className="flex flex-col items-end gap-2">
                            <span className={`px-3 py-1 rounded-md text-xs font-semibold ${getImpactColor(event.expectedImpact)}`}>
                              {event.expectedImpact} IMPACT
                            </span>
                            {event.time && (
                              <span className="text-slate-400 text-xs whitespace-nowrap">
                                {event.time}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
      </div>

      {limitedEvents.length === 0 && (
        <div className="text-center py-12">
          <Calendar className="w-16 h-16 text-slate-700 mx-auto mb-4" />
          <p className="text-slate-400">No events found for the selected filter</p>
        </div>
      )}
    </div>
  );
};

export default UpcomingEvents;
